import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "backend"
    APP_HOST: str = "http://localhost:8000"
    DATABASE_URL: str = "sqlite+aiosqlite:///./sql_app.db"
    UPLOAD_DIR: str = "./uploads"
    EXPORT_DIR: str = "./uploads"
    FACTORY_STORAGE_SECRET: str = ""  # 必须在 .env 文件中配置，切勿在源码中写死
    MODEL_VIEWER_CDN: str = "https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js"
    JWT_SECRET: str = "dev-secret-change-me"  # 生产环境必须在 .env 配置
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # token 24 小时过期
    AUTH_ENABLED: bool = False  # 是否启用 JWT 鉴权；开发期临时关闭，生产环境设为 True 或 .env 配 AUTH_ENABLED=true

    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "./logs"
    LOG_FILE: str = "app.log"
    LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 单文件 10MB 轮转
    LOG_BACKUP_COUNT: int = 5
    SQL_ECHO: bool = False  # 调试时打开 sqlalchemy 引擎 SQL 回显

    # 前端托管：Vue SPA 构建产物目录 + NiceGUI 页面开关
    ENABLE_NICEGUI_UI: bool = True  # False 时关闭 NiceGUI 页面，改由 Vue SPA 接管根路径
    FRONTEND_DIST_DIR: str = "./static"  # Vue SPA 构建产物目录（镜像内为 /app/static）

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    def model_post_init(self, _context) -> None:
        """将相对路径转为绝对路径，避免工作目录变化导致文件定位失败。"""
        super().model_post_init(_context)
        self.UPLOAD_DIR = os.path.abspath(self.UPLOAD_DIR)
        self.EXPORT_DIR = os.path.abspath(self.EXPORT_DIR)
        self.LOG_DIR = os.path.abspath(self.LOG_DIR)
        self.FRONTEND_DIST_DIR = os.path.abspath(self.FRONTEND_DIST_DIR)


settings = Settings()
