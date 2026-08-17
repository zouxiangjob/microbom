<template>
  <DetailLayout :title="title" active-tab="basic">
    <div v-loading="loading" class="tab-content">
      <!-- 核心状态信息 -->
      <div class="status-summary">
        <el-row :gutter="20">
          <el-col :span="12">类型：{{ typeLabel }}</el-col>
          <el-col :span="12">生命周期状态：<el-tag :type="statusTagType(p.status)" size="small">{{ p.status || '--' }}</el-tag></el-col>
          <el-col :span="12">版本：{{ p.version || '--' }}</el-col>
        </el-row>
      </div>

      <el-divider />

      <!-- 详情信息 -->
      <section class="info-section">
        <h3 class="section-title">详情信息 <el-icon><ArrowDown /></el-icon></h3>
        <el-descriptions :column="2" border>
          <el-descriptions-item v-for="f in PART_DISPLAY_FIELDS" :key="f.key" :label="f.label">
            <el-tag v-if="f.kind === 'status'" :type="statusTagType(p[f.key])" size="small">{{ p[f.key] || '--' }}</el-tag>
            <template v-else>{{ p[f.key] != null ? p[f.key] + (f.unit || '') : '--' }}</template>
          </el-descriptions-item>
          <el-descriptions-item label="对象类型">{{ typeLabel }}</el-descriptions-item>
          <el-descriptions-item label="节点 ID">{{ nodeId }}</el-descriptions-item>
        </el-descriptions>
      </section>

      <!-- 附件说明：零部件本身不承载物理文件（文件 1:1 挂在 document/drawing 对象上），图档/技术文档见对应页签 -->
      <section class="info-section">
        <h3 class="section-title">附件 <el-icon><ArrowDown /></el-icon></h3>
        <el-empty description="零部件无直接物理文件，图档与技术文档请查看对应页签" :image-size="60" />
      </section>
    </div>
  </DetailLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowDown } from '@element-plus/icons-vue'
import DetailLayout from './DetailLayout.vue'
import { getNode, NODE_TYPES } from '../api/nodes'
import { nodeTitle, statusTagType, PART_DISPLAY_FIELDS } from '../api/mapping'

const route = useRoute()
const nodeId = route.params.id

const node = ref(null)
const loading = ref(false)
const title = ref('加载中...')

const p = computed(() => node.value?.properties || {})
const typeLabel = computed(() => node.value?.object_type || '--')

const loadNode = async () => {
  loading.value = true
  try {
    node.value = await getNode(NODE_TYPES.PART, nodeId)
    title.value = nodeTitle(node.value)
  } catch (e) {
    title.value = '未找到节点'
    ElMessage.error(e.message || '加载节点失败')
  } finally {
    loading.value = false
  }
}

onMounted(loadNode)
</script>

<style scoped>
.status-summary {
  font-size: 14px;
  color: #606266;
  line-height: 2;
  margin-bottom: 10px;
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
  min-height: 200px;
}
</style>
