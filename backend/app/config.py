from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 1. 定义配置项和类型（可以设置默认值）
    PROJECT_NAME: str = "backend"
    APP_HOST: str = "http://localhost:8000"
    DATABASE_URL: str = "sqlite+aiosqlite:///./sql_app.db"
    UPLOAD_DIR: str = "./uploads"


    # 2. 自动读取本地的 .env 环境文件
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# 实例化成一个全局可调用的对象
settings = Settings()