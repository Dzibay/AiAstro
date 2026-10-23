import { readSession } from '../composables/useSession.js'

/**
 * The site's own figures for the operator (admin → «Аналитика», «Ссылки»): the pages seen, the
 * tours, the campaign link a visitor came by (?ref=…), and what people do on a page — how far
 * they scroll, how long it holds them, the buttons and links they press (data-track, links by
 * where they lead), the offers they see (v-seen), the game's steps. The browser keeps one
 * anonymous id in localStorage — no cookie, nothing sent anywhere but the site's own API. A
 * signed-in person's session goes along, so the account knows what it did. Nothing here ever
 * stops a page: what a page gathers leaves in batches a few seconds apart, and when the tab is left.
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

function headers() {
  const out = { 'Content-Type': 'application/json' }
  const token = readSession('web')
  if (token) out.Authorization = `Bearer ${token}`
  return out
}

const cut = (name) => String(name).toLowerCase().slice(0, 48)

export function track(kind, name, extra = {}) {
  const visitor = visitorId()
  if (!visitor || !name) return
  fetch('/api/site/track', {
    method: 'POST',
    headers: headers(),
    keepalive: true,
    body: JSON.stringify({ visitor, kind, name: cut(name), ...extra }),
  }).catch(() => {})
}

/* ---- What a page gathers ---- */

const BATCH = 40
const WAIT_MS = 5000
// The page being looked at; empty in the admin panel, where nothing is gathered.
let page = ''
const queued = []
let timer = 0

/** One event of the page, sent with the next batch. */
export function queue(kind, name, value) {
  if (!page || !name || !visitorId()) return
  const item = { kind, name: cut(name), page }
  if (Number.isFinite(value)) item.value = Math.max(0, Math.min(3600, Math.round(value)))
  queued.push(item)
  if (queued.length >= BATCH) flush()
  else if (!timer) timer = setTimeout(flush, WAIT_MS)
}

function flush() {
  clearTimeout(timer)
  timer = 0
  const visitor = visitorId()
  while (queued.length) {
    fetch('/api/site/track/many', {
      method: 'POST',
      headers: headers(),
      keepalive: true,
      body: JSON.stringify({ visitor, items: queued.splice(0, BATCH) }),
    }).catch(() => {})
  }
}

/* Attention: the seconds the tab is in front and the person moved, typed or scrolled in the last half minute. */
const IDLE_MS = 30000
let held = 0
let tick = 0
let stir = 0

function count(shown = !document.hidden) {
  const now = performance.now()
  if (shown && now - stir < IDLE_MS) held += Math.min(now - tick, 6000)
  tick = now
}

/** The page is left (another page, the tab hidden — it was in front until now): its attention goes with the batch. */
function leave(shown) {
  count(shown)
  const seconds = Math.round(held / 1000)
  if (seconds > 0) queue('time', page, seconds)
  held = 0
}

function wake() {
  tick = performance.now()
  stir = tick
}

/* Depth: the share of the page that has been on screen, by quarters, each once a page. The
   window scrolls on the open pages; in the cabinet the panel does (data-scroll-depth). */
const MARKS = [25, 50, 75, 100]
let reached = 0
let pending = null

function depth(target) {
  const box = target === document ? document.scrollingElement : target
  if (!(box instanceof Element) || (target !== document && !box.hasAttribute('data-scroll-depth'))) return 0
  if (box.scrollHeight - box.clientHeight < 40) return 0
  return ((box.scrollTop + box.clientHeight) / box.scrollHeight) * 100
}

function scrolled(event) {
  stir = performance.now()
  if (pending) return
  pending = event.target
  requestAnimationFrame(() => {
    const share = depth(pending)
    pending = null
    for (const mark of MARKS) {
      if (mark > reached && share >= mark - (mark === 100 ? 2 : 0)) {
        reached = mark
        queue('scroll', page, mark)
      }
    }
  })
}

/* Buttons with data-track="name"; links without it by where they lead: «to:cabinet-sky», «out:t-me». */
let routes = null

