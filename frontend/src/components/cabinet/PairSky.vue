<script setup>
import { computed, onMounted, onUnmounted, ref, shallowRef, watch } from 'vue'
import { useSky } from '../../composables/useSky.js'
import { birthSigns } from '../../utils/skyToday.js'
import { clamp } from '../hero/sky.js'
import { signFigure } from '../hero/signFigure.js'
import { ASPECTS, POINTS, SIGN_BY_ID } from './astro.js'
import { cabinetLayout, wheelSpot } from './layout.js'

/**
 * The pair on the sky: the partner's star in the free middle of it, and a thread from the
 * person's own star (NameMark, in the corner) to it. The thread leaves the person's star level
 * and bows over the fan of sections, so it never runs through them.
 *
 * One star while a pair is open or typed in; the whole list of pairs, in an arc, otherwise.
 * A star still waiting for its invitation is a hollow ring on a dotted thread.
 *
 * In the list every star can be pressed to open its pair (`select`), and the pointer over it
 * lights its row in the panel (`hover`). The one open pair wears the engraving of its Sun sign,
 * as the person's own star does; the others dim and step back to a ring, and a press on any of
 * them opens it instead.
 *
 * A pair whose reading has just opened (`opening`) lights its thread once: gold runs along it from
 * the person's star with a spark at its head, and the partner's star answers with a burst.
 */

const props = defineProps({
  /**
   * [{ id, name, date, time, lit, hot, flash, open, bought, opening }]: `lit` once the birth data are known,
   * `open` for the pair in the panel, `opening` a new key each time its reading opens (0 otherwise).
   */
  stars: { type: Array, default: () => [] },
  /** The tone of the open pair (GET /me/partners/{id}/synastry): the colour of its thread. */
  tone: { type: String, default: '' },
  /** The aspect under the pointer in the panel: its glyphs hang on the thread. */
  aspect: { type: Object, default: null },
  /** Where the person's star is: the cabinet's own (default) or another page's. */
  from: { type: Object, default: null },
  /** The room for the partners' stars, { x, y, r }: the wheel's spot by default. */
  area: { type: Object, default: null },
})

const emit = defineEmits(['select', 'hover'])

const { geo } = useSky()
const reduce = ref(false)
const born = performance.now()
onMounted(() => {
  reduce.value = window.matchMedia('(prefers-reduced-motion: reduce)').matches
})

const fixed = (n) => n.toFixed(1)
const origin = computed(() => props.from || cabinetLayout(geo.value, 'pair').star)
const room = computed(() => props.area || wheelSpot(geo.value))

/**
 * The first stars wait for the person's star to land in the corner (NameMark's flight, 1.4 s);
 * a star typed in later starts at once.
 */
const delays = new Map()
const appeared = new Map()
function delayOf(id) {
  if (!delays.has(id)) {
    delays.set(id, Math.max(0, 1.3 - (performance.now() - born) / 1000))
    appeared.set(id, performance.now())
  }
  return delays.get(id)
}

/**
 * A sign is drawn after its star is in place: on the first visit once the star itself has
 * appeared, later once its flight to the middle is over (at once if it did not move).
 * Fixed when the sign appears, so the frames of a flight do not shift it.
 */
const signDelays = new Map()
function signDelayOf(key, known, delay, landing) {
  if (!signDelays.has(key)) signDelays.set(key, known ? (landing ? landing + 0.05 : 0.1) : delay + 1.2)
  return signDelays.get(key)
}

/** The pair in the panel: the only star on the sky, or the one the others step back from. */
const focusId = computed(() => (props.stars.length === 1 ? props.stars[0].id : props.stars.find((star) => star.open)?.id ?? null))
const stepped = computed(() => props.stars.length > 1 && focusId.value !== null)

const COLOURS = { easy: '#f0cd8a', tense: '#e08a76', mixed: '#eab48a', calm: '#e6e0f4' }

/** The burst at the partner's star: sparks flying out at uneven angles and lengths, a few a beat late. */
const SPARKS = Array.from({ length: 12 }, (_, i) => ({
  a: Math.round(i * 30 + ((i * 47) % 17) - 8),
  far: 7 + ((i * 5) % 7) * 1.3,
  r: i % 3 === 0 ? 1.5 : 1,
  late: (i % 4) * 0.06,
}))

