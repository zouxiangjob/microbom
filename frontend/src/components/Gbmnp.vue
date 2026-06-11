<template>
  <div class="workflow-container">
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

    <el-row class="full-height">
      <!-- 左侧：流程版本切换 -->
      <el-col :span="5" class="left-sidebar">
        <el-tabs v-model="leftTab" class="left-tabs">
          <el-tab-pane label="常规" name="normal" />
          <el-tab-pane label="流程" name="flow" />
          <el-tab-pane label="历史版本" name="history" />
        </el-tabs>
        
        <div class="tree-content">
          <el-tree :data="versionTree" default-expand-all :expand-on-click-node="false">
            <template #default="{ node, data }">
              <div class="custom-tree-node" :class="{ 'is-active': data.active }">
                <div class="node-title">
                  <el-icon v-if="data.children"><FolderOpened /></el-icon>
                  <span>{{ node.label }}</span>
                </div>
                <div v-if="data.active" class="node-status">
                  <span class="status-tag">正在运行</span>
                  <el-button size="small" type="primary" link>终止</el-button>
                </div>
              </div>
            </template>
          </el-tree>
        </div>
      </el-col>

      <!-- 右侧：流程图及详情 -->
      <el-col :span="19" class="main-content">
        <!-- 顶部二级导航 -->
        <div class="secondary-nav">
          <el-tabs v-model="activeDetailTab">
            <el-tab-pane label="流程导航" name="nav" />
            <el-tab-pane label="流程信息" name="info" />
            <el-tab-pane label="业务信息" name="biz" />
            <el-tab-pane label="附件" name="attach" />
            <el-tab-pane label="操作记录" name="logs" />
            <el-tab-pane label="任务委派记录" name="delegate" />
          </el-tabs>
        </div>

        <div class="scroll-area">
          <!-- 1. 流程导航（画布区） -->
          <section class="info-section">
            <div class="section-header">
              <span class="title">流程导航</span>
              <div class="canvas-tools">
                <el-checkbox size="small">全屏</el-checkbox>
                <span class="zoom-text">50%</span>
                <el-button size="small" type="primary">全面</el-button>
              </div>
            </div>
            <div class="workflow-canvas">
              <!-- 这里模拟流程图展示，实际建议集成 bpmn-js 或 LogicFlow -->
              <div class="canvas-placeholder">
                <img src="https://placeholder.com" alt="Workflow" />
              </div>
            </div>
          </section>

          <!-- 2. 流程信息 -->
          <section class="info-section">
            <div class="section-header">
              <span class="title">流程信息</span>
            </div>
            <el-descriptions :column="2" class="detail-grid">
              <el-descriptions-item label="流程ID">1494433165570478080</el-descriptions-item>
              <el-descriptions-item label="流程名称" label-class-name="blue-text">dev_工艺资源人员编制</el-descriptions-item>
              <el-descriptions-item label="流程启动时间">2026-04-16 20:23:52</el-descriptions-item>
              <el-descriptions-item label="流程推动者">--</el-descriptions-item>
            </el-descriptions>
          </section>

          <!-- 3. 业务信息 -->
          <section class="info-section">
            <div class="section-header">
              <span class="title">业务信息</span>
            </div>
            <div class="biz-form">
              <el-form inline size="small">
                <el-form-item label="视图">
                  <el-select v-model="bizView" style="width: 150px">
                    <el-option label="默认视图" value="default" />
                  </el-select>
                </el-form-item>
                <el-button type="primary" link size="small">高级搜索</el-button>
              </el-form>
            </div>
          </section>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { FolderOpened } from '@element-plus/icons-vue'

const router = useRouter()
const leftTab = ref('flow')
const activeDetailTab = ref('nav')
const bizView = ref('default')
const activeTab = ref('workflow')

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

const versionTree = [
  {
    label: 'D.1',
    children: [
      { label: 'dev_工艺资源人员编制', active: true }
    ]
  },
  { label: 'C.1', children: [] },
  { label: 'B.1', children: [] },
  { label: 'A.2', children: [] }
]
</script>

<style scoped>
.workflow-container {
  height: 600px;
  background: #fff;
  border: 1px solid #ebeef5;
}

.full-height { height: 100%; }

/* 左侧样式 */
.left-sidebar {
  border-right: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
}

.left-tabs :deep(.el-tabs__nav) { padding-left: 10px; }

.custom-tree-node {
  width: 100%;
}

.node-title {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
}

.is-active {
  background: #f0f7ff;
  border-left: 3px solid #409eff;
  margin-left: -20px;
  padding-left: 17px;
}

.node-status {
  padding: 5px 0 0 20px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.status-tag {
  font-size: 12px;
  color: #409eff;
}

/* 右侧样式 */
.main-content {
  display: flex;
  flex-direction: column;
}

.secondary-nav {
  padding: 0 15px;
  border-bottom: 1px solid #f0f2f5;
}

.scroll-area {
  flex: 1;
  overflow-y: auto;
  padding: 15px;
}

.info-section {
  margin-bottom: 25px;
}

.section-header {
  border-bottom: 1px solid #ebeef5;
  padding-bottom: 8px;
  margin-bottom: 15px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-header .title {
  font-weight: bold;
  font-size: 14px;
  color: #333;
}

.workflow-canvas {
  border: 1px solid #dcdfe6;
  height: 300px;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #fafafa;
}

.canvas-placeholder img {
  max-width: 100%;
  mix-blend-mode: multiply;
}

.canvas-tools {
  display: flex;
  align-items: center;
  gap: 15px;
}

.zoom-text {
  font-size: 12px;
  color: #909399;
}

.blue-text {
  color: #409eff !important;
}

:deep(.el-descriptions__label) {
  width: 120px;
  color: #909399;
}
</style>
