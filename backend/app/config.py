from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "backend"
    APP_HOST: str = "http://localhost:8000"
    DATABASE_URL: str = "sqlite+aiosqlite:///./sql_app.db"
    UPLOAD_DIR: str = "./uploads"
    EXPORT_DIR: str = "./uploads"
    FACTORY_STORAGE_SECRET: str = ""  # ⚠️ 必须在 .env 文件中配置，切勿在源码中写死
    MODEL_VIEWER_CDN: str = "https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()