/** The partner's sign as large as the person's own in a section, but never wider than the free sky. */
const signSpan = computed(() => {
  const { star } = cabinetLayout(geo.value, 'pair')
  return Math.min(star.span * star.k, room.value.r * (stepped.value ? 1.25 : 1.7))
})

/** Where each star is headed: the layout of the moment, before the flight that takes it there. */
const layout = computed(() => {
  const { x: cx, y: cy, r } = room.value
  const n = props.stars.length
  const narrow = geo.value.narrow
  const others = props.stars.filter((star) => star.id !== focusId.value)
  return props.stars.map((star, index) => {
    const known = delays.has(star.id)
    const delay = delayOf(star.id)
    const focus = star.id === focusId.value
    const aside = stepped.value && !focus
    let x = cx
    let y = cy
    if (aside) {
      // The others wait on a ring below the open pair, as far from the panel and the person's star as the sky allows.
      const slot = others.indexOf(star)
      const t = others.length === 1 ? 0.5 : slot / (others.length - 1)
      const angle = ((25 + 130 * t) * Math.PI) / 180
      x = cx + r * 0.9 * Math.cos(angle)
      y = cy + r * 0.9 * Math.sin(angle)
    } else if (n > 1 && !stepped.value) {
      // A gentle arc bowing away from the person's star, top to bottom.
      const t = n === 1 ? 0.5 : index / (n - 1)
      const spread = Math.min(r * 1.5, (narrow ? 34 : 70) * (n - 1))
      y = cy - spread / 2 + spread * t
      x = cx + (narrow ? r * 0.5 : r * 0.35) * Math.sin(Math.PI * t) - (narrow ? r * 0.2 : r * 0.1)
    }
    const radius = star.lit ? 1.8 + Math.min([...star.name].length, 12) * 0.28 : 3.2
    const signs = star.date ? birthSigns(star.date, star.time) : null
    const sun = signs ? SIGN_BY_ID[signs.sun] : null
    return {
      figure: focus && star.lit && signs ? signFigure(signs.sun, signSpan.value) : null,
      signKey: focus && signs ? `${star.id}:${signs.sun}:${focusTurn}` : '',
      known,
      ...star,
      focus,
      aside,
      x,
      y,
      s: aside ? 0.82 : 1,
      radius,
      colour: focus && props.tone ? COLOURS[props.tone] : '#f3dcae',
      sun: sun ? `${sun.glyph} ${sun.in}` : '',
      delay,
      // In the list only the hovered pair speaks its sign; the open one always does.
      caption: focus || star.hot,
      // Long names on a phone would leave the strip: they go under the star. A star on the ring
      // keeps its name inside the free sky, the panel is just past it.
      below: narrow || x + radius * 3 + 10 + [...star.name].length * 11 > (aside ? cx + r + 30 : geo.value.W - 12),
    }
  })
})

/**
 * Another pair opened, or the list rearranged: the stars fly to their new places unhurriedly, on a
 * bow rather than a straight line (two stars trading places pass each other side by side), and
 * the threads from the person's star bend after them. A resize or reduced motion moves them at once.
 */
const FLIGHT = 1.2
const shown = shallowRef(new Map())
const flights = new Map()
let frame = 0
let sized = ''
let focusTurn = 0
let lastFocus = null

const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2)

function placeOf(flight, now) {
  const t = Math.min(1, (now - flight.start) / (FLIGHT * 1000))
  const e = ease(t)
  const { from, to } = flight
  const dx = to.x - from.x
  const dy = to.y - from.y
  const bow = Math.sin(Math.PI * e) * 0.2
  return {
    x: from.x + dx * e - dy * bow,
    y: from.y + dy * e + dx * bow,
    s: from.s + (to.s - from.s) * e,
    done: t >= 1,
  }
}

function tick() {
  const now = performance.now()
  const next = new Map(shown.value)
  for (const [id, flight] of flights) {
    const place = placeOf(flight, now)
    next.set(id, place)
    if (place.done) flights.delete(id)
  }
  shown.value = next
  frame = flights.size ? requestAnimationFrame(tick) : 0
}

/** Seconds until the star lands (0 when it stands). */
function landingIn(id) {
  const flight = flights.get(id)
  return flight ? Math.max(0, FLIGHT - (performance.now() - flight.start) / 1000) : 0
}

