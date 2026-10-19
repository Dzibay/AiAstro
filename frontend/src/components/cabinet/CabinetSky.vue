<script setup>
import { computed, onMounted, onUnmounted, ref, shallowRef, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { useSky } from '../../composables/useSky.js'
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
})

const { geo } = useSky()

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
  <nav class="cabinet-sky" :class="{ 'motion-off': reduce }" :style="{ height: `${view.H}px` }" aria-label="Разделы кабинета">
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

    <!-- Re-keyed by section under reduced motion: the points fade in at their new places instead of flying. -->
    <div :key="reduce ? section : 'points'" class="points">
      <RouterLink
        v-for="point in points"
        :key="point.id"
        class="point"
        :class="{ 'is-active': point.active, 'is-hot': point.id === hot }"
        :style="pointStyle(point)"
        :to="{ name: point.section.route }"
        :aria-label="`${point.section.label}: ${point.section.title}`"
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
        <span class="point-label">{{ point.section.label }}</span>
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

.points { position: absolute; inset: 0; }
/* The figure's centre sits on the point: the link is 96px wide and the figure 52px tall. */
.point {
  position: absolute;
  left: -48px;
  top: -26px;
  display: grid;
  justify-items: center;
  gap: 2px;
  width: 96px;
  padding-bottom: 4px;
  border-radius: 18px;
  color: rgba(242, 228, 200, 0.72);
  text-decoration: none;
  pointer-events: auto;
  transform-origin: 48px 26px;
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

.point:hover .point-halo, .point.is-hot .point-halo, .point.is-active .point-halo { opacity: 1; transform: scale(1); }
.point:hover line, .point.is-hot line, .point.is-active line { opacity: 0.7; }
.point:hover .point-star, .point.is-hot .point-star, .point.is-active .point-star { fill: #fff8e8; animation-duration: 1.6s; }
.point:hover .point-label, .point.is-hot .point-label, .point.is-active .point-label {
  color: #f6d99c;
  text-shadow: 0 0 12px rgba(255, 196, 110, 0.45), 0 0 2px rgba(4, 6, 12, 0.9);
}
.point:focus-visible .point-halo { opacity: 1; transform: scale(1); fill: rgba(255, 210, 140, 0.1); stroke: rgba(255, 226, 168, 0.6); stroke-width: 0.8; }

@keyframes thread-draw { to { stroke-dashoffset: 0; } }
@keyframes point-twinkle { 50% { opacity: 0.6; transform: scale(0.82); } }
@keyframes points-fade { from { opacity: 0; } }

@media (max-width: 760px) {
  .point-label { font-size: 15px; }
  /* A finger needs more than the figure: the link keeps its full 96px box. */
  .point { min-height: 76px; }
}

@media (prefers-reduced-motion: reduce) {
  .thread { animation: none; stroke-dashoffset: 0; }
  .point-star { animation: none; }
  .points { animation: points-fade 0.5s ease both; }
}
</style>
