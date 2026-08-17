// 前后端字段映射契约
// 后端采用「万物皆对象」：字段全部存在 properties JSON，没有强 Schema。
// 本文件是前后端字段对齐的唯一入口，后端改键名或前端改列名都只动这里。

// 种子数据（backend/seed_data.py）实际写入 properties 的键：
//   part:     part_number / name / version / designer / status / category / weight / material
//   drawing:  name / version / drawing_type / format
//   document: name / doc_version / tag

export const PART_FIELDS = {
  code: 'part_number',
  name: 'name',
  version: 'version',
  designer: 'designer',
  status: 'status',
  category: 'category',
  weight: 'weight',
  material: 'material'
}

// 零部件详情页「基本属性」展示字段（Attribute.vue / Bom.vue 属性页复用）。
// kind='status' 表示需渲染为状态标签；unit 追加在值后（如重量 kg）。
export const PART_DISPLAY_FIELDS = [
  { key: 'name', label: '名称' },
  { key: 'part_number', label: '编码' },
  { key: 'version', label: '版本' },
  { key: 'status', label: '数据状态', kind: 'status' },
  { key: 'category', label: '类别' },
  { key: 'material', label: '材料' },
  { key: 'weight', label: '重量', unit: ' kg' },
  { key: 'designer', label: '设计者' }
]

const OBJECT_TYPE_LABELS = {
  part: '部件',
  document: '文档',
  drawing: '图档',
  attachment: '附件',
  category: '分类'
}

// 节点 → 首页列表行（对齐 Index.vue 表格列）
export function nodeToRow(node) {
  const p = node.properties || {}
  const code = p[PART_FIELDS.code] || ''
  const name = p[PART_FIELDS.name] || ''
  const version = p[PART_FIELDS.version] || ''
  return {
    id: node.id,
    code,
    name,
    version,
    status: p[PART_FIELDS.status] || '--',
    creator: p[PART_FIELDS.designer] || '--',
    category: p[PART_FIELDS.category] || '',
    displayName: `${code}/${version};${name}`
  }
}

// 节点 → 首页列表行（技术文档）
export function documentToRow(node) {
  const p = node.properties || {}
  return {
    id: node.id,
    name: p.name || '--',
    tag: p.tag || '--',
    version: p.doc_version || '--'
  }
}

// 节点 → 首页列表行（图档）
export function drawingToRow(node) {
  const p = node.properties || {}
  return {
    id: node.id,
    name: p.name || '--',
    type: p.drawing_type || '--',
    version: p.version || '--',
    format: p.format || '--'
  }
}

// ── 详情页行映射：关系边 + 目标节点 → 表格行 ──
// node 为 { id, object_type, properties }，edge 为 { id, relation_type, source_id, target_id, properties }

// BOM 子件行（Bom.vue 右侧表格）
export function bomRow(node, edge) {
  const p = node.properties || {}
  const ep = edge.properties || {}
  return {
    id: node.id,
    edgeId: edge.id,
    code: p.part_number || '',
    name: p.name || '--',
    spec: p.material || '--',
    version: p.version || '--',
    quantity: ep.quantity ?? 1,
    unit: ep.unit || 'pcs'
  }
}

// 图档行（RelatedObjects drawing）
export function drawingRow(node, edge) {
  const p = node.properties || {}
  const ep = edge.properties || {}
  return {
    id: node.id,
    edgeId: edge.id,
    name: p.name || '--',
    relation: ep.is_primary ? '主关联' : '被动关联',
    version: p.version || '--',
    type: p.drawing_type || '--',
    format: p.format || '--'
  }
}

// 文档行（RelatedObjects document）
export function docRow(node, edge) {
  const p = node.properties || {}
  const ep = edge.properties || {}
  return {
    id: node.id,
    edgeId: edge.id,
    name: p.name || '--',
    type: p.tag || '--',
    version: p.doc_version || '--',
    quantity: ep.quantity ?? '--',
    unit: ep.unit ?? '--'
  }
}

// 数据状态 → Element Plus tag 类型（首页与详情页统一着色）
const STATUS_TAG_TYPES = {
  草稿: 'info',
  待审核: 'warning',
  已发布: 'success',
  已归档: 'info'
}
export function statusTagType(status) {
  return STATUS_TAG_TYPES[status] || 'info'
}

// 节点 → 详情页标题（如「ME000000253/B.1;GSK磨床」，与首页 displayName 同构）
export function nodeTitle(node) {
  const p = node.properties || {}
  const code = p[PART_FIELDS.code] || ''
  const version = p[PART_FIELDS.version] || ''
  const name = p[PART_FIELDS.name] || '未命名'
  return code ? `${code}/${version};${name}` : name
}

// 非零部件对象（技术文档/图档）详情页标题：无 part_number，用 name + 版本
export function nodeDisplayName(node) {
  const p = node.properties || {}
  const name = p.name || '未命名'
  const version = p.version || p.doc_version || ''
  return version ? `${name} (${version})` : name
}

// 节点 → 树节点/标题 label（如「部件 - P20240914001, 智能集成辅助控制器, C.1」）
export function nodeLabel(node) {
  const p = node.properties || {}
  const typeLabel = OBJECT_TYPE_LABELS[node.object_type] || node.object_type || '对象'
  const code = p[PART_FIELDS.code] || ''
  const name = p.name || ''
  const version = p.version || p.doc_version || ''
  const parts = [code || name || '未命名']
  if (code && name) parts.push(name)
  if (version) parts.push(version)
  return `${typeLabel} - ${parts.join(', ')}`
}