function linkName(link) {
  const href = link.getAttribute('href') || ''
  if (href.startsWith('mailto:')) return 'out:mail'
  if (href.startsWith('tel:')) return 'out:phone'
  let url
  try {
    url = new URL(href, window.location.href)
  } catch {
    return ''
  }
  if (url.origin !== window.location.origin) return `out:${url.hostname.replace(/^www\./, '').replace(/[^a-z0-9-]+/g, '-')}`
  return routes ? `to:${pageName(routes.resolve(`${url.pathname}${url.search}`))}` : ''
}

const PLACE = 'astra.place'
const PLACE_MS = 30 * 60 * 1000

function pressed(event) {
  const el = event.target instanceof Element ? event.target.closest('[data-track], a[href]') : null
  if (!el) return
  const name = el.dataset.track || linkName(el)
  if (!name) return
  queue('click', name)
  // An offer's button: the payment that may follow is counted to this place.
  if (/^(sky|pair):/.test(name)) {
    try {
      sessionStorage.setItem(PLACE, JSON.stringify({ name, at: Date.now() }))
    } catch {
      /* no storage: the payment goes without its place */
    }
  }
}

/** The offer the person last pressed in this tab, within half an hour: where a payment came from. */
export function offerPlace(fallback) {
  try {
    const last = JSON.parse(sessionStorage.getItem(PLACE) || 'null')
    if (last && Date.now() - last.at < PLACE_MS && typeof last.name === 'string') return last.name
  } catch {
    /* nothing kept */
  }
  return fallback
}

/* Offers seen: v-seen="'sky:chat'" counts the element once a page, when half of it is on screen. */
const seen = new Set()
let watcher = null

function spotted(entries) {
  for (const entry of entries) {
    const name = entry.target.dataset.seen
    if (!entry.isIntersecting || !name || seen.has(name)) continue
    seen.add(name)
    queue('offer', name)
  }
}

export const vSeen = {
  mounted(el, binding) {
    el.dataset.seen = binding.value || ''
    if (typeof IntersectionObserver !== 'function') return
    watcher ||= new IntersectionObserver(spotted, { threshold: 0.5 })
    watcher.observe(el)
  },
  updated(el, binding) {
    el.dataset.seen = binding.value || ''
  },
  unmounted(el) {
    watcher?.unobserve(el)
  },
}

/** A Yandex.Metrika goal already created in the counter (id 113754457). */
export function reachGoal(name) {
  if (!name || typeof window.ym !== 'function') return
  try {
    window.ym(113754457, 'reachGoal', name)
  } catch {
    /* counter blocked or not ready */
  }
}

/** A page's name for the figures: the route's, the legal page with its own name. */
function pageName(to) {
  if (to.name === 'legal' && typeof to.params.page === 'string') return `legal:${to.params.page}`
  return typeof to.name === 'string' ? to.name : 'other'
}

/** Every page seen; the first one tells where the visitor came from, and a ?ref= is taken off the address. */
export function installTracking(router) {
  routes = router
  let first = true
  router.afterEach((to, from, failure) => {
    if (failure) return
    if (to.path.startsWith('/admin')) {
      leave()
      page = ''
      return
    }
    // A point of the chart or a period of the forecast is the same page.
    if (!first && to.name === from.name) return
    leave()
    page = pageName(to)
    reached = 0
    seen.clear()
    wake()
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
    track('view', page, extra)
  })

  const quiet = { capture: true, passive: true }
  const stirred = () => {
    stir = performance.now()
  }
  for (const type of ['pointerdown', 'pointermove', 'keydown', 'wheel', 'touchstart']) window.addEventListener(type, stirred, quiet)
  document.addEventListener('scroll', scrolled, quiet)
  document.addEventListener('click', pressed, true)
  setInterval(count, 5000)
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
      wake()
      return
    }
    leave(true)
    flush()
  })
  window.addEventListener('pagehide', () => {
    leave()
    flush()
  })
}
