import os
from uuid import uuid4
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession

# 导入数据库相关组件
from app.database.session import engine, get_db
from app.models.base import Base
from app.api.v1 import api_router
from app.models.file import FileModel  # ⚠️ 必须导入，否则 Base 无法识别并建表

UPLOAD_DIR = "./uploads"
APP_HOST = "http://localhost:8000"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时：确保本地上传文件夹存在
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    # 启动时：自动在 backend/ 下创建 sql_app.db 文件并建立 files 数据表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield
    # 关闭时：释放引擎
    await engine.dispose()


app = FastAPI(title="MicroBOM API", lifespan=lifespan)
app.mount("/static/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

app.include_router(api_router, prefix="/api/v1")




