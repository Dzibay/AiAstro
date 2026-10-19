import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import LegalView from '../views/LegalView.vue'
import LoginView from '../views/LoginView.vue'
import CabinetView from '../views/CabinetView.vue'
import AdminView from '../views/AdminView.vue'
import OverviewPanel from '../views/cabinet/OverviewPanel.vue'
import BirthPanel from '../views/cabinet/BirthPanel.vue'
import SectionSoon from '../views/cabinet/SectionSoon.vue'
import ChartPanel from '../views/cabinet/ChartPanel.vue'
import ForecastPanel from '../views/cabinet/ForecastPanel.vue'
import CheckoutView from '../views/CheckoutView.vue'
import InviteView from '../views/InviteView.vue'
import PairPanel from '../views/cabinet/PairPanel.vue'
import ChatPanel from '../views/cabinet/ChatPanel.vue'
import ProfilePanel from '../views/cabinet/ProfilePanel.vue'
import { SECTIONS } from '../components/cabinet/layout.js'
import { readSession } from '../composables/useSession.js'

const PANELS = { chart: ChartPanel, forecast: ForecastPanel, pair: PairPanel, chat: ChatPanel }

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior(to) {
    // vue-router ignores scroll-margin, so leave room for the floating header here.
    if (to.hash) return { el: to.hash, top: 96, behavior: 'smooth' }
    return { top: 0 }
  },
  routes: [
    { path: '/', name: 'home', component: HomeView, meta: { sky: 'journey' } },
    { path: '/legal/:page', name: 'legal', component: LegalView },
    { path: '/login', name: 'login', component: LoginView, meta: { sky: 'login' } },
    {
      // The shell stays while the panels inside it change; each section has its own pose of the sky.
      path: '/cabinet',
      component: CabinetView,
      meta: { sky: 'cabinet' },
      beforeEnter(to) {
        if (!readSession('web')) {
          return { name: 'login', query: { next: to.fullPath } }
        }
        return true
      },
      children: [
        { path: '', name: 'cabinet', component: OverviewPanel },
        { path: 'birth', name: 'cabinet-birth', component: BirthPanel },
        { path: 'profile', name: 'cabinet-profile', component: ProfilePanel },
        ...SECTIONS.map((section) => ({
          // /cabinet/chart/venus: one point of the chart, chosen on the wheel or in the list.
          path: section.id === 'chart' ? 'chart/:item?' : section.id,
          name: section.route,
          component: PANELS[section.id] || SectionSoon,
          meta: { sky: section.route, section: section.id, full: section.id === 'chat' },
        })),
      ],
    },
    { path: '/checkout/:product', name: 'checkout', component: CheckoutView },
    // The partner's side of an invitation: no account, the inviter's star on the login sky.
    { path: '/invite/:token', name: 'invite', component: InviteView, meta: { sky: 'login' } },
    { path: '/admin', name: 'admin', component: AdminView },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

export default router
