import os
import hashlib
from uuid import UUID as PyUUID
from typing import Type
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import FileModel
from app.models.base import ObjectModel

UPLOAD_DIR = settings.UPLOAD_DIR


async def save_physical_file(
        db: AsyncSession,
        file: UploadFile,
        object_id: PyUUID,
        model_cls: Type[ObjectModel]
) -> FileModel:
    """
    【通用多态物理文件秒传去重接口】
    1. 计算文件 MD5 值，若数据库中已有相同 MD5，则直接复用物理文件（实现秒传去重）。
    2. 若文件不存在，则以 MD5 命名落盘。
    3. 自适应解禁多态节点（Drawing/Attachment等）的属性状态。
    """
    # 确保上传目录存在
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # ==================== 步骤 1: 读取流并分块计算 MD5 ====================
    original_name = file.filename or "unknown"
    file_extension = os.path.splitext(original_name)[1].lower()

    contents = await file.read()
    file_size = len(contents)

    # 计算完整 MD5
    md5_hash = hashlib.md5(contents).hexdigest()

    # 物理文件的唯一存储名称由 MD5 + 扩展名构成
    unique_filename = f"{md5_hash}{file_extension}"
    file_save_path = os.path.join(UPLOAD_DIR, unique_filename)

    # ==================== 步骤 2: 核心去重检查 (秒传逻辑) ====================
    # 检查数据库中是否存在具有相同存储名称的物理文件记录
    dup_query = await db.execute(select(FileModel).where(FileModel.stored_name == unique_filename))
    existing_file = dup_query.scalar_one_or_none()

    is_duplicate = False

    if existing_file and os.path.exists(existing_file.absolute_path):
        # 🎯 物理去重命中：磁盘上已有相同文件，直接复用其绝对路径，不进行任何磁盘写操作！
        file_save_path = existing_file.absolute_path
        unique_filename = existing_file.stored_name
        is_duplicate = True
    else:
        # 💾 物理去重未命中：新文件，执行物理落盘
        with open(file_save_path, "wb") as buffer:
            buffer.write(contents)

    # ==================== 步骤 3: 开启数据库事务记账 ====================
    try:
        # 3.1 检查此 object_id 的多态节点是否存在（防御性校验）
        obj_node = await db.get(model_cls, object_id)
        if not obj_node:
            raise ValueError(f"Object_Node_Not_Found: 在类型 {model_cls.__name__} 中未找到该 UUID")

        # 3.2 写入文件元数据表（即使物理文件复用，每个虚拟节点仍有自己独立的文件记录名）
        db_file = FileModel(
            object_id=object_id,
            original_name=original_name,
            stored_name=unique_filename,
            file_size=file_size,
            mime_type=file.content_type or "application/octet-stream",
            absolute_path=file_save_path
        )
        db.add(db_file)

        # 3.3 自适应解禁多态关联节点的状态
        props = dict(obj_node.properties) if obj_node.properties else {}
        props["file_status"] = "ready"
        props["status"] = "ready"
        props["is_uploaded"] = True
        props["md5"] = md5_hash  # 将 MD5 记录在节点的非结构化属性中，便于前端追溯
        props["is_hit_cache"] = is_duplicate  # 标记当前文件是秒传还是真实上传

        obj_node.properties = props  # 触发 SQLAlchemy 变更追踪
        db.add(obj_node)

        await db.commit()
        await db.refresh(db_file)
        return db_file

    except Exception as db_err:
        await db.rollback()
        # 🚨 事务异常物理清理防护：只有在“新文件落盘且数据库失败”时才删除物理文件；
        # 如果是秒传复用的老文件，绝对不能误删磁盘文件！
        if not is_duplicate and os.path.exists(file_save_path):
            os.remove(file_save_path)

        if isinstance(db_err, ValueError):
            raise db_err
        raise RuntimeError(f"文件记账失败，事务已安全撤销。原因: {str(db_err)}")


async def get_file_for_download(db: AsyncSession, file_id: PyUUID) -> FileModel:
    """
    根据文件 UUID 获取文件记录，并校验物理文件是否存在
    """
    result = await db.execute(select(FileModel).where(FileModel.object_id == file_id))
    db_file = result.scalar_one_or_none()

    if not db_file:
        raise ValueError("File_Not_Found")

    if not os.path.exists(db_file.absolute_path):
        raise FileNotFoundError("Physical_File_Missing")

    return db_file
