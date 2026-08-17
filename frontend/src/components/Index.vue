<template>
  <div class="common-layout">
    <el-container class="layout-container">
      <el-header class="header">
        <div class="logo">BOM 管理系统</div>
      </el-header>

      <el-container class="body-container">
        <el-aside width="150px" class="main-aside">
          <el-menu :default-active="activeMenu" class="side-menu" background-color="#1f2937" text-color="#fff" @select="handleMenuSelect">
            <el-menu-item index="1"><el-icon><HomeFilled /></el-icon><span>首页</span></el-menu-item>
            <el-sub-menu index="2">
              <template #title><el-icon><Management /></el-icon><span>产品管理</span></template>
              <el-menu-item index="2-1">零部件</el-menu-item>
              <el-menu-item index="2-2">技术文档</el-menu-item>
              <el-menu-item index="2-3">图档</el-menu-item>
            </el-sub-menu>
          </el-menu>
        </el-aside>

        <el-aside v-if="showTree" width="260px" class="tree-aside">
          <div class="tree-header">
            <span class="tree-title">分类</span>
            <el-button size="small" @click="clearCategory">全部零部件</el-button>
          </div>
          <CategoryTree @select="onCategorySelect" @change="onCategoryChange" />
        </el-aside>

        <el-main class="main-content">
          <template v-if="showList">
          <div class="toolbar">
            <el-button type="primary" :icon="Plus" @click="handleCreate">创建</el-button>
          </div>

          <div class="search-form">
            <el-input v-model="searchForm.code" class="search-input" @keyup.enter="handleSearch">
              <template #prepend>模糊搜索</template>
              <template #append>
                <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
              </template>
            </el-input>
          </div>

          <el-table v-loading="loading" :data="pagedData" border style="width: 100%" class="data-table">
            <el-table-column type="selection" width="40" />
            <el-table-column
              v-for="col in columns"
              :key="col.prop"
              :prop="col.prop"
              :label="col.label"
              :min-width="col.minWidth"
              :width="col.width"
              :sortable="col.sortable"
            >
              <template #default="scope">
                <el-link v-if="col.kind === 'link'" type="primary" @click="navigateToDetail(scope.row)">
                  {{ scope.row[col.prop] }}
                </el-link>
                <el-tag v-else-if="col.kind === 'tag'" :type="scope.row.status === '已发布' ? 'success' : 'warning'">
                  {{ scope.row[col.prop] }}
                </el-tag>
                <span v-else>{{ scope.row[col.prop] }}</span>
              </template>
            </el-table-column>
          </el-table>

          <div class="pagination-container">
            <el-pagination
              v-model:current-page="currentPage"
              v-model:page-size="pageSize"
              layout="total, prev, pager, next, sizes"
              :total="tableData.length"
              :page-sizes="[10, 20, 50, 100]"
              class="mt-4"
            />
          </div>
          </template>
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search, Plus,
  HomeFilled, Management
} from '@element-plus/icons-vue'
import { listNodes, createNode, NODE_TYPES } from '../api/nodes'
import { listRelations, RELATION_TYPES } from '../api/relations'
import { nodeToRow, documentToRow, drawingToRow } from '../api/mapping'
import CategoryTree from './CategoryTree.vue'

const router = useRouter()

const searchForm = reactive({
  code: '',
})

const activeMenu = ref('1')

// 右侧列表：四种菜单都显示
const showList = computed(() => ['1', '2-1', '2-2', '2-3'].includes(activeMenu.value))
// 左侧分类树：仅零部件（材料分类对文档/图档无意义）
const showTree = computed(() => activeMenu.value === '1' || activeMenu.value === '2-1')

// 菜单 → 对象类型（复用 nodes.js 的 NODE_TYPES）
const MENU_TYPE = {
  '1': NODE_TYPES.PART,
  '2-1': NODE_TYPES.PART,
  '2-2': NODE_TYPES.DOCUMENT,
  '2-3': NODE_TYPES.DRAWING
}
const activeType = computed(() => MENU_TYPE[activeMenu.value] || NODE_TYPES.PART)
const ROW_MAPPERS = {
  [NODE_TYPES.PART]: nodeToRow,
  [NODE_TYPES.DOCUMENT]: documentToRow,
  [NODE_TYPES.DRAWING]: drawingToRow
}

