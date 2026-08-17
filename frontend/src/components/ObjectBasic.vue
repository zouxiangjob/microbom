<template>
  <DetailLayout :title="title" active-tab="basic" :tabs="OBJECT_DETAIL_TABS" :path-prefix="pathPrefix">
    <div v-loading="loading" class="tab-content">
      <section class="info-section">
        <h3 class="section-title">详情信息</h3>
        <el-descriptions :column="2" border>
          <el-descriptions-item v-for="f in fields" :key="f.key" :label="f.label">
            {{ p[f.key] != null ? p[f.key] : '--' }}
          </el-descriptions-item>
          <el-descriptions-item label="对象类型">{{ typeLabel }}</el-descriptions-item>
          <el-descriptions-item label="节点 ID">{{ nodeId }}</el-descriptions-item>
        </el-descriptions>
      </section>

      <!-- 文件档案：文档/图档是「带物理文件」的对象，接入上传/预览/下载 -->
      <section class="info-section">
        <h3 class="section-title">文件档案</h3>
        <el-descriptions :column="1" border class="file-desc">
          <el-descriptions-item label="物理文件">
            <span v-if="fileInfo">
              {{ fileInfo.original_name }}（{{ formatSize(fileInfo.file_size) }}，{{ fileInfo.mime_type || '未知类型' }}）
            </span>
            <span v-else class="file-hint">尚未上传物理文件</span>
          </el-descriptions-item>
        </el-descriptions>
        <div class="file-actions">
          <el-upload :show-file-list="false" :http-request="doUpload">
            <el-button type="primary" :icon="Upload" :loading="uploading">上传文件</el-button>
          </el-upload>
          <template v-if="fileInfo">
            <el-button :icon="View" @click="openFile(true)">预览</el-button>
            <el-button :icon="Download" @click="openFile(false)">下载</el-button>
          </template>
        </div>
      </section>
    </div>
  </DetailLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Upload, View, Download } from '@element-plus/icons-vue'
import DetailLayout from './DetailLayout.vue'
import { getNode } from '../api/nodes'
import { uploadFile, fileUrl, getFileMeta } from '../api/files'
import { nodeDisplayName } from '../api/mapping'
import { OBJECT_DETAIL_TABS } from '../constants/detailTabs'

const route = useRoute()
const objectType = computed(() => route.params.objectType) // 'document' | 'drawing'
const nodeId = route.params.id
const pathPrefix = computed(() => `/object/${objectType.value}`)

const node = ref(null)
const loading = ref(false)
const title = ref('加载中...')
const fileInfo = ref(null)
const uploading = ref(false)

const p = computed(() => node.value?.properties || {})
const typeLabel = computed(() => node.value?.object_type || objectType.value || '--')

// 各类型基本属性字段（后端 properties 键 → 展示 label）
const FIELD_CONFIGS = {
  document: [
    { label: '名称', key: 'name' },
    { label: '修订版本', key: 'doc_version' },
    { label: '标签', key: 'tag' }
  ],
  drawing: [
    { label: '名称', key: 'name' },
    { label: '版本', key: 'version' },
    { label: '类型', key: 'drawing_type' },
    { label: '格式', key: 'format' }
  ]
}
const fields = computed(() => FIELD_CONFIGS[objectType.value] || FIELD_CONFIGS.document)

const loadNode = async () => {
  loading.value = true
  try {
    node.value = await getNode(objectType.value, nodeId)
    title.value = nodeDisplayName(node.value)
    // 拉取文件元数据：有文件则展示并启用预览/下载，无文件则静默（仅显示上传）
    try {
      fileInfo.value = await getFileMeta(nodeId)
    } catch {
      fileInfo.value = null
    }
  } catch (e) {
    title.value = '未找到节点'
    ElMessage.error(e.message || '加载节点失败')
  } finally {
    loading.value = false
  }
}

// 文件上传：走 files.js 封装的 multipart 接口，返回 FileOut（含 original_name/file_size/mime_type/file_url）
const doUpload = async ({ file }) => {
  uploading.value = true
  try {
    fileInfo.value = await uploadFile(objectType.value, nodeId, file)
    ElMessage.success('上传成功')
  } catch (e) {
    ElMessage.error(e.message || '上传失败')
  } finally {
    uploading.value = false
  }
}

// 预览 / 下载：inline=true 浏览器内联渲染，inline=false 强制下载
const openFile = (inline) => {
  window.open(fileUrl(nodeId, inline), '_blank')
}

const formatSize = (bytes) => {
  if (bytes == null) return '--'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

onMounted(loadNode)
</script>

<style scoped>
.tab-content {
  padding: 10px 0;
  min-height: 200px;
}

.section-title {
  font-size: 14px;
  font-weight: bold;
  color: #303133;
  margin: 0 0 15px 0;
}

.file-desc {
  margin-bottom: 12px;
}

.file-hint {
  color: #909399;
}

.file-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}
</style>
