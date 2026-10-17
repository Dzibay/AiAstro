<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

defineProps({
  name: { type: String, required: true },
  tagline: { type: String, required: true },
})

const DARK = {
  sky: '#070707',
  line: '#f4ecd9',
  ink: '#f4ecd9',
  muted: '#cfc3aa',
  planet: '#101010',
}
const LIGHT = {
  sky: '#f7f2e6',
  line: '#8d6724',
  ink: '#2a2316',
  muted: '#6a5e49',
  planet: '#e6d5b4',
}

const figures = [
  {
    stars: [[0.055, 0.2], [0.105, 0.17], [0.155, 0.205], [0.1, 0.245], [0.2, 0.175], [0.255, 0.145], [0.305, 0.11]],
    edges: [[0, 1], [1, 2], [2, 3], [3, 0], [2, 4], [4, 5], [5, 6]],
  },
  {
    stars: [[0.68, 0.09], [0.745, 0.15], [0.815, 0.095], [0.885, 0.155], [0.95, 0.1]],
    edges: [[0, 1], [1, 2], [2, 3], [3, 4]],
  },
  {
    stars: [[0.04, 0.4], [0.09, 0.45], [0.15, 0.42], [0.21, 0.47], [0.09, 0.36], [0.1, 0.52]],
    edges: [[0, 1], [1, 2], [2, 3], [4, 1], [1, 5]],
  },
  {
    stars: [[0.76, 0.32], [0.9, 0.3], [0.78, 0.38], [0.84, 0.375], [0.9, 0.37], [0.77, 0.46], [0.91, 0.45]],
    edges: [[0, 2], [1, 4], [2, 3], [3, 4], [2, 5], [4, 6]],
  },
  {
    stars: [[0.34, 0.08], [0.39, 0.12], [0.36, 0.16], [0.42, 0.055]],
    edges: [[0, 1], [1, 2], [0, 2], [1, 3]],
  },
]

const craters = [
  { x: -0.22, y: -0.8, r: 0.028 },
  { x: 0.2, y: -0.86, r: 0.02 },
  { x: 0.04, y: -0.7, r: 0.036 },
  { x: -0.42, y: -0.74, r: 0.016 },
]

const field = makeField()
const stipple = makeStipple()

const section = ref(null)
const sky = ref(null)
const width = ref(0)
const height = ref(0)
const angle = ref(0)
const sink = ref(0)
const dragging = ref(false)

let reduceMotion = false
let resizeObserver
let visibilityObserver

const EVE = {
  sky: '#2a231c',
  line: '#e4d2ab',
  ink: '#f3ead8',
  muted: '#d9cbb3',
  planet: '#3a3228',
}

const light = computed(() => (Math.cos(angle.value) + 1) / 2)
const degrees = computed(() => {
  const turn = angle.value < 0 ? angle.value + Math.PI * 2 : angle.value
  return Math.round((turn * 180) / Math.PI) % 360
})

const theme = computed(() => ({
  '--sky': across('sky'),
  '--hero-line': across('line'),
  '--hero-ink': across('ink'),
  '--hero-muted': across('muted'),
  '--planet': across('planet'),
}))

const metrics = computed(() => {
  const w = width.value
  const h = height.value
  const top = Math.max(92, h * 0.11)
  const orbitR = Math.max(240, h * 0.52)
  const cy = top + orbitR + sink.value
  const visible = Math.min(Math.max(h * 0.2, 120), 200)
  const planetR = Math.max(orbitR * 0.92, w * 0.58)
  return {
    w,
    h,
    cx: w / 2,
    cy,
    orbitR,
    planetR,
    planetCy: h - visible + planetR + sink.value,
    unit: Math.min(Math.max(h / 820, 0.82), 1.25),
  }
})

const sun = computed(() => place(0))
const moon = computed(() => place(Math.PI))
const moonAngle = computed(() => {
  const dx = sun.value.x - moon.value.x
  const dy = sun.value.y - moon.value.y
  return (Math.atan2(dy, dx) * 180) / Math.PI
})

const ticks = computed(() => {
  const { cx, cy, orbitR } = metrics.value
  const marks = []
  for (let index = 0; index < 36; index += 1) {
    const turn = (index / 36) * Math.PI * 2
    const major = index % 3 === 0
    const inner = orbitR + 2
    const outer = orbitR + (major ? 11 : 6)
    marks.push({
      major,
      x1: cx + Math.sin(turn) * inner,
      y1: cy - Math.cos(turn) * inner,
      x2: cx + Math.sin(turn) * outer,
      y2: cy - Math.cos(turn) * outer,
    })
  }
  return marks
})

