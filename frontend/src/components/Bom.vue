<template>
  <DetailLayout :title="title" active-tab="bom">
    <div v-loading="loading" class="tab-content">
      <el-row :gutter="20" class="full-height">
        <!-- 左侧：BOM 树形结构 -->
        <el-col :span="8" class="tree-section">
          <div class="toolbar">
            <el-input v-model="treeSearch" placeholder="请输入编码、名称或规格" class="search-input">
              <template #append>
                <el-button :icon="Search" />
              </template>
            </el-input>
            <div class="tree-actions">
              <el-select v-model="level" placeholder="层级" size="small" style="width: 80px">
                <el-option label="所有" value="all" />
                <el-option label="1级" value="1" />
                <el-option label="2级" value="2" />
                <el-option label="3级" value="3" />
              </el-select>
              <el-button size="small" @click="handleExpandAll">展开所有</el-button>
              <el-button :icon="Refresh" size="small" circle @click="loadData" />
            </div>
          </div>

          <div class="tree-wrapper">
            <el-tree
              :key="treeKey"
              ref="treeRef"
              :data="bomTreeData"
              :props="defaultProps"
              node-key="id"
              :default-expanded-keys="expandedKeys"
              highlight-current
              :filter-node-method="filterNode"
              @node-click="onNodeClick"
            >
              <template #default="{ node, data }">
                <span class="custom-tree-node">
                  <el-icon v-if="data.children && data.children.length" class="folder-icon"><Setting /></el-icon>
                  <el-icon v-else class="file-icon"><Memo /></el-icon>
                  <span class="node-text">{{ node.label }}</span>
                </span>
              </template>
            </el-tree>
          </div>
        </el-col>

        <!-- 右侧：BOM 详情列表 -->
        <el-col :span="16" class="table-section">
          <div class="detail-header">
            <div class="part-info">
              <el-icon><Setting /></el-icon>
              <span class="part-title">{{ currentLabel }}</span>
            </div>

            <el-tabs v-model="subTab" class="inner-tabs">
              <el-tab-pane label="属性" name="attr" />
              <el-tab-pane label="BOM" name="bom" />
              <el-tab-pane label="技术文档" name="docs" />
              <el-tab-pane label="图档" name="drawing" />
            </el-tabs>
          </div>

          <!-- 属性 -->
          <div v-show="subTab === 'attr'" class="sub-panel">
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="名称">{{ curP.name || '--' }}</el-descriptions-item>
              <el-descriptions-item label="编码">{{ curP.part_number || '--' }}</el-descriptions-item>
              <el-descriptions-item label="版本">{{ curP.version || '--' }}</el-descriptions-item>
              <el-descriptions-item label="数据状态">
                <el-tag :type="statusTagType(curP.status)" size="small">{{ curP.status || '--' }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="类别">{{ curP.category || '--' }}</el-descriptions-item>
              <el-descriptions-item label="材料">{{ curP.material || '--' }}</el-descriptions-item>
              <el-descriptions-item label="重量">{{ curP.weight != null ? curP.weight + ' kg' : '--' }}</el-descriptions-item>
              <el-descriptions-item label="设计者">{{ curP.designer || '--' }}</el-descriptions-item>
            </el-descriptions>
          </div>

          <!-- BOM 子件表 -->
          <div v-show="subTab === 'bom'">
            <div class="table-toolbar">
              <div class="right-actions">
                <el-dropdown split-button type="primary" @click="openAddDialog" @command="openAddDialog">
                  插入
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="existing">现有部件</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
                <el-button type="danger" :icon="Delete" plain @click="removeSelected">移除</el-button>
                <el-button size="small" :icon="Refresh" circle @click="loadData" />
              </div>
            </div>

            <el-table
              :data="tableData"
              row-key="id"
              border
              stripe
              style="width: 100%"
              size="small"
              @selection-change="handleSelectionChange"
            >
              <el-table-column type="selection" width="40" />
              <el-table-column type="index" label=" " width="50" />
              <el-table-column prop="code" label="编码" min-width="120">
                <template #default="{ row }">
                  <el-link type="primary" :underline="false" @click="navigateToNode(row)">{{ row.code }}</el-link>
                </template>
              </el-table-column>
              <el-table-column prop="name" label="名称" />
              <el-table-column prop="spec" label="规格" min-width="180" />
              <el-table-column prop="version" label="版本" width="80" />
              <el-table-column prop="quantity" label="数量" width="130">
                <template #default="{ row }">
                  <el-input-number
                    v-model="row.quantity"
                    :min="0"
                    :precision="2"
                    :step="1"
                    size="small"
                    controls-position="right"
                    @change="(val) => onQuantityChange(row, val)"
                  />
                </template>
              </el-table-column>
              <el-table-column prop="unit" label="单位" width="60" />
            </el-table>
          </div>

          <!-- 技术文档 -->
          <div v-show="subTab === 'docs'" class="sub-panel">
            <div class="table-toolbar">
              <el-button type="primary" size="small" :icon="Plus" @click="openAddRel('docs')">添加</el-button>
            </div>
            <el-table :data="docData" row-key="id" border size="small" style="width: 100%">
              <el-table-column prop="name" label="名称" min-width="160" />
              <el-table-column prop="type" label="指派类型" width="140" />
              <el-table-column prop="version" label="修订版本" width="100" />
              <el-table-column label="操作" width="120" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" size="small" @click="openPreview(row)">预览</el-button>
                  <el-button link type="danger" size="small" @click="removeRel('docs', row)">移除</el-button>
                </template>
              </el-table-column>
              <template #empty>
                <el-empty description="暂无数据" :image-size="60" />
              </template>
            </el-table>
          </div>

          <!-- 图档 -->
          <div v-show="subTab === 'drawing'" class="sub-panel">
            <div class="table-toolbar">
              <el-button type="primary" size="small" :icon="Plus" @click="openAddRel('drawing')">添加</el-button>
            </div>
            <el-table :data="drawData" row-key="id" border size="small" style="width: 100%">
              <el-table-column prop="name" label="名称" min-width="160" />
              <el-table-column prop="relation" label="关联类型" width="110" />
              <el-table-column prop="version" label="版本" width="90" />
              <el-table-column prop="type" label="类型" width="110" />
              <el-table-column prop="format" label="格式" width="90" />
              <el-table-column label="操作" width="120" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" size="small" @click="openPreview(row)">预览</el-button>
                  <el-button link type="danger" size="small" @click="removeRel('drawing', row)">移除</el-button>
                </template>
              </el-table-column>
              <template #empty>
                <el-empty description="暂无数据" :image-size="60" />
              </template>
            </el-table>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- 插入现有部件对话框 -->
    <el-dialog v-model="addDialogVisible" title="插入现有部件" width="480px">
      <el-select v-model="selectedPartId" filterable placeholder="搜索并选择部件" style="width: 100%">
        <el-option v-for="p in candidateParts" :key="p.id" :label="nodeLabel(p)" :value="p.id" />
      </el-select>
      <template #footer>
        <el-button @click="addDialogVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!selectedPartId" @click="confirmAddPart">确定</el-button>
      </template>
    </el-dialog>

    <!-- 附件预览模态框（技术文档 / 图档共用） -->
    <el-dialog v-model="previewVisible" :title="previewName" width="80%" top="5vh" destroy-on-close>
      <iframe v-if="previewHasFile" :src="previewUrl" style="width:100%; height:70vh; border:none; border-radius:4px;" />
      <el-empty v-else description="该文件尚未上传物理文件" :image-size="60" />
    </el-dialog>

    <!-- 添加关联关系对话框（技术文档 / 图档通用） -->
    <el-dialog v-model="addRelVisible" :title="addRelTitle" width="480px">
      <el-select v-model="addRelSelectedId" filterable :placeholder="addRelPlaceholder" style="width: 100%">
        <el-option v-for="n in addRelCandidates" :key="n.id" :label="nodeLabel(n)" :value="n.id" />
      </el-select>
      <template #footer>
        <el-button @click="addRelVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!addRelSelectedId" @click="confirmAddRel">确定</el-button>
      </template>
    </el-dialog>
  </DetailLayout>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search, Refresh, Setting, Memo, Delete, Plus } from '@element-plus/icons-vue'
