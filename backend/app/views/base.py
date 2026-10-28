"""
全局共享的基础 UI 模块：顶栏渲染、ECN 变更通知总线。
"""
from nicegui import ui

# ECN 通知总线已抽离到服务层（app/services/ecn.py），此处重新导出供视图层
# `from app.views.base import ecn_notifier` 继续可用。
from app.services.ecn import ECNNotifier, ecn_notifier  # noqa: F401
from app.views.styles import GLOBAL_CSS


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