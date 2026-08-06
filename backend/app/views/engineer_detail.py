"""
装配体详情页：BOM 树 + 工程图纸 + 技术文档 + 下级子 BOM 表格。
"""
import hashlib
import os
import uuid
from typing import Any, Callable, Dict, List

from nicegui import app, ui
from sqlalchemy import select as sa_select

from app.config import settings
from app.database.session import get_sync_db
from app.models.base import ObjectModel, FileModel
from app.models.business import (
    PartModel, DocumentModel, DrawingModel,
    BOMRelation, PartDocRelation, PartDrawingRelation,
)
from app.services.graph import AsyncGraphCrudEngine
from app.views.base import render_header
from app.views.components import (
    render_bom_tree,
    render_card_header,
    render_file_row,
    render_industrial_table,
)
from app.views.styles import SECTION_HEADER_CLASSES


def render_engineer_detail_page() -> None:
    render_header('engineer')

    node_detail = _load_node_detail()
    _render_breadcrumb(node_detail)
    _render_main_layout(node_detail)


def _load_node_detail() -> Dict[str, Any]:
    """从 storage 或 URL 参数读取物料编码，从数据库加载对应的详情数据。"""
    code = app.storage.user.get('selected_code', '')
    if not code:
        code = ''
    return _get_node_detail(code)


def _get_node_detail(code: str) -> Dict[str, Any]:
    """根据物料编码从数据库加载节点详情。"""
    if not code:
        return _empty_detail()

    with get_sync_db() as session:
        # 1. 查找零部件
        parts = AsyncGraphCrudEngine.query_nodes_by_property_sync(
            session, PartModel, "part_number", code
        )
        if not parts:
            return _empty_detail(code)

        part = parts[0]
        props = part.properties if part.properties else {}

        # 2. 元数据
        detail = {
            'part_id': str(part.id),
            'code': props.get('part_number', code),
            'name': props.get('name', ''),
            'version': props.get('version', 'V1.0'),
            'designer': props.get('designer', ''),
            'status': props.get('status', '草稿'),
            'type': part.object_type,
            'drawings': _load_drawings(session, part.id),
            'documents': _load_documents(session, part.id),
            'child_bom': _load_child_bom(session, part.id),
            'tree': _load_bom_tree_data(session, part.id),
        }
        return detail


def _empty_detail(code: str = 'N/A') -> Dict[str, Any]:
    """返回空的详情结构（节点不存在时使用）。"""
    return {
        'part_id': '',
        'code': code,
        'name': '',
        'version': '',
        'designer': '',
        'status': '',
        'type': '',
        'drawings': [],
        'documents': [],
        'child_bom': [],
        'tree': [],
    }


def _load_drawings(session, part_id: uuid.UUID) -> List[Dict[str, Any]]:
    """加载与指定零部件关联的工程图纸列表（仅返回已上传物理文件的条目）。"""
    drawings = []
    relations = AsyncGraphCrudEngine.query_relations_sync(
        session, PartDrawingRelation, source_id=part_id
    )
    for rel in relations:
        file_record = session.get(FileModel, rel.target_id)
        if not file_record:
            continue  # 跳过未上传物理文件的虚节点
        file_url = f"{settings.APP_HOST}/api/v1/files/download/{file_record.object_id}"
        file_size = _format_file_size(file_record.file_size)

        drawing = session.get(ObjectModel, rel.target_id)
        d_props = drawing.properties if drawing and drawing.properties else {}
        drawings.append({
            'name': file_record.original_name,
            'version': d_props.get('version', 'A.0'),
            'size': file_size,
            'url': file_url,
        })
    return drawings


