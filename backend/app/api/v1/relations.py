import uuid
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, ConfigDict
from starlette import status

from app.api.v1.nodes import NodeResponseSchema
from app.database.session import get_db
from app.api.deps import require_roles
from app.schemas.graph_batch import BatchCreatedResponse, GraphBatchCreateRequest, BatchUpdatedResponse, \
    GraphBatchUpdateRequest, ReverseTreeNodeSchema, OverwriteSuccessResponse, GraphTopologyOverwriteRequest

from app.schemas.graph_batch import RelationCreateSchema, RelationUpdateSchema, RelationResponseSchema

from app.services.graph import AsyncGraphCrudEngine
from app.models.base import ObjectModel
from app.models.business import BOMRelation, PartDocRelation, PartDrawingRelation, PartModel, DocumentModel, \
    DrawingModel, AttachmentModel, CategoryNodeModel, CategoryRelationModel, CategoryPartRelationModel

router = APIRouter()

# URL 文本到关系模型类的映射
RELATION_TYPE_MAPPER = {
    "bom": BOMRelation,
    "bom_relation": BOMRelation,
    "cad_ref": PartDrawingRelation,
    "part_drawing_relation": PartDrawingRelation,
    "doc_ref": PartDocRelation,
    "part_doc_relation": PartDocRelation,
    "category_relation": CategoryRelationModel,
    "category_part_relation": CategoryPartRelationModel
}


class TreeNodeSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    depth: int = Field(..., description="在依赖树中所处的层级，1 代表直属子件")
    edge: RelationResponseSchema = Field(..., description="关系边数据")
    target_node: NodeResponseSchema = Field(..., description="终点目标节点快照")


# --- 拓扑树穿透路由 ---

# 静态路径路由须注册在动态变量路径之前，避免被吞掉
@router.get("/nodes/{node_id}/tree", response_model=List[TreeNodeSchema],
            summary="正向穿透获取整棵多级 BOM/依赖拓扑树")
async def get_object_dependencies_tree(
        node_id: uuid.UUID = Path(..., description="根节点的 UUID"),
        max_depth: int = Query(5, ge=1, le=20, description="限制递归展开的最大深度"),
        db: AsyncSession = Depends(get_db)
):
    """传入根节点，使用单次递归 CTE 穿透获取整棵依赖树。"""
    root_node = await db.get(ObjectModel, node_id)
    if not root_node:
        raise HTTPException(status_code=404, detail="指定的拓扑根节点不存在")

    return await AsyncGraphCrudEngine.get_node_tree_by_cte(db, root_id=node_id, max_depth=max_depth)


# --- 拓扑树逆向穿透路由 ---

@router.get("/nodes/{node_id}/reverse-tree", response_model=List[ReverseTreeNodeSchema],
            summary="逆向追溯父级引用网络（Where-Used）")
async def get_object_where_used_tree(
        node_id: uuid.UUID = Path(..., description="需要逆向追溯的子节点 UUID"),
        max_depth: int = Query(5, ge=1, le=20, description="限制逆向追踪的最大深度"),
        db: AsyncSession = Depends(get_db)
):
    """传入子节点 UUID，逆向追溯其所有上游父总成与引用拥有者。"""
    leaf_node = await db.get(ObjectModel, node_id)
    if not leaf_node:
        raise HTTPException(status_code=404, detail="指定的逆向溯源目标节点在系统中不存在")

    return await AsyncGraphCrudEngine.get_reverse_node_tree_by_cte(db, leaf_id=node_id, max_depth=max_depth)


@router.post("/{relation_type}", response_model=RelationResponseSchema, status_code=201,
             summary="建立节点之间的拓扑关系边")
async def create_relation(
        payload: RelationCreateSchema,
        relation_type: str = Path(..., description="可选值: bom, cad_ref, doc_ref"),
        db: AsyncSession = Depends(get_db),
        _user=Depends(require_roles("admin", "engineer"))
):
    if relation_type not in RELATION_TYPE_MAPPER:
        raise HTTPException(status_code=400, detail=f"不支持的关系拓扑类型: {relation_type}")

    # 校验连线的两个端点在数据库中确实存在
    source_node = await db.get(ObjectModel, payload.source_id)
    target_node = await db.get(ObjectModel, payload.target_id)
    if not source_node or not target_node:
        raise HTTPException(status_code=404, detail="无法建立关系：指定的起点或终点节点在数据库中不存在")

    # BOM 环检测：source->target 若会让 target 成为自己的祖先，则拒绝
    if relation_type in ("bom", "bom_relation"):
        if await AsyncGraphCrudEngine.has_bom_cycle(db, payload.source_id, payload.target_id):
            raise HTTPException(status_code=422, detail="BOM 环检测失败：该关系会形成循环引用")

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
        db: AsyncSession = Depends(get_db),
        _user=Depends(require_roles("admin", "engineer"))
):
    if relation_type not in RELATION_TYPE_MAPPER:
        raise HTTPException(status_code=400, detail="不支持的关系类型")

    model_cls = RELATION_TYPE_MAPPER[relation_type]
    edge = await AsyncGraphCrudEngine.get_relation_by_id(db, model_cls, edge_id)
    if not edge:
        raise HTTPException(status_code=404, detail="目标关系连接不存在")

    return await AsyncGraphCrudEngine.update_relation_properties(db, edge, payload.properties)


