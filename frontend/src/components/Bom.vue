<template>
  <div class="bom-container">
    <!-- 顶部标题栏 -->
    <div class="header-section">
      <h2 class="page-title">ME000000253/B.1;GSK磨床</h2>
    </div>

    <!-- 标签页 -->
    <el-tabs v-model="activeTab" class="custom-tabs">
      <el-tab-pane label="基本属性" name="basic" />
      <el-tab-pane label="BOM" name="bom">
        <div class="tab-content">
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
            </el-select>
            <el-button size="small">展开所有</el-button>
            <el-button :icon="Refresh" size="small" circle />
          </div>
        </div>

        <div class="tree-wrapper">
          <el-tree
            :data="bomTreeData"
            :props="defaultProps"
            node-key="id"
            default-expand-all
            highlight-current
          >
            <template #default="{ node, data }">
              <span class="custom-tree-node">
                <el-icon v-if="data.children" class="folder-icon"><Setting /></el-icon>
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
            <span class="part-title">部件 - P20240914001, 智能集成辅助控制器, C.1</span>
            <el-tag size="small" type="info" effect="plain">非精确</el-tag>
          </div>
          
          <el-tabs v-model="subTab" class="inner-tabs">
            <el-tab-pane label="属性" name="attr" />
            <el-tab-pane label="可视化" name="view" />
            <el-tab-pane label="BOM" name="bom" />
            <el-tab-pane label="未使用" name="unused" />
            <el-tab-pane label="BOM视图" name="bom-view" />
          </el-tabs>
        </div>

        <div class="table-toolbar">
          <div class="left-actions">
            <el-button type="primary" plain size="small">设计</el-button>
            <el-input v-model="tableSearch" placeholder="请输入编码、名称或规格" size="small" style="width: 200px; margin-left: 10px;">
              <template #append><el-button :icon="Search" /></template>
            </el-input>
          </div>
          <div class="right-actions">
            <el-dropdown split-button type="primary" size="small">
              插入
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item>现有部件</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-button size="small" :icon="Delete" plain>移除</el-button>
            <el-button size="small" :icon="Refresh" circle />
          </div>
        </div>

        <el-table :data="tableData" border stripe style="width: 100%" size="small">
          <el-table-column type="selection" width="40" />
          <el-table-column type="index" label=" " width="50" />
          <el-table-column prop="code" label="编码" min-width="120">
            <template #default="{ row }">
              <el-link type="primary" :underline="false">{{ row.code }}</el-link>
            </template>
          </el-table-column>
          <el-table-column prop="name" label="名称" />
          <el-table-column prop="spec" label="规格" min-width="180" />
          <el-table-column prop="version" label="版本" width="80" />
          <el-table-column prop="quantity" label="数量" width="80" />
          <el-table-column prop="unit" label="单位" width="60" />
        </el-table>
            </el-col>
          </el-row>
        </div>
      </el-tab-pane>
      <el-tab-pane label="CAD 模型" name="cad" />
      <el-tab-pane label="相关文档" name="docs" />
      <el-tab-pane label="版本历史" name="history" />
      <el-tab-pane label="被引用" name="referenced" />
      <el-tab-pane label="流程" name="workflow" />
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Refresh, Setting, Memo, Delete } from '@element-plus/icons-vue'

const router = useRouter()
const activeTab = ref('bom')

// 监听标签页切换，根据标签名称跳转到对应页面
watch(activeTab, (newVal) => {
  const routeMap = {
    'basic': '/attribute',
    'bom': '/bom',
    'cad': '/cad',
    'docs': '/doc',
    'history': '/ehistory',
    'referenced': '/fget',
    'workflow': '/gbmnp'
  }

  if (routeMap[newVal]) {
    router.push(routeMap[newVal])
  }
})

const treeSearch = ref('')
const tableSearch = ref('')
const level = ref('all')
const subTab = ref('bom')

const defaultProps = {
  children: 'children',
  label: 'label',
}

// 模拟左侧树数据
const bomTreeData = [
  {
    id: 1,
    label: '部件 - P20240914001, 智能集成辅助控制器, C.1',
    children: [
      {
        id: 2,
        label: '部件 - Y20240617002, 电气组件, A.2',
        children: [
          { id: 4, label: '部件 - A20240730407, 电阻, A.1' },
          { id: 5, label: '部件 - A20240730001, 电容, A.1' }
        ]
      },
      { id: 3, label: '部件 - Y20240618001, 机构组件, A.3' }
    ]
  }
]

// 模拟右侧表格数据
const tableData = ref([
  { code: 'Y20240617002', name: '电气组件', spec: 'HC-EB5424L-M055S-KL10-V-EP', version: 'A.2', quantity: '1.0', unit: 'pcs' },
  { code: 'Y20240618001', name: '机构组件', spec: 'HC-EB5424L-M055S-KL10-V-MP', version: 'A.3', quantity: '1.0', unit: 'pcs' },
  { code: 'Y20240618002', name: '线束组件', spec: 'HC-EB5424L-M055S-KL02-V-XS', version: 'A.2', quantity: '1.0', unit: 'pcs' },
  { code: 'Y20240618003', name: '辅料组件', spec: 'HC-EB5424L-M035D-KL01-PAM', version: 'A.2', quantity: '1.0', unit: 'pcs' }
])
</script>

<style scoped>
.bom-container {
  padding: 20px;
  background-color: #fff;
  min-height: 100vh;
}

.header-section {
  margin-bottom: 20px;
}

.page-title {
  font-size: 18px;
  color: #303133;
  margin: 0;
  font-weight: 600;
}

.custom-tabs :deep(.el-tabs__item) {
  font-weight: bold;
}

.tab-content {
  padding: 10px 0;
}

.bom-content {
  height: calc(100vh - 200px);
  background: #fff;
  padding: 10px;
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

.table-toolbar {
  display: flex;
  justify-content: space-between;
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
