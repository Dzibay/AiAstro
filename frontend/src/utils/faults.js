import { ApiError } from '../api/http.js'
import { readSession } from '../composables/useSession.js'

/**
 * Errors in the visitor's browser go to the operator's journal (admin → «Ошибки»): what failed,
 * the line of the code, the page. The same error is sent once per page load, at most a few per load,
 * and nothing about it ever reaches the person. The server's answers (ApiError) are not errors of
 * the page: the server keeps its own.
 *
 * After a release the files of the old build are gone: a page opened before it asks for a chunk
 * that is no longer there. One reload brings the new build instead of a broken screen.
 */

const LIMIT = 8
// The browsers' and extensions' own noise, not the site's.
const NOISE = [
  /ResizeObserver loop/i,
  /^Script error\.?$/i,
  /(chrome|moz|safari(-web)?)-extension:\/\//i,
  /Non-Error promise rejection captured/i,
  /AbortError|The operation was aborted|signal is aborted/i,
]
const CHUNK = /Failed to fetch dynamically imported module|Importing a module script failed|error loading dynamically imported module|Unable to preload CSS/i
const RELOADED = 'astra.reloaded'

const sent = new Set()

/** «/assets/HomeView-3fa9c1d2.js:12:345» from a stack line: the file without the build's hash. */
function placeOf(stack) {
  const line = String(stack || '').split('\n').find((row) => /https?:\/\//.test(row) && !/extension:\/\//.test(row))
  const url = line?.match(/(https?:\/\/[^\s)]+?):(\d+):(\d+)/)
  if (!url) return ''
  try {
    const path = new URL(url[1]).pathname.replace(/-[A-Za-z0-9_-]{8}(\.js)$/, '$1')
    return `${path}:${url[2]}:${url[3]}`
  } catch {
    return ''
  }
}

export function report(kind, error, extra = '') {
  try {
    if (error instanceof ApiError || sent.size >= LIMIT) return
    const message = String(error?.message ?? error ?? '').slice(0, 1000)
    const stack = String(error?.stack || '').slice(0, 8000)
    if (!message || NOISE.some((re) => re.test(message) || re.test(stack))) return
    const key = `${kind}|${message}`
    if (sent.has(key)) return
    sent.add(key)
    const headers = { 'Content-Type': 'application/json' }
    const token = readSession('web')
    if (token) headers.Authorization = `Bearer ${token}`
    fetch('/api/site/fault', {
      method: 'POST',
      headers,
      keepalive: true,
      body: JSON.stringify({
        kind: String(kind).slice(0, 40),
        message: extra ? `${message} · ${String(extra).slice(0, 120)}` : message,
        place: placeOf(stack).slice(0, 300),
        stack,
        page: (location.pathname + location.search).slice(0, 300),
      }),
    }).catch(() => {})
  } catch {
    // The reporter itself must never become an error of the page.
  }
}

/** A chunk of an old build: reload once (not in a loop, if the server itself is broken). */
function reloadForNewBuild(to) {
  try {
    const last = Number(sessionStorage.getItem(RELOADED) || 0)
    if (Date.now() - last < 30000) return false
    sessionStorage.setItem(RELOADED, String(Date.now()))
  } catch {
    return false
  }
  if (to) window.location.assign(to)
  else window.location.reload()
  return true
}

export function installFaults(app, router) {
  app.config.errorHandler = (error, instance, info) => {
    report('vue', error, info)
    console.error(error)
  }
  window.addEventListener('error', (event) => {
    // A failed <img> or <script> has no error object: not a fault of the code.
    if (!event.error && !event.message) return
    report('error', event.error || event.message)
  })
  window.addEventListener('unhandledrejection', (event) => report('promise', event.reason))
  window.addEventListener('vite:preloadError', (event) => {
    if (reloadForNewBuild()) event.preventDefault()
  })
  router.onError((error, to) => {
    if (CHUNK.test(String(error?.message || '')) && reloadForNewBuild(to?.fullPath)) return
    report('router', error)
  })
}
