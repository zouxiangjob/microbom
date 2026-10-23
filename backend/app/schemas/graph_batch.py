import uuid
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class RelationCreateSchema(BaseModel):
    """创建单条关系的请求体。"""
    source_id: uuid.UUID = Field(..., description="起点节点 UUID")
    target_id: uuid.UUID = Field(..., description="终点节点 UUID")
    properties: Dict[str, Any] = Field(default_factory=dict, description="关系的属性（如数量、单重、图号位置）")


class RelationUpdateSchema(BaseModel):
    """修改单条关系属性的请求体。"""
    properties: Dict[str, Any] = Field(..., description="增量合并修改关系的属性")


class RelationResponseSchema(BaseModel):
    """单条关系的响应模型。"""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    relation_type: str = Field(..., description="关系多态类型: bom, cad_ref, doc_ref")
    source_id: uuid.UUID
    target_id: uuid.UUID
    properties: Dict[str, Any] = Field(default_factory=dict)


# ==============================================================================
# 0. 图谱原子输出组件
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
# 1. 图遍历响应
# ==============================================================================

class TreeNodeSchema(BaseModel):
    """正向依赖树遍历响应模型（从父到子）。"""
    model_config = ConfigDict(from_attributes=True)

    depth: int = Field(..., description="在依赖树中所处的层级，1 代表直属子件")
    edge: RelationResponseSchema = Field(..., description="关系边数据")
    target_node: NodeResponseSchema = Field(..., description="终点目标节点快照")


class ReverseTreeNodeSchema(BaseModel):
    """逆向依赖溯源响应模型（从子到父，Where-Used）。"""
    model_config = ConfigDict(from_attributes=True)

    depth: int = Field(..., description="逆向追溯的层级，1 代表直属上级/父件，2 代表祖父件")
    edge: RelationResponseSchema = Field(..., description="关系边数据")
    source_node: NodeResponseSchema = Field(..., description="溯源捕获到的上级父节点快照")


# ==============================================================================
# 2. 图结构批量创建
# ==============================================================================

class BatchNodeItem(BaseModel):
    id: Optional[uuid.UUID] = Field(default=None, description="可选，前端不传则由后端写入时自动生成")
    object_type: str = Field(..., description="节点多态类型: part, document, drawing, attachment")
    properties: Dict[str, Any] = Field(default_factory=dict, description="业务动态非结构化属性")


class BatchRelationItem(BaseModel):
    relation_type: str = Field(..., description="关系多态类型: bom, cad_ref, doc_ref 等")
    source_id: uuid.UUID = Field(..., description="拓扑起点节点 ID")
    target_id: uuid.UUID = Field(..., description="拓扑终点节点 ID")
    properties: Dict[str, Any] = Field(default_factory=dict, description="关系上的业务属性，如装配数量")


class GraphBatchCreateRequest(BaseModel):
    nodes: List[BatchNodeItem] = Field(default_factory=list, description="待创建的节点集合")
    relations: List[BatchRelationItem] = Field(default_factory=list, description="待建立的关系边集合")


class BatchCreatedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    created_node_ids: List[uuid.UUID] = Field(..., description="成功创建的节点 UUID 列表")
    created_edge_ids: List[uuid.UUID] = Field(..., description="成功创建的关系边 UUID 列表")


# ==============================================================================
# 3. 图结构批量修改
# ==============================================================================

class BatchNodeUpdateItem(BaseModel):
    id: uuid.UUID = Field(..., description="目标节点的 UUID")
    object_type: str = Field(..., description="节点多态类型: part, document, drawing, attachment")
    properties: Dict[str, Any] = Field(..., description="增量合并更新的 JSON 属性字典")


class BatchRelationUpdateItem(BaseModel):
    id: uuid.UUID = Field(..., description="目标关系边的 UUID")
    relation_type: str = Field(..., description="关系多态类型: bom, cad_ref, doc_ref")
    source_id: Optional[uuid.UUID] = Field(default=None, description="可选，若需批量重定向拓扑起点")
    target_id: Optional[uuid.UUID] = Field(default=None, description="可选，若需批量重定向拓扑终点")
    properties: Dict[str, Any] = Field(default_factory=dict, description="增量合并的关系属性")


class GraphBatchUpdateRequest(BaseModel):
    nodes: List[BatchNodeUpdateItem] = Field(default_factory=list, description="需要批量修改的节点集")
    relations: List[BatchRelationUpdateItem] = Field(default_factory=list, description="需要批量修改的关系边集")


class BatchUpdatedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    updated_node_count: int = Field(..., description="成功修改的节点数量")
    updated_edge_count: int = Field(..., description="成功修改的关系边数量")


# ==============================================================================
# 4. 图拓扑全量重写
# ==============================================================================

class OverwriteNodeItem(BaseModel):
    id: uuid.UUID = Field(..., description="子节点 UUID，由前端生成或已存在")
    object_type: str = Field(..., description="节点多态类型: part, document, drawing, attachment")
    properties: Dict[str, Any] = Field(default_factory=dict, description="最新版的非结构化属性")


class OverwriteRelationItem(BaseModel):
    relation_type: str = Field(..., description="关系多态类型: bom, cad_ref, doc_ref")
    target_id: uuid.UUID = Field(..., description="最新的终点目标节点 ID")
    properties: Dict[str, Any] = Field(default_factory=dict, description="关系附带的属性（如装配数量）")


class GraphTopologyOverwriteRequest(BaseModel):
    root_id: uuid.UUID = Field(..., description="需要重写图拓扑的根节点 UUID")
    nodes: List[OverwriteNodeItem] = Field(default_factory=list, description="最新的下游子节点全量快照")
    relations: List[OverwriteRelationItem] = Field(default_factory=list, description="最新的第一层连线")


class OverwriteSuccessResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    purged_old_edges_count: int = Field(..., description="被清理的旧关系边数量")
    inserted_new_edges_count: int = Field(..., description="写入的新拓扑边数量")
