import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from app.config import settings
# 导入数据库相关组件

from app.database.session import engine, get_db
from app.models.base import Base
from app.api.v1 import api_router

# 导入你的全新全局拦截总线
from app.middleware.exceptions import setup_exception_handlers

UPLOAD_DIR = settings.UPLOAD_DIR  # 从配置中读取上传目录路径
APP_HOST = settings.APP_HOST  # 从配置中读取应用主机地址

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时：确保本地上传文件夹存在
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    # 启动时：自动在 backend/ 下创建 sql_app.db 文件并建立 files 数据表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield
    # 关闭时：释放引擎
    await engine.dispose()


app = FastAPI(title="MicroBOM API", lifespan=lifespan)


# 1. 激活并挂载全局异常拦截机制
setup_exception_handlers(app)

# 2. 补齐生产级跨域中间件，彻底解决前后端分离部署导致的拒绝请求问题
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 联调时允许全域名，生产环境建议换成确切的前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

app.include_router(api_router, prefix="/api/v1")




