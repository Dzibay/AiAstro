import { readSession } from '../composables/useSession.js'

/**
 * The site's own figures for the operator (admin → «Аналитика», «Ссылки»): the pages seen, the
 * tours, the campaign link a visitor came by (?ref=…). The browser keeps one anonymous id in
 * localStorage — no cookie, nothing sent anywhere but the site's own API. A signed-in person's
 * session goes along, so the account knows which pages it saw. Nothing here ever stops a page.
 */

const KEY = 'astra.visitor'
const BOTS = /bot|crawl|spider|slurp|preview|headless|lighthouse/i
let id = null

export function visitorId() {
  if (id !== null) return id
  id = ''
  if (BOTS.test(navigator.userAgent || '')) return id
  try {
    id = localStorage.getItem(KEY) || ''
    if (!/^[a-z0-9-]{16,40}$/.test(id)) {
      id = (crypto.randomUUID?.() || `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 14)}`).toLowerCase()
      localStorage.setItem(KEY, id)
    }
  } catch {
    // Private mode without storage: such a visitor is simply not counted.
    id = ''
  }
  return id
}

export function track(kind, name, extra = {}) {
  const visitor = visitorId()
  if (!visitor || !name) return
  const headers = { 'Content-Type': 'application/json' }
  const token = readSession('web')
  if (token) headers.Authorization = `Bearer ${token}`
  fetch('/api/site/track', {
    method: 'POST',
    headers,
    keepalive: true,
    body: JSON.stringify({ visitor, kind, name: String(name).toLowerCase().slice(0, 48), ...extra }),
  }).catch(() => {})
}

/** A page's name for the figures: the route's, the legal page with its own name. */
function pageName(to) {
  if (to.name === 'legal' && typeof to.params.page === 'string') return `legal:${to.params.page}`
  return typeof to.name === 'string' ? to.name : 'other'
}

/** Every page seen; the first one tells where the visitor came from, and a ?ref= is taken off the address. */
export function installTracking(router) {
  let first = true
  router.afterEach((to, from, failure) => {
    if (failure || to.path.startsWith('/admin')) return
    // A point of the chart or a period of the forecast is the same page.
    if (!first && to.name === from.name) return
    const extra = {}
    if (first) {
      first = false
      try {
        const source = document.referrer ? new URL(document.referrer) : null
        if (source && source.host !== window.location.host) extra.source = source.origin
      } catch {
        // A referrer that is not an address: no source.
      }
      extra.device = window.matchMedia('(max-width: 760px), (hover: none) and (pointer: coarse)').matches ? 'phone' : 'desktop'
    }
    const ref = to.query.ref
    if (typeof ref === 'string' && ref) {
      extra.ref = ref.slice(0, 40)
      // The address stays clean for sharing; vue-router keeps its own state.
      const url = new URL(window.location.href)
      url.searchParams.delete('ref')
      window.history.replaceState(window.history.state, '', `${url.pathname}${url.search}${url.hash}`)
    }
    track('view', pageName(to), extra)
  })
}
