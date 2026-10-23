"""
发布基线相关的 Pydantic 请求/响应模型。
"""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class BaselineCreateRequest(BaseModel):
    """发布基线的请求体。"""
    root_id: uuid.UUID = Field(..., description="冻结的根总成对象 UUID")
    name: Optional[str] = Field(None, description="基线名称（缺省用版本号生成）")
    release_version: Optional[str] = Field(None, description="发布版本号（缺省自动递增 A→B→…→Z→AA）")
    note: Optional[str] = Field(None, description="发布说明")
    created_by: Optional[str] = Field(None, description="发布人")


class BaselineItemResponse(BaseModel):
    """冻结条目响应模型。"""
    model_config = ConfigDict(from_attributes=True)

    object_id: uuid.UUID
    object_type: str
    relation_type: str
    properties: Dict[str, Any]
    parent_object_id: Optional[uuid.UUID]
    depth: int
    quantity: Optional[int]
    edge_properties: Optional[Dict[str, Any]]


class BaselineSummaryResponse(BaseModel):
    """基线列表项响应模型。"""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    release_version: str
    root_object_id: Optional[uuid.UUID]
    status: str
    note: Optional[str]
    created_by: Optional[str]
    created_at: datetime
    item_count: int


class BaselineDetailResponse(BaseModel):
    """单条基线完整响应模型。"""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    release_version: str
    root_object_id: Optional[uuid.UUID]
    status: str
    note: Optional[str]
    created_by: Optional[str]
    created_at: datetime
    items: List[BaselineItemResponse]
