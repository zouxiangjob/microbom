<template>
  <DetailLayout :title="title" active-tab="basic">
    <div v-loading="loading" class="tab-content">
      <!-- 核心状态信息（只读：版本/状态由基线发布与状态机管理，不在此表单编辑） -->
      <div class="status-summary">
        <el-row :gutter="20">
          <el-col :span="8">类型：{{ typeLabel }}</el-col>
          <el-col :span="8">生命周期状态：<el-tag :type="statusTagType(p.status)" size="small">{{ p.status || '--' }}</el-tag></el-col>
          <el-col :span="8">版本：{{ p.version || '--' }}</el-col>
          <el-col :span="8">所属分类：{{ categoryName }}</el-col>
        </el-row>
      </div>

      <el-divider />

      <el-form :model="form" label-width="120px" class="attr-form">
        <h3 class="section-title">核心信息</h3>
        <el-form-item label="编码">
          <el-input v-model="form.part_number" placeholder="零件编码" />
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="零件名称" />
        </el-form-item>
        <el-form-item label="设计者">
          <el-input v-model="form.designer" placeholder="设计者" />
        </el-form-item>

        <h3 class="section-title">分类属性</h3>
        <el-empty
          v-if="!attributes.length"
          description="该零件未配置分类属性定义（请先在分类下定义属性模板）"
          :image-size="60"
        />

        <template v-for="attr in attributes" :key="attr.id">
          <el-form-item :label="attr.attr_label" :required="attr.required">
            <!-- string -->
            <el-input v-if="attr.value_type === 'string'" v-model="form[attr.attr_key]" />
            <!-- number -->
            <el-input-number
              v-else-if="attr.value_type === 'number'"
              v-model="form[attr.attr_key]"
              :controls="false"
              :value-on-clear="null"
              class="full-width"
            />
            <!-- boolean -->
            <el-switch v-else-if="attr.value_type === 'boolean'" v-model="form[attr.attr_key]" />
            <!-- enum -->
            <el-select v-else-if="attr.value_type === 'enum'" v-model="form[attr.attr_key]" clearable class="full-width">
              <el-option v-for="opt in (attr.options || [])" :key="opt" :label="opt" :value="opt" />
            </el-select>
            <!-- date -->
            <el-date-picker
              v-else-if="attr.value_type === 'date'"
              v-model="form[attr.attr_key]"
              type="date"
              value-format="YYYY-MM-DD"
              class="full-width"
            />
            <!-- text -->
            <el-input v-else-if="attr.value_type === 'text'" v-model="form[attr.attr_key]" type="textarea" :rows="3" />
            <!-- fallback -->
            <el-input v-else v-model="form[attr.attr_key]" />
            <span v-if="attr.unit" class="unit-suffix">{{ attr.unit }}</span>
          </el-form-item>
        </template>

        <el-form-item>
          <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
        </el-form-item>
      </el-form>
    </div>
  </DetailLayout>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import DetailLayout from './DetailLayout.vue'
import { getNode, updateNode, NODE_TYPES } from '../api/nodes'
import { getPartAttributeSchema } from '../api/category-attributes'
import { nodeTitle, statusTagType } from '../api/mapping'

const route = useRoute()
const nodeId = route.params.id

const node = ref(null)
const schema = ref(null)
const loading = ref(false)
const saving = ref(false)
const title = ref('加载中...')

const form = reactive({})
const p = computed(() => node.value?.properties || {})
const typeLabel = computed(() => node.value?.object_type || '--')
const attributes = computed(() => schema.value?.attributes || [])
const categoryName = computed(() => schema.value?.category_name || '--')

// 按 value_type 归一化初始值：boolean 必须给布尔（el-switch 不接受 null），其余保留或置 null
const normalizeValue = (attr) => {
  if (attr.value_type === 'boolean') return !!attr.value
  return attr.value ?? null
}

const loadNode = async () => {
  loading.value = true
  try {
    const [nodeResp, schemaResp] = await Promise.all([
      getNode(NODE_TYPES.PART, nodeId),
      getPartAttributeSchema(nodeId).catch(() => null)
    ])
    node.value = nodeResp
    schema.value = schemaResp
    title.value = nodeTitle(nodeResp)

    const props = nodeResp.properties || {}
    form.part_number = props.part_number || ''
    form.name = props.name || ''
    form.designer = props.designer || ''
    for (const attr of schemaResp?.attributes || []) {
      form[attr.attr_key] = normalizeValue(attr)
    }
  } catch (e) {
    title.value = '未找到节点'
    ElMessage.error(e.message || '加载节点失败')
  } finally {
    loading.value = false
  }
}

const handleSave = async () => {
  const payload = {
    part_number: form.part_number,
    name: form.name,
    designer: form.designer
  }

  for (const attr of attributes.value) {
    let v = form[attr.attr_key]

    // 必填校验
    if (attr.required && (v === null || v === undefined || v === '')) {
      ElMessage.error(`字段 [${attr.attr_label}] 为必填项`)
      return
    }

    // 数字类型：空值跳过，非空则强制转 number 并校验
    if (attr.value_type === 'number' && v !== null && v !== undefined && v !== '') {
      const n = Number(v)
      if (Number.isNaN(n)) {
        ElMessage.error(`字段 [${attr.attr_label}] 须为数字`)
        return
      }
      v = n
    }

    payload[attr.attr_key] = v
  }

  saving.value = true
  try {
    node.value = await updateNode(NODE_TYPES.PART, nodeId, payload)
    ElMessage.success('保存成功')
  } catch (e) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(loadNode)
</script>

<style scoped>
.status-summary {
  font-size: 14px;
  color: var(--ink-500);
  line-height: 2;
  margin-bottom: 10px;
}

.section-title {
  font-size: 14px;
  font-weight: bold;
  color: var(--ink-900);
  margin: 25px 0 15px 0;
}

.attr-form {
  max-width: 640px;
}

.full-width {
  width: 100%;
}

.unit-suffix {
  margin-left: 8px;
  color: var(--ink-500);
  font-size: 13px;
}
</style>