import DetailLayout from './DetailLayout.vue'
import { getNode, listNodes, NODE_TYPES } from '../api/nodes'
import { fileUrl, getFileMeta } from '../api/files'
import { getNodeTree, createRelation, deleteRelation, updateRelation, RELATION_TYPES, RELATION_DATA_TYPES } from '../api/relations'
import { nodeLabel, nodeTitle, statusTagType, bomRow } from '../api/mapping'
import { flatToTree } from '../utils/tree'

const route = useRoute()
const router = useRouter()
const nodeId = route.params.id

const treeSearch = ref('')
const level = ref('all')
const subTab = ref('bom')
const loading = ref(false)
const title = ref('加载中...')

const treeRef = ref()
const treeKey = ref(0)
const expandedKeys = ref([])

const defaultProps = {
  children: 'children',
  label: 'label',
}

// 数据源
const rootNode = ref(null)
const treeFlat = ref([]) // 全关系类型的平铺项 { depth, edge, target_node }（一次穿透复用）
const bomFlat = computed(() =>
  treeFlat.value.filter((i) => i.edge?.relation_type === RELATION_DATA_TYPES.BOM)
)
const nodeMap = ref(new Map()) // id -> node（根节点 + 所有子件）

// 当前选中的节点（点击树节点时更新）
const currentNodeId = ref(nodeId)
const currentNode = computed(() => nodeMap.value.get(currentNodeId.value) || null)
const curP = computed(() => currentNode.value?.properties || {})
const currentLabel = computed(() => (currentNode.value ? nodeLabel(currentNode.value) : ''))

