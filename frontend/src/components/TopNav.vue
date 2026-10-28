<template>
  <el-header class="header">
    <div class="logo">MicroBOM<span class="logo-accent"></span></div>
    <nav class="nav-links">
      <router-link :class="['nav-link', { active: active === 'engineer' }]" to="/">📟 工程师端</router-link>
      <router-link :class="['nav-link', { active: active === 'purchase' }]" to="/purchase">📊 采购审计</router-link>
      <router-link :class="['nav-link', { active: active === 'workshop' }]" to="/workshop">🏭 车间看图</router-link>
    </nav>
    <div class="sheet-tag">SHEET <span class="sheet-no">01</span> · {{ label }}</div>
  </el-header>
</template>

<script setup>
defineProps({
  active: { type: String, required: true },
  label: { type: String, default: '' }
})
</script>

<style scoped>
.header {
  background-color: var(--paper);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  color: var(--ink-900);
  padding: 0 20px;
  border-bottom: 1px solid var(--line-strong);
}

.logo {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--ink-900);
  white-space: nowrap;
}

.logo-accent {
  color: var(--blue);
}

.nav-links {
  display: flex;
  gap: 4px;
  align-self: stretch;
}

.nav-link {
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 600;
  color: var(--ink-700);
  text-decoration: none;
  padding: 0 12px;
  display: flex;
  align-items: center;
  border-bottom: 2px solid transparent;
  transition: color 0.15s, border-color 0.15s;
}

.nav-link:hover {
  color: var(--ink-900);
}

.nav-link.active {
  color: var(--blue);
  border-bottom-color: var(--blue);
}

.sheet-tag {
  font-family: var(--font-data);
  font-size: 12px;
  letter-spacing: 0.08em;
  color: var(--ink-500);
  white-space: nowrap;
}

.sheet-no {
  color: var(--blue);
}
</style>