watch(focusId, (id) => {
  if (id !== lastFocus) focusTurn += 1
  lastFocus = id
}, { flush: 'sync', immediate: true })

watch(layout, (stars) => {
  const now = performance.now()
  const size = `${geo.value.W}x${geo.value.H}`
  const jump = reduce.value || size !== sized
  sized = size
  const next = new Map()
  for (const star of stars) {
    const to = { x: star.x, y: star.y, s: star.s }
    const flight = flights.get(star.id)
    const at = flight ? placeOf(flight, now) : shown.value.get(star.id)
    if (!at || jump) {
      flights.delete(star.id)
      next.set(star.id, to)
      continue
    }
    next.set(star.id, at)
    const same = (a) => Math.abs(a.x - to.x) < 0.5 && Math.abs(a.y - to.y) < 0.5 && Math.abs(a.s - to.s) < 0.01
    if (flight ? same(flight.to) : same(at)) continue
    flights.set(star.id, { from: { x: at.x, y: at.y, s: at.s }, to, start: now })
  }
  for (const id of flights.keys()) if (!next.has(id)) flights.delete(id)
  shown.value = next
  if (flights.size && !frame) frame = requestAnimationFrame(tick)
}, { immediate: true })

/**
 * The reading opened: the gold waits for the star to stand (its thread drawn and the star lit on
 * its first visit, or its flight to the middle over), then runs for OPENING seconds and is gone.
 * Each key runs once, so a pair reloaded after the payment does not light again.
 */
const OPENING = 4.4
const effects = shallowRef(new Map())
const greeted = new Map()
const timers = new Set()

watch(() => props.stars.map((star) => `${star.id}:${star.opening || 0}`).join(), () => {
  for (const star of props.stars) {
    if (!star.opening || greeted.get(star.id) === star.opening) continue
    greeted.set(star.id, star.opening)
    const ready = appeared.get(star.id) + (delayOf(star.id) + 1.9) * 1000
    const delay = Math.max(0, (ready - performance.now()) / 1000, landingIn(star.id))
    effects.value = new Map(effects.value).set(star.id, { key: star.opening, delay })
    const timer = setTimeout(() => {
      timers.delete(timer)
      if (effects.value.get(star.id)?.key !== star.opening) return
      const next = new Map(effects.value)
      next.delete(star.id)
      effects.value = next
    }, (delay + OPENING) * 1000)
    timers.add(timer)
  }
}, { immediate: true })

onUnmounted(() => {
  cancelAnimationFrame(frame)
  for (const timer of timers) clearTimeout(timer)
})

const drawn = computed(() => {
  const from = origin.value
  const places = shown.value
  return layout.value.map((star) => {
    const { x, y, s } = places.get(star.id) || star
    // Leaves level, above the fan of sections, and comes down onto the star.
    const control = [from.x + (x - from.x) * 0.62, Math.min(from.y, y) - clamp(Math.abs(y - from.y) * 0.25, 20, 70)]
    return {
      ...star,
      x,
      y,
      s,
      // A pair opened from the sky draws its sign once its star has landed in the middle.
      signDelay: star.signKey ? signDelayOf(star.signKey, star.known, star.delay, landingIn(star.id)) : 0,
      effect: effects.value.get(star.id) || null,
      d: `M${fixed(from.x)} ${fixed(from.y)}Q${fixed(control[0])} ${fixed(control[1])} ${fixed(x)} ${fixed(y)}`,
      mid: [0.25 * from.x + 0.5 * control[0] + 0.25 * x, 0.25 * from.y + 0.5 * control[1] + 0.25 * y],
    }
  })
})

const label = computed(() => {
  const open = drawn.value.find((star) => star.focus)
  if (!props.aspect || !open) return null
  const [x, y] = open.mid
  return {
    x,
    y: y - 12,
    text: `${POINTS[props.aspect.a].glyph}  ${ASPECTS[props.aspect.type].glyph}  ${POINTS[props.aspect.b].glyph}`,
    tone: ASPECTS[props.aspect.type].tone,
  }
})

function pick(star) {
  emit('hover', null)
  emit('select', star.id)
}

const aria = computed(() => {
  const names = props.stars.filter((star) => star.name).map((star) => star.name)
  return names.length ? `Ваша звезда и ${names.length === 1 ? 'звезда' : 'звёзды'}: ${names.join(', ')}` : ''
})
</script>

