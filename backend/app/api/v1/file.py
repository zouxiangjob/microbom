from datetime import datetime
from uuid import UUID as PyUUID
from typing import Dict, Any
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Path, Form
from pydantic import BaseModel, ConfigDict, computed_field, Field
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.responses import FileResponse

from app.config import settings
from app.database.session import get_db
# 🚀 导入多态业务模型，让文件管理也能感知“万物皆对象”
from app.models.business import AttachmentModel, DrawingModel, DocumentModel
from app.services.file_service import save_physical_file, get_file_for_download

router = APIRouter()

# 🎯 核心：统一维护的 URL 文件类型到真实 Python 类的多态映射映射
FILE_TYPE_MAPPER = {
    "attachment": AttachmentModel,
    "drawing": DrawingModel,
    "document": DocumentModel
}


# 修改 app/api/v1/endpoints/file.py (或 app/api/v1/file.py) 中的 Schema

class FileOut(BaseModel):
    object_id: PyUUID
    original_name: str
    file_size: int
    stored_name: str = Field(exclude=True)
    mime_type: str
    created_at: datetime

    # 💡 建议在原基础上增加这两个字段，前端在拿到响应时可以打上“物理秒传”的标签，开发体验极佳！
    # 由于我们在 save_physical_file 中把它们写进了关联节点，稍后在返回时也可以直接基于 ORM 关系拉取，
    # 或者直接保持你目前的返回。如果你希望返回更直观，可以用这个扩充版：

    @computed_field
    def file_url(self) -> str:
        return f"{settings.APP_HOST}/api/v1/files/download/{self.object_id}"

    model_config = ConfigDict(from_attributes=True)


# 🚀 【核心通用重构】：通过 {file_type} 动态路由适配所有文件节点
@router.post("/{file_type}/upload", response_model=FileOut, summary="通用多态物理文件后补上传")
async def upload_user_file(
        file_type: str = Path(..., description="文件类型，可选值: attachment, drawing, document"),
        object_id: PyUUID = Form(..., description="客户端在基表（objects）先行领到的全局唯一 UUID"),
        file: UploadFile = File(...),
        db: AsyncSession = Depends(get_db)
):
    """
    ### 通用文件上传网关
    前端/插件先提交网状拓扑结构（Nodes/Relations 织网），随后异步调用此接口补全物理落盘。
    系统会自动识别 `file_type` 并自适应解禁对应实体在基表中的 pending 状态。
    """
    # 1. 拦截不合法的类型
    if file_type not in FILE_TYPE_MAPPER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型: {file_type}。有效值请参考: {list(FILE_TYPE_MAPPER.keys())}"
        )

    # 2. 获取对应的多态子类
    model_cls = FILE_TYPE_MAPPER[file_type]

    try:
        # 3. 委托给自适应业务引擎
        new_file = await save_physical_file(db, file, object_id, model_cls)
        return new_file

    except ValueError as val_err:
        # 处理 UUID 与类型不匹配的异常（例如：拿 attachment 的 UUID 去调 drawing 的上传接口）
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(val_err))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/download/{object_id}", response_class=FileResponse, summary="通过对象UUID下载/查看文件")
async def download_file(
        object_id: PyUUID,
        db: AsyncSession = Depends(get_db)
):
    """
    车间扫码、图纸预览、附件下载的核心通用下载网关。
    """
    try:
        db_file = await get_file_for_download(db, object_id)
        return FileResponse(
            path=db_file.absolute_path,
            media_type=db_file.mime_type,
            filename=db_file.original_name
        )

    except ValueError as val_err:
        if str(val_err) == "File_Not_Found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该文件在系统中无任何记账记录")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))

    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="物理文件已从磁盘丢失或尚未传输完毕")

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
