"""
工程师端页面：BOM 特征树 + 版本历史 + 发布控制。
"""
from typing import Any, List

from nicegui import app, ui

from app.database.session import AsyncSessionLocal
from app.logging_config import get_logger
from app.models.business import PartModel
from app.services.ecn import build_ecn_diff_logs
from app.services.graph import AsyncGraphCrudEngine
from app.views.base import ecn_notifier, render_header
from app.views.components import render_bom_tree, render_industrial_table
from app.views.styles import HEADER_LABEL_CLASSES

logger = get_logger("engineer")


async def render_engineer_page() -> None:
    render_header('engineer')

    current_role = app.storage.user.get('role', 'admin')

    _render_toolbar(current_role)
    await _render_main_content(current_role)


def _render_toolbar(current_role: str) -> None:
    with ui.row().classes('w-full p-4 bg-gray-100 items-center justify-between border-b shadow-sm'):
        ui.label('📟 设计部图文档资产库').classes(HEADER_LABEL_CLASSES)
        role_label = '🌟 主管总工 (拥有硬发布权)' if current_role == 'admin' else '普通工程师 (仅限上传)'
        ui.label(f'权限锁：{role_label}').classes(
            'bg-blue-900 text-white px-3 py-1.5 rounded font-black text-sm shadow'
        )


async def _render_main_content(current_role: str) -> None:
    with ui.card().classes('w-12/12 p-4 shadow-md bg-white border border-gray-200'):
        ui.label('待审发布版本控制台').classes('text-lg font-black text-blue-950 border-b pb-2 mb-2')

        pending_table = render_industrial_table(
            columns=_get_engineer_table_columns(),
            rows=await _get_pending_rows(),
            row_key='code',
        )
        _inject_code_slot(pending_table)
        _inject_action_slot(pending_table, current_role)


def _inject_code_slot(pending_table: ui.table) -> None:
    """物料编码列渲染为可点击链接，点击跳转到详情页。"""
    pending_table.add_slot('body-cell-code', '''
        <q-td :props="props" class="cursor-pointer hover:bg-blue-50 transition-colors">
            <span class="text-blue-700 font-bold underline"
                  @click="() => $q.notify({ type: 'info', message: '正在加载 [' + props.row.code + '] 的详情...' })">
                {{ props.row.code }}
            </span>
        </q-td>
    ''')

    def on_row_click(event: Any) -> None:
        """安全捕获并解析 Quasar 行点击事件列表参数"""
        if hasattr(event, 'args') and isinstance(event.args, list) and len(event.args) > 1:
            row_data = event.args[1]
            if isinstance(row_data, dict):
                code = row_data.get('code', '')
                if code:
                    app.storage.user['selected_code'] = code
                    ui.navigate.to(f'/engineer_detail?code={code}')

    # 绑定 Quasar 行点击原生事件
    pending_table.on('rowClick', on_row_click)


def _inject_action_slot(pending_table: ui.table, current_role: str) -> None:
    """渲染关键控制按钮：主管拥有发布新版控制权。"""
    is_admin = current_role == 'admin'
    disabled_attr = 'false' if is_admin else 'true'

    pending_table.add_slot('body-cell-action', f'''
        <q-td :props="props">
            <q-btn
                color="green-8"
                icon="rocket_launch"
                label="审核通过并发布新版"
                dense
                class="q-px-md text-weight-bold"
                :disabled="{disabled_attr}"
                @click="() => {{
                    $q.notify({{ type: 'positive', message: '项目 [' + props.row.code + '] 新版本发布成功！自动下发变更通知。' }});
                    NiceGUI.run_method('on_click_release_btn', props.row.code);
                }}"
            />
        </q-td>
    ''')


async def on_click_release_btn(item_code: str) -> None:
    """主管点击发布按钮后的后端响应逻辑。"""
    logger.info("主管已授权发布新版本，编码: %s", item_code)
    async with AsyncSessionLocal() as session:
        logs = await build_ecn_diff_logs(session, item_code)
    ecn_notifier.publish(logs)
    ui.notify(f'已向全厂下发 {item_code} 的 ECN 变更通知！', type='positive')


# ============================================================
# 业务数据获取函数（后续替换为实际数据库/服务调用）
# ============================================================

def _get_engineer_table_columns() -> List[dict]:
    """返回工程师端待审表格列定义。"""
    # TODO: 从业务层获取列配置，或直接返回固定列定义
    return [
        {'name': 'code', 'label': '物料编码', 'field': 'code', 'align': 'left'},
        {'name': 'name', 'label': '名称', 'field': 'name', 'align': 'left'},
        {'name': 'ver', 'label': '备份版本', 'field': 'ver', 'align': 'center'},
        {'name': 'user', 'label': '上传设计师', 'field': 'user', 'align': 'center'},
        {'name': 'action', 'label': '关键发布控制', 'field': 'action', 'align': 'center'},
    ]


async def _get_pending_rows() -> List[dict]:
    """从数据库查询所有零部件（PartModel），返回待审表格行数据。"""
    async with AsyncSessionLocal() as session:
        parts = await AsyncGraphCrudEngine.query_nodes_by_type(session, PartModel, limit=500)
        rows: List[dict] = []
        for p in parts:
            rows.append({
                'code': p.properties.get('part_number', ''),
                'name': p.properties.get('name', ''),
                'ver': p.properties.get('version', 'V1.0'),
                'user': p.properties.get('designer', ''),
            })
        return rows