const placedFigures = computed(() =>
  figures.map((figure) => ({
    stars: figure.stars.map(([x, y]) => [x * width.value, y * height.value]),
    edges: figure.edges,
  })),
)

const placedField = computed(() =>
  field.map((star) => ({
    ...star,
    x: star.x * width.value,
    y: star.y * height.value,
  })),
)

const placedStipple = computed(() => {
  const { cx, planetCy, planetR } = metrics.value
  const sx = sun.value.x - cx
  const sy = sun.value.y - planetCy
  const length = Math.hypot(sx, sy) || 1
  const ux = sx / length
  const uy = sy / length
  return stipple.map((dot) => {
    const radial = Math.min(1, Math.hypot(dot.x, dot.y) / 0.95)
    const away = Math.max(0, -(dot.x * ux + dot.y * uy))
    return {
      cx: cx + dot.x * planetR,
      cy: planetCy + dot.y * planetR,
      r: 0.7 + dot.s * 1.15,
      opacity: 0.14 + radial * 0.42 + away * 0.4,
    }
  })
})

const placedCraters = computed(() => {
  const { cx, planetCy, planetR } = metrics.value
  return craters.map((crater) => ({
    cx: cx + crater.x * planetR,
    cy: planetCy + crater.y * planetR,
    r: crater.r * planetR,
  }))
})

const sunRays = computed(() =>
  Array.from({ length: 24 }, (_, index) => {
    const turn = (index / 24) * Math.PI * 2
    const long = index % 2 === 0
    return {
      x1: Math.cos(turn) * (long ? 15 : 16),
      y1: Math.sin(turn) * (long ? 15 : 16),
      x2: Math.cos(turn) * (long ? 34 : 23),
      y2: Math.sin(turn) * (long ? 34 : 23),
    }
  }),
)

const corona = computed(() =>
  Array.from({ length: 14 }, (_, index) => {
    const turn = (index / 14) * Math.PI * 2
    return { x: Math.cos(turn) * 40, y: Math.sin(turn) * 40 }
  }),
)

const parallels = [0.58, 0.74, 0.88]

function place(offset) {
  const { cx, cy, orbitR } = metrics.value
  const turn = angle.value + offset
  return {
    x: cx + orbitR * Math.sin(turn),
    y: cy - orbitR * Math.cos(turn),
  }
}

function figurePath(figure) {
  return figure.edges
    .map(([from, to]) => {
      const start = figure.stars[from]
      const end = figure.stars[to]
      return `M ${start[0]} ${start[1]} L ${end[0]} ${end[1]}`
    })
    .join(' ')
}

function burstLines(origin, radius) {
  return Array.from({ length: 8 }, (_, index) => {
    const turn = (index / 8) * Math.PI * 2 + 0.2
    const inner = index % 2 === 0 ? radius * 0.25 : radius * 0.45
    const outer = index % 2 === 0 ? radius : radius * 0.62
    return {
      x1: origin.x + Math.cos(turn) * inner,
      y1: origin.y + Math.sin(turn) * inner,
      x2: origin.x + Math.cos(turn) * outer,
      y2: origin.y + Math.sin(turn) * outer,
    }
  })
}

function mix(from, to, amount) {
  const left = rgb(from)
  const right = rgb(to)
  const channels = left.map((channel, index) =>
    Math.round(channel + (right[index] - channel) * amount),
  )
  return `rgb(${channels.join(' ')})`
}

function across(key) {
  const amount = light.value
  if (amount >= 0.5) return mix(EVE[key], LIGHT[key], (amount - 0.5) * 2)
  return mix(DARK[key], EVE[key], amount * 2)
}

function rgb(hex) {
  const value = Number.parseInt(hex.slice(1), 16)
  return [(value >> 16) & 255, (value >> 8) & 255, value & 255]
}

function measure() {
  if (!sky.value) return
  width.value = sky.value.clientWidth
  height.value = sky.value.clientHeight
}

function onScroll() {
  if (!section.value || reduceMotion) return
  const traveled = Math.min(Math.max(-section.value.getBoundingClientRect().top, 0), 140)
  sink.value = traveled * 0.16
}

