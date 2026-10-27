"""
分类属性定义专用数据模型。

设计原则：
- 定义「某个分类下零部件应具备哪些属性」的模板（schema），与属性值解耦。
- 独立成表（category_attribute_defs），与 objects / relations 完全解耦，不污染业务表。
- 属性值仍存于零部件的 properties JSON（向后兼容），本表只存「定义」。
- 分类引用使用普通 UUID 列（非外键），与发布基线表保持同一约定。
"""
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CategoryAttributeDef(Base):
    """分类属性定义：描述某分类下零部件的属性模板（键名/显示名/类型/约束）。"""
    __tablename__ = "category_attribute_defs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    category_id: Mapped[uuid.UUID] = mapped_column(index=True, nullable=False)  # 所属分类对象 ID（非外键）
    attr_key: Mapped[str] = mapped_column(String(100), nullable=False)          # properties 中的键名
    attr_label: Mapped[str] = mapped_column(String(100), nullable=False)        # 显示名（如「减速比」）
    value_type: Mapped[str] = mapped_column(String(20), nullable=False, default="string")  # string/number/boolean/enum/date/text
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)          # 是否必填
    default_value: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)    # 默认值
    options: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)         # enum 候选值列表
    unit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)       # 单位（如 N·m）
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 展示排序

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
