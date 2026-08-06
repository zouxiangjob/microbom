"""
可复用的 UI 组件函数，优化上下文管理器与渲染逻辑。
"""
from contextlib import contextmanager
from typing import Any, Callable, Generator, List, Optional

from nicegui import ui

from app.views.styles import (
    CARD_TITLE_BOLD_CLASSES,
    CARD_TITLE_CLASSES,
    INDUSTRIAL_TABLE_CLASSES,
    INDUSTRIAL_TABLE_STYLE,
)


def render_bom_tree(
    tree_data: List[dict],
    on_node_click: Callable[[str], None],
    classes: str = 'text-sm',
    expand_all: bool = True,
) -> ui.tree:
    """渲染 BOM 树，点击任意节点触发 on_node_click(node_id)。

    双通道策略：
    - update:selected → 无 children 的叶子节点（需启用 selected prop）
    - update:expanded → 有 children 的父节点（差集法检测展开/折叠）

    初始化时 prev_expanded 预种展开列表，避免 programmatic expand 误触回调。
    """
    tree = ui.tree(nodes=tree_data, label_key='label').classes(classes)

    # ── 启用 Quasar QTree selection 功能（灰色选中高亮 + 叶子节点点击）──
    tree._props['selected'] = None

    # ── 收集父节点 key ──
    parent_keys: List[str] = []

    def _collect_parent_keys(nodes: List[dict]) -> None:
        for n in nodes:
            children = n.get('children', [])
            if children:
                kid = str(n.get('id', ''))
                if kid:
                    parent_keys.append(kid)
                _collect_parent_keys(children)

    _collect_parent_keys(tree_data)

    # ── 策略 A：select 事件（叶子节点 + 显式选中）──
    def _handle_select(e: Any) -> None:
        val = e.args if hasattr(e, 'args') else getattr(e, 'value', None)
        if val is not None and val != '':
            node_id = str(val) if not isinstance(val, dict) else str(val.get('id', ''))
            if node_id:
                on_node_click(node_id)

    tree.on('update:selected', _handle_select)

    # ── 策略 B：expand / collapse 事件（父节点）──
    # 预种已展开的 key，使 programmatic expand 的差集为空
    prev_expanded: List[str] = list(parent_keys)

    def _handle_expand(e: Any) -> None:
        nonlocal prev_expanded
        val = e.args if hasattr(e, 'args') else getattr(e, 'value', [])
        current: List[str] = val if isinstance(val, list) else []
        current_set = set(current)
        prev_set = set(prev_expanded)
        new_keys = current_set - prev_set         # 用户展开的
        removed_keys = prev_set - current_set      # 用户折叠的
        prev_expanded = list(current)
        for node_id in new_keys | removed_keys:
            on_node_click(node_id)

    tree.on('update:expanded', _handle_expand)

    # ── 默认展开父节点（prev_expanded 已预种，不会误触回调）──
    if expand_all and parent_keys:
        tree.expand(parent_keys)

    return tree


def render_card_header(
    icon_name: str,
    title: str,
    button_text: Optional[str] = None,
    on_click: Optional[Callable] = None,
    button_classes: str = 'bg-blue-900 text-white font-bold text-xs',
) -> None:
    """统一渲染卡片头部：图标 + 标题 + 可选按钮。"""
    with ui.row().classes('w-full justify-between items-center border-b pb-2 mb-2'):
        with ui.row().classes('items-center gap-2'):
            ui.icon(icon_name, size='sm')
            ui.label(title).classes(CARD_TITLE_BOLD_CLASSES)
        if button_text and on_click:
            ui.button(button_text, on_click=on_click).classes(button_classes)


def render_industrial_table(
    columns: List[dict],
    rows: List[dict],
    row_key: str = 'code',
) -> ui.table:
    """统一渲染工业风大字号表格。"""
    table = ui.table(columns=columns, rows=rows, row_key=row_key)
    table.classes(INDUSTRIAL_TABLE_CLASSES).style(INDUSTRIAL_TABLE_STYLE)
    return table


def render_file_row(
    icon_name: str,
    icon_color: str,
    name: str,
    meta: str,
    meta_classes: str,
    button_text: str,
    button_classes: str,
    on_click: Callable[..., Any],
) -> None:
    """统一渲染行文件/文档项目。"""
    with ui.row().classes('w-full justify-between items-center bg-stone-50 p-2 rounded border border-stone-200 mb-2'):
        with ui.row().classes('items-center gap-2'):
            ui.icon(icon_name, size='sm').classes(f'text-{icon_color}')
            ui.label(name).classes('font-bold text-gray-800 text-base')
            ui.label(meta).classes(meta_classes)
        ui.button(button_text, on_click=on_click).classes(button_classes)