function updateFromPointer(event) {
  const rect = sky.value.getBoundingClientRect()
  const { cx, cy } = metrics.value
  const x = event.clientX - rect.left - cx
  const y = event.clientY - rect.top - cy
  angle.value = Math.atan2(x, -y)
}

function startDrag(event) {
  if (event.button !== undefined && event.button !== 0) return
  dragging.value = true
  event.preventDefault()
  updateFromPointer(event)
  window.addEventListener('pointermove', updateFromPointer)
  window.addEventListener('pointerup', stopDrag)
}

function stopDrag() {
  dragging.value = false
  window.removeEventListener('pointermove', updateFromPointer)
  window.removeEventListener('pointerup', stopDrag)
}

function setFromSlider(event) {
  angle.value = (Number(event.target.value) * Math.PI) / 180
}

function paintSite() {
  const site = section.value?.closest('.site')
  if (!site) return
  for (const [key, value] of Object.entries(theme.value)) site.style.setProperty(key, value)
}

function clearSite() {
  const site = section.value?.closest('.site')
  if (!site) return
  for (const key of Object.keys(theme.value)) site.style.removeProperty(key)
}

function mulberry32(seed) {
  let state = seed
  return () => {
    state |= 0
    state = (state + 0x6d2b79f5) | 0
    let value = Math.imul(state ^ (state >>> 15), 1 | state)
    value = (value + Math.imul(value ^ (value >>> 7), 61 | value)) ^ value
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296
  }
}

function makeField() {
  const random = mulberry32(20261017)
  const stars = []
  for (let index = 0; index < 64; index += 1) {
    const x = 0.03 + random() * 0.94
    const y = 0.025 + random() * 0.46
    const roll = random()
    let kind = 'dot'
    if (roll > 0.94) kind = 'burst'
    else if (roll > 0.86) kind = 'ring'
    const radius = kind === 'burst' ? 7 + random() * 6 : roll > 0.8 ? 1.5 : roll > 0.45 ? 1.05 : 0.65
    stars.push({ x, y, r: radius, kind })
  }
  for (let index = 0; index < 28; index += 1) {
    stars.push({
      x: 0.3 + random() * 0.4,
      y: 0.2 + random() * 0.28,
      r: random() > 0.8 ? 1.15 : 0.7,
      kind: 'dot',
    })
  }
  return stars
}

function makeStipple() {
  const random = mulberry32(41)
  const dots = []
  let guard = 0
  while (dots.length < 240 && guard < 4000) {
    guard += 1
    const x = random() * 2 - 1
    const y = random() * 2 - 1
    if (x * x + y * y > 0.9) continue
    if (y > -0.15) continue
    dots.push({ x, y, s: random() })
  }
  return dots
}

watch(theme, () => paintSite())

onMounted(() => {
  reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  document.body.classList.add('home-sky', 'sky-live')
  measure()
  paintSite()
  resizeObserver = new ResizeObserver(() => measure())
  resizeObserver.observe(sky.value)
  visibilityObserver = new IntersectionObserver(
    ([entry]) => document.body.classList.toggle('sky-live', entry.isIntersecting),
    { threshold: 0, rootMargin: '-72px 0px -35% 0px' },
  )
  visibilityObserver.observe(section.value)
  window.addEventListener('scroll', onScroll, { passive: true })
})

onUnmounted(() => {
  stopDrag()
  resizeObserver?.disconnect()
  visibilityObserver?.disconnect()
  window.removeEventListener('scroll', onScroll)
  clearSite()
  document.body.classList.remove('home-sky', 'sky-live')
})
</script>

