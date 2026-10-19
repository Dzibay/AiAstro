<script setup>
import { computed } from 'vue'
import { ZODIAC_ART } from './zodiacArt.js'

const props = defineProps({
  figures: { type: Array, required: true },
  geo: { type: Object, required: true },
  /** id → { sun, moon } closeness 0..1 */
  near: { type: Object, required: true },
  hot: { type: String, default: '' },
  open: { type: String, default: '' },
})
const emit = defineEmits(['hover', 'toggle'])

const u = computed(() => Math.max(props.geo.u, 0.6))

const drawn = computed(() => props.figures.map((figure) => {
  const lines = figure.edges.map(([from, to], index) => {
    const a = figure.stars[from]
    const b = figure.stars[to]
    const len = Math.hypot(b.x - a.x, b.y - a.y) || 1
    const ux = (b.x - a.x) / len
    const uy = (b.y - a.y) / len
    const ga = a.r + 3.5 * u.value
    const gb = b.r + 3.5 * u.value
    return {
      index,
      x1: a.x + ux * ga,
      y1: a.y + uy * ga,
      x2: b.x - ux * gb,
      y2: b.y - uy * gb,
      d: `M${a.x + ux * ga} ${a.y + uy * ga}L${b.x - ux * gb} ${b.y - uy * gb}`,
    }
  })
  const cluster = figure.stars.filter((star) => star.cluster)
  const haze = cluster.length
    ? {
        x: cluster.reduce((sum, star) => sum + star.x, 0) / cluster.length,
        y: cluster.reduce((sum, star) => sum + star.y, 0) / cluster.length,
      }
    : null
  // Art is drawn in the figure's 0..1000 box; map it onto the placed constellation.
  const map = ([x, y]) => `${(figure.cx + (x / 1000 - 0.5) * figure.span).toFixed(1)} ${(figure.cy + (y / 1000 - 0.5) * figure.span).toFixed(1)}`
  const art = (ZODIAC_ART[figure.id] || []).map((stroke, index) => ({
    index,
    kind: stroke.kind,
    d: `M${stroke.pts.map(map).join('L')}`,
  }))
  const closeness = props.near[figure.id] || { sun: 0, moon: 0 }
  return {
    ...figure,
    lines,
    art,
    artCount: art.length,
    haze,
    style: {
      '--sun-near': closeness.sun.toFixed(3),
      '--moon-near': closeness.moon.toFixed(3),
      '--near': Math.max(closeness.sun, closeness.moon).toFixed(3),
    },
  }
}))

function onKey(event, id) {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    emit('toggle', id)
  }
}
</script>

