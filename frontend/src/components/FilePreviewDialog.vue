<template>
  <el-dialog
    :model-value="modelValue"
    :title="resolvedName || '文件预览'"
    width="80%"
    top="5vh"
    destroy-on-close
    @update:model-value="(v) => $emit('update:modelValue', v)"
  >
    <div v-loading="checking" class="preview-body">
      <el-empty v-if="checked && !hasFile" description="该文件尚未上传物理文件" :image-size="60" />

      <template v-else-if="checked && hasFile">
        <!-- PDF / 文本：浏览器内联渲染 -->
        <iframe v-if="kind === 'pdf' || kind === 'text'" :src="previewUrl" class="preview-frame" />

        <!-- 图片 -->
        <div v-else-if="kind === 'image'" class="img-wrap">
          <img :src="previewUrl" class="preview-img" alt="" />
        </div>

        <!-- 3D 模型 -->
        <div v-else-if="kind === 'model3d'" class="model3d-wrap">
          <model-viewer :src="previewUrl" auto-rotate camera-controls class="model3d" ar-status="not-presenting" />
        </div>

        <!-- Word：mammoth.js 客户端转 HTML -->
        <iframe v-else-if="kind === 'docx'" :srcdoc="docxHtml" class="preview-frame" />

        <!-- Excel：SheetJS 客户端转 HTML 表格 -->
        <iframe v-else-if="kind === 'xlsx'" :srcdoc="xlsxHtml" class="preview-frame" />

        <!-- 不支持预览 -->
        <div v-else class="unsupported">
          <div class="unsupported-icon">📁</div>
          <div>暂不支持此文件格式（{{ ext }}）的在线预览</div>
          <div v-if="hint" class="unsupported-hint">建议使用 <b>{{ hint }}</b> 打开此格式</div>
        </div>
      </template>
    </div>

    <template #footer>
      <el-button type="primary" :disabled="!hasFile" @click="download">📥 下载原文件</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { fileUrl, getFileMeta } from '../api/files'
import { docxPreviewHtml, xlsxPreviewHtml } from '../utils/previewHtml'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  fileName: { type: String, default: '' },
  objectId: { type: String, default: '' }
})
const emit = defineEmits(['update:modelValue'])

// ── 扩展名分类（对齐后端 components.py 的 render_preview_dialog）──
const IMAGE_EXTS = ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.bmp', '.ico']
const MODEL_3D_EXTS = ['.glb', '.gltf']
const TEXT_EXTS = ['.txt', '.csv', '.json', '.xml', '.md', '.log', '.yaml', '.yml', '.py', '.js', '.ts', '.html', '.css', '.sh', '.ini', '.cfg', '.toml']
const DOCX_EXTS = ['.docx']
const XLSX_EXTS = ['.xlsx', '.xls']
const UNSUPPORTED_HINTS = {
  '.dwg': 'AutoCAD',
  '.dxf': 'AutoCAD',
  '.stp': 'SolidWorks / FreeCAD',
  '.step': 'SolidWorks / FreeCAD',
  '.igs': 'CAD 软件',
  '.iges': 'CAD 软件'
}

// 用物理文件的 original_name 判定扩展名（getFileMeta 返回），而非传入的文档名；
// 文档名可能不含后缀（如「ASM-091_检验标准」），否则会被误判为「不支持格式」
const resolvedName = computed(() => fileMeta.value?.original_name || props.fileName)

const ext = computed(() => {
  const i = resolvedName.value.lastIndexOf('.')
  return i >= 0 ? resolvedName.value.slice(i).toLowerCase() : ''
})

const kind = computed(() => {
  if (ext.value === '.pdf') return 'pdf'
  if (IMAGE_EXTS.includes(ext.value)) return 'image'
  if (MODEL_3D_EXTS.includes(ext.value)) return 'model3d'
  if (DOCX_EXTS.includes(ext.value)) return 'docx'
  if (XLSX_EXTS.includes(ext.value)) return 'xlsx'
  if (TEXT_EXTS.includes(ext.value)) return 'text'
  return 'unsupported'
})

const hint = computed(() => UNSUPPORTED_HINTS[ext.value] || '')

const previewUrl = computed(() => (props.objectId ? fileUrl(props.objectId, true) : ''))
const downloadUrl = computed(() => (props.objectId ? fileUrl(props.objectId, false) : ''))

// ── 打开时探测物理文件是否存在 ──
const checking = ref(false)
const checked = ref(false)
const hasFile = ref(false)
const fileMeta = ref(null) // FileOut（含 original_name，用于扩展名判定）

watch(
  () => props.modelValue,
  async (visible) => {
    if (!visible) return
    checking.value = true
    checked.value = false
    hasFile.value = false
    fileMeta.value = null
    try {
      fileMeta.value = await getFileMeta(props.objectId)
      hasFile.value = true
    } catch {
      hasFile.value = false
    } finally {
      checked.value = true
      checking.value = false
    }
  }
)

const download = () => {
  if (downloadUrl.value) window.open(downloadUrl.value, '_blank')
}

// ── model-viewer CDN 惰性注入 ──
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
watch(kind, (k) => {
  if (k === 'model3d') injectModelViewer()
})

// ── DOCX / XLSX 自包含预览 HTML（iframe srcdoc，模板在 utils/previewHtml.js）──
const docxHtml = computed(() => docxPreviewHtml(previewUrl.value))
const xlsxHtml = computed(() => xlsxPreviewHtml(previewUrl.value))

</script>

<style scoped>
.preview-body {
  min-height: 200px;
}

.preview-frame {
  width: 100%;
  height: 70vh;
  border: none;
  border-radius: 4px;
  background: #fafafa;
}

.img-wrap {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
  background: #f5f5f5;
  border-radius: 4px;
}

.preview-img {
  max-width: 100%;
  max-height: 70vh;
  object-fit: contain;
}

.model3d-wrap {
  background: #e8e8e8;
  border-radius: 4px;
}

.model3d {
  width: 100%;
  height: 70vh;
}

.unsupported {
  text-align: center;
  padding: 60px 20px;
  color: #666;
}

.unsupported-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.unsupported-hint {
  margin-top: 8px;
}
</style>
