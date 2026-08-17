import api from './index'

// 节点类型与后端 NODE_TYPE_MAPPER 对齐：part / document / drawing / attachment / category
export const NODE_TYPES = {
  PART: 'part',
  DOCUMENT: 'document',
  DRAWING: 'drawing',
  ATTACHMENT: 'attachment',
  CATEGORY: 'category'
}

// 分类分页列表：GET /nodes/{object_type}?limit=&offset=
export function listNodes(objectType, { limit = 100, offset = 0 } = {}) {
  return api.get(`/nodes/${objectType}`, { params: { limit, offset } })
}

// 精确读取：GET /nodes/{object_type}/{node_id}
export function getNode(objectType, nodeId) {
  return api.get(`/nodes/${objectType}/${nodeId}`)
}

// 创建：POST /nodes/{object_type}
export function createNode(objectType, properties = {}) {
  return api.post(`/nodes/${objectType}`, { properties })
}

// 增量更新属性：PUT /nodes/{object_type}/{node_id}
export function updateNode(objectType, nodeId, properties = {}) {
  return api.put(`/nodes/${objectType}/${nodeId}`, { properties })
}

// 级联删除：DELETE /nodes/{object_type}/{node_id}
export function deleteNode(objectType, nodeId) {
  return api.delete(`/nodes/${objectType}/${nodeId}`)
}
