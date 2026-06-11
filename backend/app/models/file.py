from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class FileModel(Base):
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False) # 原始文件名，如 "photo.jpg"
    stored_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False) # 本地唯一文件名
    file_size: Mapped[int] = mapped_column(Integer, nullable=False) # 文件大小（字节）
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False) # 文件类型，如 "image/jpeg"
    created_at: Mapped[DateTime] = mapped_column(DateTime, default=func.now())