<template>
  <svg class="zodiac-layer" :class="{ 'has-open': open }" :viewBox="`0 0 ${geo.W} ${geo.H}`" :width="geo.W" :height="geo.H">
    <defs>
      <radialGradient id="star-halo">
        <stop offset="0" stop-color="#fff4dc" stop-opacity="0.9" />
        <stop offset="0.18" stop-color="#ffd9a0" stop-opacity="0.35" />
        <stop offset="0.55" stop-color="#d9a86a" stop-opacity="0.08" />
        <stop offset="1" stop-color="#d9a86a" stop-opacity="0" />
      </radialGradient>
      <radialGradient id="star-spike">
        <stop offset="0" stop-color="#fff8e8" stop-opacity="0.95" />
        <stop offset="0.4" stop-color="#ffe2b0" stop-opacity="0.25" />
        <stop offset="1" stop-color="#ffe2b0" stop-opacity="0" />
      </radialGradient>
      <radialGradient id="cluster-haze">
        <stop offset="0" stop-color="#a9c2ff" stop-opacity="0.28" />
        <stop offset="1" stop-color="#a9c2ff" stop-opacity="0" />
      </radialGradient>
      <filter id="art-glow" x="-10%" y="-10%" width="120%" height="120%">
        <feGaussianBlur stdDeviation="2.2" result="b" />
        <feColorMatrix in="b" type="matrix" values="1 0 0 0 0  0 0.8 0 0 0  0 0 0.45 0 0  0 0 0 0.9 0" result="g" />
        <feMerge><feMergeNode in="g" /><feMergeNode in="SourceGraphic" /></feMerge>
      </filter>
      <filter id="line-glow" x="-20%" y="-20%" width="140%" height="140%">
        <feGaussianBlur stdDeviation="1.6" result="b" />
        <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
      </filter>
    </defs>

    <g
      v-for="figure in drawn"
      :key="figure.id"
      class="figure"
      :class="{ 'is-hot': hot === figure.id, 'is-open': open === figure.id }"
      :style="figure.style"
      role="button"
      tabindex="0"
      :aria-label="`${figure.name}: открыть описание`"
      :aria-expanded="open === figure.id"
      @pointerenter="emit('hover', figure.id)"
      @pointerleave="emit('hover', '')"
      @focus="emit('hover', figure.id)"
      @blur="emit('hover', '')"
      @click="emit('toggle', figure.id)"
      @keydown="onKey($event, figure.id)"
    >
      <rect class="hit" :x="figure.box.x" :y="figure.box.y" :width="figure.box.w" :height="figure.box.h" :rx="16 * u" />

      <circle v-if="figure.haze" class="cluster-haze" :cx="figure.haze.x" :cy="figure.haze.y" :r="22 * u" fill="url(#cluster-haze)" />

      <g class="art" filter="url(#art-glow)">
        <path
          v-for="stroke in figure.art"
          :key="stroke.index"
          :class="`art-${stroke.kind}`"
          :d="stroke.d"
          pathLength="1"
          :style="{ '--i': stroke.index, '--n': figure.artCount }"
        />
      </g>

      <g class="lines">
        <line v-for="line in figure.lines" :key="line.index" :x1="line.x1" :y1="line.y1" :x2="line.x2" :y2="line.y2" />
      </g>
      <g class="lines-lit" filter="url(#line-glow)">
        <path v-for="line in figure.lines" :key="line.index" :d="line.d" pathLength="1" :style="{ '--i': line.index }" />
      </g>

      <g v-for="(star, index) in figure.stars" :key="star.name" class="star" :style="{ '--d': `${(index * 0.73) % 4}s` }">
        <title>{{ star.name }}</title>
        <circle class="star-halo" :cx="star.x" :cy="star.y" :r="star.r * 5.5" fill="url(#star-halo)" />
        <template v-if="star.mag < 2.1">
          <ellipse class="star-spike" :cx="star.x" :cy="star.y" :rx="star.r * 7" :ry="star.r * 0.45" fill="url(#star-spike)" />
          <ellipse class="star-spike" :cx="star.x" :cy="star.y" :rx="star.r * 0.45" :ry="star.r * 7" fill="url(#star-spike)" />
        </template>
        <circle class="star-core" :cx="star.x" :cy="star.y" :r="star.cluster ? star.r * 0.7 : star.r" />
      </g>

      <text class="label" :x="figure.labelX" :y="figure.labelY" :style="{ fontSize: `${Math.max(9, 10 * u)}px` }">
        {{ figure.name }}
      </text>
    </g>
  </svg>
</template>

<style scoped>
.zodiac-layer {
  position: absolute;
  inset: 0;
  overflow: visible;
  pointer-events: none;
}

.figure {
  pointer-events: auto;
  cursor: pointer;
  outline: none;
  --lift: max(var(--near), 0);
}
.hit { fill: transparent; }
.figure { transition: opacity 0.5s ease; }
.zodiac-layer.has-open .figure:not(.is-open) { opacity: 0.3; }

