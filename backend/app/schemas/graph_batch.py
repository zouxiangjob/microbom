import uuid
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class RelationCreateSchema(BaseModel):
    """建立单条网络连接时的前端输入安检网关"""
    source_id: uuid.UUID = Field(..., description="起点节点 UUID")
    target_id: uuid.UUID = Field(..., description="终点节点 UUID")
    properties: Dict[str, Any] = Field(default_factory=dict, description="关系的属性（如数量、单重、图号位置）")

class RelationUpdateSchema(BaseModel):
    """修改单条关系线上属性时的增量合并网关"""
    properties: Dict[str, Any] = Field(..., description="增量合并修改关系的属性")

class RelationResponseSchema(BaseModel):
    """单条网状关系向前端输出时的过滤器"""
    model_config = ConfigDict(from_attributes=True)  # 🔥 Pydantic 2.0 标准规范

    id: uuid.UUID
    relation_type: str = Field(..., description="关系多态类型: bom, cad_ref, doc_ref")
    source_id: uuid.UUID
    target_id: uuid.UUID
    properties: Dict[str, Any] = Field(default_factory=dict)


# ==============================================================================
# 0. 图谱原子输出组件 (解耦基础 Schema，防止与路由层产生循环导入死锁)
# ==============================================================================

class NodeResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    object_type: str = Field(..., description="多态节点类型: part, document, drawing, attachment")
    properties: Dict[str, Any] = Field(default_factory=dict, description="业务自定义动态属性")


class RelationResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    relation_type: str = Field(..., description="关系多态类型: bom, cad_ref, doc_ref")
    source_id: uuid.UUID
    target_id: uuid.UUID
    properties: Dict[str, Any] = Field(default_factory=dict)


# ==============================================================================
# 1. 拓扑图谱高级穿透响应 (Traversal Schemas)
# ==============================================================================

class TreeNodeSchema(BaseModel):
    """正向多级依赖树穿透响应模型 (从父到子)"""
    model_config = ConfigDict(from_attributes=True)

    depth: int = Field(..., description="在依赖树中所处的层级，1代表直属子件")
    edge: RelationResponseSchema = Field(..., description="关系边数据")
    target_node: NodeResponseSchema = Field(..., description="终点目标节点快照")


class ReverseTreeNodeSchema(BaseModel):
    """逆向依赖溯源响应模型 (从子到父，Where-Used)"""
    model_config = ConfigDict(from_attributes=True)

    depth: int = Field(..., description="逆向追溯的层级，1代表直属上级/父件，2代表爷爷件...")
    edge: RelationResponseSchema = Field(..., description="关系边数据")
    source_node: NodeResponseSchema = Field(..., description="溯源捕获到的上级父节点快照")


# ==============================================================================
# 2. 图结构批量原子创建 (Batch Ingestion Schemas)
# ==============================================================================

class BatchNodeItem(BaseModel):
    id: Optional[uuid.UUID] = Field(default=None, description="可选，若前端不传则由后端在写入时自动补全")
    object_type: str = Field(..., description="节点多态类型: part, document, drawing, attachment")
    properties: Dict[str, Any] = Field(default_factory=dict, description="业务动态非结构化属性")


class BatchRelationItem(BaseModel):
    relation_type: str = Field(..., description="关系多态类型: bom, cad_ref, doc_ref 等")
    source_id: uuid.UUID = Field(..., description="拓扑起点节点 ID")
    target_id: uuid.UUID = Field(..., description="拓扑终点节点 ID")
    properties: Dict[str, Any] = Field(default_factory=dict, description="关系上的业务属性，如装配数量")


class GraphBatchCreateRequest(BaseModel):
    nodes: List[BatchNodeItem] = Field(default_factory=list, description="待创建的图节点集合")
    relations: List[BatchRelationItem] = Field(default_factory=list, description="待建立的网状关系边集合")


class BatchCreatedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    created_node_ids: List[uuid.UUID] = Field(..., description="成功持久化的节点 UUID 列表")
    created_edge_ids: List[uuid.UUID] = Field(..., description="成功持久化的关系边 UUID 列表")


# ==============================================================================
# 3. 图结构批量原子修改 (Batch Mutation Schemas)
# ==============================================================================

class BatchNodeUpdateItem(BaseModel):
    id: uuid.UUID = Field(..., description="必须传入目标节点的 UUID")
    object_type: str = Field(..., description="节点多态类型: part, document, drawing, attachment")
    properties: Dict[str, Any] = Field(..., description="增量合并覆盖更新的 JSON 属性字典")


class BatchRelationUpdateItem(BaseModel):
    id: uuid.UUID = Field(..., description="必须传入目标关系边的 UUID")
    relation_type: str = Field(..., description="关系多态类型: bom, cad_ref, doc_ref")
    source_id: Optional[uuid.UUID] = Field(default=None, description="可选，若需要批量改签拓扑起点")
    target_id: Optional[uuid.UUID] = Field(default=None, description="可选，若需要批量改签拓扑终点")
    properties: Dict[str, Any] = Field(default_factory=dict, description="增量覆盖的关系属性")


class GraphBatchUpdateRequest(BaseModel):
    nodes: List[BatchNodeUpdateItem] = Field(default_factory=list, description="需要批量修改的节点集")
    relations: List[BatchRelationUpdateItem] = Field(default_factory=list, description="需要批量修改的关系边集")


class BatchUpdatedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    updated_node_count: int = Field(..., description="成功修改的节点总数量")
    updated_edge_count: int = Field(..., description="成功修改的关系边总数量")


# ==============================================================================
# 4. 方案 B: 全量重写图拓扑 (Graph Overwrite Schemas)
# ==============================================================================

class OverwriteNodeItem(BaseModel):
    id: uuid.UUID = Field(..., description="子节点的 UUID，必须由前端生成或已存在")
    object_type: str = Field(..., description="节点多态类型: part, document, drawing, attachment")
    properties: Dict[str, Any] = Field(default_factory=dict, description="最新版的非结构化属性")


class OverwriteRelationItem(BaseModel):
    relation_type: str = Field(..., description="关系多态类型: bom, cad_ref, doc_ref")
    target_id: uuid.UUID = Field(..., description="当前最新的终点目标节点 ID")
    properties: Dict[str, Any] = Field(default_factory=dict, description="当前最新关系附带的属性（如装配数量）")


class GraphTopologyOverwriteRequest(BaseModel):
    root_id: uuid.UUID = Field(..., description="需要重写图拓扑的根节点 UUID（如当前父零件）")
    nodes: List[OverwriteNodeItem] = Field(default_factory=list, description="当前最新的下游子节点全量快照")
    relations: List[OverwriteRelationItem] = Field(default_factory=list, description="当前最新的全量第一层连线网")


class OverwriteSuccessResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    purged_old_edges_count: int = Field(..., description="被成功清理的旧僵尸连线数量")
    inserted_new_edges_count: int = Field(..., description="成功灌入的最新拓扑边数量")
