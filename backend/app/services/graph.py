import uuid
from typing import List, Optional, Type, TypeVar, Dict, Any
from sqlalchemy import select, and_, or_, literal_column
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.base import ObjectModel, RelationModel

# 定义泛型以支持 IDE 类型推导
T_Node = TypeVar("T_Node", bound=ObjectModel)
T_Edge = TypeVar("T_Edge", bound=RelationModel)


# ==============================================================================
# 模糊搜索字段配置：object_type -> 参与 LIKE 匹配的 JSON 属性字段
# 扩展搜索范围只需在此追加字段，无需改动查询逻辑。
# ==============================================================================
SEARCHABLE_FIELDS: Dict[str, List[str]] = {
    "part": ["part_number", "name", "spec", "material", "designer", "category"],
    "document": ["name", "tag", "doc_version"],
    "drawing": ["name", "drawing_type", "version"],
    "attachment": ["name"],
    "category": ["name"],
}
_DEFAULT_SEARCH_FIELDS = ["part_number", "name"]  # 未知类型兜底


def _resolve_searchable_fields(object_type: Optional[str]) -> List[str]:
    """按对象类型解析参与模糊搜索的字段；未指定类型时取所有类型字段并集。"""
    if object_type and object_type in SEARCHABLE_FIELDS:
        return SEARCHABLE_FIELDS[object_type]
    if object_type:
        return _DEFAULT_SEARCH_FIELDS
    fields: List[str] = []
    for fs in SEARCHABLE_FIELDS.values():
        for f in fs:
            if f not in fields:
                fields.append(f)
    return fields


# 关键字段校验配置：object_type -> 创建时必填非空的 JSON 属性字段
REQUIRED_FIELDS: Dict[str, List[str]] = {
    "part": ["part_number"],
    "document": ["name"],
    "drawing": ["name"],
    "attachment": ["name"],
    "category": ["name"],
}

# 关系边端点类型约束：relation_type（多态标识）-> (允许的 source object_type 集合, 允许的 target object_type 集合)
# 用于在写入关系时校验两端节点的类型是否合法，避免出现 drawing -> document 的 BOM 边等语义错误。
RELATION_ENDPOINT_RULES: Dict[str, tuple[set, set]] = {
    "bom_relation": ({"part"}, {"part"}),
    "part_drawing_relation": ({"part"}, {"drawing"}),
    "part_doc_relation": ({"part"}, {"document"}),
    "doc_attachment_relation": ({"document"}, {"attachment"}),
    "drawing_attachment_relation": ({"drawing"}, {"attachment"}),
    "category_relation": ({"category"}, {"category"}),
    "category_part_relation": ({"category"}, {"part"}),
}


