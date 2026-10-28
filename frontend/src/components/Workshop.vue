<template>
  <div class="common-layout">
    <el-container class="layout-container">
      <TopNav active="workshop" label="车间看图" />

      <el-main class="main-content blueprint-grid">
        <div class="search-panel panel">
          <div class="search-title">请输入或扫描物料条码/代号，查询车间最新生产图纸</div>
          <div class="search-row">
            <el-input
              v-model="code"
              class="search-input"
              placeholder="输入物料代号（如：WD-001）"
              clearable
              @keyup.enter="handleSearch"
            />
            <el-button type="primary" :icon="Search" :loading="loading" @click="handleSearch">
              调出最新图纸
            </el-button>
          </div>
        </div>

        <div v-if="result" class="viewer panel">
          <div class="viewer-title">📐 当前物料图纸看板 [{{ result.part_name }}]</div>
          <el-tabs v-model="activeTab">
            <el-tab-pane label="📦 3D 模具视角 (支持拖拽旋转)" name="3d" :disabled="!result.glb">
              <div class="viewer-body">
                <model-viewer
                  v-if="result.glb"
                  :src="result.glb.url"
                  auto-rotate
                  camera-controls
                  class="model3d"
                />
                <el-empty v-else description="暂无 3D 模型" />
              </div>
            </el-tab-pane>
            <el-tab-pane label="📐 2D 矢量工艺图 (PDF/DXF)" name="2d" :disabled="!result.pdf">
              <div class="viewer-body">
                <iframe v-if="result.pdf" :src="result.pdf.url" class="pdf-frame" title="2D 图纸" />
                <el-empty v-else description="暂无 2D 图纸" />
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import TopNav from './TopNav.vue'
import { fetchDrawings } from '../api/workshop'
import { fetchEcnNotifications } from '../api/ecn'

const code = ref('')
const loading = ref(false)
const result = ref(null)
const activeTab = ref('3d')
const hasNotifications = ref(false)

// model-viewer CDN 惰性注入
const MODEL_VIEWER_CDN = 'https://unpkg.com/@google/model-viewer/dist/model-viewer.min.js'
let cdnInjected = false
const injectModelViewer = () => {
  if (cdnInjected) return
  cdnInjected = true
  const s = document.createElement('script')
  s.src = MODEL_VIEWER_CDN
  s.async = true
  document.head.appendChild(s)
}

const doLoad = async () => {
  loading.value = true
  try {
    const data = await fetchDrawings(code.value.trim())
    result.value = data
    activeTab.value = data.glb ? '3d' : '2d'
    if (data.glb) injectModelViewer()
  } catch (e) {
    result.value = null
    ElMessage.error(e.message || '查询图纸失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = async () => {
  if (!code.value.trim()) {
    ElMessage.warning('请输入有效的物料编码/条码！')
    return
  }
  if (hasNotifications.value) {
    try {
      await ElMessageBox.confirm(
        `您调取的是最新变更物料 [${code.value.trim()}]，请注意核对版次是否与看板一致！`,
        '🚨 ECN 变更警告',
        { confirmButtonText: '我已明白，立刻看最新电子图', cancelButtonText: '取消', type: 'warning' }
      )
    } catch {
      return // 用户取消
    }
  }
  await doLoad()
}

onMounted(async () => {
  try {
    const data = await fetchEcnNotifications()
    hasNotifications.value = !!data.has_notifications
  } catch (e) {
    // 通知拉取失败不阻断主流程
  }
})
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

.main-content {
  padding: 15px;
  overflow-y: auto;
  min-height: 0;
}

.search-panel {
  padding: 20px;
}

.search-title {
  font-family: var(--font-display);
  font-weight: 600;
  color: var(--ink-900);
  margin-bottom: 12px;
}

.search-row {
  display: flex;
  gap: 10px;
  align-items: center;
}

.search-input {
  max-width: 420px;
}

.viewer {
  margin-top: 15px;
  padding: 15px;
}

.viewer-title {
  font-family: var(--font-display);
  font-weight: 600;
  color: var(--ink-900);
  margin-bottom: 10px;
}

.viewer-body {
  background: #e8e8e8;
  min-height: 300px;
}

.model3d {
  width: 100%;
  height: 60vh;
}

.pdf-frame {
  width: 100%;
  height: 60vh;
  border: none;
}
</style>
