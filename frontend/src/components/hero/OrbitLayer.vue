<script setup>
import { computed } from 'vue'
import { onOrbit, signedAngle } from './sky.js'

const props = defineProps({
  geo: { type: Object, required: true },
  sun: { type: Number, required: true },
  moon: { type: Number, required: true },
  active: { type: String, default: '' },
  emblemHot: { type: Boolean, default: false },
})

const BEADS = [-1.02, 0, 1.01, 1.19]
const LIMIT = 1.62

const orbit = computed(() => props.geo.orbit)
const planet = computed(() => props.geo.planet)
const u = computed(() => props.geo.u)

function near(theta, body, width) {
  return Math.exp(-((signedAngle(theta - body) / width) ** 2))
}

const ticks = computed(() => {
  const list = []
  const step = Math.PI / 90
  for (let i = -Math.round(LIMIT / step); i <= Math.round(LIMIT / step); i += 1) {
    const theta = i * step
    const major = i % 9 === 0
    const mid = !major && i % 3 === 0
    const len = (major ? 9 : mid ? 5.5 : 3) * u.value
    const a = onOrbit(orbit.value, theta, -1.5 * u.value)
    const b = onOrbit(orbit.value, theta, -1.5 * u.value - len)
    const glow = Math.max(near(theta, props.sun, 0.22), near(theta, props.moon, 0.22) * 0.8)
    list.push({ key: i, a, b, major, opacity: (major ? 0.5 : mid ? 0.32 : 0.18) + glow * 0.55 })
  }
  return list
})

const beads = computed(() => BEADS.map((theta) => {
  const point = onOrbit(orbit.value, theta)
  const glow = Math.max(near(theta, props.sun, 0.3), near(theta, props.moon, 0.3))
  return { theta, ...point, glow }
}))

/** Short glowing arc behind each body, built from fading segments. */
function trail(body, spread) {
  const parts = []
  const count = 18
  for (let i = -count; i < count; i += 1) {
    const a = body + (i / count) * spread
    const b = body + ((i + 1) / count) * spread
    const p = onOrbit(orbit.value, a)
    const q = onOrbit(orbit.value, b)
    const fade = 1 - Math.abs((i + 0.5) / count)
    parts.push({ key: i, d: `M${p.x} ${p.y}L${q.x} ${q.y}`, opacity: fade ** 1.6 })
  }
  return parts
}

// Discs match the shader radii (35/33 ref px) plus a hair so the ring tucks behind them.
const bodies = computed(() => [
  { key: 'sun', ...onOrbit(orbit.value, props.sun), r: 38 * u.value },
  { key: 'moon', ...onOrbit(orbit.value, props.moon), r: 35.5 * u.value },
])

const sunTrail = computed(() => trail(props.sun, 0.42))
const moonTrail = computed(() => trail(props.moon, 0.32))

const grid = computed(() => {
  const { cx, cy, r, top } = planet.value
  const lat = [124, 210, 330].map((depth) => r - depth * u.value)
  const emblem = { x: cx, y: top + 124 * u.value, r: 19 * u.value }
  const reach = Math.asin(Math.min(1, (props.geo.W / 2) / lat[0]))
  const a = { x: cx - lat[0] * Math.sin(reach), y: cy - lat[0] * Math.cos(reach) }
  const b = { x: cx + lat[0] * Math.sin(reach), y: a.y }
  const runner = `M${a.x} ${a.y}A${lat[0]} ${lat[0]} 0 0 1 ${b.x} ${b.y}`
  return { cx, cy, r, top, lat, emblem, runner }
})

function starPath(x, y, size) {
  const k = size * 0.22
  return `M${x} ${y - size}Q${x + k} ${y - k} ${x + size} ${y}Q${x + k} ${y + k} ${x} ${y + size}Q${x - k} ${y + k} ${x - size} ${y}Q${x - k} ${y - k} ${x} ${y - size}Z`
}
</script>

