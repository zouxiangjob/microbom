"""
发布基线服务层：BOM 结构深冻结、基线查询与双基线差异对比。
"""
import copy
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import ObjectModel, RelationModel
from app.models.baseline import Baseline, BaselineItem
from app.services.status import STATUS_RELEASED
from app.models.business import (
    BOMRelation,
    DocAttachmentRelation,
    DrawingAttachmentRelation,
    PartDocRelation,
    PartDrawingRelation,
)

# 快照白名单：BOM + 零件图纸 + 零件文档 + 图纸附件 + 文档附件
_SNAPSHOT_RELATION_TYPES = (
    BOMRelation.__mapper_args__["polymorphic_identity"],
    PartDrawingRelation.__mapper_args__["polymorphic_identity"],
    PartDocRelation.__mapper_args__["polymorphic_identity"],
    DrawingAttachmentRelation.__mapper_args__["polymorphic_identity"],
    DocAttachmentRelation.__mapper_args__["polymorphic_identity"],
)
# BOM 边标识（quantity 仅此类边有值）
_BOM_IDENTITY = BOMRelation.__mapper_args__["polymorphic_identity"]
# 根条目标识（无父、无边）
_ROOT_RELATION_TYPE = "root"

_MAX_DEPTH = 50  # 防御深环/死循环


# ==============================================================================
# 0. 字母版本号工具（Excel 列名式：A→…→Z→AA→AB→…）
# ==============================================================================

def _version_to_seq(ver: str) -> int:
    """字母版本号转序号：A=1, B=2, …, Z=26, AA=27, AB=28 …"""
    n = 0
    for ch in (ver or "").strip().upper():
        if ch.isalpha():
            n = n * 26 + (ord(ch) - ord("A") + 1)
    return n


def _seq_to_version(seq: int) -> str:
    """序号转字母版本号（bijective base-26）。"""
    s = ""
    while seq > 0:
        seq -= 1
        s = chr(ord("A") + seq % 26) + s
        seq //= 26
    return s


async def next_release_version(db: AsyncSession, root_id: uuid.UUID) -> str:
    """计算某根总成的下一个发布版本号：取其历史基线最大版本 + 1。"""
    result = await db.execute(
        select(Baseline.release_version).where(Baseline.root_object_id == root_id)
    )
    max_seq = max((_version_to_seq(row[0]) for row in result.all()), default=0)
    return _seq_to_version(max_seq + 1)


# ==============================================================================
# 1. 基线发布（冻结）
# ==============================================================================

