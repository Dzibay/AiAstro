<script setup>
import { computed, onMounted, onUnmounted, ref, shallowRef, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useSky } from '../../composables/useSky.js'
import { startTour, tour } from '../../utils/tour.js'
import { SECTION_BY_ID, cabinetLayout, mixLayout, starScale } from './layout.js'

/**
 * The cabinet's menu, drawn on the sky: five small constellations about the person's star
 * (NameMark draws the star itself, from the same layout). Hovered or focused, a constellation
 * lights up and a gold thread runs to it from the star; the open section keeps its thread.
 * Choosing one flies the points to their new places with the sky, on its curve and in its time.
 */

const props = defineProps({
  /** The open section, '' on the overview and the birth form. */
  section: { type: String, default: '' },
  /** The birth form is open: the star leads back instead of to it. */
  birthOpen: { type: Boolean, default: false },
  /** «Небосвод» is lit: the crowns of the sections it opens in full turn gold. */
  lit: { type: Boolean, default: false },
  /** The sections flaring gold while «Небосвод» catches fire (CabinetTour). */
  flare: { type: Array, default: () => [] },
})

const { geo } = useSky()
const route = useRoute()

// SkyStage's FLIGHT_MS and its ease, so the points land with the sky.
const FLIGHT_MS = 1400
const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2)

const reduce = ref(false)
const target = computed(() => cabinetLayout(geo.value, props.section))
const view = shallowRef(target.value)
let raf = 0

watch(target, (next, prev) => {
  cancelAnimationFrame(raf)
  // A resize puts everything in place at once; only a change of section flies.
  if (reduce.value || !prev || prev.W !== next.W || prev.H !== next.H) {
    view.value = next
    return
  }
  const from = view.value
  const start = performance.now()
  const step = (now) => {
    const t = Math.min(1, (now - start) / FLIGHT_MS)
    view.value = mixLayout(from, next, ease(t))
    if (t < 1) raf = requestAnimationFrame(step)
  }
  raf = requestAnimationFrame(step)
})

const hot = ref('')
/** The overview on a desktop has room to say what each section holds. */
const notes = computed(() => !props.section && !props.birthOpen && !geo.value.narrow)

const points = computed(() => view.value.points.map((point) => {
  const section = SECTION_BY_ID[point.id]
  return {
    ...point,
    section,
    active: point.id === props.section,
    stars: section.stars.map(([x, y, size]) => ({ x: x * 19, y: y * 19, r: 0.9 + size * 1.25 })),
    lines: section.edges.map(([a, b]) => ({ key: `${a}-${b}`, a: section.stars[a], b: section.stars[b] })),
  }
}))

/** A gentle arc from the star to a point, clear of both. */
function arc(star, point) {
  const dx = point.x - star.x
  const dy = point.y - star.y
  const length = Math.hypot(dx, dy) || 1
  const ux = dx / length
  const uy = dy / length
  const from = 14 * starScale(star.k)
  const to = 26 * point.s
  const ax = star.x + ux * from
  const ay = star.y + uy * from
  const bx = point.x - ux * to
  const by = point.y - uy * to
  // Bowed to one side by a tenth of its length, as a thread hangs rather than a ruler.
  const cx = (ax + bx) / 2 - uy * length * 0.1
  const cy = (ay + by) / 2 + ux * length * 0.1
  return `M${ax.toFixed(1)} ${ay.toFixed(1)}Q${cx.toFixed(1)} ${cy.toFixed(1)} ${bx.toFixed(1)} ${by.toFixed(1)}`
}

const threads = computed(() => {
  const star = view.value.star
  return points.value
    .filter((point) => point.active || point.id === hot.value)
    .map((point) => ({ key: point.id, d: arc(star, point), active: point.active, hot: point.id === hot.value }))
})

