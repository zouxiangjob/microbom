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
  background-color: var(--ink-900);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  color: #fff;
  padding: 0 20px;
  border-bottom: 2px solid var(--blue);
}

.logo {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: #fff;
  white-space: nowrap;
}

.logo-accent {
  color: var(--cyan);
}

.nav-links {
  display: flex;
  gap: 8px;
}

.nav-link {
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 600;
  color: #b7c4d4;
  text-decoration: none;
  padding: 6px 12px;
  border-radius: 2px;
  transition: background-color 0.15s, color 0.15s;
}

.nav-link:hover {
  color: #fff;
  background-color: var(--blue-strong);
}

.nav-link.active {
  background-color: var(--blue);
  color: #fff;
}

.sheet-tag {
  font-family: var(--font-data);
  font-size: 12px;
  letter-spacing: 0.08em;
  color: var(--ink-300);
  white-space: nowrap;
}

.sheet-no {
  color: var(--cyan);
}
</style>
