import os
from uuid import uuid4
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.file import FileModel

UPLOAD_DIR = "./uploads"


async def upload_and_bind_user(db: AsyncSession, file: UploadFile, bus_id: str, bus_type: str) -> FileModel:
    # 确保上传目录存在
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # 1. 计算文件名与磁盘物理路径
    original_name = file.filename
    file_extension = os.path.splitext(original_name)[1]
    unique_filename = f"{uuid4().hex}{file_extension}"
    file_save_path = os.path.join(UPLOAD_DIR, unique_filename)

    # 2. 外部 I/O 写入：读取流并写入本地硬盘
    contents = await file.read()
    with open(file_save_path, "wb") as buffer:
        buffer.write(contents)

    # 3. 开启数据库事务边界
    try:
        db_file = FileModel(
            original_name=original_name,
            stored_name=unique_filename,
            file_size=len(contents),
            mime_type=file.content_type,
            bus_id=bus_id,  # 👈 核心修正：真正将文件与业务id 绑定
            bus_type=bus_type, # 👈 核心修正：真正将文件与业务类型 绑定
        )
        db.add(db_file)
        await db.commit()  # 提交异步事务
        await db.refresh(db_file)  # 刷新以确保模型带有自增 id 和 created_at

        return db_file

    except Exception as db_err:
        # 4. 🚨 数据连带清理：如果数据库记账失败，必须立刻撤销并删除刚写进硬盘的磁盘文件
        # 否则服务器磁盘会堆满无人知晓的脏文件（通过代码提升系统鲁棒性）
        await db.rollback()  # 异步回滚数据库记录
        if os.path.exists(file_save_path):
            os.remove(file_save_path)

        # 5. ✨ 优雅升级：向上层抛出干净的原生异常，拒绝向业务层引入 Web 框架的 HTTPException
        raise RuntimeError(f"数据库写入失败，磁盘文件已安全撤销。原因: {str(db_err)}")
