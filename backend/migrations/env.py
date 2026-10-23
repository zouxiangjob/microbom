from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# 导入所有模型，确保 Base.metadata 包含全部表（供 autogenerate 使用）
from app.models.base import Base
import app.models.business  # noqa: F401
import app.models.baseline  # noqa: F401
import app.models.user  # noqa: F401
from app.config import settings

# Alembic Config 对象，提供对 .ini 文件值的访问
config = context.config

# 配置 Python 日志
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 从应用配置读取数据库 URL（转为同步 URL，供 Alembic 使用）
config.set_main_option(
    "sqlalchemy.url",
    settings.DATABASE_URL.replace("sqlite+aiosqlite://", "sqlite://"),
)

# 用于 autogenerate 的目标元数据
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """以离线模式运行迁移（不连接数据库，仅生成 SQL）。"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """以在线模式运行迁移（连接数据库执行）。"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