<template>
  <svg
    v-if="drawn.length"
    class="pair-sky"
    :class="{ 'motion-off': reduce }"
    :width="geo.W"
    :height="geo.H"
    :viewBox="`0 0 ${geo.W} ${geo.H}`"
    role="img"
    :aria-label="aria"
  >
    <defs>
      <filter id="pair-sign-glow" x="-10%" y="-10%" width="120%" height="120%">
        <feGaussianBlur stdDeviation="2.2" result="b" />
        <feColorMatrix in="b" type="matrix" values="1 0 0 0 0  0 0.78 0 0 0  0 0 0.6 0 0  0 0 0 0.9 0" result="g" />
        <feMerge><feMergeNode in="g" /><feMergeNode in="SourceGraphic" /></feMerge>
      </filter>
      <radialGradient id="pair-gold">
        <stop offset="0" stop-color="#fff8e6" stop-opacity="0.95" />
        <stop offset="0.28" stop-color="#ffd98e" stop-opacity="0.42" />
        <stop offset="1" stop-color="#f0b860" stop-opacity="0" />
      </radialGradient>
      <radialGradient id="pair-halo">
        <stop offset="0" stop-color="#fff4ee" stop-opacity="0.9" />
        <stop offset="0.25" stop-color="#ffc9b8" stop-opacity="0.32" />
        <stop offset="1" stop-color="#ffb4a0" stop-opacity="0" />
      </radialGradient>
    </defs>

    <g
      v-for="star in drawn"
      :key="star.id"
      class="pair"
      :class="{ 'is-lit': star.lit, 'is-bought': star.bought, 'is-hot': star.hot, 'is-aside': star.aside, 'is-quiet': drawn.length > 1 && !star.focus && !star.aside && !star.hot }"
      :style="{ '--d0': `${star.delay}s`, '--c': star.colour }"
    >
      <path class="thread-glow" :d="star.d" pathLength="1" />
      <path class="thread" :d="star.d" pathLength="1" />
      <g v-if="star.effect" :key="`run-${star.effect.key}`" class="open-run" :style="{ '--od': `${star.effect.delay.toFixed(2)}s` }">
        <path class="open-trail-glow" :d="star.d" pathLength="1" />
        <path class="open-trail" :d="star.d" pathLength="1" />
        <path class="open-comet-glow" :d="star.d" pathLength="1" />
        <path class="open-comet" :d="star.d" pathLength="1" />
      </g>

      <g class="partner" :style="{ transform: `translate(${fixed(star.x)}px, ${fixed(star.y)}px)${star.s !== 1 ? ` scale(${star.s.toFixed(3)})` : ''}` }">
        <Transition name="sign">
          <g v-if="star.figure" :key="star.figure.id" class="sign" :style="{ '--sd': `${star.signDelay}s` }">
            <g class="sign-art" filter="url(#pair-sign-glow)">
              <path
                v-for="stroke in star.figure.art"
                :key="stroke.index"
                :class="`art-${stroke.kind}`"
                :d="stroke.d"
                pathLength="1"
                :style="{ '--i': stroke.index / Math.max(1, star.figure.art.length - 1) }"
              />
            </g>
            <g class="sign-lines">
              <line v-for="line in star.figure.lines" :key="line.key" :x1="line.a.x" :y1="line.a.y" :x2="line.b.x" :y2="line.b.y" />
            </g>
            <circle v-for="(dot, index) in star.figure.stars" :key="index" class="sign-star" :cx="dot.x" :cy="dot.y" :r="dot.r" />
          </g>
        </Transition>
        <template v-if="star.lit">
          <circle class="partner-halo" :r="star.radius * 7" fill="url(#pair-halo)" />
          <path
            class="partner-spike"
            :d="`M0 ${-star.radius * 5}Q${star.radius * 0.45} ${-star.radius * 0.45} ${star.radius * 5} 0Q${star.radius * 0.45} ${star.radius * 0.45} 0 ${star.radius * 5}Q${-star.radius * 0.45} ${star.radius * 0.45} ${-star.radius * 5} 0Q${-star.radius * 0.45} ${-star.radius * 0.45} 0 ${-star.radius * 5}Z`"
          />
          <circle class="partner-core" :r="star.radius" />
        </template>
        <circle v-else class="partner-wait" :r="star.radius" />
        <circle v-if="star.flash" class="partner-flash" :r="star.radius * 3" />

        <text
          v-if="star.name"
          class="partner-name"
          :x="star.below ? 0 : star.radius * 3 + 10"
          :y="star.below ? star.radius * 3 + 20 : 5"
          :text-anchor="star.below ? 'middle' : 'start'"
        >{{ star.name }}</text>
        <text
          v-if="star.caption && (star.sun || !star.lit)"
          class="partner-sign"
          :x="star.below ? 0 : star.radius * 3 + 10"
          :y="star.below ? star.radius * 3 + 40 : 26"
          :text-anchor="star.below ? 'middle' : 'start'"
        >{{ star.lit ? star.sun : 'звезда ещё не зажглась' }}</text>

        <g
          v-if="drawn.length > 1 && !star.focus"
          class="partner-hit"
          role="button"
          :aria-label="`Открыть пару: ${star.name}`"
          @click="pick(star)"
          @pointerenter="emit('hover', star.id)"
          @pointerleave="emit('hover', null)"
        >
          <circle r="26" />
          <rect
            :x="star.below ? -[...star.name].length * 5.5 - 8 : star.radius * 3 + 4"
            :y="star.below ? star.radius * 3 + 2 : -16"
            :width="[...star.name].length * 11 + 16"
            height="28"
          />
        </g>
      </g>

      <g
        v-if="star.effect"
        :key="`burst-${star.effect.key}`"
        class="open-burst"
        :style="{ '--od': `${star.effect.delay.toFixed(2)}s`, transform: `translate(${fixed(star.x)}px, ${fixed(star.y)}px)` }"
      >
        <circle class="open-bloom" :r="star.radius * 14" fill="url(#pair-gold)" />
        <circle class="open-ring" :r="star.radius * 2.6" />
        <circle class="open-ring is-late" :r="star.radius * 2.6" />
        <circle
          v-for="spark in SPARKS"
          :key="spark.a"
          class="open-spark"
          :r="spark.r"
          :style="{ '--a': `${spark.a}deg`, '--far': `${(star.radius * spark.far).toFixed(1)}px`, '--sd': `${spark.late}s` }"
        />
      </g>
    </g>

    <Transition name="label">
      <text v-if="label" :key="label.text" class="aspect-label" :class="`tone-${label.tone}`" :x="label.x" :y="label.y" text-anchor="middle">
        {{ label.text }}
      </text>
    </Transition>
  </svg>
