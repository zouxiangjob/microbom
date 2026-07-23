import uuid
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.database.session import get_db
from app.services.graph import AsyncGraphCrudEngine
from app.models.base import ObjectModel
# 导入你的多态关系业务模型
from app.models.business import BOMRelation, PartDocRelation, PartDrawingRelation

router = APIRouter()

# 统一维护的 URL 文本到真实关系 Python 类的映射
RELATION_TYPE_MAPPER = {
    "bom": BOMRelation,
    "cad_ref": PartDrawingRelation,
    "doc_ref": PartDocRelation
}


# --- Pydantic 校验模型 ---
class RelationCreateSchema(BaseModel):
    source_id: uuid.UUID = Field(..., description="起点节点 UUID")
    target_id: uuid.UUID = Field(..., description="终点节点 UUID")
    properties: Dict[str, Any] = Field(default_factory=dict, description="关系的属性（如数量、单重、图号位置）")


class RelationUpdateSchema(BaseModel):
    properties: Dict[str, Any] = Field(..., description="增量合并修改关系的属性")


class RelationResponseSchema(BaseModel):
    id: uuid.UUID
    relation_type: str
    source_id: uuid.UUID
    target_id: uuid.UUID
    properties: Dict[str, Any]

    class Config:
        from_attributes = True


# --- 动态拓扑网关系增删改查路由 ---

@router.post("/{relation_type}", response_model=RelationResponseSchema, status_code=201,
             summary="建立节点之间的拓扑关系边")
async def create_relation(
        payload: RelationCreateSchema,
        relation_type: str = Path(..., description="可选值: bom, cad_ref, doc_ref"),
        db: AsyncSession = Depends(get_db)
):
    if relation_type not in RELATION_TYPE_MAPPER:
        raise HTTPException(status_code=400, detail=f"不支持的关系拓扑类型: {relation_type}")

    # 安全性检查：强体验设计，确保连线的两个端点在数据库里确实存在
    source_node = await db.get(ObjectModel, payload.source_id)
    target_node = await db.get(ObjectModel, payload.target_id)
    if not source_node or not target_node:
        raise HTTPException(status_code=404, detail="无法织网：指定的起点或终点节点在数据库中不存在")

    model_cls = RELATION_TYPE_MAPPER[relation_type]
    new_edge = model_cls(
        source_id=payload.source_id,
        target_id=payload.target_id,
        properties=payload.properties
    )
    return await AsyncGraphCrudEngine.create_relation(db, new_edge)


@router.get("/{relation_type}", response_model=List[RelationResponseSchema], summary="过滤和检索图谱关系列表")
async def query_relations(
        relation_type: str = Path(...),
        source_id: Optional[uuid.UUID] = Query(None, description="过滤特定起点发出的边"),
        target_id: Optional[uuid.UUID] = Query(None, description="过滤特定终点接收的边"),
        db: AsyncSession = Depends(get_db)
):
    if relation_type not in RELATION_TYPE_MAPPER:
        raise HTTPException(status_code=400, detail="不支持的关系类型")

    model_cls = RELATION_TYPE_MAPPER[relation_type]
    return await AsyncGraphCrudEngine.query_relations(db, model_cls, source_id, target_id)


@router.put("/{relation_type}/{edge_id}", response_model=RelationResponseSchema, summary="修改关系线上的业务属性")
async def update_relation_properties(
        edge_id: uuid.UUID,
        payload: RelationUpdateSchema,
        relation_type: str = Path(...),
        db: AsyncSession = Depends(get_db)
):
    if relation_type not in RELATION_TYPE_MAPPER:
        raise HTTPException(status_code=400, detail="不支持的关系类型")

    model_cls = RELATION_TYPE_MAPPER[relation_type]
    edge = await AsyncGraphCrudEngine.get_relation_by_id(db, model_cls, edge_id)
    if not edge:
        raise HTTPException(status_code=404, detail="目标关系连接不存在")

    return await AsyncGraphCrudEngine.update_relation_properties(db, edge, payload.properties)


@router.delete("/{relation_type}/{edge_id}", summary="斩断单条图谱关系边")
async def delete_relation(
        edge_id: uuid.UUID,
        relation_type: str = Path(...),
        db: AsyncSession = Depends(get_db)
):
    if relation_type not in RELATION_TYPE_MAPPER:
        raise HTTPException(status_code=400, detail="不支持的关系类型")

    model_cls = RELATION_TYPE_MAPPER[relation_type]
    edge = await AsyncGraphCrudEngine.get_relation_by_id(db, model_cls, edge_id)
    if not edge:
        raise HTTPException(status_code=404, detail="关系不存在或已被删除")

    await AsyncGraphCrudEngine.delete_relation(db, edge)
    return {"status": "success", "detail": f"关系边 {edge_id} 已成功删除，两端节点未受任何影响"}
