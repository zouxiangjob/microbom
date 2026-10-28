from typing import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import settings

DATABASE_URL = settings.DATABASE_URL

# ==============================================================================
# 1. 异步数据库引擎（供 FastAPI 路由层使用）
# ==============================================================================
engine = create_async_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLite 多线程访问所需参数
)

# 2. 异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False
)

# ==============================================================================
# 3. SQLite 连接配置：外键级联 + WAL 模式 + 锁超时
# ==============================================================================
# 事件须绑定在 engine.sync_engine 上，并使用原生 event 模块
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """每次建立连接时向 SQLite 写入 PRAGMA 配置。

    开启外键级联后，删除节点时才能自动触发 ON DELETE CASCADE 清理关联边。
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.execute("PRAGMA journal_mode=WAL;")  # WAL 模式提升读写并发性能
    cursor.execute("PRAGMA busy_timeout=5000;")  # 锁等待超时 5 秒，避免瞬时报错
    cursor.close()


# ==============================================================================
# 4. 会话依赖注入
# ==============================================================================
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 路由层通用的异步会话注入器（Depends(get_db)）。"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
