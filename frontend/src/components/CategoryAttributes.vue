<template>
  <div class="common-layout">
    <el-container class="layout-container">
      <TopNav active="engineer" label="分类属性定义" />

      <el-main class="main-content blueprint-grid">
        <div class="toolbar panel">
          <el-button :icon="ArrowLeft" @click="goBack">返回</el-button>
          <span class="toolbar-title">{{ categoryName || '分类' }} · 属性定义</span>
          <el-button type="primary" :icon="Plus" @click="openCreate">新增属性</el-button>
        </div>

        <el-table v-loading="loading" :data="attrs" border class="data-table panel">
          <el-table-column prop="attr_label" label="显示名" min-width="120" />
          <el-table-column prop="attr_key" label="键名" min-width="130" class-name="font-data" />
          <el-table-column label="类型" width="100" align="center">
            <template #default="scope">
              <el-tag size="small">{{ VALUE_TYPE_LABELS[scope.row.value_type] || scope.row.value_type }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="必填" width="70" align="center">
            <template #default="scope">{{ scope.row.required ? '是' : '否' }}</template>
          </el-table-column>
          <el-table-column prop="default_value" label="默认值" min-width="100">
            <template #default="scope">{{ scope.row.default_value != null ? scope.row.default_value : '--' }}</template>
          </el-table-column>
          <el-table-column prop="unit" label="单位" width="90" align="center">
            <template #default="scope">{{ scope.row.unit || '--' }}</template>
          </el-table-column>
          <el-table-column prop="sort_order" label="排序" width="70" align="center" />
          <el-table-column label="操作" width="140" align="center">
            <template #default="scope">
              <el-button size="small" @click="openEdit(scope.row)">编辑</el-button>
              <el-button size="small" type="danger" @click="handleDelete(scope.row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-empty v-if="!loading && !attrs.length" description="该分类暂无属性定义，点击「新增属性」开始配置" />
      </el-main>
    </el-container>

    <!-- 新增 / 编辑属性定义 -->
    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑属性' : '新增属性'" width="520px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="显示名" required>
          <el-input v-model="form.attr_label" placeholder="如：减速比" />
        </el-form-item>
        <el-form-item label="键名" required>
          <el-input v-model="form.attr_key" placeholder="properties 中的键，如 ratio" :disabled="!!form.id" />
        </el-form-item>
        <el-form-item label="类型" required>
          <el-select v-model="form.value_type" style="width: 100%">
            <el-option v-for="t in VALUE_TYPES" :key="t" :label="VALUE_TYPE_LABELS[t]" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.value_type === 'enum'" label="候选值" required>
          <el-input v-model="form.optionsText" placeholder="逗号分隔，如：5:1,10:1,20:1" />
        </el-form-item>
        <el-form-item label="必填">
          <el-switch v-model="form.required" />
        </el-form-item>
        <el-form-item label="默认值">
          <el-input v-model="form.default_value" placeholder="可选" />
        </el-form-item>
        <el-form-item label="单位">
          <el-input v-model="form.unit" placeholder="如 kg、N·m" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :min="0" :controls="false" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Plus } from '@element-plus/icons-vue'
import TopNav from './TopNav.vue'
import { getNode, NODE_TYPES } from '../api/nodes'
import {
  listCategoryAttributes,
  createCategoryAttribute,
  updateCategoryAttribute,
  deleteCategoryAttribute
} from '../api/category-attributes'

const route = useRoute()
const router = useRouter()
const categoryId = route.params.id

const VALUE_TYPES = ['string', 'number', 'boolean', 'enum', 'date', 'text']
const VALUE_TYPE_LABELS = {
  string: '文本',
  number: '数字',
  boolean: '布尔',
  enum: '枚举',
  date: '日期',
  text: '长文本'
}

const attrs = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const categoryName = ref('')

const emptyForm = () => ({
  id: null,
  attr_key: '',
  attr_label: '',
  value_type: 'string',
  required: false,
  default_value: '',
  optionsText: '',
  unit: '',
  sort_order: 0
})
const form = reactive(emptyForm())

const load = async () => {
  loading.value = true
  try {
    const [cat, defs] = await Promise.all([
      getNode(NODE_TYPES.CATEGORY, categoryId).catch(() => null),
      listCategoryAttributes(categoryId)
    ])
    categoryName.value = cat?.properties?.name || ''
    attrs.value = defs || []
  } catch (e) {
    ElMessage.error(e.message || '加载属性定义失败')
    attrs.value = []
  } finally {
    loading.value = false
  }
}

const openCreate = () => {
  Object.assign(form, emptyForm())
  dialogVisible.value = true
}

const openEdit = (row) => {
  Object.assign(form, {
    id: row.id,
    attr_key: row.attr_key,
    attr_label: row.attr_label,
    value_type: row.value_type,
    required: !!row.required,
    default_value: row.default_value != null ? String(row.default_value) : '',
    optionsText: (row.options || []).join(', '),
    unit: row.unit || '',
    sort_order: row.sort_order || 0
  })
  dialogVisible.value = true
}

// 按 value_type 归一化默认值，保证写入 properties 后类型正确（数字/布尔/字符串）
const coerceDefault = (raw, valueType) => {
  if (raw === null || raw === undefined || raw === '') return null
  if (valueType === 'number') {
    const n = Number(raw)
    return Number.isNaN(n) ? null : n
  }
  if (valueType === 'boolean') {
    return raw === true || raw === 'true' || raw === '1' || raw === 1
  }
  return String(raw)
}

const handleSave = async () => {
  if (!form.attr_label.trim()) return ElMessage.warning('请填写显示名')
  if (!form.attr_key.trim()) return ElMessage.warning('请填写键名')

  const options = form.value_type === 'enum'
    ? (form.optionsText || '').split(',').map((s) => s.trim()).filter(Boolean)
    : null
  if (form.value_type === 'enum' && !options.length) return ElMessage.warning('枚举类型必须提供候选值')

  const payload = {
    attr_label: form.attr_label.trim(),
    attr_key: form.attr_key.trim(),
    value_type: form.value_type,
    required: form.required,
    default_value: coerceDefault(form.default_value, form.value_type),
    options,
    unit: form.unit.trim() || null,
    sort_order: form.sort_order ?? 0
  }

  saving.value = true
  try {
    if (form.id) {
      await updateCategoryAttribute(form.id, payload)
    } else {
      await createCategoryAttribute({ ...payload, category_id: categoryId })
    }
    ElMessage.success('保存成功')
    dialogVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确认删除属性「${row.attr_label}」？`, '删除属性', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return // 用户取消
  }
  try {
    await deleteCategoryAttribute(row.id)
    ElMessage.success('已删除')
    await load()
  } catch (e) {
    ElMessage.error(e.message || '删除失败')
  }
}

const goBack = () => router.push('/')

onMounted(load)
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

.toolbar {
  padding: 10px 15px;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.toolbar-title {
  font-family: var(--font-display);
  font-weight: 600;
  color: var(--ink-900);
  flex: 1;
}

.data-table {
  margin-top: 10px;
}
</style>
