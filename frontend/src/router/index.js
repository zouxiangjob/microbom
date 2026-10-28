import { createRouter, createWebHistory } from 'vue-router'

// 所有页面组件按路由懒加载，Vite 会为每个页面拆出独立 chunk，避免首页一次性拉取全部代码。
const routes = [
  { path: '/', component: () => import('../components/Index.vue') },
  { path: '/purchase', component: () => import('../components/Purchase.vue') },
  { path: '/workshop', component: () => import('../components/Workshop.vue') },
  { path: '/category/:id/attributes', component: () => import('../components/CategoryAttributes.vue') },
  { path: '/attribute/:id', component: () => import('../components/Attribute.vue') },
  { path: '/bom/:id', component: () => import('../components/Bom.vue') },
  // 图档 / 技术文档（零部件详情页签）：同一组件按 kind 区分
  { path: '/cad/:id', component: () => import('../components/RelatedObjects.vue'), props: { kind: 'drawing' } },
  { path: '/doc/:id', component: () => import('../components/RelatedObjects.vue'), props: { kind: 'document' } },
  // 版本历史 / 被引用：零部件页与对象页共用，靠 route.params.objectType 区分
  { path: '/ehistory/:id', component: () => import('../components/VersionHistory.vue') },
  { path: '/fget/:id', component: () => import('../components/WhereUsed.vue') },
  // 技术文档 / 图档等非零部件对象的详情页（objectType: document | drawing）
  { path: '/object/:objectType/attribute/:id', component: () => import('../components/ObjectBasic.vue') },
  { path: '/object/:objectType/parts/:id', component: () => import('../components/ObjectParts.vue') },
  { path: '/object/:objectType/history/:id', component: () => import('../components/VersionHistory.vue') },
  { path: '/object/:objectType/referenced/:id', component: () => import('../components/WhereUsed.vue') },
  // 兜底：未知路径回首页
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

export default createRouter({
  history: createWebHistory(),
  routes
})
