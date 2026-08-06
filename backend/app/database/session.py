import os
from contextlib import contextmanager
from typing import AsyncGenerator, Generator

from sqlalchemy import event, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import settings

DATABASE_URL = settings.DATABASE_URL

# ==============================================================================
# 1. 创建全异步数据库引擎 (供 FastAPI 路由层使用)
# ==============================================================================
engine = create_async_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLite 多线程并发防御必备参数
)

# 2. 创建全异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False
)

# ==============================================================================
# 3. 创建同步数据库引擎 (供 NiceGUI 视图层在事件循环内同步调用)
# ==============================================================================
SYNC_DATABASE_URL = DATABASE_URL.replace("sqlite+aiosqlite://", "sqlite://")
sync_engine = create_engine(
    SYNC_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)
SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autoflush=False,
    expire_on_commit=False,
)


# ==============================================================================
# 4. 核心修正：正确配置 SQLite 异步环境下的物理外键级联监听总线
# ==============================================================================
# 注意：必须把事件绑定在 engine.sync_engine 上，且使用原生 event 模块
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    🎯 核心安全防御：每次数据库连接建立时，强制向 SQLite 灌入外键激活指令。
    只有这样，你删除零部件节点时，底层的边连线才能全自动触发 ON DELETE CASCADE 级联清理！
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON;")   # 开启外键级联
    cursor.execute("PRAGMA journal_mode=WAL;")  # 🔥 核心：开启 WAL 模式 (大幅提升读写并发性能)
    cursor.execute("PRAGMA busy_timeout=5000;")  # 🔥 核心：等待锁的超时时间设为 5 秒，避免瞬间报错
    cursor.close()


# ==============================================================================
# 5. 同步引擎上也激活外键 (供 NiceGUI 视图层使用)
# ==============================================================================
@event.listens_for(sync_engine, "connect")
def set_sync_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA busy_timeout=5000;")
    cursor.close()


# ==============================================================================
# 6. FastAPI 专用的依赖注入会话生成器
# ==============================================================================
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI 路由层通用的 Depends(get_db) 会话注入器
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@contextmanager
def get_sync_db() -> Generator[Session, None, None]:
    """
    NiceGUI 视图层专用的同步会话上下文管理器。
    在事件循环已运行的环境中，使用同步引擎安全地访问数据库。
    """
    with SyncSessionLocal() as session:
        try:
            yield session
        finally:
            session.close()
