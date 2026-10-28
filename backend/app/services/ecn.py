"""
ECN 工程变更通知：线程安全的内存总线 + 变更差异日志生成。

从 NiceGUI 视图层抽离到服务层，供 NiceGUI 页面与 REST 接口共用。
"""
import threading
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business import PartModel
from app.services.graph import AsyncGraphCrudEngine


class ECNNotifier:
    """线程安全的 ECN（工程变更通知）全局总线。

    设计部发布新版本后，采购端和车间端实时感知变更。
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._notifications: List[str] = []

    def publish(self, notifications: List[str]) -> None:
        """发布一批变更通知，覆盖旧通知。"""
        with self._lock:
            self._notifications = list(notifications)

    def get(self) -> List[str]:
        """获取当前所有变更通知的快照。"""
        with self._lock:
            return list(self._notifications)

    def clear(self) -> None:
        """清空所有通知。"""
        with self._lock:
            self._notifications.clear()

    @property
    def has_notifications(self) -> bool:
        """是否有待处理的通知。"""
        with self._lock:
            return len(self._notifications) > 0


ecn_notifier = ECNNotifier()


async def build_ecn_diff_logs(db: AsyncSession, item_code: str) -> List[str]:
    """按物料编码生成 ECN 变更差异日志（供发布端调用）。"""
    parts = await AsyncGraphCrudEngine.query_nodes_by_property(
        db, PartModel, "part_number", item_code
    )
    if not parts:
        return [f"物料 [{item_code}] 未在系统中找到"]

    part = parts[0]
    props = part.properties or {}
    part_name = props.get("name", item_code)
    version = props.get("version", "V1.0")
    designer = props.get("designer", "未知")

    tree = await AsyncGraphCrudEngine.get_node_tree_by_cte(db, part.id, max_depth=10)
    logs = [
        f"变更对象: {item_code} ({part_name})",
        f"版本号: {version} | 设计师: {designer}",
    ]

    if tree:
        direct_children = [n for n in tree if n["depth"] == 1]
        logs.append(f"直属子件共 {len(direct_children)} 个:")
        for child in direct_children[:20]:
            target_props = child.get("target_node", {}).get("properties", {})
            child_code = target_props.get("part_number", "") or str(child["target_node"]["id"])[:8]
            child_name = target_props.get("name", "")
            edge_props = child.get("edge", {}).get("properties", {})
            qty = edge_props.get("quantity", 1) if isinstance(edge_props, dict) else 1
            logs.append(f"  └ {child_code} ({child_name}) × {qty}")

        total_descendants = len(tree)
        logs.append(f"BOM 树共计 {total_descendants} 条关系边，最大深度 {max(n['depth'] for n in tree)}")
    else:
        logs.append("当前 BOM 无子件结构（可能为叶子零件）")

    return logs
