import os
from typing import AsyncGenerator
from sqlalchemy import event  # 🔥 修正：必须从 sqlalchemy 中直接导入 event 模块
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# 从配置中读取数据库路径，如果不存在则默认在本地 backend 下创建 sql_app.db
# 你可以根据实际配置修改，通常格式为 sqlite+aiosqlite:///./sql_app.db
DATABASE_URL = "sqlite+aiosqlite:///./sql_app.db"

# 1. 创建全异步数据库引擎
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
# 3. 核心修正：正确配置 SQLite 异步环境下的物理外键级联监听总线
# ==============================================================================
# 注意：必须把事件绑定在 engine.sync_engine 上，且使用原生 event 模块
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    🎯 核心安全防御：每次数据库连接建立时，强制向 SQLite 灌入外键激活指令。
    只有这样，你删除零部件节点时，底层的边连线才能全自动触发 ON DELETE CASCADE 级联清理！
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.close()

# ==============================================================================
# 4. FastAPI 专用的依赖注入会话生成器
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
