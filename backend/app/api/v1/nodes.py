import uuid
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.database.session import get_db
from app.api.deps import require_roles
from app.services.graph import AsyncGraphCrudEngine
from app.services.status import STATUS_DRAFT, ALL_STATUSES, is_valid_status, validate_transition
from app.models.business import PartModel, DocumentModel, DrawingModel, AttachmentModel, CategoryNodeModel

router = APIRouter()

# URL 文本到模型类的映射
NODE_TYPE_MAPPER = {
    "part": PartModel,
    "document": DocumentModel,
    "drawing": DrawingModel,
    "attachment": AttachmentModel,
    "category": CategoryNodeModel
}


# --- Pydantic 校验模型 ---
class NodeCreateUpdateSchema(BaseModel):
    properties: Dict[str, Any] = Field(default_factory=dict, description="业务自定义的非结构化属性")


class NodeResponseSchema(BaseModel):
    id: uuid.UUID
    object_type: str
    properties: Dict[str, Any]

    class Config:
        from_attributes = True  # 支持从 SQLAlchemy ORM 模型自动转换


# --- 动态数据增删改查路由 ---

@router.get("/search", response_model=List[NodeResponseSchema], summary="按类型模糊搜索对象")
async def search_nodes_endpoint(
        keyword: str = Query(..., min_length=1, description="模糊关键字"),
        object_type: Optional[str] = Query(None, description="可选值: part, document, drawing, attachment, category"),
        limit: int = Query(50, ge=1, le=200, description="返回条数上限"),
        db: AsyncSession = Depends(get_db)
):
    """对配置的 JSON 字段（如 part_number/name/spec/material）做模糊匹配，可选按类型过滤。"""
    if object_type and object_type not in NODE_TYPE_MAPPER:
        raise HTTPException(status_code=400, detail=f"不合法的对象类型: {object_type}")
    return await AsyncGraphCrudEngine.search_nodes(db, object_type, keyword, limit)


@router.post("/{object_type}", response_model=NodeResponseSchema, status_code=201,
             summary="创建任意类型的业务对象节点")
async def create_node(
        payload: NodeCreateUpdateSchema,
        object_type: str = Path(..., description="节点类型，可选值: part, document, drawing, attachment"),
        db: AsyncSession = Depends(get_db),
        _user=Depends(require_roles("admin", "engineer"))
):
    if object_type not in NODE_TYPE_MAPPER:
        raise HTTPException(status_code=400, detail=f"系统无法识别的节点对象类型: {object_type}")

    # 关键字段校验
    field_error = AsyncGraphCrudEngine.validate_required_fields(object_type, payload.properties)
    if field_error:
        raise HTTPException(status_code=422, detail=field_error)

    # 状态：缺省置 draft；显式指定则须为合法枚举
    props = dict(payload.properties)
    status_value = props.get("status")
    if not status_value:
        props["status"] = STATUS_DRAFT
    elif not is_valid_status(status_value):
        raise HTTPException(status_code=422, detail=f"非法状态值: {status_value}")

    # 零件编码唯一性校验（应用层）
    if object_type == "part":
        dup_err = await AsyncGraphCrudEngine.ensure_unique_part_number(db, props)
        if dup_err:
            raise HTTPException(status_code=422, detail=dup_err)

    model_cls = NODE_TYPE_MAPPER[object_type]
    new_node = model_cls(properties=props)
    return await AsyncGraphCrudEngine.create_node(db, new_node)


@router.get("/{object_type}/{node_id}", response_model=NodeResponseSchema, summary="读取任意业务对象节点")
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


@router.get("/{object_type}", response_model=List[NodeResponseSchema], summary="按类型分页列表查询")
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


@router.put("/{object_type}/{node_id}", response_model=NodeResponseSchema, summary="增量更新节点属性")
async def update_node_properties(
        node_id: uuid.UUID,
        payload: NodeCreateUpdateSchema,
        object_type: str = Path(...),
        db: AsyncSession = Depends(get_db),
        _user=Depends(require_roles("admin", "engineer"))
):
    if object_type not in NODE_TYPE_MAPPER:
        raise HTTPException(status_code=400, detail="不合法的对象类型")

    model_cls = NODE_TYPE_MAPPER[object_type]
    node = await AsyncGraphCrudEngine.get_node_by_id(db, model_cls, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="目标节点不存在，无法更新")

    # 状态转移校验
    if "status" in payload.properties:
        new_status = payload.properties["status"]
        old_status = (node.properties or {}).get("status", STATUS_DRAFT)
        # 兼容历史脏数据（如曾被写入 "ready"）：未知旧状态一律视为 draft 起点
        if old_status not in ALL_STATUSES:
            old_status = STATUS_DRAFT
        if not validate_transition(old_status, new_status):
            raise HTTPException(
                status_code=422,
                detail=f"非法状态转移: {old_status} -> {new_status}",
            )

    # 零件编码唯一性校验（改编码时排除自身）
    if object_type == "part" and "part_number" in payload.properties:
        dup_err = await AsyncGraphCrudEngine.ensure_unique_part_number(
            db, payload.properties, exclude_id=node.id
        )
        if dup_err:
            raise HTTPException(status_code=422, detail=dup_err)

    return await AsyncGraphCrudEngine.update_node_properties(db, node, payload.properties)


@router.delete("/{object_type}/{node_id}", summary="删除业务节点（级联删除关联关系）")
async def delete_node(
        node_id: uuid.UUID,
        object_type: str = Path(...),
        db: AsyncSession = Depends(get_db),
        _user=Depends(require_roles("admin", "engineer"))
):
    if object_type not in NODE_TYPE_MAPPER:
        raise HTTPException(status_code=400, detail="不合法的对象类型")

    model_cls = NODE_TYPE_MAPPER[object_type]
    node = await AsyncGraphCrudEngine.get_node_by_id(db, model_cls, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="目标节点不存在或已被删除")

    await AsyncGraphCrudEngine.delete_node(db, node)
    return {"status": "success", "detail": f"节点 {node_id} 及其所有关联关系已成功级联清理"}