<template>
  <svg class="orbit-layer" :viewBox="`0 0 ${geo.W} ${geo.H}`" :width="geo.W" :height="geo.H" aria-hidden="true">
    <defs>
      <mask id="planet-cut" maskUnits="userSpaceOnUse" :x="0" :y="0" :width="geo.W" :height="geo.H">
        <rect :width="geo.W" :height="geo.H" fill="#fff" />
        <circle :cx="planet.cx" :cy="planet.cy" :r="planet.r + 2 * u" fill="#000" filter="url(#soft)" />
        <circle v-for="body in bodies" :key="body.key" :cx="body.x" :cy="body.y" :r="body.r" fill="#000" filter="url(#soft-body)" />
      </mask>
      <clipPath id="planet-clip">
        <circle :cx="planet.cx" :cy="planet.cy" :r="planet.r" />
      </clipPath>
      <filter id="soft" x="-5%" y="-5%" width="110%" height="110%">
        <feGaussianBlur :stdDeviation="3 * u" />
      </filter>
      <filter id="soft-body" x="-30%" y="-30%" width="160%" height="160%">
        <feGaussianBlur :stdDeviation="1.6 * u" />
      </filter>
      <filter id="bloom" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur :stdDeviation="2.4 * u" result="b" />
        <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
      </filter>
      <linearGradient id="grid-fade" gradientUnits="userSpaceOnUse" :x1="planet.cx - planet.r * 0.62" :x2="planet.cx + planet.r * 0.62" y1="0" y2="0">
        <stop offset="0" stop-color="#e6b867" stop-opacity="0" />
        <stop offset="0.3" stop-color="#e6b867" stop-opacity="0.55" />
        <stop offset="0.5" stop-color="#f3d39a" stop-opacity="0.85" />
        <stop offset="0.7" stop-color="#e6b867" stop-opacity="0.55" />
        <stop offset="1" stop-color="#e6b867" stop-opacity="0" />
      </linearGradient>
      <linearGradient id="meridian-fade" gradientUnits="userSpaceOnUse" x1="0" x2="0" :y1="grid.top" :y2="geo.H">
        <stop offset="0" stop-color="#f3d39a" stop-opacity="0.75" />
        <stop offset="1" stop-color="#e6b867" stop-opacity="0.15" />
      </linearGradient>
      <radialGradient id="emblem-fill">
        <stop offset="0" stop-color="#1a1408" stop-opacity="0.85" />
        <stop offset="1" stop-color="#0a0b10" stop-opacity="0.65" />
      </radialGradient>
    </defs>

    <g mask="url(#planet-cut)" class="orbit-rings" :class="{ 'is-active': active }">
      <circle class="ring ring-ghost" :cx="orbit.cx" :cy="orbit.cy" :r="orbit.r - 9 * u" />
      <circle class="ring ring-main" :cx="orbit.cx" :cy="orbit.cy" :r="orbit.r" />
      <line
        v-for="tick in ticks"
        :key="tick.key"
        class="tick"
        :x1="tick.a.x"
        :y1="tick.a.y"
        :x2="tick.b.x"
        :y2="tick.b.y"
        :style="{ opacity: tick.opacity }"
      />
      <g filter="url(#bloom)">
        <path v-for="part in sunTrail" :key="`s${part.key}`" class="trail trail-sun" :d="part.d" :style="{ opacity: part.opacity }" />
        <path v-for="part in moonTrail" :key="`m${part.key}`" class="trail trail-moon" :d="part.d" :style="{ opacity: part.opacity }" />
      </g>
      <g v-for="bead in beads" :key="bead.theta" class="bead" :style="{ '--glow': bead.glow }">
        <circle class="bead-halo" :cx="bead.x" :cy="bead.y" :r="7 * u" />
        <circle class="bead-core" :cx="bead.x" :cy="bead.y" :r="2.6 * u" />
      </g>
    </g>

    <g class="planet-grid" clip-path="url(#planet-clip)">
      <circle v-for="(r, index) in grid.lat" :key="r" class="lat" :class="`lat-${index}`" :cx="grid.cx" :cy="grid.cy" :r="r" stroke="url(#grid-fade)" />
      <path class="lat-runner" :d="grid.runner" pathLength="100" />
      <line class="meridian" :x1="grid.cx" :y1="grid.top" :x2="grid.cx" :y2="geo.H" stroke="url(#meridian-fade)" />
      <path
        v-for="side in [-1, 1]"
        :key="side"
        class="meridian meridian-curve"
        :d="`M${grid.cx + side * 2} ${grid.top}Q${grid.cx + side * 150 * u} ${grid.top + 160 * u} ${grid.cx + side * 260 * u} ${geo.H + 40 * u}`"
        stroke="url(#meridian-fade)"
      />
    </g>

    <g class="emblem" :class="{ 'is-hot': emblemHot }" filter="url(#bloom)">
      <circle class="emblem-pulse" :cx="grid.emblem.x" :cy="grid.emblem.y" :r="grid.emblem.r" />
      <circle class="emblem-ring" :cx="grid.emblem.x" :cy="grid.emblem.y" :r="grid.emblem.r" fill="url(#emblem-fill)" />
      <circle class="emblem-pulse emblem-pulse-late" :cx="grid.emblem.x" :cy="grid.emblem.y" :r="grid.emblem.r" />
      <path class="emblem-star" :d="starPath(grid.emblem.x, grid.emblem.y, grid.emblem.r * 0.62)" />
      <circle class="emblem-dot" :cx="grid.emblem.x" :cy="grid.emblem.y" :r="1.4 * u" />
    </g>
  </svg>