const home = computed(() => {
  const { star } = view.value
  const size = 64 * starScale(star.k)
  return { left: `${star.x - size / 2}px`, top: `${star.y - size / 2}px`, width: `${size}px`, height: `${size}px` }
})
/** The round «?» at the star's upper left (the name is written to its right): the introduction, again. */
const help = computed(() => {
  const { star } = view.value
  const reach = 32 * starScale(star.k) + 6
  const above = star.y - reach * 0.75 - 14
  // Under the header there may be no room above (a phone, a section open): then lower left.
  const top = above < 84 ? star.y + reach * 0.75 - 14 : above
  return { left: `${Math.max(6, star.x - reach * 0.75 - 14)}px`, top: `${top}px` }
})

const homeTo = computed(() => (props.section || props.birthOpen ? { name: 'cabinet' } : { name: 'cabinet-birth' }))
const homeLabel = computed(() => (props.section || props.birthOpen ? 'Ваша звезда: к обзору кабинета' : 'Ваша звезда: данные рождения'))

function pointStyle(point) {
  return { transform: `translate(${point.x.toFixed(1)}px, ${point.y.toFixed(1)}px) scale(${point.s.toFixed(3)})` }
}

onMounted(() => {
  reduce.value = window.matchMedia('(prefers-reduced-motion: reduce)').matches
})
onUnmounted(() => cancelAnimationFrame(raf))
</script>

<template>
  <nav class="cabinet-sky" :class="{ 'motion-off': reduce, 'with-notes': notes }" :style="{ height: `${view.H}px` }" aria-label="Разделы кабинета">
    <svg class="threads" :viewBox="`0 0 ${view.W} ${view.H}`" aria-hidden="true">
      <defs>
        <linearGradient id="thread-gold" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stop-color="#ffe9b8" />
          <stop offset="1" stop-color="#e3b66a" />
        </linearGradient>
      </defs>
      <path
        v-for="thread in threads"
        :key="thread.key"
        class="thread"
        :class="{ 'is-active': thread.active, 'is-hot': thread.hot }"
        :d="thread.d"
        pathLength="1"
      />
    </svg>

    <RouterLink class="home-star" :to="homeTo" :aria-label="homeLabel" :style="home" />
    <!-- Only on the overview: elsewhere the star moves aside, and each section has its own «?». -->
    <Transition name="help">
    <button
      v-if="route.name === 'cabinet'"
      type="button"
      class="tour-help"
      :class="{ 'is-on': tour.kind }"
      :style="help"
      aria-label="Знакомство с кабинетом"
      title="Знакомство с кабинетом"
      @click="startTour('intro')"
    >?</button>
    </Transition>

    <!-- Re-keyed by section under reduced motion: the points fade in at their new places instead of flying. -->
    <div :key="reduce ? section : 'points'" class="points">
      <RouterLink
        v-for="point in points"
        :key="point.id"
        class="point"
        :class="{ 'is-active': point.active, 'is-hot': point.id === hot, 'is-flare': flare.includes(point.id) }"
        :style="pointStyle(point)"
        :data-section="point.id"
        :to="{ name: point.section.route }"
        :aria-label="`${point.section.label}: ${point.section.title}${point.section.paid ? (lit ? ', открыт целиком с «Небосводом»' : ', часть открывает «Небосвод»') : ''}`"
        :aria-current="point.active ? 'page' : undefined"
        @pointerenter="hot = point.id"
        @pointerleave="hot = ''"
        @focus="hot = point.id"
        @blur="hot = ''"
      >
        <svg class="point-figure" viewBox="-30 -30 60 60" aria-hidden="true">
          <circle class="point-halo" r="27" />
          <line
            v-for="line in point.lines"
            :key="line.key"
            :x1="line.a[0] * 19"
            :y1="line.a[1] * 19"
            :x2="line.b[0] * 19"
            :y2="line.b[1] * 19"
          />
          <circle
            v-for="(star, index) in point.stars"
            :key="index"
            class="point-star"
            :cx="star.x"
            :cy="star.y"
            :r="star.r"
            :style="{ '--d': `${(index * 0.7 + point.x * 0.003) % 3}s` }"
          />
        </svg>
        <span class="point-label">
          {{ point.section.label }}
          <svg v-if="point.section.paid" class="point-crown" :class="{ 'is-lit': lit }" viewBox="0 0 16 12" aria-hidden="true">
            <path d="M1.5 10.5L1 3l4 3.2L8 1l3 5.2L15 3l-.5 7.5z" />
          </svg>
        </span>
        <span class="point-note" aria-hidden="true">{{ point.section.note }}</span>
      </RouterLink>
    </div>
  </nav>
