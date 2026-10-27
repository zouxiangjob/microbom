"""
分类属性定义相关的 Pydantic 请求/响应模型。
"""
import uuid
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CategoryAttributeCreate(BaseModel):
    """新增分类属性定义的请求体。"""
    category_id: uuid.UUID = Field(..., description="所属分类对象 UUID")
    attr_key: str = Field(..., description="properties 中的键名")
    attr_label: str = Field(..., description="显示名")
    value_type: str = Field("string", description="属性类型: string/number/boolean/enum/date/text")
    required: bool = Field(False, description="是否必填")
    default_value: Optional[Any] = Field(None, description="默认值")
    options: Optional[List[str]] = Field(None, description="enum 候选值列表")
    unit: Optional[str] = Field(None, description="单位")
    sort_order: int = Field(0, description="展示排序")


class CategoryAttributeUpdate(BaseModel):
    """更新分类属性定义的请求体（全部字段可选，仅更新显式传入的字段）。"""
    attr_key: Optional[str] = None
    attr_label: Optional[str] = None
    value_type: Optional[str] = None
    required: Optional[bool] = None
    default_value: Optional[Any] = None
    options: Optional[List[str]] = None
    unit: Optional[str] = None
    sort_order: Optional[int] = None


class CategoryAttributeResponse(BaseModel):
    """分类属性定义响应模型。"""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category_id: uuid.UUID
    attr_key: str
    attr_label: str
    value_type: str
    required: bool
    default_value: Optional[Any]
    options: Optional[List[str]]
    unit: Optional[str]
    sort_order: int
    created_at: datetime
    updated_at: datetime
