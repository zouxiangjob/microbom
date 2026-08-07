"""
可复用的 UI 组件函数，优化上下文管理器与渲染逻辑。
"""
import base64
import os
from typing import Any, Callable, List, Optional, Set

from nicegui import ui

from app.config import settings
from app.views.styles import (
    CARD_TITLE_BOLD_CLASSES,
    CARD_TITLE_CLASSES,
    INDUSTRIAL_TABLE_CLASSES,
    INDUSTRIAL_TABLE_STYLE,
)

# CDN 惰性注入追踪
_cdn_injected: Set[str] = set()

# 文件扩展名分类
_IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.bmp', '.ico'}
_MODEL_3D_EXTS = {'.glb', '.gltf'}
_TEXT_EXTS = {'.txt', '.csv', '.json', '.xml', '.md', '.log', '.yaml', '.yml', '.py', '.js', '.ts', '.html', '.css', '.sh', '.ini', '.cfg', '.toml'}
_DOCX_EXTS = {'.docx'}
_XLSX_EXTS = {'.xlsx', '.xls'}

# 不支持预览的格式 → 推荐工具名
_UNSUPPORTED_HINTS = {
    '.dwg': 'AutoCAD',
    '.dxf': 'AutoCAD',
    '.stp': 'SolidWorks / FreeCAD',
    '.step': 'SolidWorks / FreeCAD',
    '.igs': 'CAD 软件',
    '.iges': 'CAD 软件',
}


# ── DOCX/XLSX 自包含预览模板（iframe srcdoc）──────────────────────────
# 使用 iframe srcdoc 替代 ui.add_body_html() 轮询方案，消除 DOM 竞态条件
_DOCX_PREVIEW_HTML = '''<!DOCTYPE html>
<html><head><meta charset="utf-8">
<script src="https://cdn.jsdelivr.net/npm/mammoth@1.8.0/mammoth.browser.min.js"
    onerror="document.getElementById('container').innerHTML='<div class=error>mammoth.js CDN 加载失败，请检查网络连接</div>'">
</script>
<style>
body {{ font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif; margin: 0; padding: 24px; }}
.loading {{ text-align: center; padding: 40px; color: #999; }}
.error {{ color: #c0392b; padding: 40px; text-align: center; }}
</style></head><body>
<div id="container" class="loading">正在加载文档预览...</div>
<script>
(function() {{
    var container = document.getElementById('container');
    if (typeof mammoth !== 'undefined') {{
        doPreview();
    }} else {{
        var n = 0, t = setInterval(function() {{
            if (typeof mammoth !== 'undefined') {{ clearInterval(t); doPreview(); }}
            if (++n > 50) {{ clearInterval(t); container.innerHTML = '<div class=error>mammoth.js 加载超时（5秒），请刷新重试</div>'; }}
        }}, 100);
    }}
    function doPreview() {{
        fetch('{file_url}')
            .then(function(r) {{ if (!r.ok) throw new Error('HTTP ' + r.status); return r.arrayBuffer(); }})
            .then(function(buf) {{
                return mammoth.convertToHtml({{arrayBuffer: buf}},
                    {{ styleMap: [
                        "p[style-name='Normal'] => p:fresh",
                        "r[style-name='Strong'] => strong:fresh"
                    ]}});
            }})
            .then(function(result) {{
                container.innerHTML = result.value;
                container.className = '';
            }})
            .catch(function(e) {{
                container.innerHTML = '<div class=error>预览失败: ' + e.message + '<br><small>请下载后用本机 Word 查看</small></div>';
            }});
    }}
}})();
</script>
</body></html>'''

