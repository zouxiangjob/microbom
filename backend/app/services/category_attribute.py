"""
分类属性定义服务：专用表 CRUD 与载荷校验。
"""
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category_attribute import CategoryAttributeDef

# 合法属性类型
VALUE_TYPES = {"string", "number", "boolean", "enum", "date", "text"}


def validate_attr_payload(value_type: str, options: Optional[List[str]]) -> Optional[str]:
    """校验属性定义载荷，返回错误信息；通过返回 None。"""
    if value_type not in VALUE_TYPES:
        return f"非法属性类型 [{value_type}]，可选值: {', '.join(sorted(VALUE_TYPES))}"
    if value_type == "enum" and (not options):
        return "enum 类型必须提供非空的 options 候选值"
    return None


async def create_attr_def(
        db: AsyncSession,
        *,
        category_id: uuid.UUID,
        attr_key: str,
        attr_label: str,
        value_type: str = "string",
        required: bool = False,
        default_value: Optional[Any] = None,
        options: Optional[List[str]] = None,
        unit: Optional[str] = None,
        sort_order: int = 0,
) -> CategoryAttributeDef:
    """为某分类新增一条属性定义。"""
    defn = CategoryAttributeDef(
        category_id=category_id,
        attr_key=attr_key,
        attr_label=attr_label,
        value_type=value_type,
        required=required,
        default_value=default_value,
        options=options,
        unit=unit,
        sort_order=sort_order,
    )
    db.add(defn)
    await db.commit()
    await db.refresh(defn)
    return defn


async def list_attr_defs(db: AsyncSession, category_id: uuid.UUID) -> List[CategoryAttributeDef]:
    """按分类查询其全部属性定义，按 sort_order 排序。"""
    stmt = (
        select(CategoryAttributeDef)
        .where(CategoryAttributeDef.category_id == category_id, CategoryAttributeDef.is_deleted == False)
        .order_by(CategoryAttributeDef.sort_order, CategoryAttributeDef.created_at)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_attr_def(db: AsyncSession, attr_id: uuid.UUID) -> Optional[CategoryAttributeDef]:
    """按 ID 查询单条属性定义（软删视为不存在）。"""
    defn = await db.get(CategoryAttributeDef, attr_id)
    if defn is None or defn.is_deleted:
        return None
    return defn


async def update_attr_def(
        db: AsyncSession,
        attr_id: uuid.UUID,
        updates: Dict[str, Any],
) -> CategoryAttributeDef:
    """增量更新属性定义；合并后重新校验，非法则抛 ValueError。"""
    defn = await db.get(CategoryAttributeDef, attr_id)
    if not defn:
        raise ValueError(f"属性定义 [{attr_id}] 不存在")

    # 合并后校验：value_type 与 options 取「更新值或当前值」
    merged_type = updates.get("value_type", defn.value_type)
    merged_options = updates.get("options", defn.options)
    err = validate_attr_payload(merged_type, merged_options)
    if err:
        raise ValueError(err)

    for key, value in updates.items():
        if value is not None:
            setattr(defn, key, value)

    await db.commit()
    await db.refresh(defn)
    return defn


async def delete_attr_def(db: AsyncSession, attr_id: uuid.UUID) -> bool:
    """软删除单条属性定义，成功返回 True，不存在或已删除返回 False。"""
    defn = await db.get(CategoryAttributeDef, attr_id)
    if not defn or defn.is_deleted:
        return False
    defn.is_deleted = True
    await db.commit()
    return True


async def build_part_attribute_schema(db: AsyncSession, part_id: uuid.UUID) -> Optional[Dict[str, Any]]:
    """聚合：反查零件所属分类 → 拉该分类属性定义 → 合并当前 properties 值。

    返回 None 表示零件不存在或 object_type 不是 part。
    """
    from app.models.base import ObjectModel
    from app.models.business import CategoryPartRelationModel, PartModel
    from app.services.graph import AsyncGraphCrudEngine

    part = await db.get(ObjectModel, part_id)
    if not isinstance(part, PartModel) or part.is_deleted:
        return None

    props = part.properties or {}

    # 反查分类：category_part_relation（分类 -> 零件）；一个零件理论上可挂多个分类，暂取第一个
    relations = await AsyncGraphCrudEngine.query_relations(
        db, CategoryPartRelationModel, target_id=part_id
    )
    category_id = relations[0].source_id if relations else None

    category_name = ""
    if category_id:
        category = await db.get(ObjectModel, category_id)
        if category and not category.is_deleted:
            category_name = (category.properties or {}).get("name", "")

    defs = await list_attr_defs(db, category_id) if category_id else []

    attributes: List[Dict[str, Any]] = []
    for d in defs:
        has_value = d.attr_key in props
        value = props.get(d.attr_key)
        if value is None and not has_value:
            value = d.default_value
        attributes.append({
            "id": d.id,
            "attr_key": d.attr_key,
            "attr_label": d.attr_label,
            "value_type": d.value_type,
            "required": d.required,
            "default_value": d.default_value,
            "options": d.options,
            "unit": d.unit,
            "sort_order": d.sort_order,
            "value": value,
            "has_value": has_value,
        })

    return {
        "part_id": part.id,
        "part_number": props.get("part_number", ""),
        "category_id": category_id,
        "category_name": category_name,
        "attributes": attributes,
    }
