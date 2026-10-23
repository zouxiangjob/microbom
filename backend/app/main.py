import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from nicegui import ui
from starlette.middleware.cors import CORSMiddleware

from app.config import settings
from app.database.session import engine, get_db
from app.api.v1 import api_router
from app.logging_config import get_logger, setup_logging
from app.middleware.exceptions import setup_exception_handlers
from app.middleware.logging import RequestLoggingMiddleware
from app.views.engineer import render_engineer_page

setup_logging()
logger = get_logger("main")

UPLOAD_DIR = settings.UPLOAD_DIR  # 从 config 读取，已是绝对路径
APP_HOST = settings.APP_HOST


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时：确保上传目录存在
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # 建表由 Alembic 负责（部署时执行 `alembic upgrade head`）
    # 启动时：无用户则创建默认演示账号
    from app.database.session import AsyncSessionLocal
    from app.services.auth import seed_default_users
    async with AsyncSessionLocal() as session:
        created = await seed_default_users(session)
        if created:
            logger.info("已创建 %d 个默认演示用户", created)

    # 启动时：修复历史数据中的相对存储路径为绝对路径
    from sqlalchemy import select, update
    from app.models.base import FileModel
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(FileModel.object_id, FileModel.absolute_path).where(
                FileModel.absolute_path.like("./%")
            )
        )
        fixed = 0
        for row in result:
            abs_path = os.path.abspath(row[1])
            await session.execute(
                update(FileModel)
                .where(FileModel.object_id == row[0])
                .values(absolute_path=abs_path)
            )
            fixed += 1
        if fixed:
            await session.commit()
            logger.info("已修复 %d 条历史文件路径为绝对路径", fixed)

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
    allow_origin_regex=r".*",  # 反射所有 Origin（包括 null）
    allow_credentials=False,   # 关闭凭证：API 不走 cookie 认证
    allow_methods=["*"],
    allow_headers=["*"],
)

# 访问日志中间件：记录每个请求的 method/path/status/耗时
app.add_middleware(RequestLoggingMiddleware)

app.mount("/static/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

app.include_router(api_router, prefix="/api/v1")


# ==============================================================================
# 3. 注册网页路由（NiceGUI 页面）
#    ENABLE_NICEGUI_UI=False 时（如 Docker 镜像）不注册，由 Vue SPA 接管根路径。
# ==============================================================================
if settings.ENABLE_NICEGUI_UI:
    @ui.page('/')
    @ui.page('/index')
    async def home():
        await render_engineer_page()


    @ui.page('/engineer')
    async def engineer():
        from app.views.engineer import render_engineer_page
        await render_engineer_page()


    @ui.page('/engineer_detail')
    async def engineer_detail():
        from app.views.engineer_detail import render_engineer_detail_page
        await render_engineer_detail_page()


    @ui.page('/purchase')
    async def purchase():
        from app.views.purchase import render_purchase_page
        await render_purchase_page()


    @ui.page('/workshop')
    async def workshop():
        from app.views.workshop import render_workshop_page
        render_workshop_page()


    # 4. 让 NiceGUI 复用 FastAPI 服务
    ui.run_with(app, storage_secret=settings.FACTORY_STORAGE_SECRET)


# ==============================================================================
# 5. 托管 Vue SPA 构建产物（dist），作为镜像默认对外界面。
#    仅在 FRONTEND_DIST_DIR 目录存在时启用；本地开发由 Vite dev server 提供。
# ==============================================================================
if os.path.isdir(settings.FRONTEND_DIST_DIR):
    # 静态资源（JS/CSS 等）单独挂载，走正确的 MIME 与缓存
    assets_dir = os.path.join(settings.FRONTEND_DIST_DIR, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="spa-assets")

    # 兜底路由：非 API / 上传 / 文档 / NiceGUI 内部路径的 GET 请求，回退到 SPA 的 index.html
    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        # 避免把不存在的 API 请求吞成 index.html
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = os.path.join(settings.FRONTEND_DIST_DIR, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(settings.FRONTEND_DIST_DIR, "index.html"))
