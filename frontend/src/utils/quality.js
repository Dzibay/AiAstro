import { ref, watch } from 'vue'
import { LITE } from './device.js'

/**
 * How much of the sky this machine can afford, found by watching real frames rather than guessed
 * from the hardware: a desktop with a weak integrated GPU looks strong on paper and still stutters.
 *
 * The steps go down from the least visible loss:
 *   0 — everything;
 *   1 — the sky canvas at a lower resolution, without the finest nebula detail;
 *   2 — the cheaper nebula shader (about half the noise);
 *   3 — no live glass and no SVG glow: panels get a denser tint, as on phones;
 *   4 — calm stars: only the brightest ones twinkle.
 * The scroll journey is never taken away here: on desktops it stays, phones decide it in device.js.
 *
 * A step down is remembered for this device for a month, so the next visit starts where it settled.
 */
export const MAX_LEVEL = 4
const STORE_KEY = 'aiastro_quality'
const KEEP_MS = 30 * 24 * 3600 * 1000

/** A frame slower than this (in ms) on the median means under ~45 fps. */
const SLOW_FRAME = 22
/** Frames per sample, and how many slow samples in a row it takes to step down. */
const SAMPLE = 90
const STRIKES = 2
/** No judging during the start and right after a step: loading and recompiling stutter anyway. */
const SETTLE_MS = 2500
/** A gap this long is a hidden tab or a blocking task, not the frame rate. */
const GAP_MS = 250

function stored() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORE_KEY) || 'null')
    if (saved && Date.now() - saved.at < KEEP_MS) return Math.min(MAX_LEVEL, Math.max(0, saved.level | 0))
  } catch {
    /* a broken record starts over */
  }
  return 0
}

function forced() {
  const value = new URLSearchParams(window.location.search).get('quality')
  return value !== null && /^[0-4]$/.test(value) ? Number(value) : null
}

function initial() {
  if (typeof window === 'undefined') return 0
  const pinned = forced()
  if (pinned !== null) return pinned
  // Phones and modest machines already start on the light sky.
  return LITE ? MAX_LEVEL : stored()
}

export const quality = ref(initial())

function mark() {
  const html = document.documentElement
  html.classList.toggle('no-glass', quality.value >= 3)
  html.classList.toggle('calm-stars', quality.value >= 4)
}

function stepDown() {
  if (quality.value >= MAX_LEVEL) return
  quality.value += 1
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify({ level: quality.value, at: Date.now() }))
  } catch {
    /* private mode: the step holds for this visit */
  }
}

/** Marks <html> and starts watching the frames; called once at start, from main.js. */
export function watchQuality() {
  watch(quality, mark, { immediate: true })
  if (LITE || forced() !== null || quality.value >= MAX_LEVEL) return
  let last = 0
  let calmUntil = performance.now() + SETTLE_MS
  let strikes = 0
  const frames = []
  function tick(now) {
    if (quality.value >= MAX_LEVEL) return
    requestAnimationFrame(tick)
    const gap = now - last
    last = now
    if (document.hidden || gap > GAP_MS || now < calmUntil) return
    frames.push(gap)
    if (frames.length < SAMPLE) return
    frames.sort((a, b) => a - b)
    const median = frames[frames.length >> 1]
    frames.length = 0
    strikes = median > SLOW_FRAME ? strikes + 1 : 0
    if (strikes >= STRIKES) {
      strikes = 0
      stepDown()
      calmUntil = now + SETTLE_MS
    }
  }
  requestAnimationFrame(tick)
}