// 各类型表格列配置（kind: link 链接跳转 / tag 状态着色 / 其余纯文本）
const COLUMN_CONFIGS = {
  [NODE_TYPES.PART]: [
    { prop: 'displayName', label: '显示名称', minWidth: 180, kind: 'link', sortable: true },
    { prop: 'name', label: '名称', minWidth: 120 },
    { prop: 'status', label: '数据状态', width: 100, kind: 'tag' },
    { prop: 'version', label: '修订版本', width: 100 },
    { prop: 'creator', label: '创建者', width: 120 }
  ],
  [NODE_TYPES.DOCUMENT]: [
    { prop: 'name', label: '名称', minWidth: 180, kind: 'link' },
    { prop: 'tag', label: '标签', minWidth: 120 },
    { prop: 'version', label: '修订版本', width: 120 }
  ],
  [NODE_TYPES.DRAWING]: [
    { prop: 'name', label: '名称', minWidth: 160, kind: 'link' },
    { prop: 'type', label: '类型', width: 120 },
    { prop: 'version', label: '版本', width: 100 },
    { prop: 'format', label: '格式', width: 100 }
  ]
}
const columns = computed(() => COLUMN_CONFIGS[activeType.value] || COLUMN_CONFIGS[NODE_TYPES.PART])

// ── 分类树 + 分类↔零部件关联 ──
const selectedCategoryId = ref(null)   // null = 全部零部件
const selectedCategoryName = ref('')
const categoryParts = ref([])          // 选中分类关联的零部件（含 edgeId）

// 表格数据：allRows 缓存后端全量，tableData 为过滤后，pagedData 为分页后
const allRows = ref([])
const tableData = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)

// 当前展示数据源：选中分类 → 该分类关联零部件；否则 → 全部零部件
const activeRows = computed(() =>
  selectedCategoryId.value ? categoryParts.value : allRows.value
)

const pagedData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return tableData.value.slice(start, start + pageSize.value)
})

const applyFilter = () => {
  const kw = (searchForm.code || '').trim().toLowerCase()
  tableData.value = activeRows.value.filter((r) => {
    return !kw || Object.values(r).some((v) => String(v).toLowerCase().includes(kw))
  })
  currentPage.value = 1
}

const handleSearch = () => {
  applyFilter()
}

// 请求竞态守卫：快速切换菜单时，只让最后一次请求的结果落盘
let loadSeq = 0

const loadData = async () => {
  const seq = ++loadSeq
  loading.value = true
  try {
    const nodes = await listNodes(activeType.value, { limit: 1000, offset: 0 })
    if (seq !== loadSeq) return // 已有更新的请求发出，丢弃本次结果
    allRows.value = (nodes || []).map((n) => ROW_MAPPERS[activeType.value](n))
    applyFilter()
  } catch (e) {
    if (seq !== loadSeq) return
    ElMessage.error(e.message || '加载列表失败')
  } finally {
    if (seq === loadSeq) loading.value = false
  }
}

const handleMenuSelect = (index) => {
  activeMenu.value = index
  searchForm.code = ''
  selectedCategoryId.value = null
  selectedCategoryName.value = ''
  categoryParts.value = []
  currentPage.value = 1
  loadData()
}

// 创建新资源：按当前类型调用后端 createNode，成功后刷新列表
const CREATE_PROPS = {
  [NODE_TYPES.PART]: {
    label: '零部件',
    defaults: (name) => ({
      part_number: `ME-${Date.now()}`,
      name,
      version: 'A.1',
      status: '草稿',
      designer: '当前用户'
    })
  },
  [NODE_TYPES.DOCUMENT]: {
    label: '文档',
    defaults: (name) => ({ name, doc_version: 'A.0', tag: '技术文档' })
  },
  [NODE_TYPES.DRAWING]: {
    label: '图档',
    defaults: (name) => ({ name, version: 'A.1', drawing_type: '2D工程图', format: '--' })
  }
}

