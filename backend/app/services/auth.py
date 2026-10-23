"""
认证服务：bcrypt 密码哈希、JWT 签发/解析、登录认证、默认用户种子。
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import UserModel


# ==============================================================================
# 1. 密码哈希（bcrypt）
# ==============================================================================

def hash_password(password: str) -> str:
    """对明文密码做 bcrypt 哈希，返回可存储的字符串。"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """校验明文密码与哈希是否匹配。"""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ==============================================================================
# 2. JWT 签发与解析
# ==============================================================================

def create_access_token(user_id: uuid.UUID, role: str) -> str:
    """签发 JWT：sub 存用户 ID，role 存角色，exp 存过期时间。"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "role": role, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """解析并校验 JWT，返回 payload；无效/过期抛 jwt.PyJWTError。"""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


# ==============================================================================
# 3. 登录认证
# ==============================================================================

async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[UserModel]:
    """校验用户名密码，成功返回用户，失败返回 None。"""
    result = await db.execute(select(UserModel).where(UserModel.username == username))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


# ==============================================================================
# 4. 默认用户种子
# ==============================================================================

# 开发环境默认演示账号（生产环境务必替换为真实账号管理）
_DEFAULT_USERS = [
    {"username": "admin", "password": "admin123", "role": "admin"},
    {"username": "engineer", "password": "engineer123", "role": "engineer"},
    {"username": "purchase", "password": "purchase123", "role": "purchase"},
    {"username": "workshop", "password": "workshop123", "role": "workshop"},
]


async def seed_default_users(db: AsyncSession) -> int:
    """users 表为空时创建默认演示账号，返回创建数量。"""
    count = (await db.execute(select(func.count(UserModel.id)))).scalar_one()
    if count:
        return 0
    for item in _DEFAULT_USERS:
        db.add(UserModel(
            username=item["username"],
            password_hash=hash_password(item["password"]),
            role=item["role"],
        ))
    await db.commit()
    return len(_DEFAULT_USERS)
