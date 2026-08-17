<template>
  <DetailLayout :title="title" active-tab="referenced" :tabs="tabs" :path-prefix="pathPrefix">
    <div v-loading="loading">
      <!-- 被引用关系树表格 -->
      <el-table
        :data="referencedData"
        row-key="id"
        border
        default-expand-all
        :tree-props="{ children: 'children' }"
        style="width: 100%"
        size="small"
      >
        <el-table-column prop="code" label="编码" min-width="160" />
        <el-table-column prop="name" label="名称" min-width="180" />
        <el-table-column prop="version" label="修订版本" width="100" />
        <el-table-column prop="relation" label="关联类型" min-width="200" />
        <template #empty>
          <el-empty description="暂无被引用记录" :image-size="60" />
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
import { getNode, NODE_TYPES } from '../api/nodes'
import { getReverseTree, relationLabel } from '../api/relations'
import { nodeTitle, nodeDisplayName } from '../api/mapping'
import { DETAIL_TABS, OBJECT_DETAIL_TABS } from '../constants/detailTabs'
import { flatToReverseTree } from '../utils/tree'

const route = useRoute()
const nodeId = route.params.id
// 对象详情页（/object/:objectType/referenced/:id）与零部件页（/fget/:id）共用本组件，
// 通过是否存在 objectType 参数区分上下文。
const isObject = computed(() => !!route.params.objectType)
const objectType = computed(() => route.params.objectType) // 'document' | 'drawing'

const tabs = computed(() => (isObject.value ? OBJECT_DETAIL_TABS : DETAIL_TABS))
const pathPrefix = computed(() => (isObject.value ? `/object/${objectType.value}` : ''))

const referencedData = ref([])
const loading = ref(false)
const title = ref('加载中...')

// 逆向树节点 → 表格行（保留编码/名称/版本/关联类型，递归还原 children）
const toRows = (nodes) =>
  (nodes || []).map((n) => {
    const p = n.node?.properties || {}
    return {
      id: n.id,
      code: p.part_number || p.name || '--',
      name: p.name || '--',
      version: p.version || p.doc_version || '--',
      relation: relationLabel(n.edge?.relation_type),
      children: toRows(n.children)
    }
  })

const loadData = async () => {
  loading.value = true
  try {
    const flat = (await getReverseTree(nodeId)) || []
    const nodeType = isObject.value ? objectType.value : NODE_TYPES.PART
    const titleFn = isObject.value ? nodeDisplayName : nodeTitle

    let root = null
    try {
      root = await getNode(nodeType, nodeId)
      title.value = titleFn(root)
    } catch {
      title.value = '被引用'
    }

    const rootP = root?.properties || {}
    referencedData.value = [
      {
        id: nodeId,
        code: rootP.part_number || rootP.name || '--',
        name: rootP.name || '--',
        version: rootP.version || rootP.doc_version || '--',
        relation: '—',
        children: toRows(flatToReverseTree(flat, nodeId))
      }
    ]
  } catch (e) {
    ElMessage.error(e.message || '加载被引用关系失败')
    referencedData.value = []
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>
