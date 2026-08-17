import { createRouter, createWebHistory } from 'vue-router'
import Index from '../components/Index.vue'
import Attribute from '../components/Attribute.vue'
import Bom from '../components/Bom.vue'
import RelatedObjects from '../components/RelatedObjects.vue'
import WhereUsed from '../components/WhereUsed.vue'
import VersionHistory from '../components/VersionHistory.vue'
import ObjectBasic from '../components/ObjectBasic.vue'
import ObjectParts from '../components/ObjectParts.vue'

const routes = [
  { path: '/', component: Index },
  { path: '/attribute/:id', component: Attribute },
  { path: '/bom/:id', component: Bom },
  // 图档 / 技术文档（零部件详情页签）：同一组件按 kind 区分
  { path: '/cad/:id', component: RelatedObjects, props: { kind: 'drawing' } },
  { path: '/doc/:id', component: RelatedObjects, props: { kind: 'document' } },
  // 版本历史 / 被引用：零部件页与对象页共用，靠 route.params.objectType 区分
  { path: '/ehistory/:id', component: VersionHistory },
  { path: '/fget/:id', component: WhereUsed },
  // 技术文档 / 图档等非零部件对象的详情页（objectType: document | drawing）
  { path: '/object/:objectType/attribute/:id', component: ObjectBasic },
  { path: '/object/:objectType/parts/:id', component: ObjectParts },
  { path: '/object/:objectType/history/:id', component: VersionHistory },
  { path: '/object/:objectType/referenced/:id', component: WhereUsed },
  // 兜底：未知路径回首页
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

export default createRouter({
  history: createWebHistory(),
  routes
})
