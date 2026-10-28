"""
针对本轮修复的集成测试：覆盖真实 SQLite 事务路径（非纯函数）。

被测修复：
1. overwrite 拓扑重写不再误删非 BOM 关系
2. 文件上传不再污染 lifecycle 状态机（status 不被写成 "ready"）
3. 数据完整性：part_number 唯一 + 关系边端点类型约束
4. 顺序编码器原子发号（并发去重）
5. 上传逻辑去重后 file_service 核心可被 API / 视图两条通道复用
"""
import asyncio
import os
import uuid
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.base import Base, FileModel
from app.models.business import (
    AttachmentModel,
    BOMRelation,
    CategoryNodeModel,
    CategoryPartRelationModel,
    CategoryRelationModel,
    DocumentModel,
    DrawingModel,
    PartDocRelation,
    PartDrawingRelation,
    PartModel,
)
from app.services.category_encoder import create_encoder, generate_code, get_encoder_by_category
from app.services.file_service import save_physical_file, store_file_contents
from app.services.graph import AsyncGraphCrudEngine
from app.api.v1.nodes import NodeCreateUpdateSchema, create_node, update_node_properties
from app.api.v1.relations import create_relation
from app.schemas.graph_batch import (
    BatchNodeItem,
    BatchRelationItem,
    GraphBatchCreateRequest,
    GraphTopologyOverwriteRequest,
    OverwriteNodeItem,
    OverwriteRelationItem,
    RelationCreateSchema,
)

# 与路由层一致的模型映射（服务方法以参数注入，测试内自建便于隔离）
NODE_MAPPER = {
    "part": PartModel,
    "document": DocumentModel,
    "drawing": DrawingModel,
    "attachment": AttachmentModel,
    "category": CategoryNodeModel,
}
EDGE_MAPPER = {
    "bom": BOMRelation,
    "bom_relation": BOMRelation,
    "cad_ref": PartDrawingRelation,
    "part_drawing_relation": PartDrawingRelation,
    "doc_ref": PartDocRelation,
    "part_doc_relation": PartDocRelation,
    "category_relation": CategoryRelationModel,
    "category_part_relation": CategoryPartRelationModel,
}


@pytest.fixture()
def db(tmp_path: Path):
    """为每个测试创建隔离的临时 SQLite 引擎 + 会话工厂（含外键/WAL/超时 PRAGMA）。"""
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA busy_timeout=5000;")
        cursor.close()

    factory = async_sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return engine, factory


def _run(engine, coro):
    """同一事件循环内：建表 -> 运行场景 -> 释放引擎，返回场景结果。"""

    async def _scenario():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        try:
            return await coro
        finally:
            await engine.dispose()

    return asyncio.run(_scenario())


# ==============================================================================
# 1. overwrite 拓扑重写：不误删非 BOM 关系
# ==============================================================================

def test_overwrite_preserves_non_bom_edges(db):
    engine, factory = db

    async def scenario():
        async with factory() as s:
            root = PartModel(object_type="part", properties={"part_number": "ASM-1", "name": "总成"})
            child = PartModel(object_type="part", properties={"part_number": "WD-1", "name": "减速机"})
            doc = DocumentModel(object_type="document", properties={"name": "工艺卡"})
            s.add_all([root, child, doc])
            await s.flush()

            # 从根节点发出的 BOM 边 + 文档边
            s.add(BOMRelation(relation_type="bom_relation", source_id=root.id, target_id=child.id,
                              properties={"quantity": 2}))
            s.add(PartDocRelation(relation_type="part_doc_relation", source_id=root.id, target_id=doc.id,
                                  properties={}))
            await s.commit()

            new_child = PartModel(object_type="part", properties={"part_number": "WD-2", "name": "电机"})
            s.add(new_child)
            await s.flush()

            payload = GraphTopologyOverwriteRequest(
                root_id=root.id,
                nodes=[OverwriteNodeItem(id=new_child.id, object_type="part", properties=new_child.properties)],
                relations=[OverwriteRelationItem(relation_type="bom_relation", target_id=new_child.id,
                                                 properties={"quantity": 1})],
            )
            purged, inserted = await AsyncGraphCrudEngine.overwrite_graph_topology(
                db=s, node_mappers=NODE_MAPPER, edge_mappers=EDGE_MAPPER, batch_data=payload
            )

            doc_rels = (await s.execute(
                select(PartDocRelation).where(PartDocRelation.source_id == root.id)
            )).scalars().all()
            bom_rels = (await s.execute(
                select(BOMRelation).where(BOMRelation.source_id == root.id)
            )).scalars().all()
            return purged, inserted, len(doc_rels), len(bom_rels), str(bom_rels[0].target_id), str(new_child.id)

    purged, inserted, doc_count, bom_count, bom_target, new_child_id = _run(engine, scenario())
    assert purged == 1          # 只清理了旧 BOM 边
    assert inserted == 1        # 写入新 BOM 边
    assert doc_count == 1       # 文档边未被误删
    assert bom_count == 1       # BOM 边只剩新的一条
    assert bom_target == new_child_id


# ==============================================================================
# 2/3. part_number 唯一性（单条 + 批量）
# ==============================================================================