async def create_baseline(
        db: AsyncSession,
        root_id: uuid.UUID,
        name: Optional[str] = None,
        release_version: Optional[str] = None,
        note: Optional[str] = None,
        created_by: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """以 root_id 为根总成，冻结其完整 BOM 树，生成一条不可变基线。

    未显式传 release_version 时，按该根总成历史基线自动递增（A→B→…→Z→AA→AB）；
    发布后同步把版本号写回根对象的 version 属性。
    """
    root = await db.get(ObjectModel, root_id)
    if not root:
        raise ValueError(f"基线发布失败：根对象 [{root_id}] 在系统中不存在")

    # 版本号自动递增 + 名称兜底
    if not release_version:
        release_version = await next_release_version(db, root_id)
    if not name:
        name = f"{release_version} 发布基线"

    # 发布后写回根对象版本，使零件"当前版本"始终等于最新发布版本；状态联动为已发布
    root_props = dict(root.properties) if root.properties else {}
    root_props["version"] = release_version
    if root_props.get("status") != STATUS_RELEASED:
        root_props["status"] = STATUS_RELEASED
    root.properties = root_props
    db.add(root)

    baseline = Baseline(
        name=name,
        release_version=release_version,
        root_object_id=root_id,
        status="released",
        note=note,
        created_by=created_by,
    )
    db.add(baseline)
    await db.flush()  # 先拿到 baseline.id

    # 冻结根节点（depth=0，无父级，无数量）
    db.add(BaselineItem(
        baseline_id=baseline.id,
        object_id=root.id,
        object_type=root.object_type,
        relation_type=_ROOT_RELATION_TYPE,
        properties=copy.deepcopy(root.properties or {}),
        parent_object_id=None,
        depth=0,
        quantity=None,
        edge_properties=None,
    ))

    # 一次性 CTE 递归收集全部 BOM 后代（仅 bom_relation 边，不混入图纸/文档等其它关系）
    rows = await _collect_snapshot_edges(db, root_id)
    for row in rows:
        edge_props = row["edge_properties"] if isinstance(row["edge_properties"], dict) else {}
        relation_type = row["relation_type"]
        db.add(BaselineItem(
            baseline_id=baseline.id,
            object_id=row["target_id"],
            object_type=row["object_type"],
            relation_type=relation_type,
            properties=copy.deepcopy(row["node_properties"] or {}),
            parent_object_id=row["source_id"],
            depth=row["depth"],
            quantity=_safe_qty(edge_props.get("quantity")) if relation_type == _BOM_IDENTITY else None,
            edge_properties=copy.deepcopy(edge_props),
        ))

    await db.commit()
    return await get_baseline(db, baseline.id)


async def _collect_snapshot_edges(db: AsyncSession, root_id: uuid.UUID) -> List[Dict[str, Any]]:
    """快照专用递归 CTE：沿白名单关系边（BOM/图纸/文档/附件）穿透，返回全部后代行。"""
    anchor = select(
        RelationModel.id,
        RelationModel.relation_type,
        RelationModel.source_id,
        RelationModel.target_id,
        RelationModel.properties.label("edge_properties"),
        literal_column("1").label("depth"),
    ).where(
        RelationModel.source_id == root_id,
        RelationModel.relation_type.in_(_SNAPSHOT_RELATION_TYPES),
    )

    cte = anchor.cte(name="baseline_snapshot_cte", recursive=True)

    recursive = select(
        RelationModel.id,
        RelationModel.relation_type,
        RelationModel.source_id,
        RelationModel.target_id,
        RelationModel.properties.label("edge_properties"),
        (cte.c.depth + 1).label("depth"),
    ).join(cte, RelationModel.source_id == cte.c.target_id).where(
        RelationModel.relation_type.in_(_SNAPSHOT_RELATION_TYPES),
        cte.c.depth < _MAX_DEPTH,
    )

    full = cte.union_all(recursive)

    stmt = select(
        full.c.relation_type,
        full.c.source_id,
        full.c.target_id,
        full.c.edge_properties,
        full.c.depth,
        ObjectModel.object_type,
        ObjectModel.properties.label("node_properties"),
    ).join(ObjectModel, ObjectModel.id == full.c.target_id)

    result = await db.execute(stmt)
    return [dict(row) for row in result.mappings().all()]


# ==============================================================================
# 2. 基线查询
# ==============================================================================

async def list_baselines(db: AsyncSession, root_id: Optional[uuid.UUID] = None) -> List[Dict[str, Any]]:
    """按时间倒序列出基线，可选按根总成过滤，附带条目数统计。"""
    stmt = select(Baseline).order_by(Baseline.created_at.desc())
    if root_id:
        stmt = stmt.where(Baseline.root_object_id == root_id)
    result = await db.execute(stmt)
    baselines = list(result.scalars().all())

    rows: List[Dict[str, Any]] = []
    if not baselines:
        return rows

    ids = [b.id for b in baselines]
    count_stmt = (
        select(BaselineItem.baseline_id, func.count(BaselineItem.id))
        .where(BaselineItem.baseline_id.in_(ids))
        .group_by(BaselineItem.baseline_id)
    )
    count_result = await db.execute(count_stmt)
    counts = {row[0]: row[1] for row in count_result.all()}

    for b in baselines:
        rows.append({
            "id": b.id,
            "name": b.name,
            "release_version": b.release_version,
            "root_object_id": b.root_object_id,
            "status": b.status,
            "note": b.note,
            "created_by": b.created_by,
            "created_at": b.created_at,
            "item_count": counts.get(b.id, 0),
        })
    return rows


async def get_baseline(db: AsyncSession, baseline_id: uuid.UUID) -> Optional[Dict[str, Any]]:
    """返回单条基线的元信息 + 完整冻结条目列表。"""
    loaded = await _load_items(db, baseline_id)
    if not loaded:
        return None
    h = loaded["header"]
    return {
        "id": h.id,
        "name": h.name,
        "release_version": h.release_version,
        "root_object_id": h.root_object_id,
        "status": h.status,
        "note": h.note,
        "created_by": h.created_by,
        "created_at": h.created_at,
        "items": loaded["items"],
    }


# ==============================================================================
# 3. 双基线差异对比
# ==============================================================================

async def diff_baselines(
        db: AsyncSession,
        baseline_a_id: uuid.UUID,
        baseline_b_id: uuid.UUID,
) -> Optional[Dict[str, Any]]:
    """对比两条基线：按 object_id 对齐，输出新增/删除/变更（数量、父级、属性）。"""
    a = await _load_items(db, baseline_a_id)
    b = await _load_items(db, baseline_b_id)
    if a is None or b is None:
        return None

    a_items = {it["object_id"]: it for it in a["items"]}
    b_items = {it["object_id"]: it for it in b["items"]}

    added: List[Dict[str, Any]] = []
    removed: List[Dict[str, Any]] = []
    changed: List[Dict[str, Any]] = []

    for oid, b_item in b_items.items():
        if oid not in a_items:
            added.append(_item_brief(b_item))
        else:
            diffs = _compare_items(a_items[oid], b_item)
            if diffs:
                changed.append({
                    "object_id": oid,
                    "part_number": _part_number(b_item["properties"]),
                    "changes": diffs,
                })

    for oid, a_item in a_items.items():
        if oid not in b_items:
            removed.append(_item_brief(a_item))

    unchanged = len(a_items) - len(removed) - len(changed)

    return {
        "baseline_a": _header_brief(a),
        "baseline_b": _header_brief(b),
        "summary": {
            "added": len(added),
            "removed": len(removed),
            "changed": len(changed),
            "unchanged": unchanged,
        },
        "added_items": added,
        "removed_items": removed,
        "changed_items": changed,
    }


# ==============================================================================
# 4. 内部工具函数
# ==============================================================================

async def _load_items(db: AsyncSession, baseline_id: uuid.UUID) -> Optional[Dict[str, Any]]:
    """加载基线头 + 按深度排序的冻结条目，转成规整字典。"""
    baseline = await db.get(Baseline, baseline_id)
    if not baseline:
        return None
    stmt = (
        select(BaselineItem)
        .where(BaselineItem.baseline_id == baseline_id)
        .order_by(BaselineItem.depth)
    )
    result = await db.execute(stmt)
    items = list(result.scalars().all())
    return {"header": baseline, "items": [_item_dict(it) for it in items]}


def _item_dict(it: BaselineItem) -> Dict[str, Any]:
    return {
        "object_id": it.object_id,
        "object_type": it.object_type,
        "relation_type": it.relation_type,
        "properties": it.properties,
        "parent_object_id": it.parent_object_id,
        "depth": it.depth,
        "quantity": it.quantity,
        "edge_properties": it.edge_properties,
    }


def _item_brief(it: Dict[str, Any]) -> Dict[str, Any]:
    """差异列表中的轻量条目摘要。"""
    return {
        "object_id": it["object_id"],
        "part_number": _part_number(it["properties"]),
        "object_type": it["object_type"],
        "relation_type": it["relation_type"],
        "depth": it["depth"],
        "quantity": it["quantity"],
    }


def _header_brief(loaded: Dict[str, Any]) -> Dict[str, Any]:
    h = loaded["header"]
    return {
        "id": h.id,
        "name": h.name,
        "release_version": h.release_version,
        "root_object_id": h.root_object_id,
    }


def _compare_items(a: Dict[str, Any], b: Dict[str, Any]) -> List[Dict[str, Any]]:
    """逐字段对比两个同 object_id 的冻结条目，返回变更明细。"""
    changes: List[Dict[str, Any]] = []
    if a["quantity"] != b["quantity"]:
        changes.append({"field": "quantity", "from": a["quantity"], "to": b["quantity"]})
    if a["parent_object_id"] != b["parent_object_id"]:
        changes.append({
            "field": "parent_object_id",
            "from": a["parent_object_id"],
            "to": b["parent_object_id"],
        })
    if a["object_type"] != b["object_type"]:
        changes.append({"field": "object_type", "from": a["object_type"], "to": b["object_type"]})
    if a["relation_type"] != b["relation_type"]:
        changes.append({"field": "relation_type", "from": a["relation_type"], "to": b["relation_type"]})
    if a["properties"] != b["properties"]:
        changes.append({"field": "properties", "from": a["properties"], "to": b["properties"]})

    # quantity 已作为独立列单独对比，这里剥离该键，避免同一变更重复上报
    a_edge = {k: v for k, v in (a["edge_properties"] or {}).items() if k != "quantity"}
    b_edge = {k: v for k, v in (b["edge_properties"] or {}).items() if k != "quantity"}
    if a_edge != b_edge:
        changes.append({
            "field": "edge_properties",
            "from": a_edge or None,
            "to": b_edge or None,
        })
    return changes


def _part_number(props: Optional[Dict[str, Any]]) -> str:
    if not props:
        return ""
    return props.get("part_number", "") or props.get("name", "") or ""


def _safe_qty(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return 1
