<template>
  <div class="cad-model-container">
    <!-- 顶部标题栏 -->
    <div class="header-section">
      <h2 class="page-title">ME000000253/B.1;GSK磨床</h2>
    </div>

    <!-- 标签页 -->
    <el-tabs v-model="activeTab" class="custom-tabs">
      <el-tab-pane label="基本属性" name="basic" />
      <el-tab-pane label="BOM" name="bom" />
      <el-tab-pane label="CAD 模型" name="cad"/>


    <!-- 表格上方工具栏 -->
    <div class="table-toolbar">
      <div class="left-placeholder"></div>
      <div class="right-actions">
        <el-button-group>
          <el-button type="primary" :icon="Plus" plain size="small">创建</el-button>
          <el-button type="primary" :icon="Plus" plain size="small">增加</el-button>
        </el-button-group>
        <el-button :icon="Delete" size="small" plain>移除</el-button>
        <el-button :icon="Refresh" size="small" circle />
        <el-button :icon="Setting" size="small" circle />
      </div>
    </div>

    <!-- 数据表格 -->
    <el-table 
      :data="cadData" 
      border 
      stripe 
      style="width: 100%" 
      size="small"
      header-cell-class-name="custom-header"
    >
      <el-table-column type="selection" width="40" fixed />
      <el-table-column type="index" label=" " width="50" fixed />
      
      <el-table-column prop="code" label="编码" min-width="150" sortable>
        <template #default="{ row }">
          <el-link type="primary" :underline="false">{{ row.code }}</el-link>
        </template>
      </el-table-column>
      
      <el-table-column prop="name" label="名称" min-width="120" sortable />
      <el-table-column prop="relation" label="关联类型" width="120" sortable />
      <el-table-column prop="version" label="版本" width="80" />
      <el-table-column prop="type" label="类型" width="120" />
      <el-table-column prop="remark" label="检入备注" width="120" />
      <el-table-column prop="context" label="上下文" min-width="150" show-overflow-tooltip />
      <el-table-column prop="status" label="生命周期状态" width="120" />
      <el-table-column prop="createTime" label="创建时间" width="160" sortable />
      <el-table-column prop="updateTime" label="修改时间" width="160" sortable />
      <el-table-column prop="creator" label="创建者" width="100" />
      
      <el-table-column label="操作" width="80" fixed="right">
        <template #default>
          <el-button link type="primary" size="small">移除</el-button>
        </template>
      </el-table-column>
    </el-table>
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
import { Plus, Delete, Refresh, Setting } from '@element-plus/icons-vue'

const router = useRouter()
const activeTab = ref('cad')

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

const subActiveTab = ref('cad')

const cadData = ref([
  {
    code: 'Erd-202400...',
    name: '测试图纸',
    relation: '被动关联',
    version: 'A.1',
    type: 'CAD 工程图',
    remark: '--',
    context: '智能集成辅助...',
    status: '正在工作',
    createTime: '2024-09-26 ...',
    updateTime: '2024-09-26 ...',
    creator: '超级管理'
  }
])
</script>

<style scoped>
.cad-model-container {
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

/* 三级Tab样式微调 */
.sub-nav :deep(.el-tabs__header) {
  margin: 0 0 10px 0;
}

.sub-nav :deep(.el-tabs__nav-wrap::after) {
  height: 1px;
}

/* 工具栏样式 */
.table-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.right-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 表格表头样式自定义（模拟图中的漏斗图标效果） */
:deep(.custom-header) {
  background-color: #f5f7fa !important;
  color: #606266;
}

/* 兼容超长文本的提示样式 */
:deep(.el-table .cell) {
  white-space: nowrap;
}
</style>
