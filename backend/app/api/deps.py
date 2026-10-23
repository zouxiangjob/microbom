"""
FastAPI 鉴权依赖注入：解析 JWT 获取当前用户 + 角色校验。
"""
import uuid
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.session import get_db
from app.models.user import UserModel
from app.services.auth import decode_token

# 从 Authorization: Bearer <token> 提取令牌；auto_error=False 让无令牌时返回 None 而非自动 401
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
        db: AsyncSession = Depends(get_db),
) -> UserModel:
    """解析 Bearer token，返回当前登录用户；失败抛 401。"""
    # 鉴权开关关闭时跳过令牌校验，返回匿名管理员（角色 admin 使所有 require_roles 均放行）
    if not settings.AUTH_ENABLED:
        return UserModel(
            id=uuid.uuid4(),
            username="anonymous",
            password_hash="",
            role="admin",
            is_active=True,
        )
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供认证令牌")

    try:
        payload = decode_token(credentials.credentials)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌无效或已过期")

    try:
        user_id = uuid.UUID(payload.get("sub", ""))
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌无效")

    user = await db.get(UserModel, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已停用")
    return user


def require_roles(*allowed_roles: str):
    """角色校验依赖工厂：当前用户角色不在允许列表则 403。"""
    async def checker(user: UserModel = Depends(get_current_user)) -> UserModel:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足：需要角色 {'/'.join(allowed_roles)}",
            )
        return user
    return checker
