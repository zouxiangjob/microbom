"""
采购端页面：BOM 打平合并总表 + ERP 标准采购导入格式 Excel 导出。
"""
import os
from typing import List, Optional

import pandas as pd
from nicegui import ui

from app.config import settings
from app.database.session import get_sync_db
from app.services.graph import AsyncGraphCrudEngine
from app.views.base import ecn_notifier, render_header
from app.views.components import render_industrial_table
from app.views.styles import HEADER_LABEL_CLASSES

EXPORT_DIR = settings.EXPORT_DIR
EXPORT_FILENAME = '采购订单导入表.xlsx'

_purchase_table_ref: Optional[ui.table] = None


def render_purchase_page() -> None:
    render_header('purchase')
    _render_ecn_alert()
    _render_toolbar()
    _render_bom_table()


def _render_ecn_alert() -> None:
    if not ecn_notifier.has_notifications:
        return

    with ui.card().classes('w-full bg-red-50 border-2 border-red-300 p-4 mb-2 shadow-md'):
        with ui.row().classes('items-center gap-2 text-red-800 font-black text-lg'):
            ui.icon('report_problem', size='md')
            ui.label('🚨 收到设计部新版本变更紧急通知（请务必核对并修改 ERP 订单！）')

        with ui.column().classes('pl-8 mt-1 gap-1 text-red-900 font-bold'):
            for note in ecn_notifier.get():
                ui.label(f'• {note}')

        with ui.row().classes('w-full justify-end mt-2'):
            ui.button(
                '确认知晓变更',
                on_click=lambda: (ecn_notifier.clear(), ui.navigate.reload()),
            ).classes('bg-red-800 text-white font-black text-sm px-4 py-1.5 rounded shadow')


def _render_toolbar() -> None:
    with ui.row().classes('w-full p-4 bg-gray-100 items-center justify-between border-b shadow-sm'):
        ui.label('📊 采购 BOM 汇总与导出面板').classes(HEADER_LABEL_CLASSES)
        ui.button(
            '📥 导出ERP 采购导入文件 (.xlsx)',
            on_click=_export_to_gjp_excel,
        ).classes('bg-green-800 text-white font-black text-base px-4 py-2 rounded shadow-md')


def _render_bom_table() -> None:
    global _purchase_table_ref
    with ui.card().classes('w-full p-4 shadow-md bg-white border border-gray-200 mt-2'):
        rows = _get_purchase_rows()
        _purchase_table_ref = render_industrial_table(
            columns=_get_purchase_columns(),
            rows=rows,
            row_key='code',
        )
        _inject_qty_edit_slot(_purchase_table_ref)

        if not rows:
            ui.label('暂无采购数据 — 请先在工程师端创建零部件并建立 BOM 关系').classes(
                'text-gray-400 italic text-sm mt-2'
            )


def _inject_qty_edit_slot(table: ui.table) -> None:
    """插入数量列的双击即时编辑 Pop-up。"""
    table.add_slot('body-cell-qty', '''
        <q-td :props="props" class="cursor-pointer">
            <span class="text-blue-900 font-black text-lg">{{ props.row.qty }}</span>
            <q-popup-edit v-model="props.row.qty" v-slots:default="{ value, emitValue }" buttons persistent>
                <q-input type="number" v-model.number="value" dense autofocus counter
                    @keyup.enter="emitValue"
                    style="font-size: 18px; font-weight: bold;" />
            </q-popup-edit>
        </q-td>
    ''')


def _export_to_gjp_excel() -> None:
    """导出为ERP 标准采购导入格式 Excel，拉取表格实时修改后数据。"""
    try:
        os.makedirs(EXPORT_DIR, exist_ok=True)

        # 实时从 UI 表格获取经过用户在线编辑修改后的最新 rows 列表
        web_edited_rows = _purchase_table_ref.rows if _purchase_table_ref else _get_purchase_rows()

        df = pd.DataFrame(web_edited_rows)
        df_gjp = pd.DataFrame()
        df_gjp['编号'] = df['code'] if 'code' in df else []
        df_gjp['名称'] = df['name'] if 'name' in df else []
        df_gjp['规格'] = df['spec'] if 'spec' in df else []
        df_gjp['采购数量'] = df['qty'] if 'qty' in df else []
        df_gjp['出入库仓库'] = '主物料仓'
        df_gjp['备注说明'] = 'MicroBOM 系统自动打平去重导出'

        export_path = os.path.join(EXPORT_DIR, EXPORT_FILENAME)
        df_gjp.to_excel(export_path, index=False, engine='openpyxl')

        ui.notify(f'导出成功！文件已存至: {export_path}', type='positive')
        ui.download(export_path)

    except Exception as e:
        ui.notify(f'导出 Excel 失败: {str(e)}', type='negative')


# ============================================================
# 业务数据获取函数
# ============================================================

def _get_purchase_columns() -> List[dict]:
    """返回采购 BOM 表格列定义。"""
    return [
        {'name': 'code', 'label': '编号', 'field': 'code', 'align': 'left'},
        {'name': 'name', 'label': '名称', 'field': 'name', 'align': 'left'},
        {'name': 'spec', 'label': '规格型号', 'field': 'spec', 'align': 'left'},
        {'name': 'qty', 'label': '采购数量', 'field': 'qty', 'align': 'center'},
        {'name': 'unit', 'label': '单位', 'field': 'unit', 'align': 'center'},
    ]


def _get_purchase_rows() -> List[dict]:
    """从数据库打平 BOM 树，按零件编码去重汇总，返回采购清单行。"""
    with get_sync_db() as session:
        return AsyncGraphCrudEngine.flatten_bom_sync(session)