</template>

<style scoped>
.orbit-layer {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: visible;
}

.ring { fill: none; vector-effect: non-scaling-stroke; }
.ring-main { stroke: rgba(232, 204, 150, 0.55); stroke-width: 1.1; transition: stroke 0.4s ease; }
.ring-ghost { stroke: rgba(232, 204, 150, 0.14); stroke-width: 0.8; }
.orbit-rings.is-active .ring-main { stroke: rgba(244, 220, 170, 0.8); }
.tick { stroke: #e8cc96; stroke-width: 0.9; }

.trail { fill: none; stroke-linecap: round; }
.trail-sun { stroke: #ffc370; stroke-width: 2.2; }
.trail-moon { stroke: #b9cdf2; stroke-width: 1.6; }

.bead-halo { fill: #ffd27e; opacity: calc(0.12 + var(--glow) * 0.35); filter: blur(2px); }
.bead-core { fill: #ffe2a6; opacity: calc(0.75 + var(--glow) * 0.25); }

.lat { fill: none; stroke-width: 1; }
.lat-1 { opacity: 0.55; }
.lat-2 { opacity: 0.3; }
.lat-runner {
  fill: none;
  stroke: #fff0c8;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-dasharray: 6 194;
  opacity: 0.9;
  filter: drop-shadow(0 0 4px #ffcf7a);
  animation: run 9s linear infinite;
}
.meridian { fill: none; stroke-width: 1; opacity: 0.7; }
.meridian-curve { opacity: 0.28; }

.emblem-ring { stroke: #e9c27c; stroke-width: 1.1; }
.emblem-ring { transition: stroke-width 0.4s ease; }
.emblem-star {
  fill: #ffe7b0;
  transform-box: fill-box;
  transform-origin: center;
  transition: transform 0.8s cubic-bezier(0.3, 0.7, 0.2, 1);
}
.emblem.is-hot .emblem-star { transform: rotate(135deg) scale(1.12); }
.emblem.is-hot .emblem-ring { stroke-width: 1.6; }
.emblem-pulse-late { opacity: 0; animation-delay: 1.8s; }
.emblem.is-hot .emblem-pulse { animation-duration: 1.6s; stroke-width: 1.4; }
.emblem.is-hot .emblem-pulse-late { animation-delay: 0.8s; }
.emblem-dot { fill: #fff6dc; }
.emblem-pulse {
  fill: none;
  stroke: #f1cf8a;
  stroke-width: 1;
  transform-box: fill-box;
  transform-origin: center;
  animation: pulse 3.6s ease-out infinite;
}

@keyframes run { from { stroke-dashoffset: 6; } to { stroke-dashoffset: -100; } }
@keyframes pulse {
  0% { transform: scale(1); opacity: 0.7; }
  100% { transform: scale(2.4); opacity: 0; }
}

@media (prefers-reduced-motion: reduce) {
  .lat-runner, .emblem-pulse { animation: none; opacity: 0; }
}
</style>
