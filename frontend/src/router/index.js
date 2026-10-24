import { createRouter, createWebHistory } from 'vue-router'
import { SECTIONS } from '../components/cabinet/layout.js'
import { readSession } from '../composables/useSession.js'
import { LANDINGS } from '../landing/pages.js'

// The home page comes with the first load; every other page is fetched when first opened.
import HomeView from '../views/HomeView.vue'
const LegalView = () => import('../views/LegalView.vue')
const LoginView = () => import('../views/LoginView.vue')
const LandingView = () => import('../views/LandingView.vue')
const CabinetView = () => import('../views/CabinetView.vue')
const AdminView = () => import('../views/AdminView.vue')
const AdminPulse = () => import('../views/admin/PulsePage.vue')
const AdminUsers = () => import('../views/admin/UsersPage.vue')
const AdminUser = () => import('../views/admin/UserPanel.vue')
const AdminPayments = () => import('../views/admin/PaymentsPage.vue')
const AdminPairs = () => import('../views/admin/PairsPage.vue')
const AdminSettings = () => import('../views/admin/SettingsPage.vue')
const AdminAi = () => import('../views/admin/AiPage.vue')
const AdminAnalytics = () => import('../views/admin/AnalyticsPage.vue')
const AdminLinks = () => import('../views/admin/LinksPage.vue')
const OverviewPanel = () => import('../views/cabinet/OverviewPanel.vue')
const BirthPanel = () => import('../views/cabinet/BirthPanel.vue')
const SectionSoon = () => import('../views/cabinet/SectionSoon.vue')
const ChartPanel = () => import('../views/cabinet/ChartPanel.vue')
const ForecastPanel = () => import('../views/cabinet/ForecastPanel.vue')
const InviteView = () => import('../views/InviteView.vue')
const PairPanel = () => import('../views/cabinet/PairPanel.vue')
const ChatPanel = () => import('../views/cabinet/ChatPanel.vue')
const ProfilePanel = () => import('../views/cabinet/ProfilePanel.vue')
const SkyPanel = () => import('../views/cabinet/SkyPanel.vue')

const PANELS = { chart: ChartPanel, forecast: ForecastPanel, pair: PairPanel, chat: ChatPanel, sky: SkyPanel }

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
    // The old checkout page: paying now happens in the cabinet, the pair in «Пара», the rest in «Небосвод».
    {
      path: '/checkout/:product',
      redirect: (to) => (to.params.product === 'synastry'
        ? { name: 'cabinet-pair', query: to.query.partner ? { partner: to.query.partner } : {} }
        : { name: 'cabinet-sky' }),
    },
    // The partner's side of an invitation: no account, the inviter's star on the login sky.
    { path: '/invite/:token', name: 'invite', component: InviteView, meta: { sky: 'login' } },
    {
      // The operator's pages; the shell asks for the password and keeps the menu.
      path: '/admin',
      component: AdminView,
      children: [
        { path: '', name: 'admin', component: AdminPulse },
        { path: 'analytics', name: 'admin-analytics', component: AdminAnalytics },
        { path: 'links', name: 'admin-links', component: AdminLinks },
        {
          path: 'users',
          name: 'admin-users',
          component: AdminUsers,
          // The person's card slides over the list, so the search and the scroll stay.
          children: [{ path: ':id(\\d+)', name: 'admin-user', component: AdminUser }],
        },
        { path: 'payments', name: 'admin-payments', component: AdminPayments },
        { path: 'pairs', name: 'admin-pairs', component: AdminPairs },
        { path: 'ai', name: 'admin-ai', component: AdminAi },
        { path: 'settings', name: 'admin-settings', component: AdminSettings },
      ],
    },
    // The landing pages for search and ads, one calculation each; their names are what «Аналитика» counts.
    ...LANDINGS.map((page) => ({ path: `/${page.slug}`, name: page.name, component: LandingView, meta: { sky: 'landing' } })),
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

export default router
