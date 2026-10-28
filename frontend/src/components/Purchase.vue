<template>
  <div class="common-layout">
    <el-container class="layout-container">
      <TopNav active="purchase" label="采购审计" />

      <el-main class="main-content blueprint-grid">
        <!-- ECN 变更提醒 -->
        <div v-if="ecn.has_notifications" class="ecn-alert">
          <div class="ecn-title">🚨 收到设计部新版本变更紧急通知（请务必核对并修改 ERP 订单！）</div>
          <ul class="ecn-list">
            <li v-for="(note, i) in ecn.notifications" :key="i">{{ note }}</li>
          </ul>
          <div class="ecn-actions">
            <el-button type="danger" @click="handleAck">确认知晓变更</el-button>
          </div>
        </div>

        <div class="toolbar panel">
          <span class="toolbar-title">📊 采购 BOM 汇总与导出面板</span>
          <el-button type="success" :icon="Download" :loading="exporting" @click="handleExport">
            导出ERP 采购导入文件 (.xlsx)
          </el-button>
        </div>

        <el-table v-loading="loading" :data="rows" border class="data-table panel">
          <el-table-column prop="code" label="编号" min-width="160" class-name="font-data" />
          <el-table-column prop="name" label="名称" min-width="180" />
          <el-table-column prop="spec" label="规格型号" min-width="140" />
          <el-table-column prop="qty" label="采购数量" width="110" align="center" class-name="font-data" />
          <el-table-column prop="unit" label="单位" width="90" align="center" />
        </el-table>

        <el-empty
          v-if="!loading && !rows.length"
          description="暂无采购数据 — 请先在工程师端创建零部件并建立 BOM 关系"
        />
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import TopNav from './TopNav.vue'
import { fetchPurchaseRows, exportPurchaseExcel } from '../api/purchase'
import { fetchEcnNotifications, ackEcn } from '../api/ecn'

const rows = ref([])
const loading = ref(false)
const exporting = ref(false)
const ecn = reactive({ notifications: [], has_notifications: false })

const loadRows = async () => {
  loading.value = true
  try {
    rows.value = (await fetchPurchaseRows()) || []
  } catch (e) {
    ElMessage.error(e.message || '加载采购清单失败')
  } finally {
    loading.value = false
  }
}

const loadEcn = async () => {
  try {
    const data = await fetchEcnNotifications()
    ecn.notifications = data.notifications || []
    ecn.has_notifications = !!data.has_notifications
  } catch (e) {
    // 通知拉取失败不阻断主流程
  }
}

const handleAck = async () => {
  try {
    await ackEcn()
    ecn.notifications = []
    ecn.has_notifications = false
    ElMessage.success('已确认知晓变更')
  } catch (e) {
    ElMessage.error(e.message || '确认失败')
  }
}

const handleExport = async () => {
  exporting.value = true
  try {
    await exportPurchaseExcel()
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.error(e.message || '导出失败')
  } finally {
    exporting.value = false
  }
}

onMounted(() => {
  loadRows()
  loadEcn()
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

.ecn-alert {
  background: var(--el-color-danger-light-9);
  border: 2px solid var(--el-color-danger);
  padding: 12px 16px;
  margin-bottom: 12px;
}

.ecn-title {
  color: var(--el-color-danger-dark-2);
  font-weight: 700;
  font-size: 15px;
  margin-bottom: 8px;
}

.ecn-list {
  margin: 0;
  padding-left: 20px;
  color: var(--el-color-danger-dark-2);
  font-weight: 500;
  line-height: 1.7;
}

.ecn-actions {
  margin-top: 10px;
  display: flex;
  justify-content: flex-end;
}

.toolbar {
  padding: 10px 15px;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.toolbar-title {
  font-family: var(--font-display);
  font-weight: 600;
  color: var(--ink-900);
}

.data-table {
  margin-top: 10px;
}
</style>
