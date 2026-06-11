import { createRouter, createWebHistory } from 'vue-router'
import Index from '../components/Index.vue'
import Attribute from '../components/Attribute.vue'
import Bom from '../components/Bom.vue'
import Cad from '../components/Cad.vue'
import Doc from '../components/Doc.vue'
import Ehistory from '../components/Ehistory.vue'
import Fget from '../components/Fget.vue'
import Gbmnp from '../components/Gbmnp.vue'

const routes = [
  { path: '/', component: Index },
  { path: '/attribute', component: Attribute },
  { path: '/bom', component: Bom },
  { path: '/cad', component: Cad },
  { path: '/doc', component: Doc },
  { path: '/ehistory', component: Ehistory },
  { path: '/fget', component: Fget },
  { path: '/gbmnp', component: Gbmnp }
]

export default createRouter({
  history: createWebHistory(),
  routes
})
