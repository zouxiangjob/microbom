"""
用户认证专用数据模型（独立表，不并入 objects 多态，先例同 FileModel）。
"""
import uuid
from datetime import datetime
from uuid import UUID as PyUUID

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin


class UserModel(Base, SoftDeleteMixin):
    """系统登录用户：用户名 + 密码哈希 + 角色。"""
    __tablename__ = "users"

    id: Mapped[PyUUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="engineer")  # admin/engineer/purchase/workshop
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
