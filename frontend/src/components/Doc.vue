<template>
  <div class="related-docs-container">
     <!-- 顶部标题栏 -->
    <div class="header-section">
      <h2 class="page-title">ME000000253/B.1;GSK磨床</h2>
    </div>

    <!-- 标签页 -->
    <el-tabs v-model="activeTab" class="custom-tabs">
      <el-tab-pane label="基本属性" name="basic" />
      <el-tab-pane label="BOM" name="bom" />
      <el-tab-pane label="CAD 模型" name="cad" />
      <el-tab-pane label="相关文档" name="docs">
        <div class="tab-content">
          <!-- 顶部操作工具栏 -->
          <div class="table-toolbar">
      <div class="left-placeholder"></div>
      <div class="right-actions">
        <el-button-group>
          <el-button type="primary" :icon="Plus" plain size="small">创建</el-button>
          <el-button type="primary" :icon="Plus" plain size="small">增加</el-button>
        </el-button-group>
        <el-button :icon="Delete" size="small" plain class="margin-left">移除</el-button>
        <el-button :icon="Refresh" size="small" circle />
        <el-button :icon="Setting" size="small" circle />
      </div>
    </div>

    <!-- 数据表格 (演示暂无数据状态) -->
    <el-table 
      :data="tableData" 
      border 
      style="width: 100%" 
      size="small"
      class="custom-table"
    >
      <!-- 空数据插槽 -->
      <template #empty>
        <div class="empty-wrapper">
          <el-empty description="暂无数据" :image-size="60" />
        </div>
      </template>

      <el-table-column type="selection" width="40" />
      <el-table-column prop="code" label="对象编码" min-width="150" />
      <el-table-column prop="name" label="名称" min-width="150" />
      <el-table-column prop="type" label="指派类型" width="150" />
      <el-table-column prop="version" label="修订版本" width="120" />
      <el-table-column prop="quantity" label="数量" width="100" />
      <el-table-column prop="unit" label="单位" width="100" />
    </el-table>
        </div>
      </el-tab-pane>
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

// 初始数据为空，以展示图片中的“暂无数据”状态
const router = useRouter()
const activeTab = ref('docs')

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

const tableData = ref([])
</script>

<style scoped>
.related-docs-container {
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

/* 工具栏布局 */
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

.margin-left {
  margin-left: 8px;
}

/* 表格样式自定义 */
.custom-table :deep(.el-table__header th) {
  background-color: #fafafa;
  color: #333;
  font-weight: 500;
  height: 40px;
}

/* 空状态容器居中 */
.empty-wrapper {
  padding: 40px 0;
}

:deep(.el-empty__description) {
  margin-top: 10px;
}
</style>
