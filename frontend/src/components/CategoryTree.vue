<template>
  <div class="category-tree">
    <div class="tree-header">
      <el-input v-model="filterText" placeholder="查询" :prefix-icon="Search" clearable />
      <el-button type="primary" size="small" :icon="Plus" @click="addRoot">新建分类</el-button>
    </div>

    <el-tree
      ref="treeRef"
      v-loading="loading"
      :data="treeData"
      node-key="id"
      :props="{ children: 'children', label: 'label' }"
      default-expand-all
      highlight-current
      :filter-node-method="filterNode"
      class="tree-body"
      @node-click="onNodeClick"
    >
      <template #default="{ data }">
        <span class="tree-node">
          <span class="node-label">{{ data.label }}</span>
          <!-- 节点旁操作按钮：默认缩略隐藏，hover 时展开 -->
          <span class="node-actions">
            <el-icon title="新建子分类" @click.stop="addChild(data)"><Plus /></el-icon>
            <el-icon title="重命名" @click.stop="rename(data)"><Edit /></el-icon>
            <el-icon title="删除" @click.stop="remove(data)"><Delete /></el-icon>
          </span>
        </span>
      </template>
    </el-tree>

    <el-empty v-if="!loading && !treeData.length" description="暂无分类，点击「新建分类」创建" :image-size="50" />
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, Edit, Delete } from '@element-plus/icons-vue'
import { listNodes, createNode, updateNode, deleteNode } from '../api/nodes'
import { listRelations, createRelation } from '../api/relations'

// 通用「树节点增删改查」组件：通过 props 指向任意的后端对象类型 + 父子关系类型，即可复用为
// 分类树 / BOM 树 / 文档层级等任意树结构。
//
// 后端类型前提：objectType / relationType 必须是后端已注册的类型。
//   - 节点类型（backend nodes.py NODE_TYPE_MAPPER）：part / document / drawing / attachment
//   - 关系类型（backend relations.py RELATION_TYPE_MAPPER）：bom / part_doc_relation / part_drawing_relation 等
// 默认值 category / category_relation 目前后端尚未注册，留作未来补 category 类型后的目标；
// 现在即可复用为 BOM 树：<CategoryTree object-type="part" relation-type="bom" />。
const props = defineProps({
  /** 后端节点对象类型（对应 GET/POST /nodes/{objectType}） */
  objectType: { type: String, default: 'category' },
  /** 后端父子关系类型（对应 GET/POST /relations/{relationType}，source=父 → target=子） */
  relationType: { type: String, default: 'category_relation' },
  /** 节点 properties 中用作展示名称的键 */
  labelKey: { type: String, default: 'name' }
})

/** 点击树节点时抛出该节点（{ id, label, children }） */
const emit = defineEmits(['select'])

const treeRef = ref()
const treeData = ref([])
const loading = ref(false)
const filterText = ref('')

// 平铺节点 + 边 → 嵌套树（根 = 无入边的节点）
const buildTree = (nodes, edges) => {
  const nodeMap = new Map(nodes.map((n) => [n.id, n]))
  const childrenMap = new Map()
  const childIds = new Set()
  for (const e of edges) {
    // 跳过自环边，避免节点成为自己的子节点导致死循环
    if (!e.source_id || !e.target_id || e.source_id === e.target_id) continue
    if (!childrenMap.has(e.source_id)) childrenMap.set(e.source_id, [])
    childrenMap.get(e.source_id).push(e.target_id)
    childIds.add(e.target_id)
  }

  const labelOf = (n) => (n.properties && n.properties[props.labelKey]) || '未命名'
  // seen 防止关系数据存在环时无限递归（通用组件可能被指向任意关系类型）
  const build = (id, seen = new Set()) => {
    if (seen.has(id)) return null
    seen.add(id)
    const n = nodeMap.get(id)
    if (!n) return null
    return {
      id: n.id,
      label: labelOf(n),
      children: (childrenMap.get(id) || []).map((cid) => build(cid, seen)).filter(Boolean)
    }
  }

  return nodes.filter((n) => !childIds.has(n.id)).map((n) => build(n.id)).filter(Boolean)
}

const load = async () => {
  loading.value = true
  try {
    const nodes = (await listNodes(props.objectType, { limit: 1000 })) || []
    const edges = (await listRelations(props.relationType)) || []
    treeData.value = buildTree(nodes, edges)
    await nextTick()
    if (filterText.value) treeRef.value?.filter(filterText.value)
  } catch (e) {
    ElMessage.error(e.message || '加载分类树失败')
    treeData.value = []
  } finally {
    loading.value = false
  }
}

const promptName = async (title, placeholder, inputValue = '') => {
  try {
    const { value } = await ElMessageBox.prompt(placeholder, title, {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputValue
    })
    return value ? value.trim() : ''
  } catch {
    return '' // 用户取消
  }
}

const addRoot = async () => {
  const name = await promptName('新建分类', '请输入分类名称')
  if (!name) return
  try {
    await createNode(props.objectType, { [props.labelKey]: name })
    ElMessage.success('创建成功')
    await load()
  } catch (e) {
    ElMessage.error(e.message || '创建失败')
  }
}

const addChild = async (data) => {
  const name = await promptName('新建子分类', '请输入子分类名称')
  if (!name) return
  try {
    const child = await createNode(props.objectType, { [props.labelKey]: name })
    await createRelation(props.relationType, data.id, child.id, {})
    ElMessage.success('创建成功')
    await load()
  } catch (e) {
    ElMessage.error(e.message || '创建失败')
  }
}

const rename = async (data) => {
  const name = await promptName('重命名', '请输入新的分类名称', data.label)
  if (!name || name === data.label) return
  try {
    await updateNode(props.objectType, data.id, { [props.labelKey]: name })
    ElMessage.success('已更新')
    await load()
  } catch (e) {
    ElMessage.error(e.message || '更新失败')
  }
}

const remove = async (data) => {
  const hasChildren = !!(data.children && data.children.length)
  const msg = hasChildren
    ? '该分类包含子分类，删除后子分类将变为顶级分类，确认删除？'
    : '确认删除该分类？'
  try {
    await ElMessageBox.confirm(msg, '删除分类', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return // 用户取消
  }
  try {
    await deleteNode(props.objectType, data.id)
    ElMessage.success('已删除')
    await load()
  } catch (e) {
    ElMessage.error(e.message || '删除失败')
  }
}

const onNodeClick = (data) => {
  emit('select', data)
}

const filterNode = (value, data) => {
  if (!value) return true
  return String(data.label || '').toLowerCase().includes(String(value).toLowerCase())
}

watch(filterText, (val) => {
  treeRef.value?.filter(val)
})

onMounted(load)

// 暴露刷新方法与只读数据，供父组件程序化重载 / 读取（多处复用的关键钩子）
defineExpose({ load, treeData })
</script>

<style scoped>
.category-tree {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.tree-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
}

.tree-header .el-input {
  flex: 1;
}

.tree-body {
  flex: 1;
  overflow-y: auto;
}

.tree-node {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex: 1;
  padding-right: 4px;
  font-size: 13px;
}

.node-actions {
  display: none;
  align-items: center;
  gap: 2px;
}

.tree-node:hover .node-actions {
  display: inline-flex;
}

.node-actions .el-icon {
  padding: 2px;
  border-radius: 3px;
  color: #606266;
}

.node-actions .el-icon:hover {
  background: #e6e8eb;
  color: #2563eb;
}
</style>