@router.delete("/{relation_type}/{edge_id}", summary="删除单条图谱关系边")
async def delete_relation(
        edge_id: uuid.UUID,
        relation_type: str = Path(...),
        db: AsyncSession = Depends(get_db),
        _user=Depends(require_roles("admin", "engineer"))
):
    if relation_type not in RELATION_TYPE_MAPPER:
        raise HTTPException(status_code=400, detail="不支持的关系类型")

    model_cls = RELATION_TYPE_MAPPER[relation_type]
    edge = await AsyncGraphCrudEngine.get_relation_by_id(db, model_cls, edge_id)
    if not edge:
        raise HTTPException(status_code=404, detail="关系不存在或已被删除")

    await AsyncGraphCrudEngine.delete_relation(db, edge)
    return {"status": "success", "detail": f"关系边 {edge_id} 已成功删除，两端节点未受任何影响"}


# 节点类型映射字典
NODE_MAPPER = {
    "part": PartModel,
    "document": DocumentModel,
    "drawing": DrawingModel,
    "attachment": AttachmentModel,
    "category": CategoryNodeModel
}

# 关系边类型映射字典
EDGE_MAPPER = {
    "bom": BOMRelation,
    "bom_relation": BOMRelation,
    "cad_ref": PartDrawingRelation,
    "part_drawing_relation": PartDrawingRelation,
    "doc_ref": PartDocRelation,
    "part_doc_relation": PartDocRelation,
    "category_relation": CategoryRelationModel,
    "category_part_relation": CategoryPartRelationModel
}


@router.post("/batch-ingest", response_model=BatchCreatedResponse, status_code=status.HTTP_201_CREATED,
             summary="批量创建子图")
async def ingest_sub_graph_batch(
        payload: GraphBatchCreateRequest,
        db: AsyncSession = Depends(get_db),
        _user=Depends(require_roles("admin", "engineer"))
):
    """在一个请求中批量写入节点和关系，构建子图，任一环节失败则整体回滚。"""
    if not payload.nodes and not payload.relations:
        raise HTTPException(status_code=400, detail="请求体中节点与关系边集合不能同时为空")

    try:
        node_ids, edge_ids = await AsyncGraphCrudEngine.create_graph_batch(
            db=db,
            node_mappers=NODE_MAPPER,
            edge_mappers=EDGE_MAPPER,
            batch_data=payload
        )
        return {
            "created_node_ids": node_ids,
            "created_edge_ids": edge_ids
        }
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(val_err))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"批量创建失败: {str(e)}")


@router.patch("/batch-mutation", response_model=BatchUpdatedResponse,
              summary="批量修改子图")
async def update_sub_graph_batch(
        payload: GraphBatchUpdateRequest,
        db: AsyncSession = Depends(get_db),
        _user=Depends(require_roles("admin", "engineer"))
):
    """在一个请求中批量修改节点属性与关系边属性，并支持拓扑重定向。"""
    if not payload.nodes and not payload.relations:
        raise HTTPException(status_code=400, detail="请求体中待更新的节点集合与关系边集合不能同时为空")

    try:
        node_count, edge_count = await AsyncGraphCrudEngine.update_graph_batch(
            db=db,
            node_mappers=NODE_MAPPER,
            edge_mappers=RELATION_TYPE_MAPPER,
            batch_data=payload
        )
        return {
            "updated_node_count": node_count,
            "updated_edge_count": edge_count
        }
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(val_err))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"批量更新失败: {str(e)}")


@router.put("/nodes/{root_id}/overwrite", response_model=OverwriteSuccessResponse,
            summary="全量重写根节点下游拓扑")
async def overwrite_sub_graph_topology(
        root_id: uuid.UUID = Path(..., description="需要重写依赖图网的根节点 UUID"),
        payload: GraphTopologyOverwriteRequest = None,
        db: AsyncSession = Depends(get_db),
        _user=Depends(require_roles("admin", "engineer"))
):
    """清空根节点发出的旧关系边并写入全新关系边（清除后重建）。"""
    if not payload:
        raise HTTPException(status_code=400, detail="请求体不能为空")
    if root_id != payload.root_id:
        raise HTTPException(status_code=400, detail="路径中的 root_id 与请求体 JSON 内的 root_id 不一致")

    root_check = await db.get(ObjectModel, root_id)
    if not root_check:
        raise HTTPException(status_code=404, detail="指定的拓扑重写根节点在数据库中不存在")

    try:
        purged, inserted = await AsyncGraphCrudEngine.overwrite_graph_topology(
            db=db,
            node_mappers=NODE_MAPPER,
            edge_mappers=RELATION_TYPE_MAPPER,
            batch_data=payload
        )
        return {
            "purged_old_edges_count": purged,
            "inserted_new_edges_count": inserted
        }
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(val_err))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"全量重写图失败: {str(e)}")
