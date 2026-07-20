import os
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
    【通用多态物理文件后补接口】
    1. 负责将物理文件安全落盘并记录 FileModel。
    2. 自动识别传入的多态子类（PartModel/DrawingModel等），无损更新非结构化状态。
    """
    # 确保上传目录存在
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # 1. 计算文件名与磁盘物理路径
    original_name = file.filename
    file_extension = os.path.splitext(original_name)[1] if original_name else ""
    unique_filename = f"{object_id.hex}{file_extension}"
    file_save_path = os.path.join(UPLOAD_DIR, unique_filename)

    # 2. 外部 I/O 写入：异步读取流并写入本地硬盘
    contents = await file.read()
    with open(file_save_path, "wb") as buffer:
        buffer.write(contents)

    # 3. 开启数据库事务边界
    try:
        # 3.1 写入文件元数据表（物理记账）
        db_file = FileModel(
            object_id=object_id,
            original_name=original_name or "unknown",
            stored_name=unique_filename,
            file_size=len(contents),
            mime_type=file.content_type or "application/octet-stream",
            absolute_path=file_save_path
        )
        db.add(db_file)

        # 3.2 【通用多态激活】动态感知对象类型，自适应解禁状态
        # 使用传入的 model_cls 确保类型安全
        obj_node = await db.get(model_cls, object_id)
        if obj_node:
            props = dict(obj_node.properties) if obj_node.properties else {}

            # 🛡️ 智能兼容：无论你前端设计的字段叫 file_status 还是 status，都进行无损覆盖
            props["file_status"] = "ready"
            props["status"] = "ready"
            props["is_uploaded"] = True

            obj_node.properties = props  # 重新赋值触发 SQLAlchemy 变更追踪
            db.add(obj_node)
        else:
            # 如果基表连对象都没找到，说明前端传入了非法的 UUID，直接触发回滚
            raise ValueError(f"Object_Node_Not_Found: 在类型 {model_cls.__name__} 中未找到该 UUID")

        await db.commit()
        await db.refresh(db_file)
        return db_file

    except Exception as db_err:
        # 4. 🚨 事务回滚与物理连带清理
        await db.rollback()
        if os.path.exists(file_save_path):
            os.remove(file_save_path)
        if isinstance(db_err, ValueError):
            raise db_err
        raise RuntimeError(f"物理文件保存失败，磁盘事务已安全撤销。原因: {str(db_err)}")


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