</template>

<style scoped>
/* On the sky, in its coordinates (as the natal wheel), under the sections and the panel. */
.pair-sky {
  position: fixed;
  z-index: 1;
  top: 0;
  left: 0;
  overflow: visible;
  pointer-events: none;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
  animation: show-sky 0.6s ease both;
}

.thread, .thread-glow {
  fill: none;
  stroke: var(--c);
  stroke-linecap: round;
  stroke-dasharray: 1;
  stroke-dashoffset: 1;
  animation: draw 1.4s cubic-bezier(0.4, 0.1, 0.2, 1) var(--d0) forwards;
  transition: stroke 0.6s ease, opacity 0.4s ease;
}
.thread { stroke-width: 1.1; opacity: 0.8; }
.thread-glow { stroke-width: 5; opacity: 0.12; filter: blur(3px); }
/* Waiting for the partner: a dotted thread, drawn at once. */
.pair:not(.is-lit) .thread { stroke-dasharray: 0.004 0.012; stroke-dashoffset: 0; opacity: 0.5; animation: show 1s ease var(--d0) both; }
.pair:not(.is-lit) .thread-glow { display: none; }
.pair.is-quiet .thread { opacity: 0.32; }
.pair.is-quiet .thread-glow { opacity: 0.05; }
.pair.is-aside .thread { opacity: 0.2; }
.pair.is-aside .thread-glow { opacity: 0.04; }
.pair.is-hot .thread { opacity: 1; stroke-width: 1.5; }
.pair.is-hot .thread-glow { opacity: 0.22; }
/* An opened reading keeps a little more light in its thread. */
.pair.is-bought .thread-glow { opacity: 0.18; }
.pair.is-bought.is-quiet .thread-glow { opacity: 0.08; }