def _load_documents(session, part_id: uuid.UUID) -> List[Dict[str, Any]]:
    """加载与指定零部件关联的技术文档列表（仅返回已上传物理文件的条目）。"""
    documents = []
    relations = AsyncGraphCrudEngine.query_relations_sync(
        session, PartDocRelation, source_id=part_id
    )
    for rel in relations:
        file_record = session.get(FileModel, rel.target_id)
        if not file_record:
            continue  # 跳过未上传物理文件的虚节点
        file_url = f"{settings.APP_HOST}/api/v1/files/download/{file_record.object_id}"

        doc = session.get(ObjectModel, rel.target_id)
        d_props = doc.properties if doc and doc.properties else {}
        documents.append({
            'name': file_record.original_name,
            'tag': d_props.get('tag', '技术文档'),
            'url': file_url,
        })
    return documents


def _load_child_bom(session, part_id: uuid.UUID) -> List[Dict[str, Any]]:
    """加载直属下级子物料清单（仅 BOM 关系 + PartModel）。"""
    children = []
    relations = AsyncGraphCrudEngine.query_relations_sync(
        session, BOMRelation, source_id=part_id
    )
    for rel in relations:
        child = session.get(ObjectModel, rel.target_id)
        if not child or child.object_type != 'part':
            continue
        c_props = child.properties if child.properties else {}
        r_props = rel.properties if rel.properties else {}
        children.append({
            'name': c_props.get('part_number') or c_props.get('name') or str(child.id)[:8],
            'type': child.object_type,
            'qty': r_props.get('quantity', 1),
        })
    return children


def _load_bom_tree_data(session, part_id: uuid.UUID, max_depth: int = 10) -> List[Dict[str, Any]]:
    """构建纯 BOM 层级树（只包含 object_type="part" 的零部件节点）。"""
    root = session.get(ObjectModel, part_id)
    root_props = root.properties if root and root.properties else {}
    root_label = root_props.get('part_number') or root_props.get('name') or str(part_id)[:8]

    def _get_bom_children(node_id: uuid.UUID, depth: int = 0) -> List[Dict[str, Any]]:
        if depth >= max_depth:
            return []
        children: List[Dict[str, Any]] = []
        rels = session.execute(
            sa_select(BOMRelation).where(BOMRelation.source_id == node_id)
        ).scalars().all()
        for rel in rels:
            child = session.get(ObjectModel, rel.target_id)
            # 只展示零部件节点，跳过图纸/文档等其他类型
            if not child or child.object_type != 'part':
                continue
            c_props = child.properties or {}
            child_label = c_props.get('part_number') or c_props.get('name') or str(child.id)[:8]
            grand_children = _get_bom_children(child.id, depth + 1)
            node: Dict[str, Any] = {
                'id': str(child.id),
                'label': child_label,
            }
            # 叶子节点不包含 children 键 → Quasar 识别为真叶节点 → 触发 update:selected
            if grand_children:
                node['children'] = grand_children
            children.append(node)
        return children

    bom_children = _get_bom_children(part_id)
    root_node: Dict[str, Any] = {
        'id': str(part_id),
        'label': root_label,
    }
    if bom_children:
        root_node['children'] = bom_children
    return [root_node]


def _load_node_detail_by_id(part_id: uuid.UUID) -> Dict[str, Any]:
    """根据节点 UUID 加载该节点的元数据、图纸、文档、下级 BOM（不含树）。"""
    with get_sync_db() as session:
        obj = session.get(ObjectModel, part_id)
        if not obj:
            return _empty_detail()
        props = obj.properties or {}
        return {
            'part_id': str(obj.id),
            'code': props.get('part_number') or props.get('name') or str(obj.id)[:8],
            'name': props.get('name', ''),
            'version': props.get('version', 'V1.0'),
            'designer': props.get('designer', ''),
            'status': props.get('status', '草稿'),
            'type': obj.object_type,
            'drawings': _load_drawings(session, obj.id),
            'documents': _load_documents(session, obj.id),
            'child_bom': _load_child_bom(session, obj.id),
            'tree': _load_bom_tree_data(session, obj.id),
        }