.lines line {
  stroke: color-mix(in srgb, #e3cfa6 calc(100% - var(--moon-near) * 60%), #b8ccf2);
  stroke-width: 0.8;
  stroke-linecap: round;
  opacity: calc(0.3 + var(--lift) * 0.45);
  transition: opacity 0.4s ease;
}

.lines-lit path {
  fill: none;
  stroke: #ffe1a3;
  stroke-width: 1.3;
  stroke-linecap: round;
  stroke-dasharray: 1 1;
  stroke-dashoffset: 1;
  opacity: 0;
  transition: stroke-dashoffset 0.55s cubic-bezier(0.3, 0.7, 0.2, 1) calc(var(--i) * 70ms), opacity 0.3s ease;
}
.figure.is-hot .lines-lit path,
.figure.is-open .lines-lit path {
  stroke-dashoffset: 0;
  opacity: 0.95;
}
.figure.is-hot .lines line,
.figure.is-open .lines line { opacity: 0.15; }

.art path {
  fill: none;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-dasharray: 1 1;
  stroke-dashoffset: 1;
  opacity: 0;
  /* Leaving is quick and all at once; drawing in is staggered below. */
  transition: stroke-dashoffset 0.35s ease, opacity 0.35s ease, fill 0.4s ease;
}
.art .art-outline { stroke: #f0cf8e; stroke-width: 1.15; }
.art .art-detail { stroke: #e6c17e; stroke-width: 0.8; }
.art .art-hatch { stroke: #d8b274; stroke-width: 0.6; }
.figure.is-open .art path {
  stroke-dashoffset: 0;
  transition:
    stroke-dashoffset 1.1s cubic-bezier(0.45, 0.1, 0.25, 1) calc(var(--i) / var(--n) * 900ms + 250ms),
    opacity 0.3s ease calc(var(--i) / var(--n) * 900ms + 250ms),
    fill 1.2s ease 1.6s;
}
.figure.is-open .art-outline { opacity: 0.92; fill: rgba(255, 214, 140, 0.035); }
.figure.is-open .art-detail { opacity: 0.6; }
.figure.is-open .art-hatch { opacity: 0.38; }

.star-halo {
  opacity: calc(0.45 + var(--lift) * 0.5);
  transform-box: fill-box;
  transform-origin: center;
  animation: twinkle 4.2s ease-in-out var(--d) infinite;
  transition: opacity 0.4s ease;
}
.star-spike {
  opacity: calc(0.55 + var(--lift) * 0.45);
  transform-box: fill-box;
  transform-origin: center;
  animation: twinkle 5.4s ease-in-out var(--d) infinite;
}
.star-core {
  fill: color-mix(in srgb, #fff6e2 calc(100% - var(--moon-near) * 50%), #dbe6ff);
  filter: drop-shadow(0 0 2px rgba(255, 226, 170, 0.9));
  transform-box: fill-box;
  transform-origin: center;
  transition: transform 0.35s ease;
}
.figure.is-hot .star-core,
.figure.is-open .star-core { transform: scale(1.35); }
.figure.is-hot .star-halo,
.figure.is-open .star-halo { opacity: 1; }
.cluster-haze { opacity: calc(0.7 + var(--lift) * 0.3); }

.label {
  fill: #d9ccb4;
  opacity: calc(0.55 + var(--lift) * 0.3);
  font-family: var(--sans);
  letter-spacing: 0.34em;
  text-transform: uppercase;
  text-anchor: middle;
  transition: opacity 0.3s ease, fill 0.3s ease;
}
.figure.is-hot .label,
.figure.is-open .label,
.figure:focus-visible .label { fill: #ffe2a8; opacity: 1; }
.figure:focus-visible .hit { stroke: rgba(255, 226, 168, 0.4); stroke-dasharray: 3 4; }

@keyframes twinkle {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(0.82); }
}

@media (prefers-reduced-motion: reduce) {
  .star-halo, .star-spike { animation: none; }
  .lines-lit path, .art path, .figure.is-open .art path { transition: opacity 0.2s ease; }
}
</style>