<template>
  <section ref="section" class="orbit-section" :class="{ dragging }" :style="theme">
    <div ref="sky" class="orbit-sky">
      <svg
        v-if="width"
        class="orbit-svg"
        :viewBox="`0 0 ${width} ${height}`"
        role="img"
        aria-label="Солнце и луна на орбите вокруг планеты"
      >
        <g class="sky-ink" fill="none">
          <g v-for="(figure, index) in placedFigures" :key="`figure-${index}`" class="figure">
            <path :d="figurePath(figure)" />
            <circle
              v-for="(star, starIndex) in figure.stars"
              :key="starIndex"
              class="star"
              :cx="star[0]"
              :cy="star[1]"
              r="1.7"
            />
          </g>

          <template v-for="(star, index) in placedField" :key="`field-${index}`">
            <circle v-if="star.kind === 'dot'" class="star" :cx="star.x" :cy="star.y" :r="star.r" />
            <circle v-else-if="star.kind === 'ring'" class="ring" :cx="star.x" :cy="star.y" :r="star.r + 2.2" />
            <g v-else class="burst">
              <line
                v-for="(ray, rayIndex) in burstLines(star, star.r)"
                :key="rayIndex"
                :x1="ray.x1"
                :y1="ray.y1"
                :x2="ray.x2"
                :y2="ray.y2"
              />
            </g>
          </template>

          <circle class="orbit-ring" :cx="metrics.cx" :cy="metrics.cy" :r="metrics.orbitR" />
          <line
            v-for="(tick, index) in ticks"
            :key="`tick-${index}`"
            :class="tick.major ? 'tick-major' : 'tick'"
            :x1="tick.x1"
            :y1="tick.y1"
            :x2="tick.x2"
            :y2="tick.y2"
          />
          <circle
            class="orbit-hit"
            :cx="metrics.cx"
            :cy="metrics.cy"
            :r="metrics.orbitR"
            @pointerdown="startDrag"
          />

          <g
            class="moon"
            :transform="`translate(${moon.x} ${moon.y}) rotate(${moonAngle}) scale(${metrics.unit * 1.35})`"
          >
            <circle class="moon-limb" r="20" />
            <circle class="moon-bite" r="16" cx="-8" />
            <circle class="stipple" cx="7" cy="-3" r="0.8" opacity="0.85" />
            <circle class="stipple" cx="5" cy="4" r="0.5" opacity="0.7" />
            <circle class="stipple" cx="9" cy="2.5" r="0.35" opacity="0.65" />
          </g>

          <g
            class="sun-handle"
            :transform="`translate(${sun.x} ${sun.y}) scale(${metrics.unit})`"
            @pointerdown="startDrag"
          >
            <circle class="sun-dotted" r="19" />
            <circle class="sun-core" r="12" />
            <line
              v-for="(ray, index) in sunRays"
              :key="`ray-${index}`"
              class="sun-ray"
              :x1="ray.x1"
              :y1="ray.y1"
              :x2="ray.x2"
              :y2="ray.y2"
            />
            <circle
              v-for="(dot, index) in corona"
              :key="`corona-${index}`"
              class="dust"
              :cx="dot.x"
              :cy="dot.y"
              r="0.7"
            />
            <circle class="sun-hit" r="52" />
          </g>

          <g class="planet-body">
            <circle class="planet-fill" :cx="metrics.cx" :cy="metrics.planetCy" :r="metrics.planetR" />
            <circle
              v-for="parallel in parallels"
              :key="parallel"
              class="planet-parallel"
              :cx="metrics.cx"
              :cy="metrics.planetCy"
              :r="metrics.planetR * parallel"
            />
            <circle
              v-for="(dot, index) in placedStipple"
              :key="`shade-${index}`"
              class="stipple"
              :cx="dot.cx"
              :cy="dot.cy"
              :r="dot.r"
              :opacity="dot.opacity"
            />
            <circle
              v-for="(crater, index) in placedCraters"
              :key="`crater-${index}`"
              class="crater"
              :cx="crater.cx"
              :cy="crater.cy"
              :r="crater.r"
            />
            <circle class="planet-limb-inner" :cx="metrics.cx" :cy="metrics.planetCy" :r="metrics.planetR - 8" />
            <circle class="planet-limb" :cx="metrics.cx" :cy="metrics.planetCy" :r="metrics.planetR" />
          </g>
        </g>
      </svg>
      <input
        class="sun-slider"
        type="range"
        min="0"
        max="359"
        :value="degrees"
        aria-label="Положение солнца. Вверху светло, внизу темно"
        @input="setFromSlider"
      />
    </div>
    <div class="orbit-copy">
      <div class="wrap orbit-copy-inner">
        <p class="orbit-hint">Потяните солнце: вверх день, вниз ночь</p>
        <p class="eyebrow">AI-астролог</p>
        <h1>{{ tagline }}</h1>
        <p class="lede">
          {{ name }} объясняет карту рождения обычным языком. Без гороскопа «для всех Овнов» на сегодня.
        </p>
        <RouterLink class="button" to="/login">Открыть кабинет</RouterLink>
      </div>
    </div>
  </section>
</template>
