"""
车间看图页面：条码搜索 + 3D/2D 图纸渲染。
"""
from typing import Optional
from nicegui import ui

from app.config import settings
from app.database.session import get_sync_db
from app.models.base import FileModel
from app.models.business import PartModel, DrawingModel, PartDrawingRelation
from app.services.graph import AsyncGraphCrudEngine
from app.views.base import ecn_notifier, render_header


def render_workshop_page() -> None:
    _inject_model_viewer_cdn()
    render_header('workshop')

    with ui.column().classes('w-full p-4 items-center bg-stone-100 min-h-screen'):
        _render_search_bar()


def _inject_model_viewer_cdn() -> None:
    cdn_url = settings.MODEL_VIEWER_CDN
    ui.add_head_html(f'<script type="module" src="{cdn_url}"></script>')


def _render_search_bar() -> None:
    with ui.card().classes('w-11/12 p-6 shadow-md bg-white border-2 border-stone-300 items-center'):
        ui.label('请输入或扫描物料条码/代号，查询车间最新生产图纸').classes(
            'text-xl font-black text-stone-800 mb-2'
        )

        search_input: Optional[ui.input] = None

        def trigger_search() -> None:
            user_code = search_input.value.strip() if search_input and search_input.value else ''
            if not user_code:
                ui.notify('请输入有效的物料编码/条码！', type='warning')
                return

            if ecn_notifier.has_notifications:
                _show_ecn_warning_dialog(user_code)
            else:
                _load_drawings(user_code)

        with ui.row().classes('w-full gap-2 justify-center items-center'):
            search_input = ui.input(placeholder='输入物料代号（如：WD-ZK02）').classes(
                'w-1/2 text-xl font-bold'
            )
            ui.button('🔍 调出最新图纸', on_click=trigger_search).classes(
                'bg-blue-900 text-white font-black text-lg px-6 py-2 rounded shadow'
            )


def _show_ecn_warning_dialog(user_code: str) -> None:
    with ui.dialog() as dialog, ui.card().classes('p-6 bg-red-50 border-4 border-red-600 border-dashed'):
        ui.label('🚨 ECN 变更警告！').classes('text-2xl font-black text-red-700')
        ui.label(
            f'您调取的是最新变更物料 [{user_code}]，请注意核对版次是否与看板一致！'
        ).classes('text-lg text-red-900 font-bold my-2 text-center')
        ui.button('我已明白，立刻看最新电子图', on_click=lambda: (dialog.close(), _load_drawings(user_code))).classes(
            'bg-stone-900 text-white font-bold text-lg px-6 py-2 rounded'
        )
    dialog.open()


def _load_drawings(user_code: str) -> None:
    """根据物料编码从数据库查询关联的 3D/2D 图纸文件并渲染。"""
    with get_sync_db() as session:
        parts = AsyncGraphCrudEngine.query_nodes_by_property_sync(
            session, PartModel, "part_number", user_code
        )
        if not parts:
            ui.notify(f'未找到物料编码 [{user_code}]，请检查输入是否正确', type='warning')
            return

        part = parts[0]
        part_props = part.properties if part.properties else {}
        part_name = part_props.get('name', user_code)

        # 查询关联的图纸关系
        relations = AsyncGraphCrudEngine.query_relations_sync(
            session, PartDrawingRelation, source_id=part.id
        )

        glb_url = ''
        pdf_url = ''

        for rel in relations:
            drawing = AsyncGraphCrudEngine.get_node_by_id_sync(
                session, DrawingModel, rel.target_id
            )
            if not drawing:
                continue
            file_record = session.get(FileModel, rel.target_id)
            if not file_record:
                continue

            file_url = f"/static/uploads/{file_record.stored_name}"
            original_lower = file_record.original_name.lower()
            if original_lower.endswith(('.glb', '.gltf')):
                glb_url = file_url
            elif original_lower.endswith(('.pdf', '.dxf', '.dwg', '.svg')):
                pdf_url = file_url
            else:
                # 非标准格式 → 第一个作为 2D 图纸
                if not pdf_url:
                    pdf_url = file_url

        if not glb_url and not pdf_url:
            ui.notify(f'物料 [{part_name}] 暂无关联图纸文件，请联系设计部上传', type='info')
            return

        _render_drawing_viewer(part_name, glb_url, pdf_url)


def _render_drawing_viewer(label: str, glb_url: str, pdf_url: str) -> None:
    with ui.card().classes('w-11/12 p-4 shadow-xl border mt-4 bg-white'):
        ui.label(f'📐 当前物料图纸看板 [{label}]').classes('text-xl font-black text-gray-800 mb-2')
        with ui.tabs().classes('w-full bg-stone-200 font-black text-lg text-stone-900') as tabs:
            tab_3d = ui.tab('📦 3D 模具视角 (支持拖拽旋转)')
            tab_2d = ui.tab('📐 2D 矢量工艺图 (PDF/DXF)')

        with ui.tab_panels(tabs, value=tab_3d if glb_url else tab_2d).classes('w-full h-96'):
            with ui.tab_panel(tab_3d):
                if glb_url:
                    ui.html(
                        f'<model-viewer src="{glb_url}" auto-rotate camera-controls style="width: 100%; height: 350px;"></model-viewer>'
                    )
                else:
                    ui.label('暂无 3D 模型').classes('text-gray-400 italic text-center mt-16 text-lg')
            with ui.tab_panel(tab_2d):
                if pdf_url:
                    ui.html(
                        f'<iframe src="{pdf_url}" style="width: 100%; height: 350px; border: none;"></iframe>'
                    )
                else:
                    ui.label('暂无 2D 图纸').classes('text-gray-400 italic text-center mt-16 text-lg')
