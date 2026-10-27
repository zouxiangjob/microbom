"""
分类编码器专用数据模型。

设计原则：
- 每个分类（分类节点 UUID）配一个编码器（1:1，unique），用于自动生成其零部件的 code。
- 独立成表（category_encoders），与 objects / relations 完全解耦，不污染业务表。
- 两种编码方式：
    1. sequence 顺序编码：前缀 + 流水码 + 后缀（start_seq ~ end_seq）。
    2. script 脚本编码：服务端执行自定义 Python 脚本（仅限可信管理员配置）。
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CategoryEncoder(Base):
    """分类编码器：定义某分类下零部件的 code 生成规则。"""
    __tablename__ = "category_encoders"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    category_id: Mapped[uuid.UUID] = mapped_column(unique=True, index=True, nullable=False)  # 分类节点 UUID（1:1）
    encoder_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "sequence" | "script"

    # --- 方式1：顺序编码 ---
    prefix: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)   # 前缀，如 "WD-"
    suffix: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)   # 后缀，如 "-A"
    start_seq: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)   # 起始流水
    end_seq: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)     # 终止流水
    seq_length: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 流水码位数（补零），如 4 → 0001

    # --- 方式2：脚本编码 ---
    encoder_script: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 自定义脚本

    # --- 通用跟踪 ---
    current_seq: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 当前已用的流水号（内部跟踪）
    latest_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # 最新已生成编码

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
