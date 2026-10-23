import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.database.session import get_db
from app.api.deps import require_roles
from app.schemas.baseline import (
    BaselineCreateRequest,
    BaselineDetailResponse,
    BaselineSummaryResponse,
)
from app.services.baseline import (
    create_baseline,
    diff_baselines,
    get_baseline,
    list_baselines,
)

router = APIRouter()


@router.post("", response_model=BaselineDetailResponse, status_code=status.HTTP_201_CREATED,
             summary="发布基线：冻结根总成当前完整 BOM 结构")
async def publish_baseline(
        payload: BaselineCreateRequest,
        db: AsyncSession = Depends(get_db),
        _user=Depends(require_roles("admin"))
):
    """以根总成为入口，递归深冻结其完整 BOM 树，落库到专用基线表。"""
    try:
        return await create_baseline(
            db,
            root_id=payload.root_id,
            name=payload.name,
            release_version=payload.release_version,
            note=payload.note,
            created_by=payload.created_by,
        )
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(val_err))


@router.get("", response_model=List[BaselineSummaryResponse], summary="基线列表")
async def query_baselines(
        root_id: Optional[uuid.UUID] = Query(None, description="按根总成过滤"),
        db: AsyncSession = Depends(get_db)
):
    return await list_baselines(db, root_id)


# 特异性更高的 diff 路由必须放在 /{baseline_id} 之前注册
@router.get("/{baseline_id}/diff", summary="双基线差异对比")
async def compare_baselines(
        baseline_id: uuid.UUID,
        other: uuid.UUID = Query(..., description="要对比的另一条基线 UUID"),
        db: AsyncSession = Depends(get_db)
):
    data = await diff_baselines(db, baseline_id, other)
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="基线不存在")
    return data


@router.get("/{baseline_id}", response_model=BaselineDetailResponse, summary="查看某条基线的冻结 BOM")
async def read_baseline(
        baseline_id: uuid.UUID,
        db: AsyncSession = Depends(get_db)
):
    data = await get_baseline(db, baseline_id)
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="基线不存在")
    return data
