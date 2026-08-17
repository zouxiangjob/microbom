<template>
  <DetailLayout :title="title" :active-tab="cfg.activeTab">
    <div v-loading="loading">
      <!-- 顶部操作工具栏 -->
      <div class="table-toolbar">
        <div class="left-placeholder"></div>
        <div class="right-actions">
          <el-button-group>
            <el-button type="primary" :icon="Plus" plain @click="addRow('new')">创建</el-button>
            <el-button type="primary" :icon="Plus" plain @click="addRow('existing')">添加</el-button>
          </el-button-group>
          <el-button type="danger" :icon="Delete" plain @click="removeSelected">移除</el-button>
          <el-button :icon="Refresh" size="small" circle @click="loadData" />
        </div>
      </div>

      <!-- 数据表格 -->
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
        <el-table-column
          v-for="col in cfg.columns"
          :key="col.prop"
          :prop="col.prop"
          :label="col.label"
          :min-width="col.minWidth"
          :width="col.width"
        />
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="removeRow(row)">移除</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty :description="cfg.emptyText" :image-size="60" />
        </template>
      </el-table>
    </div>

    <!-- 添加已有对象对话框 -->
    <el-dialog v-model="addDialogVisible" :title="cfg.addDialogTitle" width="480px">
      <el-select v-model="selectedId" filterable :placeholder="cfg.addPlaceholder" style="width: 100%">
        <el-option v-for="d in candidates" :key="d.id" :label="nodeLabel(d)" :value="d.id" />
      </el-select>
      <template #footer>
        <el-button @click="addDialogVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!selectedId" @click="confirmAdd">确定</el-button>
      </template>
    </el-dialog>
  </DetailLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, Refresh } from '@element-plus/icons-vue'
import DetailLayout from './DetailLayout.vue'
import { getNode, listNodes, createNode, NODE_TYPES } from '../api/nodes'
import { getNodeTree, createRelation, deleteRelation, RELATION_TYPES, RELATION_DATA_TYPES } from '../api/relations'
import { nodeTitle, nodeLabel, drawingRow, docRow } from '../api/mapping'

// kind 决定本页是「图档」还是「技术文档」：由 router 以 props 传入
const props = defineProps({
  kind: { type: String, required: true } // 'drawing' | 'document'
})

const route = useRoute()
const nodeId = route.params.id

const KIND_CONFIG = {
  drawing: {
    activeTab: 'cad',
    fallbackTitle: '图档',
    nodeType: NODE_TYPES.DRAWING,
    urlRelation: RELATION_TYPES.DRAWING,
    dataRelation: RELATION_DATA_TYPES.DRAWING,
    rowMapper: drawingRow,
    emptyText: '暂无关联图档',
    createPromptTitle: '创建图档',
    createPromptMessage: '请输入新图档名称',
    createInputValue: '新图纸',
    createDefaults: (name) => ({ name, version: 'A.1', drawing_type: '2D工程图', format: '--' }),
    addDialogTitle: '添加已有图档',
    addPlaceholder: '搜索并选择图档',
    columns: [
      { prop: 'name', label: '名称', minWidth: 160 },
      { prop: 'relation', label: '关联类型', width: 120 },
      { prop: 'version', label: '版本', width: 80 },
      { prop: 'type', label: '类型', width: 120 },
      { prop: 'format', label: '格式', width: 100 }
    ]
  },
  document: {
    activeTab: 'docs',
    fallbackTitle: '技术文档',
    nodeType: NODE_TYPES.DOCUMENT,
    urlRelation: RELATION_TYPES.DOCUMENT,
    dataRelation: RELATION_DATA_TYPES.DOCUMENT,
    rowMapper: docRow,
    emptyText: '暂无关联文档',
    createPromptTitle: '创建文档',
    createPromptMessage: '请输入新文档名称',
    createInputValue: '新文档',
    createDefaults: (name) => ({ name, doc_version: 'A.0', tag: '技术文档' }),
    addDialogTitle: '添加已有文档',
    addPlaceholder: '搜索并选择文档',
    columns: [
      { prop: 'name', label: '名称', minWidth: 180 },
      { prop: 'type', label: '指派类型', width: 150 },
      { prop: 'version', label: '修订版本', width: 120 },
      { prop: 'quantity', label: '数量', width: 100 },
      { prop: 'unit', label: '单位', width: 100 }
    ]
  }
}