def _format_file_size(size_bytes: int) -> str:
    """将字节数格式化为人类可读的大小。"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


# ============================================================
# 文件上传处理函数
# ============================================================

async def _handle_upload(
    e: Any,
    dialog: Any,
    node_detail: Dict[str, Any],
    file_type: str,
    relation_class: Any,
    model_class: Any,
) -> None:
    """处理文件上传完整流程：创建目标节点 → 织网连线 → 物理落盘（同一事务）。"""
    try:
        # NiceGUI UploadEventArguments: 文件信息在 e.file (FileUpload 对象) 中
        filename = e.file.name or 'unknown'
        mime_type = e.file.content_type or 'application/octet-stream'
        content = await e.file.read()

        if not content:
            ui.notify('文件内容为空，请重新选择', type='warning')
            return

        part_id_str = node_detail.get('part_id', '')
        if not part_id_str:
            ui.notify('无法获取当前物料信息，请刷新页面后重试', type='warning')
            return
        part_id = uuid.UUID(part_id_str)

        file_size = e.file.size()

        # ── 同一事务：创建节点 → 创建关系 → 物理落盘 ──
        with get_sync_db() as session:
            # 1. 创建目标节点（图纸或文档）
            model_name = os.path.splitext(filename)[0] if '.' in filename else filename
            obj = model_class(
                object_type=file_type,
                properties={
                    "name": model_name,
                    "version": "V1.0",
                },
            )
            session.add(obj)
            session.flush()

            # 2. 创建关系连线
            if file_type == 'drawing':
                rel = PartDrawingRelation(
                    relation_type="part_drawing_relation",
                    source_id=part_id,
                    target_id=obj.id,
                    properties={"is_primary": False},
                )
            else:
                rel = PartDocRelation(
                    relation_type="part_doc_relation",
                    source_id=part_id,
                    target_id=obj.id,
                    properties={},
                )
            session.add(rel)
            session.flush()

            # 3. 物理落盘 + 创建 FileModel 记账记录
            os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

            file_extension = os.path.splitext(filename)[1].lower() if '.' in filename else ''
            md5_hash = hashlib.md5(content).hexdigest()
            unique_filename = f"{md5_hash}{file_extension}"
            file_save_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

            # MD5 去重检查
            existing = session.execute(
                sa_select(FileModel).where(FileModel.stored_name == unique_filename)
            ).scalar_one_or_none()

            is_duplicate = False
            if existing and os.path.exists(existing.absolute_path):
                file_save_path = existing.absolute_path  # 物理文件复用
                # stored_name 有 UNIQUE 约束，去重时追加对象 ID 后缀避免冲突
                unique_filename = f"{md5_hash}_{obj.id.hex[:8]}{file_extension}"
                is_duplicate = True
            else:
                with open(file_save_path, "wb") as f:
                    f.write(content)

            # 创建 FileModel 记账记录
            db_file = FileModel(
                object_id=obj.id,
                original_name=filename,
                stored_name=unique_filename,
                file_size=file_size,
                mime_type=mime_type,
                absolute_path=file_save_path,
            )
            session.add(db_file)

            # 更新关联节点属性
            db_obj = session.get(ObjectModel, obj.id)
            if db_obj:
                props = dict(db_obj.properties) if db_obj.properties else {}
                props["file_status"] = "ready"
                props["status"] = "ready"
                props["is_uploaded"] = True
                props["md5"] = md5_hash
                props["is_hit_cache"] = is_duplicate
                db_obj.properties = props
                session.add(db_obj)

            # 同一事务提交
            session.commit()

        # 4. 关闭对话框并刷新页面
        dialog.close()
        ui.notify(f'✅ {filename} 上传成功！', type='positive', position='top')
        ui.navigate.reload()

    except Exception as exc:
        ui.notify(f'❌ 上传失败: {str(exc)}', type='negative', position='top')


def _create_upload_dialog(
    node_detail: Dict[str, Any],
    file_type: str,
    relation_class: Any,
    model_class: Any,
) -> Any:
    """创建文件上传对话框（图纸或文档通用）。"""
    type_labels = {'drawing': '图纸', 'document': '文档'}
    label = type_labels.get(file_type, file_type)
    icon = '📐' if file_type == 'drawing' else '📑'

    with ui.dialog() as dialog:
        with ui.card().classes('w-96 max-w-lg'):
            ui.label(f'{icon} 上传{label}文件').classes('text-lg font-bold mb-2')
            ui.label(f'目标物料: {node_detail.get("code", "")} — {node_detail.get("name", "")}') \
                .classes('text-sm text-gray-600 mb-4')

            async def on_upload(e: Any) -> None:
                await _handle_upload(
                    e, dialog, node_detail, file_type, relation_class, model_class
                )

            ui.upload(
                on_upload=on_upload,
                auto_upload=True,
                label=f'点击或拖拽{label}文件到此处',
                multiple=False,
            ).classes('w-full')

            ui.separator()
            with ui.row().classes('w-full justify-end mt-2 gap-2'):
                ui.button('取消', on_click=dialog.close) \
                    .classes('bg-gray-300 text-black text-xs px-4 py-1 rounded')

    return dialog


# ============================================================
# 页面渲染函数
# ============================================================

def _render_breadcrumb(node_detail: Dict[str, Any]) -> None:
    with ui.row().classes('w-full p-4 bg-gray-100 items-center justify-between border-b shadow-sm'):
        with ui.row().classes('items-center gap-2 text-base font-bold text-gray-700'):
            ui.link('📟 设计资产库', '/engineer').classes('text-blue-700 underline')
            ui.label('/')
            ui.label(f"装配体详情: {node_detail.get('code', '')}").classes('text-gray-900 font-black')
        ui.button('返回列表', on_click=lambda: ui.navigate.to('/engineer')).classes(
            'bg-gray-700 text-white font-bold text-xs px-3 py-1 rounded shadow'
        )


def _render_main_layout(node_detail: Dict[str, Any]) -> None:
    # 闭包捕获右侧面板引用的容器（在 row 内部创建后才赋值）
    _right_panel_ref: List[Any] = [None]

    def _refresh_right_panel(part_id_str: str) -> None:
        """根据节点 UUID 重新加载并渲染右侧面板的全部内容。"""
        right_panel = _right_panel_ref[0]
        if not part_id_str or right_panel is None:
            return
        try:
            new_detail = _load_node_detail_by_id(uuid.UUID(part_id_str))
        except (ValueError, AttributeError):
            return
        right_panel.clear()
        with right_panel:
            _render_drawings_section(new_detail)
            _render_documents_section(new_detail)
            _render_child_bom_section(new_detail)

    def _on_node_click(node_id: str) -> None:
        """树节点点击回调：刷新右侧图文档面板。"""
        if node_id:
            _refresh_right_panel(node_id)

    with ui.row().classes('w-full p-4 gap-4 items-start'):
        # ── 左侧列 ──
        with ui.column().classes('w-1/3 gap-4'):
            _render_meta_card(node_detail)
            _render_tree_card(node_detail, on_node_click=_on_node_click)

        # ── 右侧列（在 row 内部创建，确保属于 flex 布局）──
        with ui.column().classes('w-3/5 gap-4') as right_panel:
            _right_panel_ref[0] = right_panel
            _render_drawings_section(node_detail)
            _render_documents_section(node_detail)
            _render_child_bom_section(node_detail)


# ============================================================
# 左侧面板渲染
# ============================================================

def _render_meta_card(node_detail: Dict[str, Any]) -> None:
    with ui.card().classes('w-full p-4 shadow-sm bg-white border border-gray-200'):
        render_card_header(icon_name='info', title='📌 物料基础信息')
        with ui.column().classes('gap-1 text-base text-gray-800 font-medium'):
            ui.label(f"物料编码: {node_detail.get('code', '')}").classes('font-bold text-lg')
            ui.label(f"物料名称: {node_detail.get('name', '')}")
            ui.label(f"当前版本: {node_detail.get('version', '')}").classes('text-green-800 font-bold')
            ui.label(f"设计师: {node_detail.get('designer', '')}")
            ui.label(f"状态: {node_detail.get('status', '')}")


def _render_tree_card(node_detail: Dict[str, Any], on_node_click: Callable = None) -> None:
    with ui.card().classes('w-full p-4 shadow-sm bg-white border border-gray-200'):
        render_card_header(icon_name='account_tree', title='🌳 BOM 层级关系树')
        render_bom_tree(
            tree_data=node_detail.get('tree', []),
            on_node_click=on_node_click or (lambda node_id: None),
        )


def _render_drawings_section(node_detail: Dict[str, Any]) -> None:
    upload_dialog = _create_upload_dialog(
        node_detail, 'drawing', PartDrawingRelation, DrawingModel
    )

    with ui.card().classes('w-full p-4 shadow-sm bg-white border border-gray-200'):
        render_card_header(
            icon_name='draw',
            title='📐 关联工程图纸',
            button_text='+ 上传新图纸',
            on_click=upload_dialog.open,
        )
        drawings = node_detail.get('drawings', [])
        if not drawings:
            ui.label('暂无关联图纸').classes('text-gray-400 italic text-sm p-2')
        else:
            for dwg in drawings:
                render_file_row(
                    icon_name='picture_as_pdf',
                    icon_color='blue-7',
                    name=dwg['name'],
                    meta=f"版本 {dwg['version']} | {dwg['size']}",
                    meta_classes='text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded',
                    button_text='在线预览',
                    button_classes='text-blue-900 font-black text-sm border border-blue-300 px-3 py-1 rounded',
                    on_click=lambda d=dwg: ui.navigate.to(d['url'], new_tab=True),
                )


def _render_documents_section(node_detail: Dict[str, Any]) -> None:
    upload_dialog = _create_upload_dialog(
        node_detail, 'document', PartDocRelation, DocumentModel
    )

    with ui.card().classes('w-full p-4 shadow-sm bg-white border border-gray-200'):
        render_card_header(
            icon_name='assignment',
            title='📑 关联技术文档 & SOP 说明书',
            button_text='+ 绑定新文档',
            on_click=upload_dialog.open,
            button_classes='bg-green-800 text-white font-bold text-xs',
        )
        documents = node_detail.get('documents', [])
        if not documents:
            ui.label('暂无关联文档').classes('text-gray-400 italic text-sm p-2')
        else:
            for doc in documents:
                render_file_row(
                    icon_name='insert_drive_file',
                    icon_color='green-7',
                    name=doc['name'],
                    meta=doc['tag'],
                    meta_classes='text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded',
                    button_text='查看文档',
                    button_classes='text-green-900 font-black text-sm border border-green-300 px-3 py-1 rounded',
                    on_click=lambda d=doc: ui.navigate.to(d['url'], new_tab=True),
                )


def _render_child_bom_section(node_detail: Dict[str, Any]) -> None:
    columns = [
        {'name': 'name', 'label': '下级子物料/子装配体名称', 'field': 'name', 'align': 'left'},
        {'name': 'type', 'label': '类型', 'field': 'type', 'align': 'center'},
        {'name': 'qty', 'label': '单台用量', 'field': 'qty', 'align': 'center'},
    ]

    with ui.card().classes('w-full p-4 shadow-sm bg-white border border-gray-200'):
        ui.label('🧩 下级构成清单 (Child BOM)').classes(SECTION_HEADER_CLASSES)
        rows = node_detail.get('child_bom', [])
        if not rows:
            ui.label('暂无子物料').classes('text-gray-400 italic text-sm p-2')
        else:
            render_industrial_table(
                columns=columns,
                rows=rows,
                row_key='name',
            )