def test_create_node_route_rejects_duplicate_part_number(db):
    engine, factory = db

    async def scenario():
        async with factory() as s:
            s.add(PartModel(object_type="part", properties={"part_number": "P-DUP"}))
            await s.commit()
            with pytest.raises(HTTPException) as exc:
                await create_node(
                    payload=NodeCreateUpdateSchema(properties={"part_number": "P-DUP"}),
                    object_type="part", db=s, _user=None,
                )
            return exc.value.status_code, exc.value.detail

    status_code, detail = _run(engine, scenario())
    assert status_code == 422
    assert "重复" in detail


def test_update_node_route_excludes_self_and_rejects_others(db):
    engine, factory = db

    async def scenario():
        async with factory() as s:
            p1 = PartModel(object_type="part", properties={"part_number": "P-A"})
            p2 = PartModel(object_type="part", properties={"part_number": "P-B"})
            s.add_all([p1, p2])
            await s.commit()
            await s.refresh(p1)

            # 改成他人已占用的编码 -> 拒绝
            with pytest.raises(HTTPException) as exc:
                await update_node_properties(
                    node_id=p1.id,
                    payload=NodeCreateUpdateSchema(properties={"part_number": "P-B"}),
                    object_type="part", db=s, _user=None,
                )
            assert exc.value.status_code == 422

            # 保持自身编码不变（仅改名）-> 放行
            await update_node_properties(
                node_id=p1.id,
                payload=NodeCreateUpdateSchema(properties={"name": "改名"}),
                object_type="part", db=s, _user=None,
            )
            await s.refresh(p1)
            return p1.properties.get("name")

    assert _run(engine, scenario()) == "改名"


def test_batch_create_rejects_duplicate_part_number_in_batch(db):
    engine, factory = db

    async def scenario():
        async with factory() as s:
            payload = GraphBatchCreateRequest(
                nodes=[
                    BatchNodeItem(id=uuid.uuid4(), object_type="part", properties={"part_number": "P-1"}),
                    BatchNodeItem(id=uuid.uuid4(), object_type="part", properties={"part_number": "P-1"}),
                ],
                relations=[],
            )
            with pytest.raises(ValueError) as exc:
                await AsyncGraphCrudEngine.create_graph_batch(
                    db=s, node_mappers=NODE_MAPPER, edge_mappers=EDGE_MAPPER, batch_data=payload
                )
            return str(exc.value)

    msg = _run(engine, scenario())
    assert "重复" in msg and "P-1" in msg


def test_batch_create_rejects_existing_part_number(db):
    engine, factory = db

    async def scenario():
        async with factory() as s:
            s.add(PartModel(object_type="part", properties={"part_number": "P-EXIST"}))
            await s.commit()
            payload = GraphBatchCreateRequest(
                nodes=[BatchNodeItem(id=uuid.uuid4(), object_type="part",
                                     properties={"part_number": "P-EXIST"})],
                relations=[],
            )
            with pytest.raises(ValueError) as exc:
                await AsyncGraphCrudEngine.create_graph_batch(
                    db=s, node_mappers=NODE_MAPPER, edge_mappers=EDGE_MAPPER, batch_data=payload
                )
            return str(exc.value)

    msg = _run(engine, scenario())
    assert "已存在" in msg


# ==============================================================================
# 3b. 关系边端点类型约束（单条 + 批量）
# ==============================================================================

def test_create_relation_rejects_wrong_endpoint_types(db):
    engine, factory = db

    async def scenario():
        async with factory() as s:
            doc = DocumentModel(object_type="document", properties={"name": "文档"})
            drawing = DrawingModel(object_type="drawing", properties={"name": "图档"})
            s.add_all([doc, drawing])
            await s.flush()
            # document -> drawing 不能作为 BOM 边
            with pytest.raises(HTTPException) as exc:
                await create_relation(
                    payload=RelationCreateSchema(source_id=doc.id, target_id=drawing.id, properties={}),
                    relation_type="bom", db=s, _user=None,
                )
            return exc.value.status_code, exc.value.detail

    code, detail = _run(engine, scenario())
    assert code == 422
    assert "不允许" in detail


def test_batch_create_rejects_wrong_endpoint_types(db):
    engine, factory = db

    async def scenario():
        async with factory() as s:
            part = PartModel(object_type="part", properties={"part_number": "P-1"})
            drawing = DrawingModel(object_type="drawing", properties={"name": "图档"})
            s.add_all([part, drawing])
            await s.flush()
            payload = GraphBatchCreateRequest(
                nodes=[],
                relations=[BatchRelationItem(relation_type="bom", source_id=drawing.id,
                                             target_id=part.id, properties={})],
            )
            with pytest.raises(ValueError) as exc:
                await AsyncGraphCrudEngine.create_graph_batch(
                    db=s, node_mappers=NODE_MAPPER, edge_mappers=EDGE_MAPPER, batch_data=payload
                )
            return str(exc.value)

    msg = _run(engine, scenario())
    assert "不允许" in msg


# ==============================================================================
# 4. 顺序编码器：并发发号去重 + 流水用尽回滚
# ==============================================================================

