<template>
  <div class="detail-container">
    <div class="header-section">
      <el-button class="back-btn" :icon="ArrowLeft" text @click="goBack">返回</el-button>
      <h2 class="page-title">{{ title }}</h2>
    </div>

    <el-tabs :model-value="activeTab" class="custom-tabs" @tab-change="onTabChange">
      <el-tab-pane
        v-for="t in currentTabs"
        :key="t.name"
        :label="t.label"
        :name="t.name"
      />
    </el-tabs>

    <slot />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import { DETAIL_TABS } from '../constants/detailTabs'

const props = defineProps({
  title: { type: String, required: true },
  activeTab: { type: String, required: true },
  tabs: { type: Array, default: null },
  pathPrefix: { type: String, default: '' },
})

const router = useRouter()
const route = useRoute()

// 默认使用零部件页签，非零部件对象传入自定义 tabs
const currentTabs = computed(() => props.tabs || DETAIL_TABS)

const onTabChange = (name) => {
  const tab = currentTabs.value.find((t) => t.name === name)
  if (!tab) return
  // 切换 tab 时保留当前节点 :id，避免跳转后丢失节点上下文
  const id = route.params.id
  router.push(id ? `${props.pathPrefix}${tab.path}/${id}` : `${props.pathPrefix}${tab.path}`)
}

const goBack = () => router.push('/')
</script>

<style scoped>
.detail-container {
  padding: 20px;
  background-color: #fff;
  min-height: 100vh;
}

.header-section {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--app-border);
  margin-bottom: 16px;
}

.back-btn {
  color: var(--app-text-secondary);
}

.page-title {
  font-size: 18px;
  color: var(--app-text);
  margin: 0;
  font-weight: 600;
}

.custom-tabs :deep(.el-tabs__item) {
  font-weight: 500;
}
</style>