class AsyncGraphCrudEngine:
    """通用异步图谱业务引擎：基于"万物皆对象"模型提供节点与关系的 CRUD 及图遍历能力。"""

    # ==================== 1. 节点（Node）业务逻辑 ====================

    @staticmethod
    async def create_node(db: AsyncSession, node: ObjectModel) -> ObjectModel:
        """创建节点：根据传入子类的多态标识持久化。"""
        db.add(node)
        await db.commit()
        await db.refresh(node)
        return node

    @staticmethod
    async def get_node_by_id(db: AsyncSession, model_cls: Type[T_Node], node_id: uuid.UUID) -> Optional[T_Node]:
        """按业务类和 UUID 查询节点，类型不匹配时返回 None。"""
        node = await db.get(ObjectModel, node_id)
        if isinstance(node, model_cls):
            return node
        return None

    @staticmethod
    async def query_nodes_by_type(db: AsyncSession, model_cls: Type[T_Node], limit: int = 100, offset: int = 0) -> List[
        T_Node]:
        """分页查询同类节点。"""
        stmt = select(model_cls).offset(offset).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def query_nodes_by_property(
            db: AsyncSession,
            model_cls: Type[T_Node],
            key: str,
            value: str,
    ) -> List[T_Node]:
        """按 JSON 属性精确查询节点（SQLite 使用 json_extract 定位匹配行）。"""
        stmt = select(model_cls).where(
            model_cls.properties[key].as_string() == value
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def search_nodes(
            db: AsyncSession,
            object_type: Optional[str] = None,
            keyword: str = "",
            limit: int = 50,
    ) -> List[ObjectModel]:
        """按类型模糊搜索节点：对配置的 JSON 字段做 LIKE 匹配。"""
        kw = f"%{keyword}%"
        like_conds = [
            ObjectModel.properties[f].as_string().like(kw)
            for f in _resolve_searchable_fields(object_type)
        ]
        stmt = select(ObjectModel)
        if object_type:
            stmt = stmt.where(ObjectModel.object_type == object_type)
        stmt = stmt.where(or_(*like_conds)).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def validate_required_fields(object_type: str, properties: Dict[str, Any]) -> Optional[str]:
        """校验关键字段，返回错误信息；通过返回 None。"""
        for field in REQUIRED_FIELDS.get(object_type, []):
            value = (properties or {}).get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                return f"字段 [{field}] 为必填关键字段，不能为空"
        return None

    @staticmethod
    def validate_relation_endpoints(relation_type: str, source_type: str, target_type: str) -> Optional[str]:
        """校验关系边两端节点的对象类型是否符合该关系类型的语义约束；通过返回 None。"""
        rule = RELATION_ENDPOINT_RULES.get(relation_type)
        if not rule:
            return f"未注册的关系类型 [{relation_type}]，无法校验端点类型"
        allowed_source, allowed_target = rule
        if source_type not in allowed_source or target_type not in allowed_target:
            return f"关系类型 [{relation_type}] 不允许 {source_type} -> {target_type} 的连接"
        return None

    @staticmethod
    async def find_part_by_number(
            db: AsyncSession,
            part_number: str,
            exclude_id: Optional[uuid.UUID] = None,
    ) -> Optional[ObjectModel]:
        """按 part_number 精确查找零件；命中重复项时返回第一个（更新时用 exclude_id 排除自身）。"""
        from app.models.business import PartModel
        stmt = select(PartModel).where(
            PartModel.properties["part_number"].as_string() == part_number
        )
        if exclude_id is not None:
            stmt = stmt.where(PartModel.id != exclude_id)
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def ensure_unique_part_number(
            db: AsyncSession,
            properties: Dict[str, Any],
            exclude_id: Optional[uuid.UUID] = None,
    ) -> Optional[str]:
        """校验 part_number 唯一性（应用层）；重复返回错误信息，通过返回 None。"""
        part_number = (properties or {}).get("part_number")
        if not part_number:
            return None  # 必填性由 validate_required_fields 单独校验
        existing = await AsyncGraphCrudEngine.find_part_by_number(db, part_number, exclude_id)
        if existing:
            return f"零件编码 [{part_number}] 已存在，不允许重复"
        return None

    @staticmethod
    async def ensure_single_category_for_part(db: AsyncSession, part_id: uuid.UUID) -> Optional[str]:
        """校验 category_part_relation 的「一个零件只归一个分类」约束；已归类返回错误信息。

        依据 category_part_relation（分类 -> 零件）：零件作为 target 至多出现在一条该关系边中。
        """
        from app.models.business import CategoryPartRelationModel
        stmt = select(CategoryPartRelationModel).where(
            CategoryPartRelationModel.target_id == part_id
        )
        existing = (await db.execute(stmt)).scalars().first()
        if existing:
            return f"零件 [{part_id}] 已归属其它分类，一个零件只能归一个分类"
        return None

    @staticmethod
    async def has_bom_cycle(db: AsyncSession, source_id: uuid.UUID, target_id: uuid.UUID) -> bool:
        """检测建立 source->target 的 BOM 关系是否会成环。

        逆向遍历 source 的所有 BOM 祖先，若 target 在其中则成环（target 已是 source 的祖先）。
        """
        from app.models.business import BOMRelation
        bom_identity = BOMRelation.__mapper_args__["polymorphic_identity"]
        anchor = select(RelationModel.source_id).where(
            RelationModel.target_id == source_id,
            RelationModel.relation_type == bom_identity,
        )
        cte = anchor.cte(name="bom_cycle_cte", recursive=True)
        recursive = select(RelationModel.source_id).join(
            cte, RelationModel.target_id == cte.c.source_id
        ).where(RelationModel.relation_type == bom_identity)
        full = cte.union(recursive)  # UNION 去重，防止已存在的环导致死循环
        stmt = select(full.c.source_id).where(full.c.source_id == target_id).limit(1)
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def find_root_assemblies(db: AsyncSession) -> List[ObjectModel]:
        """查找顶层总成：在 BOM 关系中作为起点、但从未作为终点的对象，即产品树根节点。"""
        from app.models.business import BOMRelation
        # 所有作为 BOM 关系终点的对象（即作为他人子件）
        child_stmt = select(RelationModel.target_id).where(
            RelationModel.relation_type == BOMRelation.__mapper_args__["polymorphic_identity"]
        )
        child_result = await db.execute(child_stmt)
        child_ids = {row[0] for row in child_result.fetchall()}

        # 所有作为 BOM 关系起点的对象
        parent_stmt = select(RelationModel.source_id).where(
            RelationModel.relation_type == BOMRelation.__mapper_args__["polymorphic_identity"]
        )
        parent_result = await db.execute(parent_stmt)
        parent_ids = {row[0] for row in parent_result.fetchall()}

        # 根节点 = 父节点集合 - 子节点集合
        root_ids = parent_ids - child_ids

        if root_ids:
            roots_stmt = select(ObjectModel).where(ObjectModel.id.in_(root_ids))
            roots_result = await db.execute(roots_stmt)
            return list(roots_result.scalars().all())
        return []

    @staticmethod
    async def update_node_properties(db: AsyncSession, node: ObjectModel, updates: Dict[str, Any]) -> ObjectModel:
        """增量合并更新节点的 JSON 属性。"""
        current_props = dict(node.properties) if node.properties else {}
        current_props.update(updates)
        node.properties = current_props
        await db.commit()
        await db.refresh(node)
        return node

    @staticmethod
    async def delete_node(db: AsyncSession, node: ObjectModel) -> bool:
        """删除节点，依赖 ON DELETE CASCADE 自动清理关联关系。"""
        await db.delete(node)
        await db.commit()
        return True

    # ==================== 2. 关系边（Edge）业务逻辑 ====================

    @staticmethod
    async def create_relation(db: AsyncSession, relation: RelationModel) -> RelationModel:
        """在两个已存在节点之间建立关系。"""
        db.add(relation)
        await db.commit()
        await db.refresh(relation)
        return relation

    @staticmethod
    async def get_relation_by_id(db: AsyncSession, model_cls: Type[T_Edge], edge_id: uuid.UUID) -> Optional[T_Edge]:
        """按关系类和 UUID 查询关系边，类型不匹配时返回 None。"""
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
        """按起点、终点或两者共同筛选关系列表。"""
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
        """增量合并更新关系边的属性（如装配数量、位置）。"""
        current_props = dict(relation.properties) if relation.properties else {}
        current_props.update(updates)
        relation.properties = current_props
        await db.commit()
        await db.refresh(relation)
        return relation

    @staticmethod
    async def delete_relation(db: AsyncSession, relation: RelationModel) -> bool:
        """删除关系边，不影响两端的节点。"""
        await db.delete(relation)
        await db.commit()
        return True

    # ==================== 3. 图遍历（正向 / 逆向） ====================

    @staticmethod
    async def get_node_tree_by_cte(
            db: AsyncSession,
            root_id: uuid.UUID,
            max_depth: int = 10
    ) -> List[Dict[str, Any]]:
        """使用递归 CTE 从指定根节点正向遍历整棵树，返回带深度的边与节点列表。"""
        # 1. 递归初始条件（Anchor）：从 root_id 发出的第一层关系边
        anchor_stmt = select(
            RelationModel.id,
            RelationModel.relation_type,
            RelationModel.source_id,
            RelationModel.target_id,
            RelationModel.properties,
            literal_column("1").label("depth")
        ).where(RelationModel.source_id == root_id)

        # 2. 构造递归 CTE 容器
        cte_expr = anchor_stmt.cte(name="graph_tree_cte", recursive=True)

        # 3. 递归成员（Recursive）：将上一层的 target_id 绑定为下一层的 source_id
        recursive_stmt = select(
            RelationModel.id,
            RelationModel.relation_type,
            RelationModel.source_id,
            RelationModel.target_id,
            RelationModel.properties,
            (cte_expr.c.depth + 1).label("depth")
        ).join(cte_expr, RelationModel.source_id == cte_expr.c.target_id).where(
            cte_expr.c.depth < max_depth  # 深度上限，防止环导致的无限递归
        )

        # 4. 合并初始条件与递归成员
        final_cte = cte_expr.union_all(recursive_stmt)

        # 5. 连表取出 target 节点的详情
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

        # 6. 转为规整字典结构
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

    # ==================== 3b. 逆向遍历（影响分析 / Where-Used） ====================

    @staticmethod
    async def get_reverse_node_tree_by_cte(
            db: AsyncSession,
            leaf_id: uuid.UUID,
            max_depth: int = 10
    ) -> List[Dict[str, Any]]:
        """使用递归 CTE 从指定节点逆向向上追溯父级引用网络。"""
        # 1. 逆向递归初始条件（Anchor）：谁指向了我（target_id == leaf_id）
        anchor_stmt = select(
            RelationModel.id,
            RelationModel.relation_type,
            RelationModel.source_id,
            RelationModel.target_id,
            RelationModel.properties,
            literal_column("1").label("depth")
        ).where(RelationModel.target_id == leaf_id)

        # 2. 构造逆向递归 CTE 容器
        cte_expr = anchor_stmt.cte(name="reverse_graph_tree_cte", recursive=True)

        # 3. 逆向递归成员：将上一层的 source_id 绑定为下一层的 target_id（向上追溯）
        recursive_stmt = select(
            RelationModel.id,
            RelationModel.relation_type,
            RelationModel.source_id,
            RelationModel.target_id,
            RelationModel.properties,
            (cte_expr.c.depth + 1).label("depth")
        ).join(cte_expr, RelationModel.target_id == cte_expr.c.source_id).where(
            cte_expr.c.depth < max_depth  # 深度上限，防止环导致的无限递归
        )

        # 4. 合并初始条件与递归成员
        final_cte = cte_expr.union_all(recursive_stmt)

        # 5. 连表取出起点（source_id）对应的上级节点详情
        stmt = select(
            final_cte.c.id.label("edge_id"),
            final_cte.c.relation_type,
            final_cte.c.source_id,
            final_cte.c.target_id,
            final_cte.c.properties.label("edge_properties"),
            final_cte.c.depth,
            ObjectModel.object_type.label("source_type"),
            ObjectModel.properties.label("source_properties")
        ).join(ObjectModel, ObjectModel.id == final_cte.c.source_id)  # 逆向连接的是 source_id

        result = await db.execute(stmt)

        # 6. 转为规整字典结构
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
                "source_node": {  # 返回的是当前层级捕获到的上级父节点
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
        """批量创建子图：在同一事务内批量写入节点和关系，失败则整体回滚。"""
        created_node_ids = []
        created_edge_ids = []

        # 内存缓存：本次批次内的节点 ID 与对象类型，用于快速校验连线端点和类型
        local_node_id_set = set()
        local_node_types: Dict[str, str] = {}
        # 本次批次内的零件编码集合，用于去重校验
        local_part_numbers: set[str] = set()
        # 本次批次内已被归类的零件（target）集合，用于「一零件一分类」约束
        local_category_part_targets: set[str] = set()

        try:
            # 第一阶段：批量实例化并写入节点
            for node_item in batch_data.nodes:
                if node_item.object_type not in node_mappers:
                    raise ValueError(f"批量终止：未注册的节点类型 '{node_item.object_type}'")

                # 零件编码唯一性校验（批次内 + 数据库）
                if node_item.object_type == "part":
                    pn = (node_item.properties or {}).get("part_number")
                    if pn:
                        if pn in local_part_numbers:
                            raise ValueError(f"批量终止：零件编码 [{pn}] 在本次批次内重复")
                        if await AsyncGraphCrudEngine.find_part_by_number(db, pn):
                            raise ValueError(f"批量终止：零件编码 [{pn}] 已存在，不允许重复")
                        local_part_numbers.add(pn)

                model_cls = node_mappers[node_item.object_type]

                # 前端传了 ID 则使用，否则系统生成
                final_id = node_item.id if node_item.id is not None else uuid.uuid4()

                new_node = model_cls(
                    id=final_id,
                    properties=node_item.properties
                )
                db.add(new_node)
                created_node_ids.append(new_node.id)
                local_node_id_set.add(str(new_node.id))
                local_node_types[str(new_node.id)] = node_item.object_type

            # 第二阶段：批量建立关系
            for edge_item in batch_data.relations:
                if edge_item.relation_type not in edge_mappers:
                    raise ValueError(f"批量终止：未注册的关系边类型 '{edge_item.relation_type}'")

                # 校验连线两端是否合法，并解析两端对象类型（用于端点类型约束）
                resolved_types: Dict[str, str] = {}
                for n_id, role in [(edge_item.source_id, "起点"), (edge_item.target_id, "终点")]:
                    key = str(n_id)
                    if key in local_node_types:
                        resolved_types[key] = local_node_types[key]
                    else:
                        exists_node = await db.get(ObjectModel, n_id)
                        if not exists_node:
                            raise ValueError(
                                f"网状拓扑中断：连线【{edge_item.relation_type}】指定的{role} ID [{n_id}] 在系统中不存在")
                        resolved_types[key] = exists_node.object_type

                edge_cls = edge_mappers[edge_item.relation_type]
                edge_identity = edge_cls.__mapper_args__["polymorphic_identity"]
                endpoint_err = AsyncGraphCrudEngine.validate_relation_endpoints(
                    edge_identity,
                    resolved_types[str(edge_item.source_id)],
                    resolved_types[str(edge_item.target_id)],
                )
                if endpoint_err:
                    raise ValueError(f"批量终止：{endpoint_err}")

                # 一零件一分类约束：同一批次内 + 数据库已有，均不允许重复归类
                if edge_identity == "category_part_relation":
                    tkey = str(edge_item.target_id)
                    if tkey in local_category_part_targets:
                        raise ValueError(f"批量终止：零件 [{edge_item.target_id}] 在本次批次内被重复归类")
                    dup_err = await AsyncGraphCrudEngine.ensure_single_category_for_part(db, edge_item.target_id)
                    if dup_err:
                        raise ValueError(f"批量终止：{dup_err}")
                    local_category_part_targets.add(tkey)

                new_edge = edge_cls(
                    id=uuid.uuid4(),
                    source_id=edge_item.source_id,
                    target_id=edge_item.target_id,
                    properties=edge_item.properties
                )
                db.add(new_edge)
                created_edge_ids.append(new_edge.id)

            # 第三阶段：统一提交
            await db.commit()
            return created_node_ids, created_edge_ids

        except Exception as batch_err:
            # 任何环节出错则整体回滚，不留残缺数据
            await db.rollback()
            raise batch_err

    @staticmethod
    async def update_graph_batch(
            db: AsyncSession,
            node_mappers: dict[str, Type],
            edge_mappers: dict[str, Type],
            batch_data: Any  # 接收 GraphBatchUpdateRequest 实例
    ) -> tuple[int, int]:
        """批量修改子图：增量更新节点属性，支持关系边属性更新与拓扑重定向，失败则整体回滚。"""
        updated_nodes = 0
        updated_edges = 0

        try:
            # 第一阶段：批量增量更新节点属性
            for node_item in batch_data.nodes:
                if node_item.object_type not in node_mappers:
                    raise ValueError(f"批量修改终止：未注册的节点多态类型 '{node_item.object_type}'")

                model_cls = node_mappers[node_item.object_type]
                node_obj = await db.get(model_cls, node_item.id)
                if not node_obj:
                    raise ValueError(f"修改失败：目标节点 [{node_item.id}] 不存在或类型不是 '{node_item.object_type}'")

                # 零件编码唯一性校验（改编码时排除自身）
                if node_item.object_type == "part" and "part_number" in (node_item.properties or {}):
                    dup_err = await AsyncGraphCrudEngine.ensure_unique_part_number(
                        db, node_item.properties, exclude_id=node_obj.id
                    )
                    if dup_err:
                        raise ValueError(f"批量修改终止：{dup_err}")

                # 增量合并属性字典
                current_props = dict(node_obj.properties) if node_obj.properties else {}
                current_props.update(node_item.properties)

                # 重新赋值以触发 SQLAlchemy 变更追踪
                node_obj.properties = current_props
                db.add(node_obj)
                updated_nodes += 1

            # 第二阶段：批量修改关系边属性或拓扑重定向
            for edge_item in batch_data.relations:
                if edge_item.relation_type not in edge_mappers:
                    raise ValueError(f"批量修改终止：未注册的关系边类型 '{edge_item.relation_type}'")

                edge_cls = edge_mappers[edge_item.relation_type]
                edge_obj = await db.get(edge_cls, edge_item.id)
                if not edge_obj:
                    raise ValueError(
                        f"修改失败：目标关系边 [{edge_item.id}] 不存在或类型不是 '{edge_item.relation_type}'")

                # 场景 A：拓扑重定向（修改起点/终点），需校验新节点存在
                if edge_item.source_id:
                    src_check = await db.get(ObjectModel, edge_item.source_id)
                    if not src_check:
                        raise ValueError(f"拓扑重定向失败：新设定的起点节点 [{edge_item.source_id}] 在系统中不存在")
                    edge_obj.source_id = edge_item.source_id

                if edge_item.target_id:
                    tgt_check = await db.get(ObjectModel, edge_item.target_id)
                    if not tgt_check:
                        raise ValueError(f"拓扑重定向失败：新设定的终点节点 [{edge_item.target_id}] 在系统中不存在")
                    edge_obj.target_id = edge_item.target_id

                # 场景 A+：重定向后校验两端对象类型是否符合该关系类型的语义约束
                src_node = await db.get(ObjectModel, edge_obj.source_id)
                tgt_node = await db.get(ObjectModel, edge_obj.target_id)
                if not src_node or not tgt_node:
                    raise ValueError("拓扑重定向失败：起点或终点节点不存在")
                endpoint_err = AsyncGraphCrudEngine.validate_relation_endpoints(
                    edge_obj.relation_type, src_node.object_type, tgt_node.object_type
                )
                if endpoint_err:
                    raise ValueError(f"批量修改终止：{endpoint_err}")

                # 场景 B：增量更新关系边属性
                if edge_item.properties:
                    current_edge_props = dict(edge_obj.properties) if edge_obj.properties else {}
                    current_edge_props.update(edge_item.properties)
                    edge_obj.properties = current_edge_props

                db.add(edge_obj)
                updated_edges += 1

            # 第三阶段：统一提交
            await db.commit()
            return updated_nodes, updated_edges

        except Exception as batch_err:
            # 任何环节出错则整体回滚
            await db.rollback()
            raise batch_err

    @staticmethod
    async def overwrite_graph_topology(
            db: AsyncSession,
            node_mappers: dict[str, Type],
            edge_mappers: dict[str, Type],
            batch_data: Any  # 接收 GraphTopologyOverwriteRequest 实例
    ) -> tuple[int, int]:
        """全量重写子图拓扑（清除后重建）。

        1. 增量更新或创建传入的子节点属性。
        2. 清空以 root_id 为源头发出的、且属于本次重写类型的旧关系边（不误删其它类型）。
        3. 写入全新关系边，任一步失败则整体回滚，旧结构保留。
        """
        purged_count = 0
        inserted_count = 0
        local_node_types: Dict[str, str] = {}

        try:
            # 步骤 0：解析本次重写涉及的关系类型（归一化为多态标识，兼容 "bom"/"bom_relation" 别名）
            rewrite_identities: set[str] = set()
            for edge_item in batch_data.relations:
                if edge_item.relation_type not in edge_mappers:
                    raise ValueError(f"重写终止：未注册的关系连线类型 '{edge_item.relation_type}'")
                rewrite_identities.add(edge_mappers[edge_item.relation_type].__mapper_args__["polymorphic_identity"])
            if not rewrite_identities:
                # 未声明任何关系类型时，按该接口的主要用途（BOM 拓扑）处理
                from app.models.business import BOMRelation
                rewrite_identities = {BOMRelation.__mapper_args__["polymorphic_identity"]}

            # 步骤 1：增量更新或创建传入的子节点
            for node_item in batch_data.nodes:
                if node_item.object_type not in node_mappers:
                    raise ValueError(f"重写终止：未注册的节点类型 '{node_item.object_type}'")

                model_cls = node_mappers[node_item.object_type]
                node_obj = await db.get(model_cls, node_item.id)

                if node_obj:
                    # 节点已存在：增量合并属性，并校验零件编码唯一性（排除自身）
                    if node_item.object_type == "part" and "part_number" in (node_item.properties or {}):
                        dup_err = await AsyncGraphCrudEngine.ensure_unique_part_number(
                            db, node_item.properties, exclude_id=node_obj.id
                        )
                        if dup_err:
                            raise ValueError(f"重写终止：{dup_err}")
                    current_props = dict(node_obj.properties) if node_obj.properties else {}
                    current_props.update(node_item.properties)
                    node_obj.properties = current_props
                else:
                    # 节点不存在：创建，并校验零件编码唯一性
                    if node_item.object_type == "part":
                        dup_err = await AsyncGraphCrudEngine.ensure_unique_part_number(
                            db, node_item.properties
                        )
                        if dup_err:
                            raise ValueError(f"重写终止：{dup_err}")
                    node_obj = model_cls(id=node_item.id, properties=node_item.properties)

                db.add(node_obj)
                local_node_types[str(node_item.id)] = node_item.object_type

            # 步骤 2：清空以 root_id 为起点发出的、属于本次重写类型的旧关系边
            old_edges_stmt = select(RelationModel).where(
                RelationModel.source_id == batch_data.root_id,
                RelationModel.relation_type.in_(rewrite_identities),
            )
            old_edges_res = await db.execute(old_edges_stmt)
            old_edges_list = old_edges_res.scalars().all()

            purged_count = len(old_edges_list)
            for old_edge in old_edges_list:
                await db.delete(old_edge)

            # flush 确保旧边在底层被删除，避免唯一索引或主键冲突
            await db.flush()

            # 步骤 3：写入全新关系边
            root_node = await db.get(ObjectModel, batch_data.root_id)
            if not root_node:
                raise ValueError(f"重写失败：根节点 [{batch_data.root_id}] 不存在")

            for edge_item in batch_data.relations:
                # 解析终点节点类型并校验存在性
                target_key = str(edge_item.target_id)
                if target_key in local_node_types:
                    target_type = local_node_types[target_key]
                else:
                    exists_node = await db.get(ObjectModel, edge_item.target_id)
                    if not exists_node:
                        raise ValueError(f"重写失败：新网络中指定的终点节点 [{edge_item.target_id}] 不存在")
                    target_type = exists_node.object_type

                edge_cls = edge_mappers[edge_item.relation_type]
                edge_identity = edge_cls.__mapper_args__["polymorphic_identity"]
                endpoint_err = AsyncGraphCrudEngine.validate_relation_endpoints(
                    edge_identity, root_node.object_type, target_type
                )
                if endpoint_err:
                    raise ValueError(f"重写终止：{endpoint_err}")

                new_edge = edge_cls(
                    id=uuid.uuid4(),
                    source_id=batch_data.root_id,  # 起点固定为当前重写的根节点
                    target_id=edge_item.target_id,
                    properties=edge_item.properties
                )
                db.add(new_edge)
                inserted_count += 1

            # 步骤 4：统一提交
            await db.commit()
            return purged_count, inserted_count

        except Exception as overwrite_err:
            # 任何环节出错则整体回滚，旧结构不受影响
            await db.rollback()
            raise overwrite_err

    # ==================== 4. BOM 打平与汇总 ====================

    @staticmethod
    async def flatten_bom(db: AsyncSession) -> List[Dict[str, Any]]:
        """全量 BOM 打平汇总：遍历所有顶层总成，递归展开 BOM，按零件编码聚合数量。"""
        from app.models.business import PartModel

        roots = await AsyncGraphCrudEngine.find_root_assemblies(db)
        # 若无根节点，回退为查询所有零部件
        if not roots:
            roots = await AsyncGraphCrudEngine.query_nodes_by_type(db, PartModel, limit=1000)

        aggregated: Dict[str, Dict[str, Any]] = {}

        for root in roots:
            tree = await AsyncGraphCrudEngine.get_node_tree_by_cte(db, root.id, max_depth=20)
            # 根节点本身也可能需要采购（外购件）
            root_props = root.properties if root.properties else {}
            root_code = root_props.get("part_number", "") or str(root.id)[:8]
            _aggregate_part(aggregated, root, root_props, 1)

            for node in tree:
                target = node["target_node"]
                edge_props = node.get("edge", {}).get("properties", {})
                quantity = edge_props.get("quantity", 1) if isinstance(edge_props, dict) else 1
                target_props = target.get("properties", {}) if isinstance(target.get("properties"), dict) else {}
                tgt_id = target["id"]
                tgt_node = await db.get(ObjectModel, tgt_id)
                if tgt_node:
                    _aggregate_part(aggregated, tgt_node, target_props, quantity)

        rows = []
        for code, entry in aggregated.items():
            rows.append({
                "code": code,
                "name": entry["name"],
                "spec": entry["spec"],
                "qty": entry["qty"],
                "unit": entry["unit"],
            })
        return rows


# ==============================================================================
# 5. 模块级工具函数
# ==============================================================================

def _aggregate_part(aggregated: Dict[str, Dict[str, Any]], node: ObjectModel, props: Dict[str, Any], qty: int) -> None:
    """将节点按 part_number 聚合到累计字典中。"""
    code = props.get("part_number", "") or str(node.id)[:8]
    if code not in aggregated:
        aggregated[code] = {
            "name": props.get("name", ""),
            "spec": props.get("spec", ""),
            "qty": 0,
            "unit": props.get("unit", "个"),
        }
    aggregated[code]["qty"] += qty


def cte_flat_to_nested_tree(flat_nodes: List[Dict[str, Any]], root_id: uuid.UUID) -> List[Dict[str, Any]]:
    """将 CTE 返回的平铺列表转换为前端树形组件所需的嵌套结构。

    每个平铺节点包含：{edge, depth, target_node}
    """
    # 按 source_id 分组，建立 parent -> children 映射
    children_map: Dict[str, List[Dict[str, Any]]] = {}
    for node in flat_nodes:
        src_id = str(node["edge"]["source_id"])
        if src_id not in children_map:
            children_map[src_id] = []
        children_map[src_id].append(node)

    def _build_subtree(node_id: str) -> List[Dict[str, Any]]:
        children = children_map.get(node_id, [])
        result = []
        for child in children:
            target = child["target_node"]
            target_props = target.get("properties", {}) if isinstance(target.get("properties"), dict) else {}
            label = target_props.get("part_number") or target_props.get("name") or str(target["id"])[:8]
            child_id = str(target["id"])
            result.append({
                "id": child_id,
                "label": label,
                "children": _build_subtree(child_id),
            })
        return result

    return _build_subtree(str(root_id))
