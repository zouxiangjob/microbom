// 后端 CTE 穿透接口返回「平铺数组」，而 el-tree 需要「嵌套树」。
// 本模块把平铺的「边 + 节点」列表按父子关系还原成嵌套结构。

function defaultLabel(node) {
  return node?.properties?.name || node?.id || '未命名'
}

// 通用：按 parentKey 分组，从 rootId 递归构建嵌套树。
// 返回节点结构：{ id, label, node, edge, children }，其中 node/edge 为原始引用，
// 供消费者直接读取边上的 quantity/unit/relation_type 或节点 properties，避免二次推导。
function build(flat, rootId, parentKey, nodeKey, getLabel) {
  const itemsByParent = new Map()
  for (const item of flat || []) {
    const parentId = item.edge?.[parentKey]
    const node = item[nodeKey]
    if (!parentId || !node) continue
    if (!itemsByParent.has(parentId)) itemsByParent.set(parentId, [])
    itemsByParent.get(parentId).push({ edge: item.edge, node })
  }

  const walk = (id) => {
    const items = itemsByParent.get(id) || []
    return items.map(({ edge, node }) => ({
      id: node.id,
      label: getLabel(node),
      node,
      edge,
      children: walk(node.id)
    }))
  }
  return walk(rootId)
}

// 正向 BOM 树：元素为 { edge: { source_id, target_id }, target_node }
// 子节点 = target_node，父节点 = edge.source_id
export function flatToTree(flat, rootId, getLabel = defaultLabel) {
  return build(flat, rootId, 'source_id', 'target_node', getLabel)
}

// 逆向 Where-Used 树：元素为 { edge: { source_id, target_id }, source_node }
// 子节点 = source_node（上游父件），父节点 = edge.target_id
export function flatToReverseTree(flat, leafId, getLabel = defaultLabel) {
  return build(flat, leafId, 'target_id', 'source_node', getLabel)
}
