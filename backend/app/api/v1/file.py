from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.schemas.file import FileOut
from app.services.file_service import upload_and_bind_user

router = APIRouter(prefix="/files", tags=["文件管理"])

@router.post("/upload", response_model=FileOut)
async def upload_user_file(
    file: UploadFile = File(...), 
    user_id: int = 1, # 这里实际开发中应从 Token/依赖注入中获取当前登录用户的 ID
    db: AsyncSession = Depends(get_db)
):
    # 调用服务层，完成落盘与数据库绑定
    new_file = await upload_and_bind_user(db, file, user_id)
    return new_file
