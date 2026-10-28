"""
采购 API：BOM 打平汇总 + ERP 采购导入 Excel 导出。
"""
from typing import List
from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.database.session import get_db
from app.services.graph import AsyncGraphCrudEngine
from app.services.purchase import build_purchase_excel

router = APIRouter()

_EXCEL_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_EXCEL_FILENAME = "采购订单导入表.xlsx"


class PurchaseRow(BaseModel):
    code: str
    name: str = ""
    spec: str = ""
    qty: int = 0
    unit: str = "个"


@router.get("/flatten", response_model=List[PurchaseRow], summary="BOM 打平汇总清单")
async def flatten_purchase_bom(db: AsyncSession = Depends(get_db)):
    """全量 BOM 打平并按零件编码聚合，返回采购清单行。"""
    return await AsyncGraphCrudEngine.flatten_bom(db)


@router.post("/export", summary="导出 ERP 采购导入 Excel")
async def export_purchase_excel(
        db: AsyncSession = Depends(get_db),
        _user=Depends(require_roles("admin", "purchase")),
):
    """将当前 BOM 打平汇总导出为 ERP 标准采购导入 Excel。"""
    rows = await AsyncGraphCrudEngine.flatten_bom(db)
    content = build_purchase_excel(rows)
    headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(_EXCEL_FILENAME)}"}
    return Response(content=content, media_type=_EXCEL_MEDIA_TYPE, headers=headers)
