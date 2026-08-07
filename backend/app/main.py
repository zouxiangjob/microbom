import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from nicegui import ui
from starlette.middleware.cors import CORSMiddleware

from app.config import settings
# 导入数据库相关组件

from app.database.session import engine, get_db
from app.models.base import Base
from app.api.v1 import api_router

# 导入你的全新全局拦截总线
from app.middleware.exceptions import setup_exception_handlers
from app.views.engineer import render_engineer_page




UPLOAD_DIR = settings.UPLOAD_DIR  # 从 config 读取，已是绝对路径
APP_HOST = settings.APP_HOST

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时：确保上传目录存在
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    # 启动时：自动建表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # 启动时：修复历史数据中的相对存储路径为绝对路径
    from app.database.session import sync_engine
    from sqlalchemy import select, update
    from app.models.base import FileModel
    with sync_engine.connect() as sync_conn:
        result = sync_conn.execute(
            select(FileModel.object_id, FileModel.absolute_path).where(
                FileModel.absolute_path.like("./%")
            )
        )
        fixed = 0
        for row in result:
            abs_path = os.path.abspath(row[1])
            sync_conn.execute(
                update(FileModel)
                .where(FileModel.object_id == row[0])
                .values(absolute_path=abs_path)
            )
            fixed += 1
        if fixed:
            sync_conn.commit()
            print(f"[startup] 已修复 {fixed} 条历史文件路径为绝对路径")

    yield
    # 关闭时：释放引擎
    await engine.dispose()


app = FastAPI(title="MicroBOM API", lifespan=lifespan)


# 1. 激活并挂载全局异常拦截机制
setup_exception_handlers(app)

# 2. 动态 CORS：反射请求 Origin，兼容 localhost 和 data: URI 的 null origin
#    注意 allow_credentials=True 不能与 allow_origins=["*"] 共存（CORS 规范禁止）
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r".*",  # 反射所有 Origin（包括 null），匹配 localhost / 127.0.0.1 / data: URI
    allow_credentials=False,   # 关闭凭证 — API 不走 cookie 认证，避免 null origin 被 Chrome 拦截
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

app.include_router(api_router, prefix="/api/v1")



# =====================================================================
# 3. 注册你的 3 个全栈网页路由路径
# =====================================================================
@ui.page('/')
@ui.page('/index')
def home():
    render_engineer_page()

@ui.page('/engineer')
def engineer():
    from app.views.engineer import render_engineer_page
    render_engineer_page()

@ui.page('/engineer_detail')
def engineer_detail():
    from app.views.engineer_detail import render_engineer_detail_page
    render_engineer_detail_page()

@ui.page('/purchase')
def purchase():
    from app.views.purchase import render_purchase_page
    render_purchase_page()

@ui.page('/workshop')
def workshop():
    from app.views.workshop import render_workshop_page
    render_workshop_page()


# 4. 核心魔线：让 NiceGUI 寄生在 FastAPI 上
ui.run_with(app, storage_secret=settings.FACTORY_STORAGE_SECRET)




