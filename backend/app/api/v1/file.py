from datetime import datetime
from uuid import UUID as PyUUID
from typing import Dict, Any
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Path, Form
from pydantic import BaseModel, ConfigDict, computed_field, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.responses import FileResponse

from app.config import settings
from app.database.session import get_db
from app.api.deps import require_roles
from app.models.business import AttachmentModel, DrawingModel, DocumentModel
from app.models import FileModel
from app.services.file_service import save_physical_file, get_file_for_download

router = APIRouter()

# URL 文件类型到模型类的映射
FILE_TYPE_MAPPER = {
    "attachment": AttachmentModel,
    "drawing": DrawingModel,
    "document": DocumentModel
}


class FileOut(BaseModel):
    object_id: PyUUID
    original_name: str
    file_size: int
    stored_name: str = Field(exclude=True)
    mime_type: str
    created_at: datetime

    @computed_field
    def file_url(self) -> str:
        return f"{settings.APP_HOST}/api/v1/files/download/{self.object_id}"

    model_config = ConfigDict(from_attributes=True)


@router.post("/{file_type}/upload", response_model=FileOut, summary="通用多态文件上传")
async def upload_user_file(
        file_type: str = Path(..., description="文件类型，可选值: attachment, drawing, document"),
        object_id: PyUUID = Form(..., description="客户端在基表（objects）中已创建的全局唯一 UUID"),
        file: UploadFile = File(...),
        db: AsyncSession = Depends(get_db),
        _user=Depends(require_roles("admin", "engineer"))
):
    """上传物理文件并登记元数据；系统按 file_type 识别对应的多态模型。"""
    if file_type not in FILE_TYPE_MAPPER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型: {file_type}。有效值请参考: {list(FILE_TYPE_MAPPER.keys())}"
        )

    model_cls = FILE_TYPE_MAPPER[file_type]

    try:
        new_file = await save_physical_file(db, file, object_id, model_cls)
        return new_file

    except ValueError as val_err:
        # UUID 与类型不匹配（例如拿 attachment 的 UUID 调 drawing 的上传接口）
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(val_err))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/download/{object_id}", response_class=FileResponse, summary="通过对象 UUID 下载/查看文件")
async def download_file(
        object_id: PyUUID,
        inline: bool = True,
        db: AsyncSession = Depends(get_db)
):
    """下载或查看文件的通用接口。

    - inline=true（默认）：浏览器内联显示，不触发下载。
    - inline=false：强制下载（Content-Disposition: attachment）。
    """
    try:
        db_file = await get_file_for_download(db, object_id)
        # inline 模式下不传 filename，Starlette 不设置 Content-Disposition，浏览器内联渲染
        kwargs: Dict[str, Any] = dict(
            path=db_file.absolute_path,
            media_type=db_file.mime_type,
        )
        if not inline:
            kwargs["filename"] = db_file.original_name
        return FileResponse(**kwargs)

    except ValueError as val_err:
        if str(val_err) == "File_Not_Found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该文件在系统中无任何文件记录")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))

    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="物理文件已从磁盘丢失或尚未传输完毕")

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{object_id}", response_model=FileOut, summary="通过对象 UUID 查询文件元数据")
async def get_file_meta(
        object_id: PyUUID,
        db: AsyncSession = Depends(get_db)
):
    """查询对象是否已关联物理文件，返回文件名/大小/MIME 等元数据；无记录则 404。"""
    result = await db.execute(select(FileModel).where(FileModel.object_id == object_id))
    db_file = result.scalar_one_or_none()
    if not db_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该文件在系统中无任何文件记录")
    return db_file
