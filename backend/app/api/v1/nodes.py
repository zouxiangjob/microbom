import uuid
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.database.session import get_db
from app.services.graph import AsyncGraphCrudEngine
# 导入你的多态实体业务模型
from app.models.business import PartModel, DocumentModel, DrawingModel, AttachmentModel

router = APIRouter()

# 统一维护的 URL 文本到真实 Python 类的映射
NODE_TYPE_MAPPER = {
    "part": PartModel,
    "document": DocumentModel,
    "drawing": DrawingModel,
    "attachment": AttachmentModel
}


# --- Pydantic 校验模型 ---
class NodeCreateUpdateSchema(BaseModel):
    properties: Dict[str, Any] = Field(default_factory=dict, description="业务自定义的非结构化属性")


class NodeResponseSchema(BaseModel):
    id: uuid.UUID
    object_type: str
    properties: Dict[str, Any]

    class Config:
        from_attributes = True  # 完美支持从 SQLAlchemy ORM 模型自动转换


# --- 动态数据增删改查路由 ---

@router.post("/{object_type}", response_model=NodeResponseSchema, status_code=201,
             summary="动态创建任意类型的业务对象节点")
async def create_node(
        payload: NodeCreateUpdateSchema,
        object_type: str = Path(..., description="节点类型，可选值: part, document, drawing, attachment"),
        db: AsyncSession = Depends(get_db)
):
    if object_type not in NODE_TYPE_MAPPER:
        raise HTTPException(status_code=400, detail=f"系统无法识别的节点对象类型: {object_type}")

    model_cls = NODE_TYPE_MAPPER[object_type]
    new_node = model_cls(properties=payload.properties)
    return await AsyncGraphCrudEngine.create_node(db, new_node)


@router.get("/{object_type}/{node_id}", response_model=NodeResponseSchema, summary="动态精准读取任意业务对象节点")
async def get_node(
        node_id: uuid.UUID = Path(..., description="节点的 UUID"),
        object_type: str = Path(..., description="节点类型"),
        db: AsyncSession = Depends(get_db)
):
    if object_type not in NODE_TYPE_MAPPER:
        raise HTTPException(status_code=400, detail="不合法的对象类型")

    model_cls = NODE_TYPE_MAPPER[object_type]
    node = await AsyncGraphCrudEngine.get_node_by_id(db, model_cls, node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"未找到指定的 {object_type} 节点实体")
    return node


@router.get("/{object_type}", response_model=List[NodeResponseSchema], summary="分类分页列表查询")
async def list_nodes_by_type(
        object_type: str = Path(...),
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
        db: AsyncSession = Depends(get_db)
):
    if object_type not in NODE_TYPE_MAPPER:
        raise HTTPException(status_code=400, detail="不合法的对象类型")

    model_cls = NODE_TYPE_MAPPER[object_type]
    return await AsyncGraphCrudEngine.query_nodes_by_type(db, model_cls, limit, offset)


@router.put("/{object_type}/{node_id}", response_model=NodeResponseSchema, summary="增量更新业务对象节点的非结构化属性")
async def update_node_properties(
        node_id: uuid.UUID,
        payload: NodeCreateUpdateSchema,
        object_type: str = Path(...),
        db: AsyncSession = Depends(get_db)
):
    if object_type not in NODE_TYPE_MAPPER:
        raise HTTPException(status_code=400, detail="不合法的对象类型")

    model_cls = NODE_TYPE_MAPPER[object_type]
    node = await AsyncGraphCrudEngine.get_node_by_id(db, model_cls, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="目标节点不存在，无法更新")

    return await AsyncGraphCrudEngine.update_node_properties(db, node, payload.properties)


@router.delete("/{object_type}/{node_id}", summary="物理级联删除业务节点")
async def delete_node(
        node_id: uuid.UUID,
        object_type: str = Path(...),
        db: AsyncSession = Depends(get_db)
):
    if object_type not in NODE_TYPE_MAPPER:
        raise HTTPException(status_code=400, detail="不合法的对象类型")

    model_cls = NODE_TYPE_MAPPER[object_type]
    node = await AsyncGraphCrudEngine.get_node_by_id(db, model_cls, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="目标节点不存在或已被删除")

    await AsyncGraphCrudEngine.delete_node(db, node)
    return {"status": "success", "detail": f"节点 {node_id} 及其所有关联的关系线已成功级联清理"}
