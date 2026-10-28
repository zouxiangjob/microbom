import uuid
from datetime import datetime
from uuid import UUID as PyUUID
from typing import Any, Dict
from sqlalchemy import Boolean, String, ForeignKey, DateTime, func, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase


class Base(DeclarativeBase):
    """统一声明式基类。"""
    pass


class SoftDeleteMixin:
    """软删除通用标记：is_deleted=True 表示已逻辑删除。所有读查询须过滤 is_deleted == False。"""
    is_deleted: Mapped[bool] = mapped_column("is_deleted", Boolean, default=False, nullable=False)


# ==============================================================================
# 1. 对象基表
# ==============================================================================

class ObjectModel(Base, SoftDeleteMixin):
    """对象基表：所有业务节点的公共父表，通过 object_type 区分具体类型。"""
    __tablename__ = "objects"

    id: Mapped[PyUUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # 对象类型判别列（part / document / drawing / attachment / category 等）
    object_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)

    __mapper_args__ = {
        "polymorphic_on": "object_type",  # 用该列区分不同的业务子类
        "polymorphic_identity": "base_object"  # 基类自身的标识
    }

    # 业务自定义属性，以 JSON 形式存储（SQLAlchemy 自动完成 dict 与文本的序列化）
    properties: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # 与文件记录的一对一关系，删除对象时级联删除对应文件
    file_info: Mapped["FileModel"] = relationship(back_populates="object_node", cascade="all, delete-orphan")


# ==============================================================================
# 2. 文件表
# ==============================================================================
class FileModel(Base, SoftDeleteMixin):
    """文件表：记录物理文件元数据，主键复用 objects.id（与对象一对一）。"""
    __tablename__ = "files"

    object_id: Mapped[PyUUID] = mapped_column(ForeignKey("objects.id", ondelete="CASCADE"), primary_key=True)

    original_name: Mapped[str] = mapped_column(String(255), nullable=False)  # 原始文件名
    stored_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)  # 落盘后的唯一文件名
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # 文件大小（字节）
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)  # MIME 类型
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    absolute_path: Mapped[str] = mapped_column(String(500), nullable=False)  # 物理文件绝对路径

    object_node: Mapped["ObjectModel"] = relationship(back_populates="file_info")


# ==============================================================================
# 3. 关系表
# ==============================================================================
class RelationModel(Base, SoftDeleteMixin):
    """关系表：表达节点之间的有向连接（source_id -> target_id）。"""
    __tablename__ = "relations"

    id: Mapped[PyUUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # 关系类型判别列（bom_relation / part_drawing_relation 等）
    relation_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)

    __mapper_args__ = {
        "polymorphic_on": "relation_type",  # 用该列区分不同的关系子类
        "polymorphic_identity": "base_relation"  # 基类自身标识
    }

    source_id: Mapped[PyUUID] = mapped_column(ForeignKey("objects.id", ondelete="CASCADE"), index=True, nullable=False)
    target_id: Mapped[PyUUID] = mapped_column(ForeignKey("objects.id", ondelete="CASCADE"), index=True, nullable=False)

    # 关系自身的业务属性（如装配数量、位置）
    properties: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
