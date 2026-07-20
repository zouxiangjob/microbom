import uuid
from datetime import datetime
from uuid import UUID as PyUUID
from typing import Any, Dict
from sqlalchemy import String, ForeignKey, DateTime, func, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase


class Base(DeclarativeBase):
    """统一声明式基类"""
    pass
# ==============================================================================
# 1. 基础对象表 (万物皆对象)
# ==============================================================================

class ObjectModel(Base):
    """对象基表"""
    __tablename__ = "objects"

    # SQLite 完美支持 UUID 存储（通常存为 32位 或 36位 字符串/BLOB）
    id: Mapped[PyUUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # "file", "part"
    object_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)

    __mapper_args__ = {
        "polymorphic_on": "object_type",  # 告诉SQLAlchemy用这个字段区分不同的业务子类
        "polymorphic_identity": "base_object"  # 基类自己的标识
    }

    # SQLite 下表现为 TEXT 类型的 JSON 字符串
    # SQLAlchemy 会在 Python 字典与文本之间自动做 json.dumps() 和 json.loads()
    properties: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # 1:1 反向关联文件表（cascade 确保删对象时，文件档案同步删除）
    file_info: Mapped["FileModel"] = relationship(back_populates="object_node", cascade="all, delete-orphan")


# ==============================================================================
# 2. 基础文件表 (特定类：核心文件档案)
# ==============================================================================
class FileModel(Base):
    """文件特定业务表：强Schema约束，保证下载和物理追踪的高效性"""
    __tablename__ = "files"

    # 核心：共享 objects 表的 UUID 作为自己的主键与外键
    object_id: Mapped[PyUUID] = mapped_column(ForeignKey("objects.id", ondelete="CASCADE"),primary_key=True)

    original_name: Mapped[str] = mapped_column(String(255), nullable=False) # 原始文件名，如 "photo.jpg"
    stored_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False) # 本地唯一文件名
    file_size: Mapped[int] = mapped_column(Integer, nullable=False) # 文件大小（字节）
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False) # 文件类型，如 "image/jpeg"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    absolute_path: Mapped[str] = mapped_column(String(500), nullable=False)

    # 双向 ORM 绑定
    object_node: Mapped["ObjectModel"] = relationship(back_populates="file_info")


# ==============================================================================
# 3. 基础关系表 (纯粹的网状纽带)
# ==============================================================================
class RelationModel(Base):
    """关系基表：负责表达一切连接"""
    __tablename__ = "relations"

    id: Mapped[PyUUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # "has_2d_drawing", "contains_part" 等
    relation_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)

    source_id: Mapped[PyUUID] = mapped_column(ForeignKey("objects.id", ondelete="CASCADE"), index=True, nullable=False)
    target_id: Mapped[PyUUID] = mapped_column(ForeignKey("objects.id", ondelete="CASCADE"), index=True, nullable=False)

    # 关系自身的属性
    properties: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)