// sourceId -> [{ edge, node }]，用于构建树与右侧表格
const childrenMap = computed(() => {
  const m = new Map()
  for (const item of bomFlat.value) {
    const sid = item.edge?.source_id
    const node = item.target_node
    if (!sid || !node) continue
    if (!m.has(sid)) m.set(sid, [])
    m.get(sid).push({ edge: item.edge, node })
  }
  return m
})

const bomTreeData = ref([])
const tableData = ref([])
const docData = ref([])
const drawData = ref([])
const selectedRows = ref([])

const levelToMaxDepth = () => (level.value === 'all' ? Infinity : Number(level.value))

// 全量 BOM 嵌套树（节点附带 edge/node），展示深度由 level 在 rebuildTree 中裁剪
const fullBomTree = computed(() => flatToTree(bomFlat.value, nodeId, nodeLabel))

const limitTreeDepth = (nodes, maxDepth) =>
  (nodes || []).map((n) => ({
    ...n,
    children: maxDepth > 1 ? limitTreeDepth(n.children || [], maxDepth - 1) : []
  }))

const rebuildTree = () => {
  bomTreeData.value = [
    {
      id: nodeId,
      label: rootNode.value ? nodeLabel(rootNode.value) : '当前节点',
      children: limitTreeDepth(fullBomTree.value, levelToMaxDepth())
    }
  ]
}

const collectKeys = (nodes, keys) => {
  for (const n of nodes) {
    keys.push(n.id)
    if (n.children && n.children.length) collectKeys(n.children, keys)
  }
}

const applyTreeFilter = () => {
  if (treeRef.value) treeRef.value.filter(treeSearch.value)
}

const setAllExpanded = () => {
  const keys = []
  collectKeys(bomTreeData.value, keys)
  expandedKeys.value = keys
  treeKey.value += 1
  nextTick(applyTreeFilter)
}

// 更新右侧表格为指定节点的直属子件
const updateTable = (id) => {
  const items = childrenMap.value.get(id) || []
  tableData.value = items.map(({ node, edge }) => bomRow(node, edge))
}

// 数量列编辑：更新关系边上的 quantity，并同步本地 treeFlat 缓存，避免切换节点后回退
const updateEdgeProperty = (edgeId, key, value) => {
  for (const item of treeFlat.value) {
    if (item.edge && item.edge.id === edgeId) {
      item.edge.properties = { ...(item.edge.properties || {}), [key]: value }
      return
    }
  }
}

const onQuantityChange = async (row, val) => {
  if (val == null) return
  try {
    await updateRelation(RELATION_TYPES.BOM, row.edgeId, { quantity: val })
    updateEdgeProperty(row.edgeId, 'quantity', val)
    ElMessage.success('数量已更新')
  } catch (e) {
    ElMessage.error(e.message || '更新数量失败')
    // 回滚：重新拉取，恢复为后端真实值
    await loadData()
  }
}

const onNodeClick = (data) => {
  currentNodeId.value = data.id
  updateTable(data.id)
  refreshSubIfNeeded()
}

const filterNode = (value, data) => {
  if (!value) return true
  return String(data.label || '').toLowerCase().includes(String(value).toLowerCase())
}

const refreshSubIfNeeded = () => {
  if (subTab.value === 'docs') loadDocs()
  else if (subTab.value === 'drawing') loadDrawings()
}

// 技术文档 / 图档直接复用 loadData 已拉取的 treeFlat（一次穿透），避免逐边 N+1 查询
const loadDocs = () => {
  const id = currentNodeId.value
  docData.value = treeFlat.value
    .filter((i) => i.edge?.relation_type === RELATION_DATA_TYPES.DOCUMENT && i.edge?.source_id === id)
    .map((i) => {
      const d = i.target_node
      if (!d) return null
      const p = d.properties || {}
      return { id: d.id, edgeId: i.edge.id, name: p.name || '--', type: p.tag || '--', version: p.doc_version || '--' }
    })
    .filter(Boolean)
}

