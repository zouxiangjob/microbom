<template>
  <DetailLayout :title="title" active-tab="parts" :tabs="OBJECT_DETAIL_TABS" :path-prefix="pathPrefix">
    <div v-loading="loading">
      <!-- 反查关联本对象的零部件 -->
      <el-table :data="tableData" border style="width: 100%" size="small">
        <el-table-column prop="code" label="编码" min-width="140" />
        <el-table-column prop="name" label="名称" min-width="180" />
        <el-table-column prop="version" label="版本" width="100" />
        <el-table-column prop="relation" label="关联类型" width="140" />
        <template #empty>
          <el-empty description="暂无关联零部件" :image-size="60" />
        </template>
      </el-table>
    </div>
  </DetailLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import DetailLayout from './DetailLayout.vue'
import { getNode } from '../api/nodes'
import { getReverseTree, RELATION_DATA_TYPES, relationLabel } from '../api/relations'
import { nodeDisplayName } from '../api/mapping'
import { OBJECT_DETAIL_TABS } from '../constants/detailTabs'

const route = useRoute()
const objectType = computed(() => route.params.objectType) // 'document' | 'drawing'
const nodeId = route.params.id
const pathPrefix = computed(() => `/object/${objectType.value}`)

const tableData = ref([])
const loading = ref(false)
const title = ref('加载中...')

// 对象类型 → 反向关系类型（本对象作为 target，source 为引用它的零件）
const REL_BY_TYPE = {
  document: RELATION_DATA_TYPES.DOCUMENT,
  drawing: RELATION_DATA_TYPES.DRAWING
}

const loadData = async () => {
  loading.value = true
  try {
    const rel = REL_BY_TYPE[objectType.value]
    // 复用逆向穿透接口，一次性带出引用本对象的零件快照，避免逐边 N+1 查询
    const flat = (await getReverseTree(nodeId)) || []
    tableData.value = flat
      .filter((i) => i.edge?.relation_type === rel && i.edge?.target_id === nodeId)
      .map((i) => {
        const part = i.source_node
        if (!part) return null
        const p = part.properties || {}
        return {
          id: part.id,
          code: p.part_number || '--',
          name: p.name || '--',
          version: p.version || '--',
          relation: relationLabel(i.edge.relation_type)
        }
      })
      .filter(Boolean)
  } catch (e) {
    ElMessage.error(e.message || '加载关联零部件失败')
    tableData.value = []
  } finally {
    loading.value = false
  }

  try {
    const node = await getNode(objectType.value, nodeId)
    title.value = nodeDisplayName(node)
  } catch {
    title.value = '零部件'
  }
}

onMounted(loadData)
</script>
