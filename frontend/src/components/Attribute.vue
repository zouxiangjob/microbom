<template>
  <div class="pdm-detail-container">
    <!-- 顶部标题栏 -->
    <div class="header-section">
      <h2 class="page-title">ME000000253/B.1;GSK磨床</h2>
    </div>

    <!-- 标签页 -->
    <el-tabs v-model="activeTab" class="custom-tabs">
      <el-tab-pane label="基本属性" name="basic">
        <div class="tab-content">
          <!-- 核心状态信息 -->
          <div class="status-summary">
            <el-row :gutter="20">
              <el-col :span="12">类型：模型</el-col>
              <el-col :span="12">生命周期状态：<span class="status-tag">正在工作</span></el-col>
              <el-col :span="12">版本：A.1</el-col>
            </el-row>
          </div>

          <el-divider />

          <!-- 详情信息 -->
          <section class="info-section">
            <h3 class="section-title">详情信息 <el-icon><ArrowDown /></el-icon></h3>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="名称">HVTS6000-VDU3000</el-descriptions-item>
              <el-descriptions-item label="编码">KM1</el-descriptions-item>
              <el-descriptions-item label="版本状态">已检入</el-descriptions-item>
              <el-descriptions-item label="生命周期模板">T20231017001, 模型生命周期模板, v1.0</el-descriptions-item>
              <el-descriptions-item label="团队模板">默认模型团队模板</el-descriptions-item>
              <el-descriptions-item label="创建者">超级管理员 (1001)</el-descriptions-item>
              <el-descriptions-item label="创建时间">2024-09-26 03:35:28</el-descriptions-item>
              <el-descriptions-item label="修改者">超级管理员 (1001)</el-descriptions-item>
              <el-descriptions-item label="更新时间">2024-09-26 03:35:28</el-descriptions-item>
              <el-descriptions-item label="所有者">超级管理员 (1001)</el-descriptions-item>
              <el-descriptions-item label="检出时间">--</el-descriptions-item>
            </el-descriptions>
          </section>

          <!-- 主要内容资源 -->
          <section class="info-section">
            <h3 class="section-title">主要内容资源 <el-icon><ArrowDown /></el-icon></h3>
            <el-descriptions :column="2">
              <el-descriptions-item label="创作应用程序">CAPTURE</el-descriptions-item>
              <el-descriptions-item label="类别">ZIP</el-descriptions-item>
              <el-descriptions-item label="模型源文件">
                <el-link type="primary" :underline="false">
                  <el-icon><Document /></el-icon> HVTS6000-VDU3000.zip
                </el-link>
              </el-descriptions-item>
            </el-descriptions>
          </section>

          <!-- 附件列表 -->
          <section class="info-section">
            <h3 class="section-title">附件 <el-icon><ArrowDown /></el-icon></h3>
            <el-table :data="attachmentData" style="width: 100%" border>
              <el-table-column type="index" label="图标" width="60" align="center">
                <template #default>
                  <el-icon><Document /></el-icon>
                </template>
              </el-table-column>
              <el-table-column prop="name" label="名称" />
              <el-table-column prop="type" label="文件类型" width="120" />
              <el-table-column prop="url" label="URL" />
              <el-table-column prop="size" label="文件大小" width="120" />
              <el-table-column prop="createTime" label="创建时间" width="180" />
              <el-table-column prop="updateTime" label="更新时间" width="180" />
              <el-table-column prop="desc" label="详细描述" />
              <el-table-column label="操作" width="100" fixed="right">
                <template #default>
                  <el-button link type="primary">操作</el-button>
                </template>
              </el-table-column>
            </el-table>
          </section>
        </div>
      </el-tab-pane>
      
      <el-tab-pane label="BOM" name="bom" />
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
import { ArrowDown, Document } from '@element-plus/icons-vue'

const router = useRouter()
const activeTab = ref('basic')

// 监听标签页切换，当切换到 BOM 标签时跳转到 Bom 页面
watch(activeTab, (newVal) => {
  if (newVal === 'bom') {
    router.push('/bom')
  }
})

const attachmentData = ref([
  {
    name: 'HVTS6000-VDU3000.zip',
    type: '主要内容资源',
    url: '',
    size: '276.24 KB',
    createTime: '2024-09-26 03:35:28',
    updateTime: '2024-09-26 03:35:28',
    desc: ''
  }
])
</script>

<style scoped>
.pdm-detail-container {
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

.status-summary {
  font-size: 14px;
  color: #606266;
  line-height: 2;
  margin-bottom: 10px;
}

.status-tag {
  color: #409eff;
}

.section-title {
  font-size: 14px;
  font-weight: bold;
  color: #303133;
  margin: 25px 0 15px 0;
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
}

:deep(.el-descriptions__label) {
  width: 150px;
  justify-content: flex-end;
  color: #909399;
  font-weight: normal;
}

:deep(.el-descriptions__content) {
  color: #303133;
}

.tab-content {
  padding: 10px 0;
}
</style>

