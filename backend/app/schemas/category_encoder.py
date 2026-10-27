"""
分类编码器相关的 Pydantic 请求/响应模型。
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CategoryEncoderCreate(BaseModel):
    """创建分类编码器的请求体。"""
    category_id: uuid.UUID = Field(..., description="分类节点 UUID")
    encoder_type: str = Field(..., description="编码方式: sequence | script")
    # 方式1 顺序编码字段
    prefix: Optional[str] = Field(None, description="前缀")
    suffix: Optional[str] = Field(None, description="后缀")
    start_seq: Optional[int] = Field(None, description="起始流水")
    end_seq: Optional[int] = Field(None, description="终止流水")
    seq_length: Optional[int] = Field(None, description="流水码补零位数")
    # 方式2 脚本编码字段
    encoder_script: Optional[str] = Field(None, description="自定义脚本")


class CategoryEncoderUpdate(BaseModel):
    """更新分类编码器的请求体（全部字段可选，仅更新显式传入的字段）。"""
    encoder_type: Optional[str] = None
    prefix: Optional[str] = None
    suffix: Optional[str] = None
    start_seq: Optional[int] = None
    end_seq: Optional[int] = None
    seq_length: Optional[int] = None
    encoder_script: Optional[str] = None


class CategoryEncoderResponse(BaseModel):
    """分类编码器响应模型。"""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category_id: uuid.UUID
    encoder_type: str
    prefix: Optional[str]
    suffix: Optional[str]
    start_seq: Optional[int]
    end_seq: Optional[int]
    seq_length: Optional[int]
    encoder_script: Optional[str]
    current_seq: Optional[int]
    latest_code: Optional[str]
    created_at: datetime
    updated_at: datetime


class GeneratedCodeResponse(BaseModel):
    """生成编码的响应模型。"""
    code: str = Field(..., description="新生成的编码")
