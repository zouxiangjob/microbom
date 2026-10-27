"""
分类编码器 API：为各分类配置 code 生成规则并生成编码。
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.database.session import get_db
from app.api.deps import require_roles
from app.schemas.category_encoder import (
    CategoryEncoderCreate,
    CategoryEncoderResponse,
    CategoryEncoderUpdate,
    GeneratedCodeResponse,
)
from app.services.category_encoder import (
    create_encoder,
    delete_encoder,
    generate_code,
    get_encoder_by_category,
    update_encoder,
    validate_encoder_payload,
)

router = APIRouter()


@router.post("", response_model=CategoryEncoderResponse, status_code=status.HTTP_201_CREATED,
             summary="为分类配置编码器")
async def create_category_encoder(
        payload: CategoryEncoderCreate,
        db: AsyncSession = Depends(get_db),
        _user=Depends(require_roles("admin", "engineer")),
):
    """为分类配置编码器（1:1，已存在则 409）。"""
    err = validate_encoder_payload(
        payload.encoder_type, payload.prefix, payload.start_seq,
        payload.end_seq, payload.seq_length, payload.encoder_script,
    )
    if err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=err)
    try:
        return await create_encoder(db, **payload.model_dump())
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(val_err))


@router.get("/{category_id}", response_model=CategoryEncoderResponse, summary="查询分类的编码器")
async def read_category_encoder(
        category_id: uuid.UUID,
        db: AsyncSession = Depends(get_db),
):
    enc = await get_encoder_by_category(db, category_id)
    if not enc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该分类未配置编码器")
    return enc


@router.put("/{category_id}", response_model=CategoryEncoderResponse, summary="更新分类编码器")
async def update_category_encoder(
        category_id: uuid.UUID,
        payload: CategoryEncoderUpdate,
        db: AsyncSession = Depends(get_db),
        _user=Depends(require_roles("admin", "engineer")),
):
    try:
        return await update_encoder(db, category_id, payload.model_dump(exclude_unset=True))
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(val_err))


@router.delete("/{category_id}", summary="删除分类编码器")
async def delete_category_encoder(
        category_id: uuid.UUID,
        db: AsyncSession = Depends(get_db),
        _user=Depends(require_roles("admin", "engineer")),
):
    ok = await delete_encoder(db, category_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该分类未配置编码器")
    return {"status": "success", "detail": f"分类 {category_id} 的编码器已删除"}


@router.post("/{category_id}/generate", response_model=GeneratedCodeResponse, summary="生成下一个编码")
async def generate_category_code(
        category_id: uuid.UUID,
        db: AsyncSession = Depends(get_db),
        _user=Depends(require_roles("admin", "engineer")),
):
    """按分类编码规则生成下一个编码，更新最新已生成编码后返回。"""
    try:
        code = await generate_code(db, category_id)
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(val_err))
    return GeneratedCodeResponse(code=code)
