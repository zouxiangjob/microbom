"""
全局日志配置：统一控制台 + 滚动文件的输出格式与级别，供应用启动时调用。
"""
import logging
import logging.config
import logging.handlers
import os

from app.config import settings

# 人类可读文本格式：时间 + 级别 + 模块名 + 消息
_LOG_FORMAT = "%(asctime)s %(levelname)-8s [%(name)s] %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 已初始化标记，避免重复配置（如 uvicorn --reload 多次触发）
_initialized = False


def setup_logging() -> None:
    """按 settings 配置根日志器：控制台 + 滚动文件，人类可读文本格式。"""
    global _initialized
    if _initialized:
        return
    _initialized = True

    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    os.makedirs(settings.LOG_DIR, exist_ok=True)
    log_file = os.path.join(settings.LOG_DIR, settings.LOG_FILE)

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": _LOG_FORMAT,
                "datefmt": _DATE_FORMAT,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": level,
                "formatter": "default",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": level,
                "formatter": "default",
                "filename": log_file,
                "maxBytes": settings.LOG_MAX_BYTES,
                "backupCount": settings.LOG_BACKUP_COUNT,
                "encoding": "utf-8",
            },
        },
        "root": {
            "level": level,
            "handlers": ["console", "file"],
        },
        "loggers": {
            "app": {"level": level, "propagate": True},
            # 第三方库降噪：只保留告警及以上
            "aiosqlite": {"level": "WARNING"},
            "uvicorn": {"level": level},
            "uvicorn.access": {"level": "WARNING"},
            # SQL 回显开关
            "sqlalchemy.engine": {
                "level": "INFO" if settings.SQL_ECHO else "WARNING",
            },
        },
    }

    logging.config.dictConfig(config)


def get_logger(name: str) -> logging.Logger:
    """获取 app 命名空间下的日志器，如 get_logger('main') → app.main。"""
    return logging.getLogger(f"app.{name}")
