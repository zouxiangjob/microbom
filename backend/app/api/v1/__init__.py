from fastapi import APIRouter

# 核心修正：必须在这里显式导入对应的 router 变量
from app.api.v1.file import router as file_router
from app.api.v1.nodes import router as nodes_router
from app.api.v1.relations import router as relations_router

api_router = APIRouter()

# 挂载物理文件流相关接口
api_router.include_router(file_router, prefix="/files", tags=["文件档案管理"])

# 挂载万物皆对象的“多态节点”通用增删改查接口
api_router.include_router(nodes_router, prefix="/nodes", tags=["图谱实体节点"])

# 挂载建立网络连接、BOM物料树穿透、图谱漫游等高阶接口
api_router.include_router(relations_router, prefix="/relations", tags=["网状拓扑边与BOM依赖"])
