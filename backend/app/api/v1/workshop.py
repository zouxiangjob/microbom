"""
车间看图 API：按物料编码/条码查询 3D/2D 图纸。
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.services.workshop import get_part_drawings

router = APIRouter()


class DrawingView(BaseModel):
    url: str
    name: str


class WorkshopDrawingResponse(BaseModel):
    part_id: str
    part_number: str
    part_name: str
    glb: Optional[DrawingView] = None
    pdf: Optional[DrawingView] = None


@router.get("/drawings", response_model=WorkshopDrawingResponse, summary="按物料编码查询车间图纸")
async def query_drawings(
        code: str = Query(..., min_length=1, description="物料编码/条码"),
        db: AsyncSession = Depends(get_db),
):
    data = await get_part_drawings(db, code)
    if data is None:
        raise HTTPException(status_code=404, detail=f"未找到物料编码 [{code}]，请检查输入是否正确")
    return data
