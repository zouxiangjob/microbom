import uuid
from typing import List, Optional, Type, TypeVar, Dict, Any
from sqlalchemy import select, and_, literal_column  #修正：必须显式导入 literal_column
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

    # ==================== 3. 拓扑图谱穿透 (Graph Traversal) 业务逻辑 ====================

    @staticmethod
    async def get_node_tree_by_cte(
            db: AsyncSession,
            root_id: uuid.UUID,
            max_depth: int = 10
    ) -> List[Dict[str, Any]]:
        """
        🚀 异步单次数据库穿透：使用 CTE 递归查询从指定根节点出发的整棵 BOM 树
        返回结果包含：所有关联的边、节点数据以及它们在这棵树中所处的深度(depth)
        """
        # 1. 定义递归初始条件（Anchor Member）：从 root_id 散发出的第一层关系边
        anchor_stmt = select(
            RelationModel.id,
            RelationModel.relation_type,
            RelationModel.source_id,
            RelationModel.target_id,
            RelationModel.properties,
            literal_column("1").label("depth")
        ).where(RelationModel.source_id == root_id)

        # 2. 构造 CTE 递归容器
        cte_expr = anchor_stmt.cte(name="graph_tree_cte", recursive=True)

        # 3. 定义递归关联条件（Recursive Member）：将上一层的 target_id 绑定为下一层的 source_id
        recursive_stmt = select(
            RelationModel.id,
            RelationModel.relation_type,
            RelationModel.source_id,
            RelationModel.target_id,
            RelationModel.properties,
            (cte_expr.c.depth + 1).label("depth")
        ).join(cte_expr, RelationModel.source_id == cte_expr.c.target_id).where(
            cte_expr.c.depth < max_depth  # 防御死循环爆破
        )

        # 4. 复合两部分 SQL 表达式
        final_cte = cte_expr.union_all(recursive_stmt)

        # 5. 执行查询，同时连表拉出 target 节点的详情信息，做到一步到位
        stmt = select(
            final_cte.c.id.label("edge_id"),
            final_cte.c.relation_type,
            final_cte.c.source_id,
            final_cte.c.target_id,
            final_cte.c.properties.label("edge_properties"),
            final_cte.c.depth,
            ObjectModel.object_type.label("target_type"),
            ObjectModel.properties.label("target_properties")
        ).join(ObjectModel, ObjectModel.id == final_cte.c.target_id)

        result = await db.execute(stmt)

        # 6. 转化为规整的字典结构，方便 FastAPI 自动序列化
        tree_nodes = []
        for row in result.mappings():
            tree_nodes.append({
                "edge": {
                    "id": row["edge_id"],
                    "relation_type": row["relation_type"],
                    "source_id": row["source_id"],
                    "target_id": row["target_id"],
                    "properties": row["edge_properties"]
                },
                "depth": row["depth"],
                "target_node": {
                    "id": row["target_id"],
                    "object_type": row["target_type"],
                    "properties": row["target_properties"]
                }
            })
        return tree_nodes

    # ==================== 3. 拓扑图谱反查穿透 (Reverse Impact Analysis / Where-Used Query) 业务逻辑 ====================
    @staticmethod
    async def get_reverse_node_tree_by_cte(
            db: AsyncSession,
            leaf_id: uuid.UUID,
            max_depth: int = 10
    ) -> List[Dict[str, Any]]:
        """
        🚀 逆向依赖一键穿透：使用 CTE 递归向上追溯引用的父节点/上级网络
        返回结果包含：所有逆向关联的边、上级父节点数据以及它们所处的逆向深度(depth)
        """
        # 1. 定义逆向递归初始条件（Anchor Member）：谁指向了我（target_id == leaf_id）
        anchor_stmt = select(
            RelationModel.id,
            RelationModel.relation_type,
            RelationModel.source_id,
            RelationModel.target_id,
            RelationModel.properties,
            literal_column("1").label("depth")
        ).where(RelationModel.target_id == leaf_id)

        # 2. 构造逆向 CTE 递归容器
        cte_expr = anchor_stmt.cte(name="reverse_graph_tree_cte", recursive=True)

        # 3. 定义逆向关联条件（Recursive Member）：将上一层的 source_id 绑定为下一层的 target_id（向上追溯）
        recursive_stmt = select(
            RelationModel.id,
            RelationModel.relation_type,
            RelationModel.source_id,
            RelationModel.target_id,
            RelationModel.properties,
            (cte_expr.c.depth + 1).label("depth")
        ).join(cte_expr, RelationModel.target_id == cte_expr.c.source_id).where(
            cte_expr.c.depth < max_depth  # 防御死循环爆破
        )

        # 4. 复合两部分 SQL 表达式
        final_cte = cte_expr.union_all(recursive_stmt)

        # 5. 执行查询，同时连表拉出起点（source_id）对应的上级父节点详情信息
        stmt = select(
            final_cte.c.id.label("edge_id"),
            final_cte.c.relation_type,
            final_cte.c.source_id,
            final_cte.c.target_id,
            final_cte.c.properties.label("edge_properties"),
            final_cte.c.depth,
            ObjectModel.object_type.label("source_type"),
            ObjectModel.properties.label("source_properties")
        ).join(ObjectModel, ObjectModel.id == final_cte.c.source_id)  # 🔥 核心对调：连接的是 source_id

        result = await db.execute(stmt)

        # 6. 转化为规整的字典结构，方便 FastAPI 自动序列化
        tree_nodes = []
        for row in result.mappings():
            tree_nodes.append({
                "edge": {
                    "id": row["edge_id"],
                    "relation_type": row["relation_type"],
                    "source_id": row["source_id"],
                    "target_id": row["target_id"],
                    "properties": row["edge_properties"]
                },
                "depth": row["depth"],
                "source_node": {  # 🔥 返回给前端：当前层级捕获到的“上级父节点”
                    "id": row["source_id"],
                    "object_type": row["source_type"],
                    "properties": row["source_properties"]
                }
            })
        return tree_nodes



    @staticmethod
    async def create_graph_batch(
            db: AsyncSession,
            node_mappers: dict[str, Type],
            edge_mappers: dict[str, Type],
            batch_data: Any  # 接收路由传入的 Schema 实例
    ) -> tuple[List[uuid.UUID], List[uuid.UUID]]:
        """
        🚀 工业级子图原子化写入引擎
        在同一个数据库事务内，批量洗入节点，随后统一织网连线，失败则全盘回滚。
        """
        created_node_ids = []
        created_edge_ids = []

        # 内存映射缓存，用于在单次批处理中快速验证节点是否存在
        local_node_id_set = set()

        try:
            # ==== 第一阶段：批量实例化并灌入节点 ====
            for node_item in batch_data.nodes:
                if node_item.object_type not in node_mappers:
                    raise ValueError(f"批量终止：未注册的节点类型 '{node_item.object_type}'")

                model_cls = node_mappers[node_item.object_type]

                # 🎯 核心防御：如果前端传了 ID 就用前端的，没传系统就原子化生成一个
                final_id = node_item.id if node_item.id is not None else uuid.uuid4()

                new_node = model_cls(
                    id=final_id,
                    properties=node_item.properties
                )
                db.add(new_node)
                created_node_ids.append(new_node.id)
                local_node_id_set.add(str(new_node.id))

            # ==== 第二阶段：批量建立关系网络 ====
            for edge_item in batch_data.relations:
                if edge_item.relation_type not in edge_mappers:
                    raise ValueError(f"批量终止：未注册的关系边类型 '{edge_item.relation_type}'")

                # 防御性图校验：验证连线的两端是否合法（要么在本次新建里，要么在老数据库里）
                for n_id, role in [(edge_item.source_id, "起点"), (edge_item.target_id, "终点")]:
                    if str(n_id) not in local_node_id_set:
                        # 如果不在本次新建列表中，再去数据库里扫一眼看存不存在
                        exists_node = await db.get(ObjectModel, n_id)
                        if not exists_node:
                            raise ValueError(
                                f"网状拓扑中断：连线【{edge_item.relation_type}】指定的{role} ID [{n_id}] 在系统中物理不存在，无法织网")

                # 获取关系多态类并实例化
                edge_cls = edge_mappers[edge_item.relation_type]
                new_edge = edge_cls(
                    id=uuid.uuid4(),
                    source_id=edge_item.source_id,
                    target_id=edge_item.target_id,
                    properties=edge_item.properties
                )
                db.add(new_edge)
                created_edge_ids.append(new_edge.id)

            # ==== 第三阶段：原子化统一提交 ====
            await db.commit()
            return created_node_ids, created_edge_ids

        except Exception as batch_err:
            # 🚨 只要任何一个环节由于脏数据出现异动，全盘撤销，绝不留任何无头死线！
            await db.rollback()
            raise batch_err


    @staticmethod
    async def update_graph_batch(
            db: AsyncSession,
            node_mappers: dict[str, Type],
            edge_mappers: dict[str, Type],
            batch_data: Any  # 接收 GraphBatchUpdateRequest 实例
    ) -> tuple[int, int]:
        """
        🚀 工业级子图原子化批量修改引擎 (Mutation Engine)
        全异步增量覆盖节点 JSON 属性，同时支持关系边属性的无损 Upsert 及拓扑重定向连线。
        任意单条记录未找到或类型错配，整个子图变更动作瞬间安全回滚。
        """
        updated_nodes = 0
        updated_edges = 0

        try:
            # ==== 第一阶段：批量增量更新节点非结构化属性 ====
            for node_item in batch_data.nodes:
                if node_item.object_type not in node_mappers:
                    raise ValueError(f"批量修改终止：未注册的节点多态类型 '{node_item.object_type}'")

                model_cls = node_mappers[node_item.object_type]
                # 精准提取并校验类型安全性，防止越权改数
                node_obj = await db.get(model_cls, node_item.id)
                if not node_obj:
                    raise ValueError(f"修改失败：目标节点 [{node_item.id}] 不存在或类型不是 '{node_item.object_type}'")

                # 内存无损增量合并字典
                current_props = dict(node_obj.properties) if node_obj.properties else {}
                current_props.update(node_item.properties)

                # 重新赋值：依赖 MutableDict 自动勾起 SQLAlchemy 的 dirty 标记触发 UPDATE 行为
                node_obj.properties = current_props
                db.add(node_obj)
                updated_nodes += 1

            # ==== 第二阶段：批量修改关系边属性或拓扑图重定向 ====
            for edge_item in batch_data.relations:
                if edge_item.relation_type not in edge_mappers:
                    raise ValueError(f"批量修改终止：未注册的关系边类型 '{edge_item.relation_type}'")

                edge_cls = edge_mappers[edge_item.relation_type]
                edge_obj = await db.get(edge_cls, edge_item.id)
                if not edge_obj:
                    raise ValueError(
                        f"修改失败：目标关系边 [{edge_item.id}] 不存在或类型不是 '{edge_item.relation_type}'")

                # 场景 A：如果前端申请了【拓扑改签/图重构】，必须防御式检验新改签的节点是否存在
                if edge_item.source_id:
                    src_check = await db.get(ObjectModel, edge_item.source_id)
                    if not src_check:
                        raise ValueError(f"拓扑改签失败：新设定的起点节点 [{edge_item.source_id}] 在系统中物理不存在")
                    edge_obj.source_id = edge_item.source_id

                if edge_item.target_id:
                    tgt_check = await db.get(ObjectModel, edge_item.target_id)
                    if not tgt_check:
                        raise ValueError(f"拓扑改签失败：新设定的终点节点 [{edge_item.target_id}] 在系统中物理不存在")
                    edge_obj.target_id = edge_item.target_id

                # 场景 B：增量更新关系边自身的非结构化属性
                if edge_item.properties:
                    current_edge_props = dict(edge_obj.properties) if edge_obj.properties else {}
                    current_edge_props.update(edge_item.properties)
                    edge_obj.properties = current_edge_props

                db.add(edge_obj)
                updated_edges += 1

            # ==== 第三阶段：强事务统一原子提交 ====
            await db.commit()
            return updated_nodes, updated_edges

        except Exception as batch_err:
            # 🚨 整个批量变更动作中，任何一条数据出现差错，全盘撤销，确保数据库脏数据零残留
            await db.rollback()
            raise batch_err


    # 全量覆盖子图结构
    @staticmethod
    async def overwrite_graph_topology(
            db: AsyncSession,
            node_mappers: dict[str, Type],
            edge_mappers: dict[str, Type],
            batch_data: Any  # 接收 GraphTopologyOverwriteRequest 实例
    ) -> tuple[int, int]:
        """
        🚀 方案 B: 工业级图拓扑全量重写引擎 (Purge & Replace)
        1. 增量更新或注入传入的子节点属性。
        2. 在同一个事务中，一键物理清空以 root_id 为源头发出的所有旧关系边。
        3. 瞬间灌入全新的网络边，若中途有任何端点不存在或崩溃，旧网络全自动原地复活（强事务隔离）。
        """
        purged_count = 0
        inserted_count = 0
        local_known_node_ids = {str(batch_data.root_id)}

        try:
            # ==== 步骤 1: 增量洗数更新或创建随同传入的子节点 ====
            for node_item in batch_data.nodes:
                local_known_node_ids.add(str(node_item.id))
                if node_item.object_type not in node_mappers:
                    raise ValueError(f"重写终止：未注册的节点类型 '{node_item.object_type}'")

                model_cls = node_mappers[node_item.object_type]
                node_obj = await db.get(model_cls, node_item.id)

                if node_obj:
                    # 节点已存在：执行无损增量合并属性
                    current_props = dict(node_obj.properties) if node_obj.properties else {}
                    current_props.update(node_item.properties)
                    node_obj.properties = current_props
                else:
                    # 节点不存在：直接在事务中就地补全创建
                    node_obj = model_cls(id=node_item.id, properties=node_item.properties)

                db.add(node_obj)

            # ==== 步骤 2: 【核心 Purge】一键斩断当前根节点发出的所有旧连线 ====
            # 查出当前以 root_id 为起点发出的所有老边
            old_edges_stmt = select(RelationModel).where(RelationModel.source_id == batch_data.root_id)
            old_edges_res = await db.execute(old_edges_stmt)
            old_edges_list = old_edges_res.scalars().all()

            purged_count = len(old_edges_list)
            for old_edge in old_edges_list:
                await db.delete(old_edge)  # 纳入 session 等待一并清理

            # 执行一次 flush，确保旧线在底层被抹除，防止联合唯一索引或主键冲突
            await db.flush()

            # ==== 步骤 3: 【核心 Replace】将前端最新的连线网一气呵成灌入 ====
            for edge_item in batch_data.relations:
                if edge_item.relation_type not in edge_mappers:
                    raise ValueError(f"重写终止：未注册的关系连线类型 '{edge_item.relation_type}'")

                # 防御式图校验：确保连线的终点节点在本次提交或老数据库中物理真实存在
                if str(edge_item.target_id) not in local_known_node_ids:
                    exists_node = await db.get(ObjectModel, edge_item.target_id)
                    if not exists_node:
                        raise ValueError(f"重写图败退：新网络中指定的终点节点 [{edge_item.target_id}] 物理不存在")

                edge_cls = edge_mappers[edge_item.relation_type]
                new_edge = edge_cls(
                    id=uuid.uuid4(),
                    source_id=batch_data.root_id,  # 起点永远锁死为当前重写的根节点
                    target_id=edge_item.target_id,
                    properties=edge_item.properties
                )
                db.add(new_edge)
                inserted_count += 1

            # ==== 步骤 4: 原子化原子锁统一提交 ====
            await db.commit()
            return purged_count, inserted_count

        except Exception as overwrite_err:
            # 🚨 防御熔断：哪怕新连线里有一个 UUID 写错，老网络瞬间完好无损地就地复活！
            await db.rollback()
            raise overwrite_err