const loadDrawings = () => {
  const id = currentNodeId.value
  drawData.value = treeFlat.value
    .filter((i) => i.edge?.relation_type === RELATION_DATA_TYPES.DRAWING && i.edge?.source_id === id)
    .map((i) => {
      const d = i.target_node
      if (!d) return null
      const p = d.properties || {}
      const ep = i.edge?.properties || {}
      return {
        id: d.id,
        edgeId: i.edge.id,
        name: p.name || '--',
        relation: ep.is_primary ? '主关联' : '被动关联',
        version: p.version || '--',
        type: p.drawing_type || '--',
        format: p.format || '--'
      }
    })
    .filter(Boolean)
}

// ── 技术文档 / 图档：预览 + 添加关联 + 移除 ──
const REL_CONFIG = {
  docs: {
    nodeType: NODE_TYPES.DOCUMENT,
    relationType: RELATION_TYPES.DOCUMENT,
    title: '添加技术文档',
    placeholder: '搜索并选择文档'
  },
  drawing: {
    nodeType: NODE_TYPES.DRAWING,
    relationType: RELATION_TYPES.DRAWING,
    title: '添加图档',
    placeholder: '搜索并选择图档'
  }
}

const previewVisible = ref(false)
const previewUrl = ref('')
const previewName = ref('')
const previewHasFile = ref(false)

const addRelVisible = ref(false)
const addRelKind = ref('docs')
const addRelCandidates = ref([])
const addRelSelectedId = ref(null)
const relCandidatesCache = { docs: [], drawing: [] }

const addRelTitle = computed(() => REL_CONFIG[addRelKind.value]?.title || '')
const addRelPlaceholder = computed(() => REL_CONFIG[addRelKind.value]?.placeholder || '')

// 预览：弹出模态框，内嵌附件预览页（文档/图档共用）
const openPreview = async (row) => {
  if (!row?.id) return
  previewName.value = row.name || '文件预览'
  previewVisible.value = true
  try {
    await getFileMeta(row.id)
    previewHasFile.value = true
    previewUrl.value = fileUrl(row.id, true)
  } catch {
    previewHasFile.value = false // 无物理文件 → 显示空态而非 iframe 404
  }
}

// 添加关联：弹窗选择已有文档/图档，建立「部件 → 文档/图档」关系
const openAddRel = async (kind) => {
  addRelKind.value = kind
  addRelSelectedId.value = null
  addRelVisible.value = true
  if (!relCandidatesCache[kind].length) {
    try {
      relCandidatesCache[kind] = await listNodes(REL_CONFIG[kind].nodeType, { limit: 1000 })
    } catch (e) {
      ElMessage.error(e.message || '加载列表失败')
    }
  }
  addRelCandidates.value = relCandidatesCache[kind]
}

const confirmAddRel = async () => {
  if (!addRelSelectedId.value) return
  const cfg = REL_CONFIG[addRelKind.value]
  const selectedNode = addRelCandidates.value.find((n) => n.id === addRelSelectedId.value)
  try {
    const edge = await createRelation(cfg.relationType, currentNodeId.value, addRelSelectedId.value, {})
    // 同步本地 treeFlat 缓存，避免重新穿透即可在列表里看到新关联
    if (selectedNode) treeFlat.value.push({ depth: 1, edge, target_node: selectedNode })
    ElMessage.success('添加成功')
    addRelVisible.value = false
    refreshSubIfNeeded()
  } catch (e) {
    ElMessage.error(e.message || '添加失败')
  }
}

// 移除关联：删除「部件 → 文档/图档」关系边
const removeRel = async (kind, row) => {
  const cfg = REL_CONFIG[kind]
  if (!row?.edgeId) return
  try {
    await deleteRelation(cfg.relationType, row.edgeId)
    treeFlat.value = treeFlat.value.filter((i) => !(i.edge && i.edge.id === row.edgeId))
    ElMessage.success('移除成功')
    refreshSubIfNeeded()
  } catch (e) {
    ElMessage.error(e.message || '移除失败')
  }
}

// 请求竞态守卫：快速刷新/增删时，只让最后一次请求的结果落盘
let loadSeq = 0

