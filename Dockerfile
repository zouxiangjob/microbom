#
# MicroBOM 单镜像多阶段构建：
#   阶段 1 用 Node 构建 Vue 前端 dist；
#   阶段 2 用 Python 运行时托管 dist + 提供 REST API（/api/v1/*）与文件下载。

# ==================== 阶段 1：构建 Vue 前端 ====================
FROM node:20-alpine AS frontend-build
WORKDIR /frontend

# 先拷贝依赖清单，利用镜像层缓存
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# 拷贝源码并构建，产物输出到 /frontend/dist
COPY frontend/ ./
RUN npm run build


# ==================== 阶段 2：后端运行时 ====================
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    # 关闭 NiceGUI 页面，改由 Vue SPA 接管根路径
    ENABLE_NICEGUI_UI=false \
    # 数据库默认落在 /app/data（与 docker-compose 一致，裸 docker run 也不混淆）
    DATABASE_URL=sqlite+aiosqlite:////app/data/sql_app.db

WORKDIR /app

# 先装依赖，利用镜像层缓存
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝后端代码（alembic.ini、migrations/、app/ 等）
COPY backend/ ./

# 拷贝前端构建产物，交由后端托管
COPY --from=frontend-build /frontend/dist ./static

# 运行期数据目录（挂载卷持久化）
RUN mkdir -p /app/data /app/uploads /app/logs

# 启动脚本：先执行数据库迁移，再拉起服务
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
