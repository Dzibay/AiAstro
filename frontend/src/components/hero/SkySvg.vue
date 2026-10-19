<script setup>
import { computed } from 'vue'
import { angDiff, placeFigures } from './celestial.js'

const props = defineProps({
  layer: { type: String, default: 'all' },
  metrics: { type: Object, required: true },
  scene: { type: Object, required: true },
  sun: { type: Object, required: true },
  moon: { type: Object, required: true },
  hoverTheta: { type: Number, default: null },
  hotId: { type: String, default: '' },
  openId: { type: String, default: '' },
  pulse: { type: String, default: '' },
  dragging: { type: String, default: '' },
  compact: { type: Boolean, default: false },
  reduce: { type: Boolean, default: false },
  ready: { type: Boolean, default: false },
})

const emit = defineEmits(['dragstart', 'hot', 'toggle'])

const figures = computed(() => placeFigures(props.metrics.w, props.metrics.h, props.compact))

const ticks = computed(() => {
  const { cx, cy, orbitR } = props.metrics
  const marks = []
  for (let index = 0; index < 72; index += 1) {
    const theta = (index / 72) * Math.PI * 2
    const major = index % 6 === 0
    const inner = orbitR + 1
    const outer = orbitR + (major ? 12 : 6)
    const near =
      props.hoverTheta != null && angDiff(theta, props.hoverTheta) < (major ? 0.18 : 0.1)
    marks.push({
      major,
      near,
      x1: cx + Math.sin(theta) * inner,
      y1: cy - Math.cos(theta) * inner,
      x2: cx + Math.sin(theta) * outer,
      y2: cy - Math.cos(theta) * outer,
    })
  }
  return marks
})

const dust = [0.12, 0.37, 0.63, 0.81]

const orbitPath = computed(() => {
  const { cx, cy, orbitR } = props.metrics
  return `M ${cx} ${cy - orbitR} A ${orbitR} ${orbitR} 0 1 1 ${cx - 0.01} ${cy - orbitR}`
})

const circumference = computed(() => 2 * Math.PI * props.metrics.orbitR)

const sunRays = computed(() =>
  Array.from({ length: 18 }, (_, index) => {
    const theta = (index / 18) * Math.PI * 2
      const long = index % 2 === 0
      return {
        x1: Math.cos(theta) * 28,
        y1: Math.sin(theta) * 28,
        x2: Math.cos(theta) * (long ? 62 : 40),
        y2: Math.sin(theta) * (long ? 62 : 40),
      width: long ? 1.15 : 0.7,
    }
  }),
)

const moonFace = computed(() => {
  const dx = props.sun.x - props.moon.x
  const dy = props.sun.y - props.moon.y
  return (Math.atan2(dy, dx) * 180) / Math.PI
})

function showLabel(figure) {
  if (!figure.interactive) return false
  if (!props.compact) return true
  return props.hotId === figure.id || props.openId === figure.id
}

function onDrag(kind, event) {
  emit('dragstart', { kind, event })
}

function onToggle(figure, event) {
  if (event.button != null && event.button !== 0) return
  emit('toggle', figure.id)
}
</script>

