#!/bin/sh
set -e

# 应用数据库迁移（幂等：表已存在则跳过；首次启动在挂载卷上创建全部表）
alembic upgrade head

# 可选：首次启动且数据库为空时灌入演示数据（会清空并重建，谨慎使用）
# 手动执行方式：docker compose exec microbom python seed_data.py

# 拉起 FastAPI 服务
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
