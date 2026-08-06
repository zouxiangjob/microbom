"""
全局共享的基础 UI 模块：顶栏渲染、ECN 变更通知总线。
"""
import threading
from typing import List

from nicegui import ui

from app.views.styles import GLOBAL_CSS


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


def _inject_global_styles() -> None:
    """注入全局工业风 CSS 样式。"""
    ui.add_head_html(GLOBAL_CSS)


def _render_nav_link(label: str, target: str, is_active: bool) -> None:
    """渲染导航链接按钮。"""
    active_classes = 'bg-blue-800 text-white shadow-md' if is_active else 'text-blue-200 hover:text-white hover:bg-blue-900'
    ui.button(label, on_click=lambda: ui.navigate.to(target)).classes(
        f'text-2xl px-5 py-2.5 rounded-lg font-black transition-colors {active_classes}'
    ).props('flat')


def render_header(current_page: str) -> None:
    """渲染全局统一的工业风大标题栏。"""
    _inject_global_styles()

    with ui.row().classes('w-full bg-blue-950 text-white p-4 items-center justify-between shadow-lg'):
        with ui.row().classes('items-center gap-3'):
            ui.icon('inventory_2', size='md').classes('text-blue-400')
            ui.label('MicroBOM').classes('text-2xl font-black tracking-wide')

        with ui.row().classes('gap-4 font-bold items-center'):
            _render_nav_link('📟 工程师端', '/engineer', current_page == 'engineer')
            _render_nav_link('📊 采购审计', '/purchase', current_page == 'purchase')
            _render_nav_link('🏭 车间看图', '/workshop', current_page == 'workshop')

        with ui.row().classes('items-center gap-2 bg-green-800 px-4 py-1.5 rounded-full text-base font-bold'):
            ui.icon('verified_user', size='sm')
            ui.label('系统状态：在线 (在线模式)').classes('text-white')