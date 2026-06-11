import os
import shutil
from uuid import uuid4
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.file import FileModel

UPLOAD_DIR = "./uploads"

async def upload_and_bind_user(db: AsyncSession, file: UploadFile, user_id: int) -> FileModel:
    # 1. 生成本地唯一文件名
    file_ext = os.path.splitext(file.filename)[1]
    unique_name = f"{uuid4().hex}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)
    
    # 2. 读取文件并计算大小（或者在写入时获取）
    # 由于是异步读取文件流，需要加上 await
    contents = await file.read()
    file_size = len(contents)
    
    # 3. 将文件写入本地磁盘
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    with open(file_path, "wb") as buffer:
        buffer.write(contents)
    
    # 4. 创建 SQLAlchemy 数据库记录
    db_file = FileModel(
        original_name=file.filename,
        stored_name=unique_name,
        file_size=file_size,
        mime_type=file.content_type,
        user_id=user_id
    )
    
    db.add(db_file)
    await db.commit() # 提交到 SQLite
    await db.refresh(db_file) # 刷新以获取自增的 id 等数据
    
    return db_file
