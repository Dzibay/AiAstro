import { onMounted, onUnmounted } from 'vue'
import { clamp } from '../components/hero/sky.js'
import { LAST_STOP } from '../components/hero/journey.js'
import { useSky } from './useSky.js'

/**
 * Lets a page drive the sky by scroll: every [data-sky-stop] section is a stop, the sky
 * rests on a stop while its section fills the screen and travels while two share it.
 */
export function useSkyJourney() {
  const { source } = useSky()
  /** Per stop: the scroll range where the sky rests on it. */
  let rests = []
  let observer

  function measure() {
    const vh = window.innerHeight
    const max = document.documentElement.scrollHeight - vh
    rests = [...document.querySelectorAll('[data-sky-stop]')].map((node) => {
      const rect = node.getBoundingClientRect()
      const top = Math.min(rect.top + window.scrollY, max)
      return [top, Math.min(top + Math.max(0, rect.height - vh), max)]
    })
  }

  function at() {
    const y = window.scrollY
    for (let i = 0; i < rests.length; i += 1) {
      const [a, b] = rests[i]
      if (y > b) continue
      if (y >= a || i === 0) return i
      const from = rests[i - 1][1]
      return i - 1 + clamp((y - from) / Math.max(1, a - from), 0, 1)
    }
    return Math.max(rests.length - 1, 0)
  }

  /** The emblem on the planet always leads on: to the next stop, and from the finale back to the top. */
  function next(journey, atEnd) {
    const stop = atEnd ? 0 : Math.min(Math.round(journey) + 1, LAST_STOP)
    const top = stop === 0 ? 0 : rests[stop]?.[0]
    if (top == null) return
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    window.scrollTo({ top, behavior: reduce ? 'auto' : 'smooth' })
  }

  const own = { at, next, fresh: true }

  onMounted(() => {
    measure()
    observer = new ResizeObserver(measure)
    // Sections change height as fonts and content load.
    document.querySelectorAll('[data-sky-stop]').forEach((node) => observer.observe(node))
    window.addEventListener('resize', measure, { passive: true })
    source.value = own
  })

  onUnmounted(() => {
    observer?.disconnect()
    window.removeEventListener('resize', measure)
    if (source.value === own) source.value = null
  })
}
