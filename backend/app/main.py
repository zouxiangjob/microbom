import os
from uuid import uuid4
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession

# 导入数据库相关组件
from app.database.session import engine, get_db
from app.models.base import Base
from app.models.file import FileModel  # ⚠️ 必须导入，否则 Base 无法识别并建表

UPLOAD_DIR = "./uploads"
APP_HOST = "http://localhost:8000"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 🚀 启动时：确保本地上传文件夹存在
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    # 🚀 启动时：自动在 backend/ 下创建 sql_app.db 文件并建立 files 数据表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield
    # 🛑 关闭时：释放引擎
    await engine.dispose()


app = FastAPI(title="MicroBOM API", lifespan=lifespan)
app.mount("/static/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.post("/api/v1/upload", summary="单文件上传并保存到数据库")
async def upload_file(
        file: UploadFile = File(...),
        db: AsyncSession = Depends(get_db)  # 👈 关键：注入异步数据库会话
):
    try:
        # 1. 异步读取并保存文件到本地硬盘
        original_name = file.filename
        file_extension = os.path.splitext(original_name)[1]
        unique_filename = f"{uuid4().hex}{file_extension}"
        file_save_path = os.path.join(UPLOAD_DIR, unique_filename)

        contents = await file.read()
        with open(file_save_path, "wb") as buffer:
            buffer.write(contents)

        # 2. ⏳ 异步将文件元数据写入 SQLite 数据库
        db_file = FileModel(
            original_name=original_name,
            stored_name=unique_filename,
            file_size=len(contents),
            mime_type=file.content_type
        )
        db.add(db_file)
        await db.commit()  # 提交异步事务
        await db.refresh(db_file)  # 刷新获取自增的 id

        # 3. 拼接返回结果
        file_url = f"{APP_HOST}/static/uploads/{unique_filename}"
        return {
            "status": "success",
            "message": "文件上传并记账成功",
            "data": {
                "id": db_file.id,  # 数据库里的自增 ID
                "original_name": db_file.original_name,
                "file_url": file_url,
                "created_at": db_file.created_at
            }
        }

    except Exception as e:
        await db.rollback()  # 发生异常时回滚数据库记录
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@app.get("/")
def read_root():
    return {"status": "running"}
