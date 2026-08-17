export const DETAIL_TABS = [
  { label: '基本属性', name: 'basic', path: '/attribute' },
  { label: 'BOM', name: 'bom', path: '/bom' },
  { label: '图档', name: 'cad', path: '/cad' },
  { label: '技术文档', name: 'docs', path: '/doc' },
  { label: '版本历史', name: 'history', path: '/ehistory' },
  { label: '被引用', name: 'referenced', path: '/fget' },
]

// 技术文档 / 图档等「非零部件」对象详情页签（path 为相对后缀，配合 pathPrefix=/object/{objectType}）
export const OBJECT_DETAIL_TABS = [
  { label: '基本属性', name: 'basic', path: '/attribute' },
  { label: '零部件', name: 'parts', path: '/parts' },
  { label: '版本历史', name: 'history', path: '/history' },
  { label: '被引用', name: 'referenced', path: '/referenced' },
]
