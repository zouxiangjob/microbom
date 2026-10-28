"""
车间看图服务：按物料编码查询零件关联的 3D/2D 图纸文件。
"""
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import FileModel
from app.models.business import PartModel, DrawingModel, PartDrawingRelation
from app.services.graph import AsyncGraphCrudEngine


async def get_part_drawings(db: AsyncSession, code: str) -> Optional[Dict[str, Any]]:
    """按物料编码查询零件及其 3D/2D 图纸，返回渲染所需信息；未找到零件返回 None。"""
    parts = await AsyncGraphCrudEngine.query_nodes_by_property(
        db, PartModel, "part_number", code
    )
    if not parts:
        return None

    part = parts[0]
    part_props = part.properties or {}
    part_name = part_props.get("name", code)

    relations = await AsyncGraphCrudEngine.query_relations(
        db, PartDrawingRelation, source_id=part.id
    )

    glb: Optional[Dict[str, str]] = None
    pdf: Optional[Dict[str, str]] = None
    for rel in relations:
        drawing = await AsyncGraphCrudEngine.get_node_by_id(db, DrawingModel, rel.target_id)
        if not drawing:
            continue
        file_record = await db.get(FileModel, rel.target_id)
        if not file_record:
            continue

        original_lower = file_record.original_name.lower()
        item = {
            "url": f"/api/v1/files/download/{rel.target_id}?inline=true",
            "name": file_record.original_name,
        }
        if original_lower.endswith((".glb", ".gltf")):
            glb = item
        elif original_lower.endswith((".pdf", ".dxf", ".dwg", ".svg")):
            pdf = item
        elif not pdf:
            # 非标准格式 → 第一个作为 2D 图纸兜底
            pdf = item

    return {
        "part_id": str(part.id),
        "part_number": code,
        "part_name": part_name,
        "glb": glb,
        "pdf": pdf,
    }
