import api from './index'

// 关系类型 URL 段：与后端 RELATION_TYPE_MAPPER 对齐，用于请求路径
// （createRelation / deleteRelation / listRelations 的 :relation_type 段）
export const RELATION_TYPES = {
  BOM: 'bom',                         // BOMRelation（零件 -> 零件）
  DRAWING: 'part_drawing_relation',   // PartDrawingRelation（零件 -> 图档）
  DOCUMENT: 'part_doc_relation',      // PartDocRelation（零件 -> 文档）
  CATEGORY: 'category_relation',      // CategoryRelationModel（分类 -> 分类）
  CATEGORY_PART: 'category_part_relation' // CategoryPartRelationModel（分类 -> 零部件）
}

// 关系类型数据名：与后端返回的 edge.relation_type 对齐，用于过滤与展示。
// 注意与 URL 段的差异——唯独 BOM 的 URL 段是 'bom'，数据名是 'bom_relation'。
export const RELATION_DATA_TYPES = {
  BOM: 'bom_relation',
  DRAWING: 'part_drawing_relation',
  DOCUMENT: 'part_doc_relation'
}

// 关系类型数据名 → 展示文案（被引用页 / 零部件反查等统一使用）
export const RELATION_LABELS = {
  bom_relation: 'BOM 装配关系',
  part_drawing_relation: '图档关联',
  part_doc_relation: '文档关联'
}

export function relationLabel(type) {
  return RELATION_LABELS[type] || type || '--'
}

// 正向 BOM/依赖树穿透：GET /relations/nodes/{node_id}/tree
// 返回平铺数组 [{ depth, edge, target_node }]，需配合 src/utils/tree.js 转嵌套
export function getNodeTree(nodeId, maxDepth = 10) {
  return api.get(`/relations/nodes/${nodeId}/tree`, { params: { max_depth: maxDepth } })
}

// 逆向 Where-Used 溯源：GET /relations/nodes/{node_id}/reverse-tree
// 返回平铺数组 [{ depth, edge, source_node }]，同样需转嵌套
export function getReverseTree(nodeId, maxDepth = 10) {
  return api.get(`/relations/nodes/${nodeId}/reverse-tree`, { params: { max_depth: maxDepth } })
}

// 检索关系列表：GET /relations/{relation_type}?source_id=&target_id=
export function listRelations(relationType, { sourceId, targetId } = {}) {
  return api.get(`/relations/${relationType}`, {
    params: { source_id: sourceId, target_id: targetId }
  })
}

// 建立关系：POST /relations/{relation_type}
export function createRelation(relationType, sourceId, targetId, properties = {}) {
  return api.post(`/relations/${relationType}`, {
    source_id: sourceId,
    target_id: targetId,
    properties
  })
}

// 删除关系：DELETE /relations/{relation_type}/{edge_id}
export function deleteRelation(relationType, edgeId) {
  return api.delete(`/relations/${relationType}/${edgeId}`)
}

// 修改关系属性（增量合并）：PUT /relations/{relation_type}/{edge_id}
export function updateRelation(relationType, edgeId, properties = {}) {
  return api.put(`/relations/${relationType}/${edgeId}`, { properties })
}
