import uuid
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, ConfigDict  # 🔥 修正：引入 ConfigDict
from starlette import status

from app.api.v1.nodes import NodeResponseSchema
from app.database.session import get_db
from app.schemas.graph_batch import BatchCreatedResponse, GraphBatchCreateRequest, BatchUpdatedResponse, \
    GraphBatchUpdateRequest, ReverseTreeNodeSchema

from app.schemas.graph_batch import RelationCreateSchema, RelationUpdateSchema, RelationResponseSchema

from app.services.graph import AsyncGraphCrudEngine
from app.models.base import ObjectModel
# 导入你的多态关系业务模型
from app.models.business import BOMRelation, PartDocRelation, PartDrawingRelation, PartModel, DocumentModel, \
    DrawingModel, AttachmentModel

router = APIRouter()

# 统一维护的 URL 文本到真实关系 Python 类的映射
RELATION_TYPE_MAPPER = {
    "bom": BOMRelation,
    "bom_relation": BOMRelation,
    "cad_ref": PartDrawingRelation,
    "part_drawing_relation": PartDrawingRelation,
    "doc_ref": PartDocRelation,
    "part_doc_relation": PartDocRelation
}

class TreeNodeSchema(BaseModel):
    # 🔥 修正：使用 Pydantic 2.0 标准配置
    model_config = ConfigDict(from_attributes=True)

    depth: int = Field(..., description="在依赖树中所处的层级，1代表直属子件")
    edge: RelationResponseSchema = Field(..., description="关系边数据")
    target_node: NodeResponseSchema = Field(..., description="终点目标节点快照")


# --- 拓扑图关系及树穿透路由 ---

# 🔥 修正：必须将特异性高的静态路径路由写在最上方，防止被下面的通用变量路径吞掉
@router.get("/nodes/{node_id}/tree", response_model=List[TreeNodeSchema],
            summary="一键穿透获取整棵多级物料BOM/依赖拓扑树")
async def get_object_dependencies_tree(
        node_id: uuid.UUID = Path(..., description="根节点的 UUID"),
        max_depth: int = Query(5, ge=1, le=20, description="限制递归展开的最大深度"),
        db: AsyncSession = Depends(get_db)
):
    """
    🎯 核心算法接口：传入任意零部件或项目根节点，全自动完成网状拓扑的单次批量穿透
    """
    # 先验证根节点是否存在
    root_node = await db.get(ObjectModel, node_id)
    if not root_node:
        raise HTTPException(status_code=404, detail="指定的拓扑根节点不存在")

    return await AsyncGraphCrudEngine.get_node_tree_by_cte(db, root_id=node_id, max_depth=max_depth)


# --- 拓扑图关系及树反向穿透路由 ---

@router.get("/nodes/{node_id}/reverse-tree", response_model=List[ReverseTreeNodeSchema],
            summary="🔍 核心王牌：根据子节点一键逆向穿透追溯整棵父级引用网络(Where-Used)")
async def get_object_where_used_tree(
        node_id: uuid.UUID = Path(..., description="需要逆向追溯的子节点/叶子节点 UUID"),
        max_depth: int = Query(5, ge=1, le=20, description="限制逆向追踪的最大深度"),
        db: AsyncSession = Depends(get_db)
):
    """
    🎯 **工业级逆向依赖影响分析网关（Impact Analysis）**
    传入任意零部件、图纸、或者工艺文档的 UUID，数据库单次全异步交互，
    即可无损拉出其在整个系统中跨越第1层、第2层、直到最高20层的所有“上游父总成”、“引用拥有者”的完整树。
    """
    # 验证当前节点是否存在
    leaf_node = await db.get(ObjectModel, node_id)
    if not leaf_node:
        raise HTTPException(status_code=404, detail="指定的逆向溯源目标节点在系统中不存在")

    return await AsyncGraphCrudEngine.get_reverse_node_tree_by_cte(db, leaf_id=node_id, max_depth=max_depth)




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


# 节点类型映射字典
NODE_MAPPER = {
    "part": PartModel,
    "document": DocumentModel,
    "drawing": DrawingModel,
    "attachment": AttachmentModel
}

# 关系边类型映射字典（兼容你在路由里的 URL 别名）
EDGE_MAPPER = {
    "bom": BOMRelation,
    "bom_relation": BOMRelation,
    "cad_ref": PartDrawingRelation,
    "part_drawing_relation": PartDrawingRelation,
    "doc_ref": PartDocRelation,
    "part_doc_relation": PartDocRelation
}

@router.post("/batch-ingest", response_model=BatchCreatedResponse, status_code=status.HTTP_201_CREATED,
             summary="⚡ 工业级子图结构一次性批量原子化洗入网关")
async def ingest_sub_graph_batch(
        payload: GraphBatchCreateRequest,
        db: AsyncSession = Depends(get_db)
):
    """
    ### 批量图谱织网网关
    前端或 CAD/PLM 插件可以一次性组织整棵 BOM 树、或者一张包含【文档-图纸-附件-零部件】的复杂拓扑子图，
    通过单个请求打包发送。后端将启用全异步强事务原子锁进行持久化。
    """
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
        # 触发上一节编写的 422 友好业务拦截提示
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(val_err))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"原子批处理执行溃败: {str(e)}")


# 追加到 app/api/v1/relations.py 的路由区域

@router.patch("/batch-mutation", response_model=BatchUpdatedResponse,
              summary="⚡ 工业级子图网络结构属性与拓扑重构批量原子化修改网关")
async def update_sub_graph_batch(
        payload: GraphBatchUpdateRequest,
        db: AsyncSession = Depends(get_db)
):
    """
    ### 批量图谱修改/改签网关
    支持在单个 HTTP 请求中：
    1. 批量增量修改任意多态节点（如Part、Document等）的 JSON 动态属性。
    2. 批量修改关系边上的属性（如修改BOM装配数量）。
    3. 批量将现有关系边指向新的节点（实现工程图网重构与改签）。
    """
    if not payload.nodes and not payload.relations:
        raise HTTPException(status_code=400, detail="请求体中待更新的节点集合与关系边集合不能同时为空")

    try:
        node_count, edge_count = await AsyncGraphCrudEngine.update_graph_batch(
            db=db,
            node_mappers=NODE_MAPPER,  # 直接复用原有的映射字典
            edge_mappers=RELATION_TYPE_MAPPER,  # 直接复用原有的映射字典
            batch_data=payload
        )
        return {
            "updated_node_count": node_count,
            "updated_edge_count": edge_count
        }
    except ValueError as val_err:
        # 触发全局异常防火墙，向前端吐出高可读性的 422 业务拦截报错
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(val_err))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"原子批量更新处理遭遇意外崩溃: {str(e)}")
