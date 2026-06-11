from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# 数据库文件将创建在 backend/ 根目录下
DATABASE_URL = "sqlite+aiosqlite:///./sql_app.db"

# 创建异步引擎
engine = create_async_engine(
    DATABASE_URL,
    echo=True,                         # 在控制台打印所有的 SQL 语句，方便开发调试
    connect_args={"check_same_thread": False}  # SQLite 特有参数，允许 FastAPI 多线程访问
)

# 创建异步 Session 工厂
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession
)

# 依赖注入函数：确保每个请求都有独立的 DB 会话，并在请求结束时自动关闭
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