</template>

<style scoped>
/* Over the sky, in its coordinates (SkyStage: fixed, full width, geo.H tall), under the panel. */
.cabinet-sky {
  position: fixed;
  z-index: 1;
  top: 0;
  left: 0;
  width: 100%;
  pointer-events: none;
}
.threads {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: visible;
}
.thread {
  fill: none;
  stroke: url(#thread-gold);
  stroke-width: 1;
  stroke-linecap: round;
  stroke-dasharray: 1;
  stroke-dashoffset: 1;
  opacity: 0.4;
  filter: drop-shadow(0 0 3px rgba(255, 205, 120, 0.55));
  animation: thread-draw 0.7s cubic-bezier(0.4, 0.1, 0.2, 1) forwards;
  transition: opacity 0.3s ease;
}
.thread.is-hot { opacity: 0.85; }

.home-star {
  position: absolute;
  border-radius: 50%;
  pointer-events: auto;
  outline: none;
}
.home-star:focus-visible { box-shadow: 0 0 0 1px rgba(255, 226, 168, 0.7), 0 0 22px rgba(255, 200, 110, 0.35); }

.tour-help {
  position: absolute;
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border-radius: 50%;
  border: 1px solid rgba(240, 205, 138, 0.5);
  background: rgba(10, 12, 20, 0.55);
  font-family: var(--serif);
  font-size: 16px;
  line-height: 1;
  color: #f3dcae;
  cursor: pointer;
  pointer-events: auto;
  box-shadow: 0 0 14px rgba(255, 200, 110, 0.2);
  transition: border-color 0.25s ease, background 0.25s ease, box-shadow 0.25s ease, left 0.3s ease, top 0.3s ease;
}
.tour-help:hover, .tour-help.is-on { border-color: #f0cd8a; background: rgba(240, 205, 138, 0.16); box-shadow: 0 0 18px rgba(255, 200, 110, 0.45); }
.tour-help:focus-visible { outline: 2px solid #ffe2a8; outline-offset: 3px; }
/* A finger needs a larger target than the eye: the hit area reaches past the circle. */
.tour-help::after { content: ''; position: absolute; inset: -8px; border-radius: 50%; }
.help-enter-active, .help-leave-active { transition: opacity 0.4s ease, transform 0.4s ease; }
.help-enter-from, .help-leave-to { opacity: 0; transform: scale(0.6); }

.points { position: absolute; inset: 0; }
/* The figure's centre sits on the point: the link is 150px wide and the figure 52px tall. */
.point {
  position: absolute;
  left: -75px;
  top: -26px;
  display: grid;
  justify-items: center;
  gap: 2px;
  width: 150px;
  padding-bottom: 4px;
  border-radius: 18px;
  color: rgba(242, 228, 200, 0.72);
  text-decoration: none;
  pointer-events: auto;
  transform-origin: 75px 26px;
  outline: none;
  -webkit-tap-highlight-color: transparent;
}
.point-figure { width: 52px; height: 52px; overflow: visible; }
.point-halo {
  fill: rgba(255, 210, 140, 0.07);
  opacity: 0;
  transform: scale(0.7);
  transform-origin: 0 0;
  transition: opacity 0.4s ease, transform 0.5s cubic-bezier(0.3, 0.7, 0.2, 1);
}
.point-figure line {
  stroke: #e9d3a6;
  stroke-width: 0.8;
  stroke-linecap: round;
  opacity: 0.32;
  transition: opacity 0.4s ease;
}
.point-star {
  fill: #fff1d4;
  filter: drop-shadow(0 0 2.5px rgba(255, 214, 140, 0.85));
  transform-box: fill-box;
  transform-origin: center;
  animation: point-twinkle 3s ease-in-out var(--d) infinite;
  transition: fill 0.3s ease;
}
.point-label {
  font-family: var(--serif);
  font-style: italic;
  font-size: 17px;
  line-height: 1.1;
  white-space: nowrap;
  text-shadow: 0 0 10px rgba(4, 6, 12, 0.9), 0 0 2px rgba(4, 6, 12, 0.9);
  transition: color 0.3s ease, text-shadow 0.3s ease;
}
/* A small crown: a part of the section is «Небосвод»'s; gold once it burns. */
.point-crown {
  width: 11px;
  height: 9px;
  margin-left: 2px;
  vertical-align: 0.45em;
  fill: none;
  stroke: rgba(240, 205, 138, 0.6);
  stroke-width: 1.2;
  stroke-linejoin: round;
}
.point-crown.is-lit { fill: #f0cd8a; stroke: #f0cd8a; filter: drop-shadow(0 0 3px rgba(255, 205, 120, 0.8)); }
.point-note {
  display: none;
  font-size: 10.5px;
  letter-spacing: 0.03em;
  line-height: 1.2;
  white-space: nowrap;
  color: rgba(226, 214, 192, 0.6);
  text-shadow: 0 0 8px rgba(4, 6, 12, 0.95), 0 0 2px rgba(4, 6, 12, 0.9);
  transition: color 0.3s ease;
}
.with-notes .point-note { display: block; }
.point:hover .point-note, .point.is-hot .point-note { color: rgba(240, 220, 180, 0.9); }

.point:hover .point-halo, .point.is-hot .point-halo, .point.is-active .point-halo { opacity: 1; transform: scale(1); }
.point:hover line, .point.is-hot line, .point.is-active line { opacity: 0.7; }
.point:hover .point-star, .point.is-hot .point-star, .point.is-active .point-star { fill: #fff8e8; animation-duration: 1.6s; }
.point:hover .point-label, .point.is-hot .point-label, .point.is-active .point-label {
  color: #f6d99c;
  text-shadow: 0 0 12px rgba(255, 196, 110, 0.45), 0 0 2px rgba(4, 6, 12, 0.9);
}
.point:focus-visible .point-halo { opacity: 1; transform: scale(1); fill: rgba(255, 210, 140, 0.1); stroke: rgba(255, 226, 168, 0.6); stroke-width: 0.8; }

/* «Небосвод» catches fire: each section in turn flashes gold and stays lit a little brighter. */
.point.is-flare .point-label { color: #f6d99c; text-shadow: 0 0 14px rgba(255, 196, 110, 0.6), 0 0 2px rgba(4, 6, 12, 0.9); }
.point.is-flare line { opacity: 0.8; stroke: #f0cd8a; }
.point.is-flare .point-star { fill: #fff8e8; }
.point.is-flare .point-halo { opacity: 1; transform: scale(1); fill: rgba(255, 210, 140, 0.16); animation: flare-burst 1.4s cubic-bezier(0.2, 0.7, 0.2, 1) both; }

@keyframes flare-burst { 0% { transform: scale(0.4); fill: rgba(255, 236, 196, 0.6); } 100% { transform: scale(1); } }
@keyframes thread-draw { to { stroke-dashoffset: 0; } }
@keyframes point-twinkle { 50% { opacity: 0.6; transform: scale(0.82); } }
@keyframes points-fade { from { opacity: 0; } }

@media (max-width: 760px) {
  .point-label { font-size: 15px; }
  /* A finger needs more than the figure: the link keeps a box as wide as its share of the row. */
  .point { min-height: 76px; left: -40px; width: 80px; transform-origin: 40px 26px; }
}

@media (prefers-reduced-motion: reduce) {
  .thread { animation: none; stroke-dashoffset: 0; }
  .point-star { animation: none; }
  .points { animation: points-fade 0.5s ease both; }
  .point.is-flare .point-halo { animation: none; }
}
</style>