_XLSX_PREVIEW_HTML = '''<!DOCTYPE html>
<html><head><meta charset="utf-8">
<script src="https://cdn.sheetjs.com/xlsx-0.20.2/package/dist/xlsx.full.min.js"
    onerror="document.getElementById('container').innerHTML='<div class=error>SheetJS CDN 加载失败，请检查网络连接</div>'">
</script>
<style>
body {{ font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif; margin: 0; display: flex; flex-direction: column; height: 100vh; }}
#tabs {{ display: flex; gap: 4px; padding: 8px; background: #f5f5f5; border-bottom: 1px solid #ddd; flex-wrap: wrap; }}
#tabs button {{ padding: 6px 16px; border: 1px solid #ccc; border-radius: 4px 4px 0 0; cursor: pointer; font-size: 14px; font-weight: bold; }}
#container {{ flex: 1; overflow: auto; padding: 16px; }}
#container table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
#container th, #container td {{ border: 1px solid #ddd; padding: 6px 12px; text-align: left; white-space: nowrap; }}
#container td {{ overflow: hidden; text-overflow: ellipsis; }}
.loading {{ text-align: center; padding: 40px; color: #999; }}
.error {{ color: #c0392b; padding: 40px; text-align: center; }}
</style></head><body>
<div id="tabs"></div>
<div id="container" class="loading">正在加载表格预览...</div>
<script>
(function() {{
    var container = document.getElementById('container');
    var tabsContainer = document.getElementById('tabs');
    if (typeof XLSX !== 'undefined') {{
        doPreview();
    }} else {{
        var n = 0, t = setInterval(function() {{
            if (typeof XLSX !== 'undefined') {{ clearInterval(t); doPreview(); }}
            if (++n > 50) {{ clearInterval(t); container.innerHTML = '<div class=error>SheetJS 加载超时（5秒），请刷新重试</div>'; }}
        }}, 100);
    }}
    function doPreview() {{
        fetch('{file_url}')
            .then(function(r) {{ if (!r.ok) throw new Error('HTTP ' + r.status); return r.arrayBuffer(); }})
            .then(function(buf) {{
                var wb = XLSX.read(new Uint8Array(buf), {{type: 'array'}});
                var names = wb.SheetNames;
                var allSheets = {{}};
                names.forEach(function(name) {{
                    allSheets[name] = XLSX.utils.sheet_to_html(wb.Sheets[name]);
                }});
                tabsContainer.innerHTML = '';
                names.forEach(function(name, idx) {{
                    var btn = document.createElement('button');
                    btn.textContent = name;
                    var isActive = idx === 0;
                    btn.style.background = isActive ? '#1976d2' : '#fff';
                    btn.style.color = isActive ? '#fff' : '#333';
                    btn.style.borderBottom = isActive ? '1px solid #1976d2' : '1px solid #ccc';
                    btn.onclick = function() {{
                        var buttons = tabsContainer.querySelectorAll('button');
                        buttons.forEach(function(b) {{ b.style.background='#fff'; b.style.color='#333'; b.style.borderBottom='1px solid #ccc'; }});
                        btn.style.background = '#1976d2';
                        btn.style.color = '#fff';
                        btn.style.borderBottom = '1px solid #1976d2';
                        container.innerHTML = allSheets[name];
                    }};
                    tabsContainer.appendChild(btn);
                }});
                if (names.length > 0) {{
                    container.innerHTML = allSheets[names[0]];
                }} else {{
                    container.innerHTML = '<div class=loading>无工作表</div>';
                }}
            }})
            .catch(function(e) {{
                container.innerHTML = '<div class=error>预览失败: ' + e.message + '<br><small>请下载后用本机 Excel 查看</small></div>';
            }});
    }}
}})();
</script>
</body></html>'''


def _build_preview_iframe(template: str, file_url: str) -> str:
    """将预览模板渲染为 base64 编码的 data URI iframe。

    不使用 sandbox 属性 — data: URI 的 origin 是 null，sandbox 会阻止 fetch()
    等网络请求，导致 CDN 脚本加载和文件下载静默失败。
    """
    html = template.format(file_url=file_url)
    encoded = base64.b64encode(html.encode('utf-8')).decode('ascii')
    return (
        f'<iframe src="data:text/html;base64,{encoded}"'
        ' style="width:100%; height:70vh; border:none; border-radius:4px;">'
        '</iframe>'
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
    remove_button_text: Optional[str] = None,
    remove_button_classes: Optional[str] = None,
    on_remove_click: Optional[Callable[..., Any]] = None,
) -> None:
    """统一渲染行文件/文档项目，支持可选的移除按钮。"""
    with ui.row().classes('w-full justify-between items-center bg-stone-50 p-2 rounded border border-stone-200 mb-2'):
        with ui.row().classes('items-center gap-2'):
            ui.icon(icon_name, size='sm').classes(f'text-{icon_color}')
            ui.label(name).classes('font-bold text-gray-800 text-base')
            ui.label(meta).classes(meta_classes)
        with ui.row().classes('items-center gap-2'):
            ui.button(button_text, on_click=on_click).classes(button_classes)
            if remove_button_text and on_remove_click:
                ui.button(remove_button_text, on_click=on_remove_click).classes(
                    remove_button_classes or 'bg-red-100 text-red-700 font-bold text-sm border border-red-300 px-3 py-1 rounded'
                )


