import os
import hashlib
from uuid import UUID as PyUUID
from typing import Optional, Type
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
    """FastAPI 上传入口：读取 UploadFile 内容后，委托给底层落盘/记账逻辑。"""
    original_name = file.filename or "unknown"
    contents = await file.read()
    return await store_file_contents(
        db,
        object_id=object_id,
        model_cls=model_cls,
        original_name=original_name,
        content_type=file.content_type,
        contents=contents,
    )


async def store_file_contents(
        db: AsyncSession,
        *,
        object_id: PyUUID,
        model_cls: Type[ObjectModel],
        original_name: str,
        content_type: Optional[str],
        contents: bytes,
) -> FileModel:
    """保存物理文件并登记元数据（与上传通道解耦，供 REST API 复用）。

    流程：
    1. 计算文件 MD5，若已有相同 MD5 则复用物理文件。
    2. 否则以 MD5 命名落盘。
    3. 登记文件元数据，并更新关联节点的上传状态。
    """
    # 确保上传目录存在
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # 步骤 1：计算 MD5
    file_extension = os.path.splitext(original_name)[1].lower()
    file_size = len(contents)
    md5_hash = hashlib.md5(contents).hexdigest()

    # 物理文件的唯一存储名由 MD5 + 扩展名构成
    unique_filename = f"{md5_hash}{file_extension}"
    file_save_path = os.path.join(UPLOAD_DIR, unique_filename)

    # 步骤 2：去重检查（复用已存在文件）
    dup_query = await db.execute(select(FileModel).where(
        FileModel.stored_name == unique_filename,
        FileModel.is_deleted == False,
    ))
    existing_file = dup_query.scalar_one_or_none()

    is_duplicate = False

    if existing_file and os.path.exists(existing_file.absolute_path):
        # 去重命中：复用磁盘上的已有文件，不执行磁盘写操作。
        # stored_name 有唯一约束，新记录须追加对象 ID 前缀，避免唯一键冲突。
        file_save_path = existing_file.absolute_path
        unique_filename = f"{md5_hash}_{object_id.hex[:8]}{file_extension}"
        is_duplicate = True
    else:
        # 未命中：执行物理落盘
        with open(file_save_path, "wb") as buffer:
            buffer.write(contents)

    # 步骤 3：登记数据库事务
    try:
        # 3.1 校验对象节点是否存在
        obj_node = await db.get(model_cls, object_id)
        if not obj_node or obj_node.is_deleted:
            raise ValueError(f"Object_Node_Not_Found: 在类型 {model_cls.__name__} 中未找到该 UUID")

        # 3.2 覆盖上传：对象与文件是一对一关系，先删除旧记录，提交后再清理旧物理文件
        old_file = (await db.execute(
            select(FileModel).where(FileModel.object_id == object_id)
        )).scalar_one_or_none()
        old_physical_path = old_file.absolute_path if old_file else None
        if old_file:
            await db.delete(old_file)
            await db.flush()

        # 3.3 写入文件元数据
        db_file = FileModel(
            object_id=object_id,
            original_name=original_name,
            stored_name=unique_filename,
            file_size=file_size,
            mime_type=content_type or "application/octet-stream",
            absolute_path=file_save_path
        )
        db.add(db_file)

        # 3.4 更新关联节点的上传状态
        props = dict(obj_node.properties) if obj_node.properties else {}
        props["file_status"] = "ready"
        props["is_uploaded"] = True
        props["md5"] = md5_hash
        props["is_hit_cache"] = is_duplicate

        obj_node.properties = props
        db.add(obj_node)

        await db.commit()
        await db.refresh(db_file)

        # 3.5 提交成功后清理被替换的旧物理文件：
        #     仅当旧文件不再被任何记录引用（且不同于当前路径）时才删除，避免误删共享文件。
        if old_physical_path and old_physical_path != file_save_path and os.path.exists(old_physical_path):
            refs = (await db.execute(
                select(FileModel).where(FileModel.absolute_path == old_physical_path)
            )).scalars().all()
            if not refs:
                try:
                    os.remove(old_physical_path)
                except OSError:
                    pass

        return db_file

    except Exception as db_err:
        await db.rollback()
        # 事务失败时，仅当"新文件落盘且数据库失败"才删除物理文件；
        # 去重复用的旧文件不能删除。
        if not is_duplicate and os.path.exists(file_save_path):
            os.remove(file_save_path)

        if isinstance(db_err, ValueError):
            raise db_err
        raise RuntimeError(f"文件记账失败，事务已安全撤销。原因: {str(db_err)}")


async def get_file_for_download(db: AsyncSession, file_id: PyUUID) -> FileModel:
    """根据对象 UUID 获取文件记录，并校验物理文件是否存在。"""
    result = await db.execute(select(FileModel).where(
        FileModel.object_id == file_id,
        FileModel.is_deleted == False,
    ))
    db_file = result.scalar_one_or_none()

    if not db_file:
        raise ValueError("File_Not_Found")

    if not os.path.exists(db_file.absolute_path):
        raise FileNotFoundError("Physical_File_Missing")

    return db_file