const handleCreate = async () => {
  const cfg = CREATE_PROPS[activeType.value] || CREATE_PROPS[NODE_TYPES.PART]
  let name
  try {
    const { value } = await ElMessageBox.prompt(`请输入新${cfg.label}名称`, `创建${cfg.label}`, {
      confirmButtonText: '创建',
      cancelButtonText: '取消',
      inputValue: '新建部件'
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
    await createNode(activeType.value, cfg.defaults(name.trim()))
    ElMessage.success('创建成功')
    await loadData()
  } catch (e) {
    ElMessage.error(e.message || '创建失败')
  }
}

// 导航到详情页（row.id 即后端 objects.id），按当前对象类型跳转到对应详情页
const DETAIL_BASE = {
  [NODE_TYPES.PART]: '/attribute',
  [NODE_TYPES.DOCUMENT]: '/object/document/attribute',
  [NODE_TYPES.DRAWING]: '/object/drawing/attribute'
}

const navigateToDetail = (row) => {
  if (!row.id) {
    ElMessage.warning('该行缺少节点 ID，无法跳转')
    return
  }
  const base = DETAIL_BASE[activeType.value]
  if (!base) return
  router.push(`${base}/${row.id}`)
}

// ── 分类 ↔ 零部件关联管理 ──
const onCategorySelect = (data) => {
  selectedCategoryId.value = data?.id || null
  selectedCategoryName.value = data?.label || ''
  if (selectedCategoryId.value) loadCategoryParts(selectedCategoryId.value)
  else applyFilter()
}

const clearCategory = () => {
  selectedCategoryId.value = null
  selectedCategoryName.value = ''
  categoryParts.value = []
  applyFilter()
}

const loadCategoryParts = async (categoryId) => {
  try {
    const edges = (await listRelations(RELATION_TYPES.CATEGORY_PART, { sourceId: categoryId })) || []
    const edgeByTarget = new Map(edges.map((e) => [e.target_id, e.id]))
    categoryParts.value = allRows.value
      .filter((r) => edgeByTarget.has(r.id))
      .map((r) => ({ ...r, edgeId: edgeByTarget.get(r.id) }))
    applyFilter()
  } catch (e) {
    ElMessage.error(e.message || '加载分类零部件失败')
    categoryParts.value = []
  }
}

const onCategoryChange = (node) => {
  // 分类增删改或零部件关联变化后，若正好是当前选中的分类，则刷新右侧列表
  if (selectedCategoryId.value === node?.id) {
    loadCategoryParts(selectedCategoryId.value)
  }
}

onMounted(loadData)
</script>

<style scoped>
.common-layout {
  height: 100vh;
  width: 100vw;
  margin: 0;
  padding: 0;
  overflow: hidden;
}

.layout-container {
  height: 100%;
}

/* 中间行容器：约束高度，让右侧主内容区在自身范围内滚动 */
.body-container {
  min-height: 0;
  overflow: hidden;
}

.header {
  background-color: #1f2937;
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: white;
  padding: 0 20px;
}

.logo {
  font-size: 16px;
  font-weight: 600;
  width: 180px;
  letter-spacing: 0.5px;
}

.main-aside {
  background-color: #1f2937;
}

.side-menu {
  border-right: none;
}

.tree-aside {
  border-right: 1px solid #dcdfe6;
  padding: 10px;
  background-color: #fff;
}

.tree-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.tree-title {
  font-weight: 600;
  color: #303133;
}

.main-content {
  background-color: #f0f2f5;
  padding: 15px;
  overflow-y: auto;
  min-height: 0;
}

.toolbar {
  background: #fff;
  padding: 10px 15px;
  margin-bottom: 10px;
  display: flex;
  gap: 10px;
}

.search-form {
  background: #fff;
  padding: 15px;
  margin-bottom: 10px;
}

.search-input {
  width: 100%;
}

.data-table {
  margin-top: 10px;
}

.pagination-container {
  background: #fff;
  padding: 10px;
  display: flex;
  justify-content: flex-end;
}

</style>