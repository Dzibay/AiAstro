<script setup>
import { computed, onBeforeMount, onMounted, onUnmounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import CosmosCanvas from './hero/CosmosCanvas.vue'
import OrbitLayer from './hero/OrbitLayer.vue'
import ConstellationLayer from './hero/ConstellationLayer.vue'
import { useSession } from '../composables/useSession.js'
import { useSkyFocus } from '../composables/useSkyFocus.js'
import {
  MOON_OFFSET,
  SUN_HOME,
  SUN_MAX,
  SUN_MIN,
  angleAt,
  clamp,
  layout,
  onOrbit,
  signedAngle,
  warmthOf,
} from './hero/sky.js'
import { LAST_STOP, STOPS, framed, placeBand, sceneAt } from './hero/journey.js'

const STORE_KEY = 'astra-sun'

const { webToken } = useSession()
const chartTo = computed(() => (webToken.value ? '/cabinet' : '/login'))

const sky = ref(null)
const size = ref({ w: 1280, h: 720 })
const theta = ref(SUN_HOME)
const dragging = ref('')
const hover = ref({ sun: 0, moon: 0 })
const hoverTarget = { sun: 0, moon: 0 }
const nearRing = ref(false)
const hotId = ref('')
const openId = ref('')
const emblemHot = ref(false)
const webgl = ref(true)
const reduce = ref(false)
const high = ref(true)
/** Scroll position as a float stop index, see journey.js. */
const journey = ref(0)

let raf = 0
let observer
let target = SUN_HOME
let velocity = 0
let grabOffset = 0
let lastPointer = { angle: 0, time: 0 }
let intro = 0
let introFrom = SUN_HOME
let introStart = 0
let releaseListeners = null
/** Per stop: the scroll range where the sky rests on it. */
let rests = []
let openedAt = 0
let travelling = false

const geo = computed(() => layout(size.value.w, size.value.h))
const scene = computed(() => sceneAt(geo.value, journey.value, theta.value))
const frame = computed(() => scene.value.frame)
// The forecast preview can turn the Sun and Moon a little, but only while the sky rests there.
const { skyTurn, skyTurning } = useSkyFocus()
const FORECASTS = STOPS.findIndex((stop) => stop.id === 'forecasts')
const bodyTheta = computed(() => {
  const near = Math.max(0, 1 - Math.abs(journey.value - FORECASTS) * 2)
  return scene.value.theta + skyTurn.value * near
})
const sun = computed(() => framed(frame.value, onOrbit(geo.value.orbit, bodyTheta.value)))
const moon = computed(() => framed(frame.value, onOrbit(geo.value.orbit, bodyTheta.value + MOON_OFFSET)))
const warm = computed(() => warmthOf(bodyTheta.value))
const figures = computed(() => placeBand(geo.value))
const planet = computed(() => {
  const { planet: p } = geo.value
  const c = framed(frame.value, { x: p.cx, y: p.cy })
  return { cx: c.x, cy: c.y, r: p.r * frame.value.s, top: c.y - p.r * frame.value.s }
})
/** The Sun and Moon can be dragged only where the planet sits at home: the hero and the finale. */
const interactive = computed(() => journey.value < 0.12 || journey.value > LAST_STOP - 0.12)
const atEnd = computed(() => journey.value > LAST_STOP - 0.5)

function altitude(point) {
  const p = planet.value
  return (Math.hypot(point.x - p.cx, point.y - p.cy) - p.r) / (geo.value.u * frame.value.s)
}

const sunUp = computed(() => altitude(sun.value) > -20)
const moonUp = computed(() => altitude(moon.value) > -20)

const near = computed(() => {
  const reach = 340 * geo.value.u
  const sunVis = clamp((altitude(sun.value) + 70) / 100, 0, 1)
  const moonVis = clamp((altitude(moon.value) + 70) / 100, 0, 1)
  const pan = scene.value.pan
  return Object.fromEntries(figures.value.map((figure) => {
    const ds = Math.hypot(sun.value.x - figure.cx - pan, sun.value.y - figure.cy)
    const dm = Math.hypot(moon.value.x - figure.cx - pan, moon.value.y - figure.cy)
    return [figure.key, {
      sun: Math.exp(-((ds / reach) ** 2)) * sunVis,
      moon: Math.exp(-((dm / reach) ** 2)) * moonVis * 0.85,
    }]
  }))
})

const sceneStyle = computed(() => {
  const { u, orbit } = geo.value
  const k = clamp(u, 0.78, 1.2)
  return {
    '--u': u,
    '--k': k,
    '--copy-top': `${geo.value.narrow ? 96 : orbit.cy - orbit.r + 100 * u}px`,
    '--warm': warm.value.toFixed(3),
  }
})

const orbitStyle = computed(() => {
  const { s, tx, ty } = frame.value
  return { transform: `translate(${tx.toFixed(1)}px, ${ty.toFixed(1)}px) scale(${s.toFixed(4)})` }
})

function bodyStyle(point, radius) {
  const d = radius * 2 * geo.value.u * frame.value.s + 24
  return { left: `${point.x - d / 2}px`, top: `${point.y - d / 2}px`, width: `${d}px`, height: `${d}px` }
}

const sunHit = computed(() => bodyStyle(sun.value, 35))
const moonHit = computed(() => bodyStyle(moon.value, 33))

const openFigure = computed(() => figures.value.find((figure) => figure.key === openId.value) || null)
const cardStyle = computed(() => {
  const figure = openFigure.value
  if (!figure) return null
  const width = Math.min(344, geo.value.W - 32)
  const cx = figure.cx + scene.value.pan
  const leftSide = cx < geo.value.W / 2
  // The drawn animal reaches past its stars, so keep clear of ~0.62 of its box.
  const reach = figure.span * 0.62 + 18
  let left = leftSide ? cx + reach : cx - reach - width
  if (geo.value.narrow) left = (geo.value.W - width) / 2
  left = clamp(left, 16, geo.value.W - width - 16)
  const top = geo.value.narrow ? 84 : clamp(figure.cy - 190, 84, geo.value.H - 440)
  return { left: `${left}px`, top: `${top}px`, width: `${width}px`, '--from': leftSide ? '-14px' : '14px' }
})

const phaseLabel = computed(() => {
  if (warm.value > 0.72) return 'Солнце в силе: тёплая атмосфера'
  if (warm.value < 0.28) return 'Луна в силе: ночная атмосфера'
  return 'Равновесие Солнца и Луны'
})

const emblemStyle = computed(() => {
  const { planet: p, u } = geo.value
  const c = framed(frame.value, { x: p.cx, y: p.top + 124 * u })
  const r = Math.max(18, 26 * u * frame.value.s)
  return { left: `${c.x - r}px`, top: `${c.y - r}px`, width: `${2 * r}px`, height: `${2 * r}px` }
})

/** The emblem on the planet always leads on: to the next stop, and from the finale back to the top. */
function scrollNext() {
  const next = atEnd.value ? 0 : Math.min(Math.round(journey.value) + 1, LAST_STOP)
  const top = next === 0 ? 0 : rests[next]?.[0]
  if (top == null) return
  window.scrollTo({ top, behavior: reduce.value ? 'auto' : 'smooth' })
}

function measureStops() {
  const vh = window.innerHeight
  const max = document.documentElement.scrollHeight - vh
  rests = [...document.querySelectorAll('[data-sky-stop]')].map((node) => {
    const rect = node.getBoundingClientRect()
    const top = Math.min(rect.top + window.scrollY, max)
    return [top, Math.min(top + Math.max(0, rect.height - vh), max)]
  })
}

/** Rests on a stop while its section fills the screen, and travels while two sections share it. */
function journeyAt(y) {
  for (let i = 0; i < rests.length; i += 1) {
    const [a, b] = rests[i]
    if (y > b) continue
    if (y >= a || i === 0) return i
    const from = rests[i - 1][1]
    return i - 1 + clamp((y - from) / Math.max(1, a - from), 0, 1)
  }
  return Math.max(rests.length - 1, 0)
}

function follow() {
  const exact = journeyAt(window.scrollY)
  const goal = reduce.value ? Math.round(exact) : exact
  const gap = goal - journey.value
  travelling = Math.abs(gap) > 1e-4
  // A light lag gives the sky some weight against the page.
  if (gap) journey.value = travelling && !reduce.value ? journey.value + gap * 0.2 : goal
  if (openId.value && Math.abs(journey.value - openedAt) > 0.2) openId.value = ''
}

/** Read by the WebGL canvas once per frame. */
function canvasState() {
  const { W, H, u } = geo.value
  return {
    width: W,
    height: H,
    u,
    bodyU: u * frame.value.s,
    pan: scene.value.pan,
    // The second Milky Way crossing, through Sagittarius at the forecasts stop.
    band2: W * (0.5 - 3),
    sun: sun.value,
    moon: moon.value,
    planet: planet.value,
    warm: warm.value,
    sunHover: hover.value.sun,
    moonHover: hover.value.moon,
    intro,
    high: high.value,
    busy: Boolean(dragging.value) || Math.abs(velocity) > 1e-5 || intro < 1 || travelling || skyTurning.value,
    still: reduce.value,
  }
}

function measure() {
  if (!sky.value) return
  size.value = { w: sky.value.clientWidth, h: sky.value.clientHeight }
  measureStops()
}

function softClamp(value) {
  if (value < SUN_MIN) return SUN_MIN - (1 - Math.exp(-(SUN_MIN - value) * 4)) * 0.06
  if (value > SUN_MAX) return SUN_MAX + (1 - Math.exp(-(value - SUN_MAX) * 4)) * 0.06
  return value
}

function tick(now) {
  raf = requestAnimationFrame(tick)
  follow()
  if (intro < 1) {
    intro = reduce.value ? 1 : clamp((now - introStart) / 2400, 0, 1)
    if (!dragging.value) {
      const e = 1 - (1 - intro) ** 3
      theta.value = introFrom + (target - introFrom) * e
    }
  } else if (dragging.value) {
    // Critically damped follow keeps the body heavy but responsive.
    const next = theta.value + (target - theta.value) * 0.32
    velocity = next - theta.value
    theta.value = next
  } else if (Math.abs(velocity) > 1e-5 || theta.value < SUN_MIN || theta.value > SUN_MAX) {
    let next = theta.value + velocity
    velocity *= 0.93
    if (next < SUN_MIN) {
      next += (SUN_MIN - next) * 0.2
      velocity *= 0.6
    } else if (next > SUN_MAX) {
      next += (SUN_MAX - next) * 0.2
      velocity *= 0.6
    }
    if (Math.abs(velocity) < 1e-5 && (next < SUN_MIN || next > SUN_MAX)) next = clamp(next, SUN_MIN, SUN_MAX)
    theta.value = next
  }
  for (const key of ['sun', 'moon']) {
    const current = hover.value[key]
    const goal = dragging.value === key ? 1 : hoverTarget[key]
    if (Math.abs(goal - current) > 0.002) hover.value = { ...hover.value, [key]: current + (goal - current) * 0.16 }
  }
}

function pointerAngle(event) {
  const rect = sky.value.getBoundingClientRect()
  return angleAt(geo.value.orbit, event.clientX - rect.left, event.clientY - rect.top)
}

function startDrag(kind, event, jump = false) {
  if (event.button != null && event.button !== 0) return
  event.preventDefault()
  intro = 1
  const body = kind === 'sun' ? theta.value : theta.value + MOON_OFFSET
  const angle = pointerAngle(event)
  grabOffset = jump ? 0 : signedAngle(body - angle)
  dragging.value = kind
  target = theta.value
  velocity = 0
  lastPointer = { angle, time: performance.now() }
  document.body.classList.add('is-dragging-sky')
  onDragMove(event)
  releaseListeners?.()
  window.addEventListener('pointermove', onDragMove, { passive: false })
  window.addEventListener('pointerup', stopDrag)
  window.addEventListener('pointercancel', stopDrag)
  releaseListeners = () => {
    window.removeEventListener('pointermove', onDragMove)
    window.removeEventListener('pointerup', stopDrag)
    window.removeEventListener('pointercancel', stopDrag)
  }
}

function onDragMove(event) {
  if (!dragging.value) return
  if (event.cancelable) event.preventDefault()
  const angle = pointerAngle(event)
  let body = angle + grabOffset
  if (dragging.value === 'moon') body -= MOON_OFFSET
  // Unwrap so a drag across the bottom never flips the sun to the far end.
  body = theta.value + signedAngle(body - theta.value)
  target = softClamp(body)
  lastPointer = { angle, time: performance.now() }
}

function stopDrag() {
  if (!dragging.value) return
  dragging.value = ''
  document.body.classList.remove('is-dragging-sky')
  releaseListeners?.()
  releaseListeners = null
  if (reduce.value) velocity = 0
  else velocity = clamp(velocity, -0.03, 0.03)
  try {
    sessionStorage.setItem(STORE_KEY, String(clamp(theta.value + velocity * 12, SUN_MIN, SUN_MAX)))
  } catch {
    /* private mode */
  }
}

function onSkyDown(event) {
  const node = event.target
  if (!(node instanceof Element)) return
  if (node.closest('a, button, input, .figure, .zodiac-card')) return
  openId.value = ''
  if (!interactive.value || !nearOrbit(event)) return
  const angle = pointerAngle(event)
  const ds = Math.abs(signedAngle(angle - theta.value))
  const dm = Math.abs(signedAngle(angle - theta.value - MOON_OFFSET))
  startDrag(ds <= dm ? 'sun' : 'moon', event, true)
}

function nearOrbit(event) {
  const rect = sky.value.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top
  const { orbit, planet } = geo.value
  const ring = Math.abs(Math.hypot(x - orbit.cx, y - orbit.cy) - orbit.r)
  const abovePlanet = Math.hypot(x - planet.cx, y - planet.cy) > planet.r
  return ring < 22 && abovePlanet
}

function onSkyMove(event) {
  if (dragging.value || event.pointerType === 'touch') return
  nearRing.value = interactive.value && nearOrbit(event)
}

function onBodyKey(event) {
  const step = event.shiftKey ? 0.2 : 0.05
  let delta = 0
  if (event.key === 'ArrowLeft' || event.key === 'ArrowDown') delta = -step
  if (event.key === 'ArrowRight' || event.key === 'ArrowUp') delta = step
  if (event.key === 'Home') delta = SUN_MIN - theta.value
  if (event.key === 'End') delta = SUN_MAX - theta.value
  if (!delta) return
  event.preventDefault()
  intro = 1
  velocity = 0
  theta.value = clamp(theta.value + delta, SUN_MIN, SUN_MAX)
  target = theta.value
}

function toggleFigure(key) {
  openId.value = openId.value === key ? '' : key
  openedAt = journey.value
}

function onKey(event) {
  if (event.key === 'Escape') openId.value = ''
}

onBeforeMount(() => {
  document.body.classList.add('home-sky')
  try {
    const saved = Number(sessionStorage.getItem(STORE_KEY))
    if (sessionStorage.getItem(STORE_KEY) && Number.isFinite(saved)) target = clamp(saved, SUN_MIN, SUN_MAX)
  } catch {
    /* private mode */
  }
})

onMounted(() => {
  reduce.value = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const cores = navigator.hardwareConcurrency || 8
  const memory = navigator.deviceMemory || 8
  high.value = !(cores <= 4 || memory <= 4 || navigator.connection?.saveData || window.innerWidth < 760)
  measure()
  introFrom = target - 0.55
  theta.value = reduce.value ? target : introFrom
  introStart = performance.now()
  observer = new ResizeObserver(measure)
  observer.observe(sky.value)
  // Sections change height as fonts and content load.
  document.querySelectorAll('[data-sky-stop]').forEach((node) => observer.observe(node))
  window.addEventListener('resize', measureStops, { passive: true })
  window.addEventListener('keydown', onKey)
  measureStops()
  journey.value = journeyAt(window.scrollY)
  raf = requestAnimationFrame(tick)
})

onUnmounted(() => {
  stopDrag()
  cancelAnimationFrame(raf)
  observer?.disconnect()
  window.removeEventListener('resize', measureStops)
  window.removeEventListener('keydown', onKey)
  document.body.classList.remove('home-sky', 'is-dragging-sky')
})
</script>

<template>
  <div
    ref="sky"
    class="sky-stage"
    :class="{ 'is-dragging': dragging, 'near-ring': nearRing, 'no-webgl': !webgl, 'motion-off': reduce }"
    :style="sceneStyle"
    @pointerdown="onSkyDown"
    @pointermove="onSkyMove"
  >
    <CosmosCanvas v-if="webgl" :state="canvasState" @unsupported="webgl = false" />

    <OrbitLayer
      :geo="geo"
      :sun="bodyTheta"
      :moon="bodyTheta + MOON_OFFSET"
      :active="dragging"
      :emblem-hot="emblemHot"
      :style="orbitStyle"
    />
    <ConstellationLayer
      :figures="figures"
      :geo="geo"
      :near="near"
      :pan="scene.pan"
      :hot="hotId"
      :open="openId"
      @hover="hotId = $event"
      @toggle="toggleFigure"
    />

    <button
      type="button"
      class="body-hit"
      :class="{ 'is-set': !sunUp || !interactive }"
      :style="sunHit"
      aria-label="Солнце. Стрелками или перетаскиванием двигайте по орбите"
      @pointerdown="startDrag('sun', $event)"
      @pointerenter="hoverTarget.sun = 1"
      @pointerleave="hoverTarget.sun = 0"
      :tabindex="interactive ? 0 : -1"
      @keydown="onBodyKey"
    />
    <button
      type="button"
      class="body-hit"
      :class="{ 'is-set': !moonUp || !interactive }"
      :style="moonHit"
      aria-label="Луна. Стрелками или перетаскиванием двигайте по орбите"
      @pointerdown="startDrag('moon', $event)"
      @pointerenter="hoverTarget.moon = 1"
      @pointerleave="hoverTarget.moon = 0"
      :tabindex="interactive ? 0 : -1"
      @keydown="onBodyKey"
    />

    <button
      type="button"
      class="emblem-btn"
      :class="{ 'is-hot': emblemHot }"
      :style="emblemStyle"
      :aria-label="atEnd ? 'Наверх, к началу' : 'Листайте к следующему разделу'"
      @pointerenter="emblemHot = true"
      @pointerleave="emblemHot = false"
      @focus="emblemHot = true"
      @blur="emblemHot = false"
      @click="scrollNext"
    >
      <span class="emblem-label" :class="{ 'is-up': atEnd }" aria-hidden="true">
        {{ atEnd ? 'Наверх' : 'Листайте' }}
        <svg viewBox="0 0 12 16"><path d="M6 2v11M2 9l4 4 4-4" /></svg>
      </span>
    </button>
  </div>

  <section class="hero" data-sky-stop="hero" :style="sceneStyle">
    <div class="hero-copy" :class="{ 'is-dimmed': openFigure && openFigure.stop === 0 }">
      <p class="kicker">Твоя личная карта</p>
      <div class="ornament" aria-hidden="true">
        <span class="ornament-line" />
        <span class="ornament-dot" />
        <svg viewBox="0 0 20 20" class="ornament-star"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg>
        <span class="ornament-dot" />
        <span class="ornament-line" />
      </div>
      <h1>Астрология<br />нового поколения</h1>
      <p class="sub">Глубокий анализ вашей натальной карты <br />и точные прогнозы на будущее с помощью ИИ</p>
      <RouterLink class="cta" :to="chartTo">
        <span>Узнать свою карту</span>
        <svg class="cta-arrow" viewBox="0 0 16 16" aria-hidden="true"><path d="M2 8h11M9 4l4 4-4 4" /></svg>
      </RouterLink>
      <p class="hint">
        <svg class="hint-icon" viewBox="0 0 28 30" aria-hidden="true">
          <path d="M23 3C26 12 20 22 7 25" />
          <path d="M11 20.5 6.5 25.2 12 28" />
          <path d="M19.5 6.5 23 2.5 26.5 6.8" />
        </svg>
        <span>Перемещайте Солнце и Луну, <br />чтобы изменить тему</span>
      </p>
      <p class="sr-only" aria-live="polite">{{ phaseLabel }}</p>
    </div>

    <aside class="note note-left">
      <span class="note-icon" aria-hidden="true">
        <svg viewBox="0 0 20 20"><path d="M10 1Q11 9 19 10Q11 11 10 19Q9 11 1 10Q9 9 10 1Z" /></svg>
      </span>
      <span class="note-text">
        <strong>Натальная карта</strong>
        <span>Ваш уникальный путь<br />и потенциал</span>
      </span>
    </aside>
    <aside class="note note-right">
      <span class="note-icon" aria-hidden="true">
        <svg viewBox="0 0 20 20" class="compass">
          <circle cx="10" cy="10" r="6.2" />
          <path d="M10 2.5v15M2.5 10h15" />
          <path class="fill" d="M10 5.5 11.2 10 10 14.5 8.8 10Z" />
        </svg>
      </span>
      <span class="note-text">
        <strong>Прогнозы</strong>
        <span>Важные события<br />и возможности</span>
      </span>
    </aside>

  </section>

  <Transition name="card">
    <div v-if="openFigure && cardStyle" :key="openFigure.key" class="zodiac-card" :style="cardStyle" role="dialog" :aria-label="openFigure.name">
      <span class="card-sheen" aria-hidden="true" />
      <button type="button" class="card-close" aria-label="Закрыть" @click="openId = ''">
        <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 4l8 8M12 4l-8 8" /></svg>
      </button>
      <div class="card-head">
        <span class="card-glyph" aria-hidden="true">
          <span class="card-glyph-orbit" />
          {{ openFigure.glyph }}
        </span>
        <div>
          <p class="card-kicker">Знак зодиака · {{ openFigure.animal }}</p>
          <p class="card-name">{{ openFigure.name }}</p>
          <p class="card-dates">{{ openFigure.dates }}</p>
        </div>
      </div>
      <ul class="card-traits">
        <li v-for="trait in openFigure.traits" :key="trait">{{ trait }}</li>
      </ul>
      <p class="card-text">{{ openFigure.text }}</p>
      <p class="card-myth">{{ openFigure.myth }}</p>
      <dl class="card-facts">
        <div><dt>Стихия</dt><dd>{{ openFigure.element }}</dd></div>
        <div><dt>Крест</dt><dd>{{ openFigure.modality }}</dd></div>
        <div><dt>Управитель</dt><dd>{{ openFigure.ruler }}</dd></div>
        <div><dt>Ярчайшая звезда</dt><dd>{{ openFigure.alpha }}</dd></div>
      </dl>
      <RouterLink class="card-cta" :to="chartTo">
        <span>Узнать свою карту</span>
        <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3 8h9M8.5 4.5 12 8l-3.5 3.5" /></svg>
      </RouterLink>
    </div>
  </Transition>
</template>

<style scoped>
/* The sky stays put for the whole page; sections scroll over it. */
.sky-stage {
  position: fixed;
  z-index: 0;
  top: 0;
  left: 0;
  width: 100%;
  height: 100vh;
  height: 100lvh;
  min-height: 620px;
  overflow: hidden;
  background: #04060c;
  color: #f3ece0;
  touch-action: pan-y;
}

.hero {
  position: relative;
  z-index: 1;
  height: 100vh;
  height: 100svh;
  min-height: 620px;
  overflow: hidden;
  color: #f3ece0;
  pointer-events: none;
}

.sky-stage.no-webgl {
  background:
    radial-gradient(60% 50% at 8% 70%, rgba(214, 120, 50, 0.45), transparent 70%),
    radial-gradient(50% 50% at 95% 30%, rgba(60, 90, 170, 0.35), transparent 70%),
    radial-gradient(120% 60% at 50% 120%, #1b1c24 50%, transparent 51%),
    #05070d;
}

.sky-stage.near-ring { cursor: grab; }
.sky-stage.is-dragging { cursor: grabbing; }

.sky-stage :deep(.cosmos-canvas) {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
}

.body-hit {
  position: absolute;
  z-index: 4;
  border: 0;
  padding: 0;
  border-radius: 50%;
  background: transparent;
  cursor: grab;
  touch-action: none;
}
.body-hit:focus-visible {
  outline: 1px dashed rgba(255, 226, 168, 0.7);
  outline-offset: 4px;
}
.body-hit.is-set { pointer-events: none; }
.sky-stage.is-dragging .body-hit { cursor: grabbing; }

.sky-stage :deep(.orbit-layer) {
  transform-origin: 0 0;
  will-change: transform;
}

/* ---------- Copy ---------- */
.hero-copy {
  position: absolute;
  z-index: 3;
  left: 50%;
  top: var(--copy-top);
  width: min(680px, calc(100% - 32px));
  transform: translateX(-50%);
  text-align: center;
  pointer-events: none;
}
.hero-copy > * { pointer-events: auto; }
.hero-copy::before {
  content: '';
  position: absolute;
  inset: -12% -10% -4%;
  z-index: -1;
  background: radial-gradient(closest-side, rgba(4, 6, 12, 0.55), transparent);
  pointer-events: none;
}

.kicker {
  margin: 0;
  font-size: calc(11px * var(--k));
  letter-spacing: 0.42em;
  text-transform: uppercase;
  color: rgba(226, 214, 192, 0.72);
  animation: rise 1s ease 0.3s both;
}

.ornament {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  margin: calc(14px * var(--k)) auto calc(26px * var(--k));
  color: #f0cd8a;
  animation: rise 1s ease 0.4s both;
}
.ornament-line {
  width: calc(100px * var(--k));
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(240, 205, 138, 0.75));
}
.ornament-line:last-child { transform: scaleX(-1); }
.ornament-dot { width: 3px; height: 3px; border-radius: 50%; background: currentColor; opacity: 0.8; }
.ornament-star {
  width: calc(14px * var(--k));
  height: calc(14px * var(--k));
  fill: #ffe4ad;
  filter: drop-shadow(0 0 5px rgba(255, 200, 110, 0.9));
  animation: star-breathe 4s ease-in-out infinite;
}

.hero-copy h1 {
  margin: 0;
  font-family: var(--serif);
  font-weight: 500;
  font-size: calc(58px * var(--k));
  line-height: 0.98;
  letter-spacing: 0;
  color: #f6efe2;
  text-shadow: 0 0 28px rgba(255, 214, 150, 0.18), 0 2px 18px rgba(0, 0, 0, 0.6);
  animation: rise 1.1s ease 0.5s both;
}

.sub {
  margin: calc(26px * var(--k)) 0 0;
  font-size: calc(15.5px * var(--k));
  line-height: 1.55;
  color: rgba(226, 220, 210, 0.78);
  animation: rise 1.1s ease 0.65s both;
}

.cta {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 14px;
  margin-top: calc(30px * var(--k));
  padding: calc(14px * var(--k)) calc(34px * var(--k)) calc(14px * var(--k)) calc(36px * var(--k));
  border-radius: 999px;
  overflow: hidden;
  text-decoration: none;
  font-size: calc(14.5px * var(--k));
  font-weight: 600;
  color: #2b1d0b;
  background: linear-gradient(180deg, #f4dba6 0%, #e3bd78 55%, #cf9f55 100%);
  box-shadow:
    inset 0 1px 0 rgba(255, 248, 228, 0.8),
    inset 0 -1px 0 rgba(120, 80, 20, 0.35),
    0 0 0 1px rgba(255, 220, 160, 0.35),
    0 8px 30px rgba(230, 170, 80, 0.32),
    0 0 60px rgba(255, 190, 100, 0.15);
  transition: transform 0.25s ease, box-shadow 0.25s ease;
  animation: rise 1.1s ease 0.8s both;
}
.cta::after {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: -60%;
  width: 45%;
  background: linear-gradient(100deg, transparent, rgba(255, 255, 255, 0.55), transparent);
  transform: skewX(-20deg);
  animation: sheen 5.5s ease-in-out 2s infinite;
}
.cta:hover {
  transform: translateY(-2px);
  box-shadow:
    inset 0 1px 0 rgba(255, 248, 228, 0.9),
    inset 0 -1px 0 rgba(120, 80, 20, 0.35),
    0 0 0 1px rgba(255, 220, 160, 0.5),
    0 12px 40px rgba(240, 180, 90, 0.45),
    0 0 90px rgba(255, 190, 100, 0.25);
}
.cta:focus-visible { outline: 2px solid #ffe2a8; outline-offset: 4px; }
.cta-arrow {
  width: 15px;
  height: 15px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.6;
  stroke-linecap: round;
  stroke-linejoin: round;
  transition: transform 0.25s ease;
}
.cta:hover .cta-arrow { transform: translateX(4px); }

.hint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin: calc(34px * var(--k)) 0 0;
  font-size: calc(11.5px * var(--k));
  line-height: 1.45;
  text-align: left;
  color: rgba(214, 208, 198, 0.62);
  animation: rise 1.1s ease 1s both;
}
.hint-icon {
  width: 24px;
  height: 26px;
  flex: none;
  fill: none;
  stroke: rgba(240, 214, 160, 0.75);
  stroke-width: 1.2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

/* ---------- Corner notes ---------- */
.note {
  position: absolute;
  z-index: 3;
  bottom: calc(118px * var(--k));
  display: flex;
  align-items: flex-start;
  gap: 16px;
  animation: rise 1.2s ease 1.1s both;
}
.note-left { left: clamp(20px, 2.7vw, 48px); }
.note-right { right: clamp(20px, 2.7vw, 48px); }
.note-icon {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  flex: none;
  border-radius: 50%;
  border: 1px solid rgba(232, 206, 158, 0.45);
  background: rgba(10, 10, 16, 0.35);
  box-shadow: 0 0 18px rgba(255, 200, 120, 0.12);
}
.note-icon svg {
  width: 15px;
  height: 15px;
  fill: #f0d7a4;
}
.note-icon .compass { fill: none; stroke: #f0d7a4; stroke-width: 1; }
.note-icon .compass .fill { fill: #f0d7a4; stroke: none; }
.note-text { display: grid; gap: 4px; }
.note-text strong {
  font-weight: 400;
  font-size: 14px;
  color: #f2ebdf;
}
.note-text span {
  font-size: 11.5px;
  line-height: 1.45;
  color: rgba(214, 208, 198, 0.6);
}

/* ---------- Scroll emblem ---------- */
.emblem-btn {
  position: absolute;
  z-index: 4;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: transparent;
  cursor: pointer;
  outline: none;
}
.emblem-btn:focus-visible { box-shadow: 0 0 0 1px rgba(255, 226, 168, 0.7), 0 0 18px rgba(255, 200, 110, 0.4); }
.emblem-label {
  position: absolute;
  top: 100%;
  left: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  margin-top: 6px;
  font-size: 10px;
  letter-spacing: 0.3em;
  text-transform: uppercase;
  white-space: nowrap;
  color: #f1d9a8;
  text-shadow: 0 0 10px rgba(255, 200, 110, 0.6);
  opacity: 0;
  transform: translate(-50%, -4px);
  transition: opacity 0.35s ease, transform 0.45s cubic-bezier(0.3, 0.7, 0.2, 1);
  pointer-events: none;
}
.emblem-label svg { width: 10px; height: 14px; fill: none; stroke: currentColor; stroke-width: 1.4; stroke-linecap: round; stroke-linejoin: round; }
.emblem-btn.is-hot .emblem-label { opacity: 1; transform: translate(-50%, 0); }
.emblem-btn.is-hot .emblem-label svg { animation: emblem-arrow 1.4s ease-in-out infinite; }
.emblem-label.is-up svg { rotate: 180deg; }
@keyframes emblem-arrow { 50% { transform: translateY(4px); } }

/* ---------- Zodiac card ---------- */
.hero-copy { transition: opacity 0.5s ease, filter 0.5s ease; }
.hero-copy.is-dimmed { opacity: 0.28; filter: blur(1px); }

.zodiac-card {
  position: fixed;
  z-index: 20;
  overflow: hidden;
  padding: 22px 22px 20px;
  border-radius: 20px;
  color: #efe7d8;
  background:
    radial-gradient(120% 70% at 0% 0%, rgba(255, 196, 120, 0.13), transparent 60%),
    radial-gradient(90% 60% at 100% 100%, rgba(120, 150, 230, 0.1), transparent 60%),
    linear-gradient(160deg, rgba(30, 26, 22, 0.8), rgba(10, 12, 22, 0.86));
  border: 1px solid rgba(240, 210, 150, 0.26);
  box-shadow:
    0 30px 80px rgba(0, 0, 0, 0.55),
    inset 0 1px 0 rgba(255, 240, 210, 0.1),
    0 0 60px rgba(255, 190, 110, 0.08);
  backdrop-filter: blur(16px) saturate(1.25);
  -webkit-backdrop-filter: blur(16px) saturate(1.25);
}
/* A second hairline frame inset, like an engraved plate. */
.zodiac-card::before {
  content: "";
  position: absolute;
  inset: 6px;
  border: 1px solid rgba(240, 210, 150, 0.1);
  border-radius: 15px;
  pointer-events: none;
}
.card-sheen {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: linear-gradient(115deg, transparent 35%, rgba(255, 236, 200, 0.1) 50%, transparent 65%);
  transform: translateX(-100%);
  animation: card-sheen 1.6s ease 0.35s forwards;
}
.card-close {
  position: absolute;
  z-index: 2;
  top: 12px;
  right: 12px;
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border: 1px solid rgba(240, 210, 150, 0.18);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.02);
  color: rgba(239, 231, 216, 0.65);
  cursor: pointer;
  transition: color 0.25s ease, border-color 0.25s ease, transform 0.35s ease;
}
.card-close svg { width: 12px; height: 12px; fill: none; stroke: currentColor; stroke-width: 1.5; stroke-linecap: round; }
.card-close:hover { color: #ffe2a8; border-color: rgba(255, 226, 168, 0.5); transform: rotate(90deg); }

.card-head { display: flex; align-items: center; gap: 16px; margin-bottom: 14px; padding-right: 28px; }
.card-glyph {
  position: relative;
  display: grid;
  place-items: center;
  flex: none;
  width: 58px;
  height: 58px;
  border-radius: 50%;
  border: 1px solid rgba(240, 210, 150, 0.45);
  background: radial-gradient(circle, rgba(255, 200, 120, 0.18), rgba(255, 200, 120, 0) 70%);
  box-shadow: 0 0 24px rgba(255, 190, 110, 0.18), inset 0 0 14px rgba(255, 200, 120, 0.12);
  font-size: 28px;
  color: #ffd998;
  text-shadow: 0 0 14px rgba(255, 200, 110, 0.85);
  font-family: 'Segoe UI Symbol', 'Noto Sans Symbols', sans-serif;
}
.card-glyph-orbit {
  position: absolute;
  inset: -7px;
  border-radius: 50%;
  border: 1px dashed rgba(240, 210, 150, 0.22);
  animation: glyph-orbit 18s linear infinite;
}
.card-glyph-orbit::after {
  content: "";
  position: absolute;
  top: -3px;
  left: 50%;
  width: 5px;
  height: 5px;
  margin-left: -2.5px;
  border-radius: 50%;
  background: #ffe7b0;
  box-shadow: 0 0 8px #ffcf7a;
}
.card-kicker {
  margin: 0 0 3px;
  font-size: 10px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: rgba(233, 194, 124, 0.75);
}
.card-name { margin: 0; font-family: var(--serif); font-size: 30px; line-height: 1; color: #fbf3e4; }
.card-dates { margin: 5px 0 0; font-size: 12px; letter-spacing: 0.06em; color: rgba(226, 214, 192, 0.62); }

.card-traits { display: flex; flex-wrap: wrap; gap: 6px; margin: 0 0 14px; padding: 0; list-style: none; }
.card-traits li {
  padding: 3px 11px;
  border-radius: 999px;
  border: 1px solid rgba(240, 210, 150, 0.24);
  background: rgba(255, 214, 150, 0.06);
  font-size: 12px;
  color: #f1d9a8;
}
.card-text { margin: 0 0 12px; font-size: 14px; line-height: 1.55; color: rgba(239, 231, 216, 0.88); }
.card-myth {
  margin: 0 0 16px;
  padding-left: 12px;
  border-left: 1px solid rgba(233, 194, 124, 0.5);
  font-family: var(--serif);
  font-style: italic;
  font-size: 15px;
  line-height: 1.4;
  color: rgba(234, 220, 196, 0.72);
}
.card-facts {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px 12px;
  margin: 0 0 16px;
  padding-top: 14px;
  border-top: 1px solid rgba(240, 210, 150, 0.16);
}
.card-facts dt { font-size: 10px; letter-spacing: 0.14em; text-transform: uppercase; color: rgba(226, 214, 192, 0.5); }
.card-facts dd { margin: 2px 0 0; font-size: 13px; color: #f3dcae; }
.card-cta {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 16px;
  border-radius: 999px;
  border: 1px solid rgba(240, 210, 150, 0.45);
  background: linear-gradient(180deg, rgba(255, 214, 150, 0.14), rgba(255, 214, 150, 0.04));
  color: #ffe6b8;
  font-size: 14px;
  text-decoration: none;
  transition: box-shadow 0.3s ease, border-color 0.3s ease, background 0.3s ease;
}
.card-cta svg { width: 14px; height: 14px; fill: none; stroke: currentColor; stroke-width: 1.5; stroke-linecap: round; stroke-linejoin: round; transition: transform 0.3s ease; }
.card-cta:hover {
  border-color: rgba(255, 226, 168, 0.85);
  box-shadow: 0 0 26px rgba(255, 196, 110, 0.25);
  background: linear-gradient(180deg, rgba(255, 214, 150, 0.22), rgba(255, 214, 150, 0.08));
}
.card-cta:hover svg { transform: translateX(3px); }

/* Content follows the card in, one row at a time. */
.zodiac-card > :not(.card-sheen):not(.card-close) { animation: card-row 0.5s cubic-bezier(0.3, 0.7, 0.2, 1) both; }
.zodiac-card > .card-head { animation-delay: 0.08s; }
.zodiac-card > .card-traits { animation-delay: 0.14s; }
.zodiac-card > .card-text { animation-delay: 0.2s; }
.zodiac-card > .card-myth { animation-delay: 0.26s; }
.zodiac-card > .card-facts { animation-delay: 0.32s; }
.zodiac-card > .card-cta { animation-delay: 0.38s; }

.card-enter-active { transition: opacity 0.4s ease, transform 0.5s cubic-bezier(0.3, 0.7, 0.2, 1), filter 0.4s ease; }
.card-leave-active { transition: opacity 0.25s ease, transform 0.25s ease; }
.card-enter-from { opacity: 0; transform: translateX(var(--from)) scale(0.97); filter: blur(6px); }
.card-leave-to { opacity: 0; transform: scale(0.98); }

@keyframes card-row { from { opacity: 0; transform: translateY(6px); } }
@keyframes card-sheen { to { transform: translateX(100%); } }
@keyframes glyph-orbit { to { transform: rotate(360deg); } }

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}

@keyframes rise {
  from { opacity: 0; transform: translateY(14px); }
  to { opacity: 1; transform: none; }
}
@keyframes sheen {
  0%, 70% { left: -60%; }
  100% { left: 130%; }
}
@keyframes star-breathe {
  0%, 100% { transform: scale(1) rotate(0deg); }
  50% { transform: scale(1.18) rotate(45deg); }
}

@media (max-width: 760px) {
  .sky-stage, .hero { min-height: 780px; }
  .hero-copy h1 { font-size: 40px; }
  .sub { font-size: 15px; }
  .sub br { display: none; }
  .note { bottom: 22px; gap: 10px; }
  .note-icon { width: 28px; height: 28px; }
  .note-text span { display: none; }
}

@media (prefers-reduced-motion: reduce) {
  .kicker, .ornament, .hero-copy h1, .sub, .cta, .hint, .note { animation: none; }
  .cta::after, .ornament-star { animation: none; }
  .card-sheen, .card-glyph-orbit, .zodiac-card > *, .emblem-btn.is-hot .emblem-label svg { animation: none; }
}
</style>
