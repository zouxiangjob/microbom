import uuid
from typing import List, Optional, Type, TypeVar, Dict, Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.base import ObjectModel, RelationModel

# 定义泛型以支持完美的 IDE 类型推导
T_Node = TypeVar("T_Node", bound=ObjectModel)
T_Edge = TypeVar("T_Edge", bound=RelationModel)


class AsyncGraphCrudEngine:
    """万物皆对象的全异步通用图谱业务引擎"""

    # ==================== 1. 节点对象 (Node) 业务逻辑 ====================

    @staticmethod
    async def create_node(db: AsyncSession, node: ObjectModel) -> ObjectModel:
        """异步创建节点：传入任意子类实例(Part/Document等)，自动识别多态标识并持久化"""
        db.add(node)
        await db.commit()
        await db.refresh(node)
        return node

    @staticmethod
    async def get_node_by_id(db: AsyncSession, model_cls: Type[T_Node], node_id: uuid.UUID) -> Optional[T_Node]:
        """异步精准节点查询：根据指定业务类和 UUID 获取节点，若类型不匹配自动返回 None"""
        node = await db.get(ObjectModel, node_id)
        if isinstance(node, model_cls):
            return node
        return None

    @staticmethod
    async def query_nodes_by_type(db: AsyncSession, model_cls: Type[T_Node], limit: int = 100, offset: int = 0) -> List[
        T_Node]:
        """异步分页查询同类节点：例如传入 PartModel，则只筛选出零件类型的列表"""
        stmt = select(model_cls).offset(offset).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def update_node_properties(db: AsyncSession, node: ObjectModel, updates: Dict[str, Any]) -> ObjectModel:
        """异步非结构化增量更新：无损合并更新底层的 JSONB/JSON 属性字典"""
        current_props = dict(node.properties) if node.properties else {}
        current_props.update(updates)
        node.properties = current_props
        await db.commit()
        await db.refresh(node)
        return node

    @staticmethod
    async def delete_node(db: AsyncSession, node: ObjectModel) -> bool:
        """异步物理级联删除：抹除节点的同时，依赖底层的 ON DELETE CASCADE 自动清理所有关联边"""
        await db.delete(node)
        await db.commit()
        return True

    # ==================== 2. 关系边 (Edge) 业务逻辑 ====================

    @staticmethod
    async def create_relation(db: AsyncSession, relation: RelationModel) -> RelationModel:
        """异步织网：在任意两个已存在的节点之间建立关系连接（如：BOM 组装、文档引用等）"""
        db.add(relation)
        await db.commit()
        await db.refresh(relation)
        return relation

    @staticmethod
    async def get_relation_by_id(db: AsyncSession, model_cls: Type[T_Edge], edge_id: uuid.UUID) -> Optional[T_Edge]:
        """异步精准关系查询：根据特定关系类和 UUID 查询关系边"""
        edge = await db.get(RelationModel, edge_id)
        if isinstance(edge, model_cls):
            return edge
        return None

    @staticmethod
    async def query_relations(
            db: AsyncSession,
            model_cls: Type[T_Edge],
            source_id: Optional[uuid.UUID] = None,
            target_id: Optional[uuid.UUID] = None
    ) -> List[T_Edge]:
        """动态网状关系过滤：支持按起点、终点或双向共同筛选关系列表"""
        stmt = select(model_cls)
        filters = []
        if source_id:
            filters.append(model_cls.source_id == source_id)
        if target_id:
            filters.append(model_cls.target_id == target_id)

        if filters:
            stmt = stmt.where(and_(*filters))

        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def update_relation_properties(db: AsyncSession, relation: RelationModel,
                                         updates: Dict[str, Any]) -> RelationModel:
        """异步更新关系边属性：例如修改 BOM 关系中的数量(quantity)或装配位置"""
        current_props = dict(relation.properties) if relation.properties else {}
        current_props.update(updates)
        relation.properties = current_props
        await db.commit()
        await db.refresh(relation)
        return relation

    @staticmethod
    async def delete_relation(db: AsyncSession, relation: RelationModel) -> bool:
        """异步斩断关系：仅删除关联边本身，绝对不伤及两侧连接的节点实体"""
        await db.delete(relation)
        await db.commit()
        return True