const cfg = computed(() => KIND_CONFIG[props.kind] || KIND_CONFIG.drawing)

const tableData = ref([])
const selectedRows = ref([])
const loading = ref(false)
const title = ref('加载中...')

// 请求竞态守卫：快速刷新/增删时，只让最后一次请求的结果落盘
let loadSeq = 0

const loadData = async () => {
  const seq = ++loadSeq
  loading.value = true
  try {
    // 复用依赖树穿透接口，一次性带出目标节点快照，避免逐边 N+1 查询
    const flat = (await getNodeTree(nodeId)) || []
    if (seq !== loadSeq) return
    const mapper = cfg.value.rowMapper
    tableData.value = flat
      .filter((i) => i.edge?.relation_type === cfg.value.dataRelation && i.edge?.source_id === nodeId)
      .map((i) => (i.target_node ? mapper(i.target_node, i.edge) : null))
      .filter(Boolean)
  } catch (e) {
    if (seq !== loadSeq) return
    ElMessage.error(e.message || '加载失败')
    tableData.value = []
  } finally {
    if (seq === loadSeq) loading.value = false
  }

  try {
    const root = await getNode(NODE_TYPES.PART, nodeId)
    if (seq === loadSeq) title.value = nodeTitle(root)
  } catch {
    if (seq === loadSeq) title.value = cfg.value.fallbackTitle
  }
}

// 创建 / 添加对象，落到后端
const addDialogVisible = ref(false)
const candidates = ref([])
const selectedId = ref(null)

const addRow = async (mode) => {
  if (mode === 'new') {
    let name
    try {
      const { value } = await ElMessageBox.prompt(cfg.value.createPromptMessage, cfg.value.createPromptTitle, {
        confirmButtonText: '创建',
        cancelButtonText: '取消',
        inputValue: cfg.value.createInputValue
      })
      name = value
    } catch {
      return // 用户取消
    }
    if (!name || !name.trim()) {
      ElMessage.warning('名称不能为空')
      return
    }
    try {
      const obj = await createNode(cfg.value.nodeType, cfg.value.createDefaults(name.trim()))
      await createRelation(cfg.value.urlRelation, nodeId, obj.id, {})
      ElMessage.success('创建成功')
      await loadData()
    } catch (e) {
      ElMessage.error(e.message || '创建失败')
    }
  } else {
    selectedId.value = null
    addDialogVisible.value = true
    if (!candidates.value.length) {
      try {
        candidates.value = await listNodes(cfg.value.nodeType, { limit: 1000 })
      } catch (e) {
        ElMessage.error(e.message || '加载列表失败')
      }
    }
  }
}

const confirmAdd = async () => {
  if (!selectedId.value) return
  try {
    await createRelation(cfg.value.urlRelation, nodeId, selectedId.value, {})
    ElMessage.success('添加成功')
    addDialogVisible.value = false
    await loadData()
  } catch (e) {
    ElMessage.error(e.message || '添加失败')
  }
}

const handleSelectionChange = (rows) => {
  selectedRows.value = rows
}

const removeSelected = async () => {
  if (!selectedRows.value.length) {
    ElMessage.warning('请先选择要移除的对象')
    return
  }
  try {
    await Promise.all(
      selectedRows.value.map((r) => deleteRelation(cfg.value.urlRelation, r.edgeId))
    )
    ElMessage.success('移除成功')
    await loadData()
  } catch (e) {
    ElMessage.error(e.message || '移除失败')
  }
}

const removeRow = async (row) => {
  try {
    await deleteRelation(cfg.value.urlRelation, row.edgeId)
    ElMessage.success('移除成功')
    await loadData()
  } catch (e) {
    ElMessage.error(e.message || '移除失败')
  }
}

onMounted(loadData)
</script>

<style scoped>
.table-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.right-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

:deep(.el-table .cell) {
  white-space: nowrap;
}
</style>