<template>
  <svg
    v-if="layer !== 'bodies'"
    class="orbit-svg orbit-back"
    :viewBox="`0 0 ${metrics.w} ${metrics.h}`"
    :class="{ ready }"
  >
    <defs>
      <radialGradient id="astra-sun-face" cx="36%" cy="34%" r="70%">
        <stop offset="0%" stop-color="#fff7dc" />
        <stop offset="42%" stop-color="#ffc15a" />
        <stop offset="100%" stop-color="#e07c28" />
      </radialGradient>
      <radialGradient id="astra-sun-glow" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stop-color="#ffd27a" stop-opacity="0.95" />
        <stop offset="45%" stop-color="#ff9a3c" stop-opacity="0.28" />
        <stop offset="100%" stop-color="#ff9a3c" stop-opacity="0" />
      </radialGradient>
      <linearGradient id="astra-moon-face" gradientUnits="userSpaceOnUse" x1="18" y1="-4" x2="-8" y2="2">
        <stop offset="0%" stop-color="#fbf8f2" />
        <stop offset="48%" stop-color="#d5dbe3" />
        <stop offset="70%" stop-color="#8e99a8" />
        <stop offset="100%" stop-color="#1c2433" />
      </linearGradient>
      <filter id="astra-soft" x="-80%" y="-80%" width="260%" height="260%">
        <feGaussianBlur stdDeviation="5" />
      </filter>
      <filter id="astra-moon-soft" x="-100%" y="-100%" width="300%" height="300%">
        <feGaussianBlur stdDeviation="3.2" />
      </filter>
    </defs>

    <g
      v-for="figure in figures"
      :key="figure.id"
      class="constellation"
      :class="{
        'is-hot': hotId === figure.id || openId === figure.id,
        'is-open': openId === figure.id,
        'is-quiet': !figure.interactive,
      }"
      :role="figure.interactive ? 'button' : undefined"
      :tabindex="figure.interactive ? 0 : undefined"
      :aria-label="figure.interactive ? figure.name : undefined"
      :aria-expanded="figure.interactive ? openId === figure.id : undefined"
      @pointerenter="figure.interactive && emit('hot', figure.id)"
      @pointerleave="figure.interactive && emit('hot', '')"
      @pointerdown.stop="figure.interactive && onToggle(figure, $event)"
      @keydown.enter.prevent="figure.interactive && emit('toggle', figure.id)"
      @keydown.space.prevent="figure.interactive && emit('toggle', figure.id)"
    >
      <path
        v-for="edge in figure.edges"
        :key="`base-${edge.index}`"
        class="c-line"
        :d="edge.d"
      />
      <path
        v-for="edge in openId === figure.id ? figure.edges : []"
        :key="`draw-${edge.index}`"
        class="c-draw"
        :d="edge.d"
        :style="{
          strokeDasharray: edge.length,
          '--len': edge.length,
          animationDelay: `${edge.index * 70}ms`,
        }"
      />
      <circle
        v-for="edge in hotId === figure.id && !reduce ? figure.edges : []"
        :key="`pulse-${figure.id}-${edge.index}`"
        class="c-pulse"
        r="1.8"
        :style="{ offsetPath: `path('${edge.d}')`, animationDelay: `${edge.index * 90}ms` }"
      />
      <g v-for="(star, index) in figure.stars" :key="`star-${index}`">
        <circle class="c-glow" :cx="star.x" :cy="star.y" :r="star.r * 3.1" :opacity="0.18 + star.glow * 0.2" />
        <circle class="c-star" :cx="star.x" :cy="star.y" :r="star.r" />
        <path
          v-if="star.glow > 0.8"
          class="c-tick"
          :d="`M ${star.x - 5} ${star.y} L ${star.x + 5} ${star.y} M ${star.x} ${star.y - 5} L ${star.x} ${star.y + 5}`"
        />
      </g>
      <text
        v-if="showLabel(figure)"
        class="c-label"
        :x="figure.labelX"
        :y="figure.labelY"
        text-anchor="middle"
      >
        {{ figure.name }}
      </text>
      <path
        v-if="figure.interactive"
        class="c-hit"
        :d="figure.edges.map((edge) => edge.d).join(' ')"
      />
    </g>

    <g class="orbit-geom" aria-hidden="true">
      <circle
        class="orbit-line orbit-line-ghost"
        :cx="metrics.cx"
        :cy="metrics.cy"
        :r="metrics.orbitR + 8"
      />
      <circle
        class="orbit-line"
        :cx="metrics.cx"
        :cy="metrics.cy"
        :r="metrics.orbitR"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="ready || reduce ? 0 : circumference"
      />
      <line
        v-for="(tick, index) in ticks"
        :key="`tick-${index}`"
        :class="['orbit-tick', { major: tick.major, near: tick.near }]"
        :x1="tick.x1"
        :y1="tick.y1"
        :x2="tick.x2"
        :y2="tick.y2"
      />
      <circle
        v-for="(spot, index) in dust"
        :key="`dust-${index}`"
        class="orbit-dust"
        r="1.7"
        :style="{
          offsetPath: `path('${orbitPath}')`,
          animationDelay: `${index * -9}s`,
          animationDuration: `${36 + index * 7}s`,
        }"
      />
    </g>
    <circle
      class="orbit-hit"
      :cx="metrics.cx"
      :cy="metrics.cy"
      :r="metrics.orbitR"
      aria-hidden="true"
      @pointerdown="onDrag('orbit', $event)"
    />

  </svg>
  <svg
    v-if="layer !== 'scene'"
    class="orbit-svg orbit-front"
    :viewBox="`0 0 ${metrics.w} ${metrics.h}`"
    :class="{ ready }"
  >
    <defs>
      <radialGradient id="astra-sun-face-front" cx="36%" cy="34%" r="70%">
        <stop offset="0%" stop-color="#fff7dc" />
        <stop offset="42%" stop-color="#ffb03a" />
        <stop offset="100%" stop-color="#e06a1c" />
      </radialGradient>
      <radialGradient id="astra-sun-glow-front" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stop-color="#ffd27a" stop-opacity="0.95" />
        <stop offset="48%" stop-color="#ff9a3c" stop-opacity="0.35" />
        <stop offset="100%" stop-color="#ff9a3c" stop-opacity="0" />
      </radialGradient>
      <linearGradient id="astra-moon-face-front" gradientUnits="userSpaceOnUse" x1="26" y1="-6" x2="-12" y2="3">
        <stop offset="0%" stop-color="#fbf8f2" />
        <stop offset="48%" stop-color="#d5dbe3" />
        <stop offset="70%" stop-color="#8e99a8" />
        <stop offset="100%" stop-color="#1c2433" />
      </linearGradient>
      <filter id="astra-soft-front" x="-80%" y="-80%" width="260%" height="260%">
        <feGaussianBlur stdDeviation="5" />
      </filter>
      <filter id="astra-moon-soft-front" x="-100%" y="-100%" width="300%" height="300%">
        <feGaussianBlur stdDeviation="3.2" />
      </filter>
    </defs>
    <g
      class="moon"
      :class="{ 'is-hot': dragging === 'moon', 'is-pulse': pulse === 'moon' }"
      :transform="`translate(${moon.x} ${moon.y})`"
      role="button"
      tabindex="0"
      aria-label="Луна. Перетащите по орбите, чтобы сменить освещение"
      @pointerdown="onDrag('moon', $event)"
      @keydown.left.prevent="emit('dragstart', { kind: 'key', event: null, delta: -0.02 })"
      @keydown.right.prevent="emit('dragstart', { kind: 'key', event: null, delta: 0.02 })"
      @keydown.up.prevent="emit('dragstart', { kind: 'key', event: null, delta: 0.02 })"
      @keydown.down.prevent="emit('dragstart', { kind: 'key', event: null, delta: -0.02 })"
    >
      <circle class="moon-glow" r="34" :opacity="0.35 + scene.night * 0.5" filter="url(#astra-moon-soft-front)" />
      <g class="moon-fit" :transform="`scale(${metrics.unit})`">
        <g class="moon-disc">
          <g :transform="`rotate(${moonFace})`">
            <circle r="22" fill="url(#astra-moon-face-front)" />
            <circle r="22" fill="none" stroke="rgba(255,255,255,0.5)" stroke-width="0.7" />
          </g>
          <circle cx="4" cy="-3" r="1.5" class="moon-crater" />
          <circle cx="7" cy="3" r="0.9" class="moon-crater" />
          <circle cx="2" cy="5" r="0.6" class="moon-crater" />
          <circle cx="-2" cy="-6" r="0.7" class="moon-crater" />
        </g>
      </g>
      <circle class="body-hit" r="48" />
    </g>

    <g
      class="sun"
      :class="{ 'is-hot': dragging === 'sun', 'is-pulse': pulse === 'sun' }"
      :transform="`translate(${sun.x} ${sun.y})`"
      role="button"
      tabindex="0"
      aria-label="Солнце. Перетащите по орбите, чтобы сменить освещение"
      @pointerdown="onDrag('sun', $event)"
      @keydown.left.prevent="emit('dragstart', { kind: 'key', event: null, delta: -0.02 })"
      @keydown.right.prevent="emit('dragstart', { kind: 'key', event: null, delta: 0.02 })"
      @keydown.up.prevent="emit('dragstart', { kind: 'key', event: null, delta: 0.02 })"
      @keydown.down.prevent="emit('dragstart', { kind: 'key', event: null, delta: -0.02 })"
    >
      <circle class="sun-glow" r="74" filter="url(#astra-soft-front)" :opacity="0.7 + scene.horizon * 0.25" />
      <g class="sun-fit" :transform="`scale(${metrics.unit})`">
        <g class="sun-spin">
          <g class="sun-rays">
            <line
              v-for="(ray, index) in sunRays"
              :key="index"
              :x1="ray.x1"
              :y1="ray.y1"
              :x2="ray.x2"
              :y2="ray.y2"
              :stroke-width="ray.width"
            />
          </g>
          <g class="sun-body">
            <circle class="sun-corona" r="42" fill="url(#astra-sun-glow-front)" />
            <circle class="sun-photo" r="26" fill="url(#astra-sun-face-front)" stroke="#c45c16" stroke-width="1.4" />
            <circle class="sun-mottle" r="16" />
            <circle class="sun-core" r="9" />
          </g>
        </g>
      </g>
      <circle class="body-hit" r="56" />
    </g>
  </svg>
</template>
