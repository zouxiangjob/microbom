"""
ECN 工程变更通知 API：查询 / 确认知晓 / 发布。
"""
from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.database.session import get_db
from app.services.ecn import build_ecn_diff_logs, ecn_notifier

router = APIRouter()


class EcnState(BaseModel):
    notifications: List[str]
    has_notifications: bool


class EcnPublishRequest(BaseModel):
    item_code: str


@router.get("/notifications", response_model=EcnState, summary="查询当前变更通知")
async def get_notifications():
    return EcnState(
        notifications=ecn_notifier.get(),
        has_notifications=ecn_notifier.has_notifications,
    )


@router.post("/ack", summary="确认知晓变更（清空通知）")
async def ack_notifications(_user=Depends(require_roles("admin", "purchase", "workshop"))):
    ecn_notifier.clear()
    return {"status": "success", "detail": "已确认知晓变更"}


@router.post("/publish", summary="发布变更通知（主管）")
async def publish_notification(
        payload: EcnPublishRequest,
        db: AsyncSession = Depends(get_db),
        _user=Depends(require_roles("admin")),
):
    logs = await build_ecn_diff_logs(db, payload.item_code)
    ecn_notifier.publish(logs)
    return {"status": "success", "detail": f"已下发 {payload.item_code} 的变更通知", "notifications": logs}