def test_sequence_encoder_concurrent_generate_is_unique(db):
    engine, factory = db

    async def scenario():
        async with factory() as s:
            enc = await create_encoder(s, category_id=uuid.uuid4(), encoder_type="sequence",
                                       prefix="WD-", start_seq=1, seq_length=4)
            cat_id = enc.category_id

        async def one(_):
            async with factory() as s2:
                return await generate_code(s2, cat_id)

        return await asyncio.gather(*[one(i) for i in range(10)])

    codes = _run(engine, scenario())
    assert len(set(codes)) == 10
    assert sorted(codes) == [f"WD-{i:04d}" for i in range(1, 11)]


def test_sequence_encoder_exhausted_rolls_back(db):
    engine, factory = db

    async def scenario():
        async with factory() as s:
            enc = await create_encoder(s, category_id=uuid.uuid4(), encoder_type="sequence",
                                       prefix="X-", start_seq=1, end_seq=1, seq_length=2)
            cat_id = enc.category_id

        async with factory() as s2:
            first = await generate_code(s2, cat_id)

        async with factory() as s3:
            with pytest.raises(ValueError):
                await generate_code(s3, cat_id)

        async with factory() as s4:
            enc2 = await get_encoder_by_category(s4, cat_id)
            return first, enc2.current_seq

    first, current_seq = _run(engine, scenario())
    assert first == "X-01"
    assert current_seq == 1  # 超限后流水号已回滚，未被误增


# ==============================================================================
# 2/5. 上传：不污染状态机 + 覆盖时清理旧文件 + 适配器复用
# ==============================================================================

def test_store_file_contents_no_status_pollution_and_overwrite_cleanup(db, monkeypatch, tmp_path):
    engine, factory = db
    monkeypatch.setattr("app.services.file_service.UPLOAD_DIR", str(tmp_path / "uploads"))

    async def scenario():
        async with factory() as s:
            drawing = DrawingModel(object_type="drawing", properties={"name": "图纸"})
            s.add(drawing)
            await s.flush()

            await store_file_contents(s, object_id=drawing.id, model_cls=DrawingModel,
                                      original_name="a.pdf", content_type="application/pdf", contents=b"AAAA")
            d1 = await s.get(DrawingModel, drawing.id)
            f1 = (await s.execute(select(FileModel).where(FileModel.object_id == drawing.id))).scalar_one()
            first_path = f1.absolute_path
            assert os.path.exists(first_path)
            assert d1.properties.get("file_status") == "ready"
            assert d1.properties.get("is_uploaded") is True
            assert "status" not in d1.properties  # 不再写 lifecycle 状态

            # 覆盖上传不同内容 -> 旧物理文件被清理，仅保留一条记录
            await store_file_contents(s, object_id=drawing.id, model_cls=DrawingModel,
                                      original_name="b.pdf", content_type="application/pdf", contents=b"BBBB")
            f2 = (await s.execute(select(FileModel).where(FileModel.object_id == drawing.id))).scalar_one()
            assert f2.absolute_path != first_path
            assert os.path.exists(f2.absolute_path)
            assert not os.path.exists(first_path)  # 旧文件已清理
            return f1.file_size, f2.file_size

    size1, size2 = _run(engine, scenario())
    assert size1 == 4 and size2 == 4


class _FakeUpload:
    """模拟 FastAPI UploadFile 的最小接口（.filename / .content_type / async read）。"""

    def __init__(self, name: str, content_type: str, data: bytes):
        self.filename = name
        self.content_type = content_type
        self._data = data

    async def read(self) -> bytes:
        return self._data


def test_save_physical_file_adapter_delegates(db, monkeypatch, tmp_path):
    engine, factory = db
    monkeypatch.setattr("app.services.file_service.UPLOAD_DIR", str(tmp_path / "uploads2"))

    async def scenario():
        async with factory() as s:
            doc = DocumentModel(object_type="document", properties={"name": "文档"})
            s.add(doc)
            await s.flush()
            fake = _FakeUpload("spec.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                               b"DOCDATA")
            db_file = await save_physical_file(s, fake, doc.id, DocumentModel)
            return db_file.original_name, db_file.object_id == doc.id, os.path.exists(db_file.absolute_path)

    name, is_same, exists = _run(engine, scenario())
    assert name == "spec.docx"
    assert is_same and exists


# ==============================================================================
# 2b. 历史脏数据 "ready" 状态可正常进入发布流程
# ==============================================================================

def test_legacy_ready_status_normalizes_to_draft(db):
    engine, factory = db

    async def scenario():
        async with factory() as s:
            part = PartModel(object_type="part", properties={"part_number": "P-READY", "status": "ready"})
            s.add(part)
            await s.commit()
            await s.refresh(part)

            # 历史 "ready" 应被归一化为 draft，从而允许 draft -> review
            await update_node_properties(
                node_id=part.id,
                payload=NodeCreateUpdateSchema(properties={"status": "review"}),
                object_type="part", db=s, _user=None,
            )
            await s.refresh(part)
            return part.properties.get("status")

    assert _run(engine, scenario()) == "review"
