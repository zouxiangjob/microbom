<template>
  <DetailLayout :title="title" active-tab="history" :tabs="tabs" :path-prefix="pathPrefix">
    <!-- 版本历史表格（后端暂无版本表，数据为空态） -->
    <el-table
      v-loading="loading"
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
      <template #empty>
        <el-empty description="暂无版本历史" :image-size="60" />
      </template>
    </el-table>
  </DetailLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import DetailLayout from './DetailLayout.vue'
import { getNode, NODE_TYPES } from '../api/nodes'
import { nodeTitle, nodeDisplayName } from '../api/mapping'
import { DETAIL_TABS, OBJECT_DETAIL_TABS } from '../constants/detailTabs'

const route = useRoute()
const nodeId = route.params.id
// 与 WhereUsed 同理：零部件页 /ehistory/:id 与对象页 /object/:objectType/history/:id 共用本组件。
const isObject = computed(() => !!route.params.objectType)
const objectType = computed(() => route.params.objectType)

const tabs = computed(() => (isObject.value ? OBJECT_DETAIL_TABS : DETAIL_TABS))
const pathPrefix = computed(() => (isObject.value ? `/object/${objectType.value}` : ''))

const title = ref('加载中...')
const loading = ref(false)
// 后端暂无版本表，版本历史暂为空态
const historyData = ref([])

const loadNode = async () => {
  loading.value = true
  try {
    const nodeType = isObject.value ? objectType.value : NODE_TYPES.PART
    const root = await getNode(nodeType, nodeId)
    title.value = isObject.value ? nodeDisplayName(root) : nodeTitle(root)
  } catch (e) {
    title.value = '版本历史'
    ElMessage.error(e.message || '加载节点失败')
  } finally {
    loading.value = false
  }
}

onMounted(loadNode)
</script>

<style scoped>
:deep(.el-table .el-link) {
  font-size: 13px;
}

/* 去掉表格外边框，模拟简洁视觉 */
:deep(.el-table__inner-wrapper::before) {
  display: none;
}
</style>
