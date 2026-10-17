import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import LegalView from '../views/LegalView.vue'
import LoginView from '../views/LoginView.vue'
import CabinetView from '../views/CabinetView.vue'
import AdminView from '../views/AdminView.vue'
import { readSession } from '../composables/useSession.js'

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior() {
    return { top: 0 }
  },
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/legal/:page', name: 'legal', component: LegalView },
    { path: '/login', name: 'login', component: LoginView },
    {
      path: '/cabinet',
      name: 'cabinet',
      component: CabinetView,
      beforeEnter(to) {
        if (!readSession('web')) {
          return { name: 'login', query: { next: to.fullPath } }
        }
        return true
      },
    },
    { path: '/admin', name: 'admin', component: AdminView },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

export default router