def _inject_cdn(script_url: str, key: str) -> None:
    """惰性注入 CDN 脚本，避免同一页面重复加载。"""
    if key not in _cdn_injected:
        ui.add_head_html(f'<script src="{script_url}"></script>')
        _cdn_injected.add(key)


def render_preview_dialog(file_url: str, file_name: str) -> ui.dialog:
    """根据文件扩展名选择合适的查看器，返回弹窗对象。

    支持的格式：
    - pdf: iframe 嵌入
    - 图片 (png/jpg/gif/svg/webp/bmp): img 标签
    - 3D 模型 (glb/gltf): model-viewer
    - Word (docx): mammoth.js 客户端渲染为 HTML
    - Excel (xlsx/xls): SheetJS 客户端渲染为 HTML 表格 + Sheet 切换
    - 文本: iframe 嵌入
    - 不支持的格式: 降级提示 + 下载按钮
    """
    ext = os.path.splitext(file_name)[1].lower()

    with ui.dialog() as dialog:
        dialog.props('maximized')
        with ui.element('div').classes('w-full bg-white rounded-lg shadow-lg p-4').style('max-width: 100vw'):
            # ── 顶部标题栏 ──
            with ui.row().classes('w-full justify-between items-center border-b pb-2 mb-2'):
                ui.label(f'📄 {file_name}').classes('text-lg font-bold text-gray-800')
                ui.button('✕ 关闭', on_click=dialog.close).props('flat').classes('text-gray-600')

            # ── 查看器主体 ──
            # 所有 ui.html() 必须设置 sanitize=False，因为 NiceGUI 默认启用 DOMPurify
            # 客户端清理，会移除 <iframe>、<model-viewer>、onerror 等。这些 HTML 均由
            # 服务端生成（非用户输入），不存在 XSS 风险。
            if ext == '.pdf':
                ui.html(f'''
                    <iframe src="{file_url}" style="width:100%; height:70vh; border:none; border-radius:4px;">
                    </iframe>
                ''', sanitize=False)

            elif ext in _IMAGE_EXTS:
                ui.html(f'''
                    <div style="display:flex; justify-content:center; align-items:center; min-height:300px; background:#f5f5f5; border-radius:4px;">
                        <img src="{file_url}" style="max-width:100%; max-height:70vh; object-fit:contain;"
                             onerror="this.parentElement.innerHTML='<div style=\\'color:#999; padding:40px; text-align:center;\\'>图片加载失败</div>'">
                    </div>
                ''', sanitize=False)

            elif ext in _MODEL_3D_EXTS:
                _inject_cdn(settings.MODEL_VIEWER_CDN, 'model-viewer')
                ui.html(f'''
                    <model-viewer src="{file_url}" auto-rotate camera-controls
                        style="width:100%; height:70vh; background:#e8e8e8; border-radius:4px;"
                        ar-status="not-presenting">
                    </model-viewer>
                ''', sanitize=False)

            elif ext in _DOCX_EXTS:
                ui.html(_build_preview_iframe(_DOCX_PREVIEW_HTML, file_url), sanitize=False)

            elif ext in _XLSX_EXTS:
                ui.html(_build_preview_iframe(_XLSX_PREVIEW_HTML, file_url), sanitize=False)

            elif ext in _TEXT_EXTS:
                ui.html(f'''
                    <iframe src="{file_url}" style="width:100%; height:70vh; border:none; border-radius:4px; background:#fafafa;">
                    </iframe>
                ''', sanitize=False)

            else:
                # ── 不支持预览的格式：降级提示 ──
                hint = _UNSUPPORTED_HINTS.get(ext, '')
                hint_text = f'<div style="font-size:14px; margin-top:8px;">建议使用 <b>{hint}</b> 打开此格式</div>' if hint else ''
                ui.html(f'''
                    <div style="text-align:center; padding:60px 20px; color:#666;">
                        <div style="font-size:48px; margin-bottom:16px;">📁</div>
                        <div style="font-size:16px; font-weight:bold; margin-bottom:4px;">暂不支持此文件格式 ({ext}) 的在线预览</div>
                        {hint_text}
                    </div>
                ''', sanitize=False)

            # ── 底部操作栏 ──
            ui.separator()
            with ui.row().classes('w-full justify-end mt-2'):
                download_url = f"{file_url}?inline=false"
                ui.button('📥 下载原文件', on_click=lambda d=download_url: ui.navigate.to(d, new_tab=True)) \
                    .classes('bg-blue-700 text-white font-bold text-sm px-4 py-2 rounded')

    return dialog