/* The reading has opened: gold along the thread, a spark at its head, a burst at the star. */
.open-run path { fill: none; stroke-linecap: round; }
.open-trail, .open-trail-glow {
  stroke: #ffe3a6;
  stroke-dasharray: 1;
  stroke-dashoffset: 1;
  animation: draw 1.1s cubic-bezier(0.4, 0.1, 0.2, 1) var(--od) forwards, fade 1.6s ease calc(var(--od) + 1.9s) forwards;
}
.open-trail { stroke-width: 1.7; }
.open-trail-glow { stroke-width: 9; opacity: 0.32; filter: blur(4px); }
.open-comet, .open-comet-glow {
  stroke: #fffaf0;
  stroke-dasharray: 0.07 2;
  stroke-dashoffset: 0.07;
  opacity: 0;
  animation: comet 1.1s cubic-bezier(0.4, 0.1, 0.2, 1) var(--od) both;
}
.open-comet { stroke-width: 2.6; }
.open-comet-glow { stroke: #ffd98e; stroke-width: 12; filter: blur(5px); }

.open-burst > * { transform-origin: 0 0; opacity: 0; }
.open-bloom { animation: bloom 2.2s ease-out calc(var(--od) + 0.95s) forwards; }
.open-ring {
  fill: none;
  stroke: #ffe3a6;
  stroke-width: 1.1;
  animation: ring 1.5s cubic-bezier(0.2, 0.7, 0.2, 1) calc(var(--od) + 1s) forwards;
}
.open-ring.is-late { stroke: #f6f0ff; stroke-width: 0.8; animation-delay: calc(var(--od) + 1.3s); }
.open-spark {
  fill: #fff2d0;
  filter: drop-shadow(0 0 2px #ffd27a);
  animation: spark 1.3s cubic-bezier(0.15, 0.7, 0.3, 1) calc(var(--od) + 1s + var(--sd)) forwards;
}

/* The place is flown in script (with the thread after it); only the dimming is left to CSS. */
.partner { transition: opacity 0.6s ease; }
/* The pairs the open one has stepped back from: dimmer and smaller, brighter again under the pointer. */
.pair.is-aside .partner { opacity: 0.5; }
.pair.is-aside.is-hot .partner { opacity: 0.95; }
.partner > * { opacity: 0; animation: show 0.8s ease calc(var(--d0) + 1.1s) forwards; }
.partner-halo { --o: 1; transform-origin: 0 0; animation: show 0.8s ease calc(var(--d0) + 1.1s) forwards, breathe 4.6s ease-in-out calc(var(--d0) + 2s) infinite; }
.partner-spike { --o: 1; fill: rgba(255, 228, 220, 0.5); }
.partner-core { --o: 1; fill: #fff6f2; filter: drop-shadow(0 0 4px #ffb9a4); transition: r 0.35s ease; }
.partner-wait { --o: 0.7; fill: none; stroke: #f3dcae; stroke-width: 1; stroke-dasharray: 2 3; }
.partner-flash {
  --o: 1;
  fill: none;
  stroke: #ffd9cc;
  stroke-width: 1.2;
  transform-origin: 0 0;
  animation: flash 1.4s cubic-bezier(0.2, 0.7, 0.2, 1) forwards;
}
.partner-name {
  --o: 1;
  font-family: var(--serif);
  font-style: italic;
  font-size: 19px;
  fill: #f6dccf;
  paint-order: stroke;
  stroke: rgba(4, 6, 12, 0.55);
  stroke-width: 4px;
}
.pair.is-quiet .partner-name { --o: 0.7; }
.partner-sign {
  --o: 0.85;
  font-family: var(--serif);
  font-style: italic;
  font-size: 14px;
  fill: rgba(242, 228, 200, 0.9);
  paint-order: stroke;
  stroke: rgba(4, 6, 12, 0.6);
  stroke-width: 4px;
}

/* The open pair's sign: the same engraving as the person's own, a shade rosier. */
.partner > .sign { --o: 1; animation-duration: 0.4s; animation-delay: var(--sd, 0s); }
.sign-art path {
  fill: none;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-dasharray: 1;
  stroke-dashoffset: 1;
  animation: draw 0.9s cubic-bezier(0.4, 0.1, 0.2, 1) calc(var(--sd, 0s) + var(--i) * 0.35s) forwards;
}
.art-outline { stroke: #f2cdb4; stroke-width: 1.15; opacity: 0.8; }
.art-detail { stroke: #e8bfa6; stroke-width: 0.8; opacity: 0.55; }
.art-hatch { stroke: #d9ad96; stroke-width: 0.6; opacity: 0.35; }
.sign-lines line { stroke: #ecd2c4; stroke-width: 0.8; stroke-linecap: round; opacity: 0.35; }
.sign-star { fill: #fff1ea; filter: drop-shadow(0 0 3px rgba(255, 190, 160, 0.9)); }
/* The sign of a pair that is no longer open lets go quickly while the next one draws. */
.partner > .sign.sign-leave-active { animation: sign-out 0.25s ease forwards; }

/* A star in the list opens its pair: the circle around it and its name answer the pointer. */
.partner > .partner-hit { --o: 1; pointer-events: auto; cursor: pointer; }
.partner-hit { outline: none; }
.partner-hit circle, .partner-hit rect { fill: transparent; }

.aspect-label {
  font-family: 'Segoe UI Symbol', 'Noto Sans Symbols', 'Noto Sans Symbols 2', sans-serif;
  font-size: 17px;
  fill: #f0cd8a;
  paint-order: stroke;
  stroke: rgba(4, 6, 12, 0.6);
  stroke-width: 4px;
  filter: drop-shadow(0 0 5px rgba(255, 200, 120, 0.6));
}
.aspect-label.tone-tense { fill: #f0a08c; }
.aspect-label.tone-joint { fill: #ece6f6; }
.label-enter-active, .label-leave-active { transition: opacity 0.25s ease; }
.label-enter-from, .label-leave-to { opacity: 0; }

@keyframes draw { to { stroke-dashoffset: 0; } }
@keyframes fade { to { opacity: 0; } }
@keyframes comet {
  0% { stroke-dashoffset: 0.07; opacity: 0; }
  6%, 88% { opacity: 1; }
  100% { stroke-dashoffset: -0.93; opacity: 0; }
}
@keyframes bloom {
  0% { transform: scale(0.25); opacity: 0; }
  18% { opacity: 1; }
  100% { transform: scale(1.15); opacity: 0; }
}
@keyframes ring {
  from { transform: scale(0.4); opacity: 0.95; }
  to { transform: scale(5); opacity: 0; }
}
@keyframes spark {
  0% { transform: rotate(var(--a)) translateX(2px); opacity: 0; }
  12% { opacity: 1; }
  100% { transform: rotate(var(--a)) translateX(var(--far)); opacity: 0; }
}
@keyframes glow-once {
  0% { opacity: 0; }
  30% { opacity: var(--o, 1); }
  100% { opacity: 0; }
}
@keyframes show { to { opacity: var(--o, 1); } }
@keyframes sign-out { to { opacity: 0; } }
@keyframes show-sky { from { opacity: 0; } }
@keyframes breathe { 50% { transform: scale(0.86); opacity: 0.8; } }
@keyframes flash {
  from { transform: scale(0.4); opacity: 1; }
  to { transform: scale(4.5); opacity: 0; }
}

@media (max-width: 760px) {
  .partner-name { font-size: 16px; }
  .partner-sign { font-size: 12.5px; }
}

.motion-off, .motion-off .partner > *, .motion-off .thread, .motion-off .thread-glow { animation: none; }
.motion-off .partner > * { opacity: var(--o, 1); }
.motion-off .thread, .motion-off .thread-glow { stroke-dashoffset: 0; }
.motion-off .partner-flash { display: none; }
.motion-off .partner { transition: none; }
.motion-off .sign-art path { animation: none; stroke-dashoffset: 0; }
/* Reduced motion: the thread and the star only brighten in gold and fade, nothing runs or flies. */
.motion-off .open-trail, .motion-off .open-trail-glow { stroke-dashoffset: 0; opacity: 0; animation: glow-once 3s ease var(--od) forwards; }
.motion-off .open-trail { --o: 0.9; }
.motion-off .open-trail-glow { --o: 0.32; }
.motion-off .open-bloom { --o: 0.8; transform: scale(0.8); animation: glow-once 3s ease var(--od) forwards; }
.motion-off .open-comet, .motion-off .open-comet-glow, .motion-off .open-ring, .motion-off .open-spark { display: none; }
</style>
