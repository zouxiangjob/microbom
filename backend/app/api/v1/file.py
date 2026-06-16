import os
from datetime import datetime
from pydantic import BaseModel, ConfigDict  # 👈 导入 ConfigDict
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.services.file_service import upload_and_bind_user

# 统一配置当前路由关心的外部常量
APP_HOST = "http://localhost:8000"

router = APIRouter(prefix="/files", tags=["文件管理"])

class FileOut(BaseModel):
    id: int
    original_name: str
    file_size: int
    mime_type: str  # 👈 核心修正：mime_type 必须是字符串 (str)
    file_url: str  # 👈 声明我们要给前端多返回一个动态拼接出来的公开网络 URL
    created_at: datetime

    # 👈 核心修正：Pydantic v2 标准的、允许读取 ORM 属性的高级配置语法
    model_config = ConfigDict(from_attributes=True)

@router.post("/upload", response_model=FileOut, summary="单文件上传")
async def upload_user_file(
        file: UploadFile = File(...),
        bus_id: str = Form(...),
        bus_type: str = Form(...),
        db: AsyncSession = Depends(get_db)
):
    try:
        # 调用业务层落盘与异步记账，拿到干净的 SQLAlchemy ORM 对象 (FileModel)
        new_file = await upload_and_bind_user(db, file, bus_id, bus_type)

        # 💡 高阶技巧：由于我们的 FileOut 契约中多写了一个数据库表里没有的字段 `file_url`，
        # 我们需要在返回前，动态把这个属性“强行塞给”这个 ORM 对象实例。
        # 这样 Pydantic 启动 attributes 读取时，就能完美捕捉到并返回给前端！
        new_file.file_url = f"{APP_HOST}/static/uploads/{new_file.stored_name}"

        # 自动执行字段剔除（如隐私的 stored_name 不会被发给前端）并格式化输出
        return new_file

    except Exception as e:
        # 职责严明：将任何底层或业务层逻辑失败，在看门人处翻译为标准的 HTTP 500
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/download", response_model=FileOut, summary="单文件下载")
async def downlod_user_file(
        bus_id: str,
        bus_type: str,
):
    # 这里我们不实现真正的下载逻辑了，因为 FastAPI 的 StaticFiles 已经帮我们做好了公开访问的路由
    # 只要前端拿到 FileOut 里那个 file_url 就能直接访问了
    pass;
