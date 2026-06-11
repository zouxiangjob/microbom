<template>
  <div class="version-history-container">
    <!-- 顶部标题栏 -->
    <div class="header-section">
      <h2 class="page-title">ME000000253/B.1;GSK磨床</h2>
    </div>

    <!-- 横向菜单（与其他页面保持一致，切换时会触发路由跳转） -->
      <el-tabs v-model="activeTab" class="custom-tabs">
        <el-tab-pane label="基本属性" name="basic" />
        <el-tab-pane label="BOM" name="bom" />
        <el-tab-pane label="CAD 模型" name="cad" />
        <el-tab-pane label="相关文档" name="docs" />
        <el-tab-pane label="版本历史" name="history" />
        <el-tab-pane label="被引用" name="referenced" />
        <el-tab-pane label="流程" name="workflow" />
      </el-tabs>

    <!-- 版本历史表格 -->
    <el-table 
      :data="historyData" 
      style="width: 100%" 
      size="small"
      :header-cell-style="{ background: '#fcfcfc', color: '#333' }"
    >
      <el-table-column prop="version" label="修订版本" width="100">
        <template #default="{ row }">
          <el-link type="primary" :underline="false">{{ row.version }}</el-link>
        </template>
      </el-table-column>
      
      <el-table-column prop="name" label="名称" min-width="120" />
      <el-table-column prop="dataStatus" label="数据状态" width="120" />
      <el-table-column prop="workStatus" label="工作状态" width="120" />
      <el-table-column prop="creator" label="创建者" width="120" />
      <el-table-column prop="createTime" label="创建时间" width="180" />
      <el-table-column prop="updater" label="更新者" width="120" />
      <el-table-column prop="updateTime" label="最后更新日期" width="180" />
      
      <el-table-column label="操作" width="100" fixed="right">
        <template #default>
          <el-button link type="primary" size="small">查看版次</el-button>
        </template>
      </el-table-column>
    </el-table>
    
      
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight } from '@element-plus/icons-vue'

const router = useRouter()
const activeTab = ref('history')

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
  if (routeMap[newVal]) router.push(routeMap[newVal])
})

const isExpanded = ref(true)

const historyData = ref([
  {
    version: 'A.1',
    name: '下料',
    dataStatus: '工作中',
    workStatus: '已检入',
    creator: 'lixuan1001',
    createTime: '2026-03-12 17:00:07',
    updater: 'lixuan1001',
    updateTime: '2026-03-12 17:00:07'
  }
])
</script>

<style scoped>
.version-history-container {
  padding: 10px;
  background-color: #fff;
}

/* 自定义折叠标题样式 */
.info-collapse {
  margin-bottom: 15px;
}

.collapse-header {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 8px 0;
  user-select: none;
}

.collapse-header .el-icon {
  transition: transform 0.3s;
  font-size: 12px;
  color: #909399;
}

.collapse-header .el-icon.is-active {
  transform: rotate(90deg);
}

.header-text {
  font-size: 13px;
  font-weight: bold;
  color: #303133;
}

.collapse-content {
  padding: 10px 20px;
  color: #606266;
  font-size: 13px;
}

/* 表格链接样式 */
:deep(.el-table .el-link) {
  font-size: 13px;
}

/* 去掉表格外边框，模拟图中简洁的视觉感 */
:deep(.el-table__inner-wrapper::before) {
  display: none;
}
</style>
