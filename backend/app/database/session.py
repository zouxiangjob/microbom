from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from app.config import settings

# 1. 安全防御：确保你的 URL 使用的是 aiosqlite 异步驱动
DATABASE_URL = settings.DATABASE_URL
if DATABASE_URL.startswith("sqlite://") and not DATABASE_URL.startswith("sqlite+aiosqlite://"):
    DATABASE_URL = DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")

# 2. 创建异步引擎
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # 开发环境打印 SQL 方便调试
    connect_args={
        "check_same_thread": False,  # 允许 FastAPI 在不同线程的事件循环间复用连接
        "timeout": 30                # 修正：将锁等待超时从默认 5 秒延长到 30 秒，极大缓解 locked 报错
    }
)

# 3. 创建异步 Session 工厂
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,  # 配合 AsyncGraphCrudEngine 的 refresh() 必须设为 False
    class_=AsyncSession
)

# 4. 🚀 核心优化：通过引擎级事件，强制开启 SQLite 的 WAL 高性能并发模式
@engine.認證_event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")  # 开启 WAL 模式，允许读写并发
    cursor.execute("PRAGMA synchronous=NORMAL") # 优化刷盘策略，成倍提升写入速度
    cursor.close()

# 5. 依赖注入函数（保持不变，你原先的写法非常标准！）
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
