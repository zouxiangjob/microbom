"""
工程师端页面：BOM 特征树 + 版本时光机 + 发布控制。
"""
from typing import Any, List

from nicegui import app, ui

from app.database.session import get_sync_db
from app.models.business import PartModel
from app.services.graph import AsyncGraphCrudEngine
from app.views.base import ecn_notifier, render_header
from app.views.components import render_bom_tree, render_industrial_table
from app.views.styles import HEADER_LABEL_CLASSES


def render_engineer_page() -> None:
    render_header('engineer')

    current_role = app.storage.user.get('role', 'admin')

    _render_toolbar(current_role)
    _render_main_content(current_role)


def _render_toolbar(current_role: str) -> None:
    with ui.row().classes('w-full p-4 bg-gray-100 items-center justify-between border-b shadow-sm'):
        ui.label('📟 设计部图文档资产库').classes(HEADER_LABEL_CLASSES)
        role_label = '🌟 主管总工 (拥有硬发布权)' if current_role == 'admin' else '普通工程师 (仅限上传)'
        ui.label(f'权限锁：{role_label}').classes(
            'bg-blue-900 text-white px-3 py-1.5 rounded font-black text-sm shadow'
        )


def _render_main_content(current_role: str) -> None:
    with ui.card().classes('w-12/12 p-4 shadow-md bg-white border border-gray-200'):
        ui.label('待审发布版本控制台').classes('text-lg font-black text-blue-950 border-b pb-2 mb-2')

        pending_table = render_industrial_table(
            columns=_get_engineer_table_columns(),
            rows=_get_pending_rows(),
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


def on_click_release_btn(item_code: str) -> None:
    """主管点击发布按钮后的后端响应逻辑。"""
    print(f'====== 主管已授权发布新版本，编码: {item_code} ======')
    ecn_notifier.publish(_get_ecn_diff_logs(item_code))
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


def _get_pending_rows() -> List[dict]:
    """从数据库查询所有零部件（PartModel），返回待审表格行数据。"""
    with get_sync_db() as session:
        parts = AsyncGraphCrudEngine.query_nodes_by_type_sync(session, PartModel, limit=500)
        rows: List[dict] = []
        for p in parts:
            rows.append({
                'code': p.properties.get('part_number', ''),
                'name': p.properties.get('name', ''),
                'ver': p.properties.get('version', 'V1.0'),
                'user': p.properties.get('designer', ''),
            })
        return rows


def _get_ecn_diff_logs(item_code: str) -> List[str]:
    """从数据库加载指定物料的 BOM 结构，生成 ECN 变更差异日志。"""
    with get_sync_db() as session:
        parts = AsyncGraphCrudEngine.query_nodes_by_property_sync(
            session, PartModel, "part_number", item_code
        )
        if not parts:
            return [f"物料 [{item_code}] 未在系统中找到"]

        part = parts[0]
        props = part.properties if part.properties else {}
        part_name = props.get('name', item_code)
        version = props.get('version', 'V1.0')
        designer = props.get('designer', '未知')

        # 加载 BOM 树，生成变更描述
        tree = AsyncGraphCrudEngine.get_node_tree_by_cte_sync(session, part.id, max_depth=10)

        logs = [
            f"变更对象: {item_code} ({part_name})",
            f"版本号: {version} | 设计师: {designer}",
        ]

        if tree:
            # 汇总直接子件
            direct_children = [n for n in tree if n["depth"] == 1]
            logs.append(f"直属子件共 {len(direct_children)} 个:")
            for child in direct_children[:20]:  # 最多显示 20 个
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