const loadData = async () => {
  const seq = ++loadSeq
  loading.value = true
  try {
    // 根节点（当前部件详情节点）
    try {
      rootNode.value = await getNode(NODE_TYPES.PART, nodeId)
      title.value = nodeTitle(rootNode.value)
    } catch {
      title.value = 'BOM'
    }

    // tree 接口一次穿透返回全关系类型的依赖树：BOM 页只保留 BOM 关系（bomFlat 为 computed），
    // 技术文档/图档也复用同一份 treeFlat，避免逐边 N+1 查询
    treeFlat.value = (await getNodeTree(nodeId)) || []
    if (seq !== loadSeq) return

    // 构建节点索引（根节点 + 所有子件，含文档/图档）
    const map = new Map()
    if (rootNode.value) map.set(nodeId, rootNode.value)
    for (const item of treeFlat.value) {
      if (item.target_node) map.set(item.target_node.id, item.target_node)
    }
    nodeMap.value = map

    currentNodeId.value = nodeId
    rebuildTree()
    setAllExpanded()
    updateTable(nodeId)
  } catch (e) {
    if (seq !== loadSeq) return
    ElMessage.error(e.message || '加载 BOM 失败')
    title.value = 'BOM'
  } finally {
    if (seq === loadSeq) loading.value = false
  }
}

// 点击右侧表格部件 → 跳转到该节点详情页
const navigateToNode = (row) => {
  if (!row?.id) return
  router.push(`/attribute/${row.id}`)
}

// 插入现有部件：弹窗选择已有部件后建立 BOM 关系
const addDialogVisible = ref(false)
const candidateParts = ref([])
const selectedPartId = ref(null)

const openAddDialog = async () => {
  selectedPartId.value = null
  addDialogVisible.value = true
  if (!candidateParts.value.length) {
    try {
      candidateParts.value = await listNodes(NODE_TYPES.PART, { limit: 1000 })
    } catch (e) {
      ElMessage.error(e.message || '加载部件列表失败')
    }
  }
}

const confirmAddPart = async () => {
  if (!selectedPartId.value) return
  try {
    // 插入到当前选中的节点（currentNodeId），而非固定根节点——否则在子总成上点插入会挂到顶层
    await createRelation(RELATION_TYPES.BOM, currentNodeId.value, selectedPartId.value, { quantity: 1, unit: 'pcs' })
    ElMessage.success('已插入现有部件')
    addDialogVisible.value = false
    await loadData()
  } catch (e) {
    ElMessage.error(e.message || '插入失败')
  }
}

const handleSelectionChange = (rows) => {
  selectedRows.value = rows
}

const removeSelected = async () => {
  if (!selectedRows.value.length) {
    ElMessage.warning('请先选择要移除的部件')
    return
  }
  try {
    await Promise.all(
      selectedRows.value.map((r) => deleteRelation(RELATION_TYPES.BOM, r.edgeId))
    )
    ElMessage.success('移除成功')
    await loadData()
  } catch (e) {
    ElMessage.error(e.message || '移除失败')
  }
}

watch(treeSearch, (val) => {
  nextTick(() => {
    if (treeRef.value) treeRef.value.filter(val)
  })
})

watch(level, () => {
  rebuildTree()
  setAllExpanded()
})

watch(subTab, (val) => {
  if (val === 'docs') loadDocs()
  else if (val === 'drawing') loadDrawings()
})

onMounted(loadData)
</script>

<style scoped>
.tab-content {
  padding: 10px 0;
  min-height: 400px;
}

.full-height {
  height: 100%;
}

/* 左侧树形区域样式 */
.tree-section {
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
}

.toolbar {
  margin-bottom: 10px;
}

.tree-actions {
  margin-top: 8px;
  display: flex;
  gap: 5px;
  align-items: center;
}

.tree-wrapper {
  flex: 1;
  overflow-y: auto;
}

.custom-tree-node {
  display: flex;
  align-items: center;
  font-size: 13px;
}

.folder-icon { color: #e6a23c; margin-right: 5px; }
.file-icon { color: #909399; margin-right: 5px; }

/* 右侧表格区域样式 */
.detail-header {
  border-bottom: 1px solid #f0f2f5;
  margin-bottom: 10px;
}

.part-info {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.part-title {
  font-weight: bold;
  font-size: 14px;
}

.inner-tabs :deep(.el-tabs__header) {
  margin: 0;
}

.sub-panel {
  padding: 10px 0;
}

.table-toolbar {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  margin-bottom: 10px;
  padding: 5px 0;
}

.right-actions {
  display: flex;
  gap: 8px;
}

:deep(.el-table .cell) {
  white-space: nowrap;
}
</style>
