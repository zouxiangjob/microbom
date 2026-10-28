"""
发布基线专用数据模型。

设计原则：
- 基线是「某一时刻 BOM 结构 + 节点属性 + 关系数量」的不可变快照。
- 独立成表（baselines / baseline_items），与 objects / files / relations 完全解耦，
  不污染现有业务表，也不复用其多态机制。
- 冻结数据对 live 对象的引用使用【普通 UUID 列，而非外键】，确保原对象后续被
  修改或删除时，历史基线不受影响（这正是"冻结"的意义所在）。
"""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID as PyUUID

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin


class Baseline(Base, SoftDeleteMixin):
    """发布基线主表：记录一次发布动作的元信息。"""
    __tablename__ = "baselines"

    id: Mapped[PyUUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    name: Mapped[str] = mapped_column(String(255), nullable=False)            # 基线名称
    release_version: Mapped[str] = mapped_column(String(50), nullable=False)  # 发布版本号，如 R1.0
    root_object_id: Mapped[Optional[PyUUID]] = mapped_column(index=True)      # 冻结的根总成原对象 ID（非外键）
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="released")
    note: Mapped[Optional[str]] = mapped_column(String(500))
    created_by: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    items: Mapped[List["BaselineItem"]] = relationship(
        back_populates="baseline",
        cascade="all, delete-orphan",
        order_by="BaselineItem.depth",
    )


class BaselineItem(Base, SoftDeleteMixin):
    """基线冻结条目表：逐条冻结 BOM 树中的节点及其父子结构关系。"""
    __tablename__ = "baseline_items"

    id: Mapped[PyUUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    baseline_id: Mapped[PyUUID] = mapped_column(
        ForeignKey("baselines.id", ondelete="CASCADE"), index=True, nullable=False
    )

    object_id: Mapped[PyUUID] = mapped_column(index=True)                      # 冻结节点的原对象 ID（非外键）
    object_type: Mapped[str] = mapped_column(String(50), nullable=False)       # 节点多态类型
    relation_type: Mapped[str] = mapped_column(String(50), nullable=False)     # 冻结边类型：root / bom_relation / part_drawing_relation / ...
    properties: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)  # 冻结的节点属性

    parent_object_id: Mapped[Optional[PyUUID]] = mapped_column(index=True)     # 父对象原 ID（根节点为 NULL）
    depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)     # 层级深度，根为 0
    quantity: Mapped[Optional[int]] = mapped_column(Integer)                   # 装配数量（根节点为 NULL）
    edge_properties: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)    # 冻结的关系边属性（数量之外的补充）

    baseline: Mapped["Baseline"] = relationship(back_populates="items")
