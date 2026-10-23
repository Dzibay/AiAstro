<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { FIGURE, GOLD, LOOKS, PALE, createScene } from './scene.js'
import {
  BELT,
  EARTH_RADIUS,
  MOON_ORBIT,
  ORBITS,
  OUTER,
  add,
  aimAt,
  angleOf,
  beltHit,
  gap,
  onOrbit,
  signAt,
  sub,
  toward,
  wheelRadius,
  wrap,
} from './geometry.js'
import { POINTS, SIGN_LIST, degrees, spread } from '../cabinet/astro.js'
import { panelLeft, panelWidth, wheelSpot } from '../cabinet/layout.js'
import { useSky } from '../../composables/useSky.js'
import { useChart } from '../../composables/useChart.js'
import { quality } from '../../utils/quality.js'
import { LITE } from '../../utils/device.js'
import { formatDate } from '../../utils/format.js'
import { queue, reachGoal } from '../../utils/track.js'

/**
 * «Соберите своё небо»: the natal chart built by hand, over the chart page (CabinetView). The Sun
 * in the middle, the planets on their orbits, the belt of signs around them; a sign is the
 * direction a body is seen in from the Earth, so the player turns each body until the ray from
 * the Earth through it lights the sign it stood in at the birth. First the Earth (that places the
 * Sun), the Moon, the Ascendant (the Earth turned on its axis; only when the time and the place
 * are known), Mercury, Venus and Mars; the slow planets fly in by themselves. Then the sky rewinds
 * to the birthday, rises to a view from straight above and, with the Earth set in the middle,
 * becomes the wheel (NatalWheel) standing beneath it: `land` asks the page to show the wheel,
 * `close` follows once the game has faded.
 *
 * There are no wrong moves: a miss only tells where the ray is and how far the sign is.
 */

const props = defineProps({
  chart: { type: Object, required: true },
  user: { type: Object, default: null },
})
const emit = defineEmits(['land', 'close'])

const { geo } = useSky()
const { reading } = useChart()
const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false

const RAD = Math.PI / 180
const clamp = (value, lo, hi) => Math.min(hi, Math.max(lo, value))
const mixPoint = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]

/** Each body's ray of sight among the scene's twelve. */
const BEAM = { sun: 0, moon: 1, asc: 2, mercury: 3, venus: 4, mars: 5, jupiter: 6, saturn: 7, uranus: 8, neptune: 9, pluto: 10 }
/** How fast (°/s) a body not placed yet keeps going round; `asc` is the Earth turning on its axis. */
const DRIFT = { mercury: 6.4, venus: 3.1, earth: 2, mars: 1.3, moon: 9, asc: 24 }
/** The planets' own turn, °/s: Venus and Uranus the other way round. */
const SPIN = { mercury: 4, venus: -2, mars: 14, jupiter: 32, saturn: 28, uranus: -16, neptune: 18, pluto: 5 }
/** The Earth drawn larger while the Moon and the horizon are set around it. */
const EARTH_SCALE = { intro: 1.2, sun: 1.25, moon: 1.8, asc: 2.2, planet: 1.2 }
/** Whole turns back while the sky rewinds: the quick ones spin, the slow ones keep their signs. */
const REWIND = { mercury: 6, venus: 4, earth: 3, mars: 2, moon: 12, asc: 9 }
/** The canvas resolution by the site's quality step (utils/quality.js). */
const DPR = [1.75, 1.5, 1.5, 1.25, 1.25]
const NUMBERS = ['', 'один знак', 'два знака', 'три знака', 'четыре знака', 'пять знаков', 'шесть знаков']
const EARTH_GLYPH = '♁︎'

/** The birthplace stands just above the Earth's surface. */
const markRadius = (scale) => EARTH_RADIUS * scale * 1.06

/** `grab` finishes «Тяните в любом месте экрана — …»; `what` is whom the hint's ring is for. */
const COPY = {
  sun: (sign) => ({
    task: `В день вашего рождения Солнце стояло ${sign.in}. Ведите Землю по орбите, пока луч от неё через Солнце не зажжёт знак ${sign.name}.`,
    why: 'Знак Солнца — это направление с Земли на Солнце. За год Земля обходит Солнце, и луч успевает пройти все двенадцать знаков — по месяцу на каждый.',
    grab: 'Земля пойдёт по своей орбите',
    what: 'Землю',
  }),
  moon: (sign) => ({
    task: `Луна была ${sign.in}. Поверните её вокруг Земли, пока луч с Земли через Луну не зажжёт знак ${sign.name}.`,
    why: 'Луна обходит Землю за месяц и в каждом знаке гостит два-три дня — поэтому её знак так точно говорит о дне рождения.',
    grab: 'Луна пойдёт вокруг Земли',
    what: 'Луну',
  }),
  asc: (sign) => ({
    task: `Асцендент — ${sign.name}. Поверните Землю вокруг оси: луч от места рождения к восточному горизонту должен зажечь знак ${sign.name}.`,
    why: 'Асцендент — знак, который поднимался над горизонтом в минуту рождения. Земля поворачивается за сутки, и восходящий знак сменяется примерно каждые два часа — поэтому для него так важно время.',
    grab: 'Земля повернётся вокруг оси',
    what: 'место рождения',
  }),
  mercury: (sign) => ({
    task: `Меркурий был ${sign.in}. Ведите его по орбите, пока луч с Земли через него не зажжёт знак ${sign.name}.`,
    why: 'Меркурий — ближайшая к Солнцу планета. С Земли он всегда виден рядом с Солнцем и не уходит от него дальше соседнего знака.',
    grab: 'Меркурий пойдёт по своей орбите',
    what: 'Меркурий',
  }),
  venus: (sign) => ({
    task: `Венера была ${sign.in}. Ведите её по орбите, пока луч с Земли через неё не зажжёт знак ${sign.name}.`,
    why: 'Венера тоже держится возле Солнца — не дальше полутора знаков от него. Поэтому её и видно только утром или вечером.',
    grab: 'Венера пойдёт по своей орбите',
    what: 'Венеру',
  }),
  mars: (sign) => ({
    task: `Марс был ${sign.in}. Ведите его по орбите, пока луч с Земли через него не зажжёт знак ${sign.name}.`,
    why: 'Марс — первая планета за орбитой Земли. Он не привязан к Солнцу и может оказаться в любой стороне неба.',
    grab: 'Марс пойдёт по своей орбите',
    what: 'Марс',
  }),
}

const FINALE = {
  flight: {
    kicker: 'Планеты поколения',
    text: 'Юпитер, Сатурн, Уран, Нептун и Плутон ходят медленно — годами стоят в одном знаке. Это планеты поколения: их знаки у вас общие со сверстниками.',
  },
  rewind: { kicker: 'Перематываем небо', text: 'Отматываем время назад — к дню, когда вы родились.' },
  flash: { kicker: 'Момент рождения', text: 'Так стояло небо в минуту вашего рождения.' },
  rise: { kicker: 'Ваша карта', text: 'Посмотрим на это небо сверху.' },
  flip: {
    kicker: 'Ваша карта',
    text: 'Поставим в центр Землю — ведь мы смотрим на небо отсюда. Это и есть ваша натальная карта.',
  },
}
FINALE.land = FINALE.flip

/* ---- The chart as steps ---- */

const pointOf = (id) => props.chart.points.find((point) => point.id === id)
const sunLon = pointOf('sun').lon
/** Where the Earth stood at the birth: from there the Sun is seen at its own longitude. */
const EARTH = toward(sunLon + 180, ORBITS.earth)

/** `body`: what the player turns — the Earth for the Sun, the Earth's spin (`asc`) for the Ascendant. */
const steps = ['sun', 'moon', ...(props.chart.angles ? ['asc'] : []), 'mercury', 'venus', 'mars'].map((id) => {
  const point = id === 'asc' ? props.chart.angles.asc : pointOf(id)
  const sign = signAt(point.lon)
  return {
    id,
    body: id === 'sun' ? 'earth' : id,
    lon: point.lon,
    deg: point.deg ?? wrap(point.lon) % 30,
    sign,
    approx: Boolean(point.approx),
    ...COPY[id](SIGN_LIST[sign]),
  }
})

/** The angle the step's body must stand at, from the Earth where it stood at the birth. */
function targetOf(s) {
  if (s.id === 'sun') return wrap(sunLon + 180)
  if (s.id === 'moon') return aimAt(EARTH, s.lon)
  if (s.id === 'asc') {
    // The ray leaves the birthplace along the horizon, a right angle from the place itself.
    const r = markRadius(EARTH_SCALE.asc)
    let phi = aimAt(EARTH, s.lon) - 90
    for (let i = 0; i < 8; i += 1) phi = aimAt(add(EARTH, toward(phi, r)), s.lon) - 90
    return wrap(phi)
  }
  return onOrbit(EARTH, s.lon, ORBITS[s.id], ang[s.id])
}

/* ---- The model (plain, read every frame) ---- */

const ang = {
  // The Earth starts four to six signs away from the answer.
  earth: wrap(sunLon + 180 + 110 + Math.random() * 80),
  moon: Math.random() * 360,
  asc: Math.random() * 360,
  mercury: Math.random() * 360,
  venus: Math.random() * 360,
  mars: Math.random() * 360,
}
for (const id of OUTER) ang[id] = onOrbit(EARTH, pointOf(id).lon, ORBITS[id], pointOf(id).lon)
const orbit = { ...ORBITS }
const look = {
  earthScale: EARTH_SCALE.intro,
  outer: Object.fromEntries(OUTER.map((id) => [id, 0])),
  marker: 0,
  slide: 0,
  flip: 0,
  rays: 1,
  orbits: 1,
  figures: 1,
  sky: 1,
  labels: 1,
  shrink: 1,
  earthShrink: 1,
  sunGlow: 0,
}
const rays = {}
const gold = {}
const placed = new Set()
const signLit = new Array(12).fill(0)
const flares = new Array(12).fill(0)
const pops = new Array(12).fill(1)
const lit = new Array(12).fill(0)
const wheelAt = {}
const flash = { lon: 0, power: 0 }
const hint = { target: 0, alpha: 0, pulse: 0, sign: -1 }
let live = null
let liveSign = -1

const fixed = (body) => placed.has(body === 'earth' ? 'sun' : body)

function where() {
  const pos = { sun: [0, 0] }
  for (const id of ['mercury', 'venus', 'earth', 'mars', ...OUTER]) pos[id] = toward(ang[id], orbit[id])
  pos.moon = add(pos.earth, toward(ang.moon, MOON_ORBIT * look.earthScale))
  pos.asc = add(pos.earth, toward(ang.asc, markRadius(look.earthScale)))
  if (look.slide > 0) {
    // The finale: the Earth slides to the middle, everything with it, then each body to the wheel.
    const shift = [pos.earth[0] * look.slide, pos.earth[1] * look.slide]
    for (const id of Object.keys(pos)) {
      pos[id] = sub(pos[id], shift)
      if (look.flip > 0 && wheelAt[id]) pos[id] = mixPoint(pos[id], wheelAt[id], look.flip)
    }
  }
  return pos
}

function rayOf(id, pos) {
  const e = pos.earth
  if (id === 'asc') return { from: pos.asc, heading: wrap(ang.asc + 90) }
  return { from: e, heading: angleOf(sub(pos[id], e)) }
}

/* ---- What the page shows ---- */

const ui = reactive({
  phase: 'intro',
  index: 0,
  readout: '',
  match: false,
  hint: '',
  helped: false,
  grabbed: false,
  keyed: false,
  dragging: false,
  busy: false,
  why: false,
  essence: {},
  finale: 'flight',
  date: '',
  birth: '',
  leaving: false,
  closing: false,
})
const step = computed(() => steps[ui.index])
const sign = computed(() => SIGN_LIST[step.value.sign])
const last = computed(() => ui.index === steps.length - 1)
const finaleCopy = computed(() => FINALE[ui.finale] || FINALE.flight)
const glyphOf = (id) => (id === 'asc' ? '' : POINTS[id].glyph)
const essence = (id) => (ui.essence[id] || '').replace(/[.…]+$/, '')
const cardKey = computed(() => (ui.phase === 'intro' || ui.phase === 'finale' ? ui.phase : `${ui.phase}-${ui.index}`))

const LABELS = [
  { id: 'sun', glyph: POINTS.sun.glyph, name: 'Солнце' },
  { id: 'earth', glyph: EARTH_GLYPH, name: 'Земля' },
  { id: 'moon', glyph: POINTS.moon.glyph, name: 'Луна' },
  ...['mercury', 'venus', 'mars', ...OUTER].map((id) => ({ id, glyph: POINTS[id].glyph, name: POINTS[id].name })),
  { id: 'asc', glyph: '', name: 'Место рождения' },
]

const size = reactive({ W: window.innerWidth, H: window.innerHeight })
const narrow = computed(() => size.W <= 760)
const sheet = computed(() => Math.round(clamp(size.H * 0.4, 230, 340)))
/** The part of the screen the sky fills: beside the card on a desktop (where the panel stands), above the sheet on a phone. */
const box = computed(() => (narrow.value
  ? { x0: 6, y0: 54, x1: size.W - 6, y1: size.H - sheet.value - 8 }
  : { x0: 24, y0: 72, x1: panelLeft(size.W) - 28, y1: size.H - 28 }))
const hudStyle = computed(() => (narrow.value
  ? { height: `${sheet.value}px` }
  : { left: `${panelLeft(size.W)}px`, width: `${panelWidth(size.W)}px` }))

const root = ref(null)
const canvas = ref(null)
const cueEl = ref(null)
const hitEl = ref(null)
const titleEl = ref(null)
const goEl = ref(null)
const nextEl = ref(null)
const tagEls = {}
const setTag = (id, el) => {
  tagEls[id] = el
}

/* ---- Time ---- */

let scene = null
let view = null
let raf = 0
let clock = 0
let lastFrame = 0
let liveUntil = 0
let moving = false
let alive = true
let closed = false
let skipping = false
let drag = null
let darkTimer = 0
let observer = null
/** Focus goes back where it came from (the replay button) once the game is gone. */
const opener = document.activeElement

const tweens = new Set()
const curves = {
  inOut: (t) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2),
  out: (t) => 1 - (1 - t) ** 3,
  linear: (t) => t,
}
function run(duration, update, curve) {
  return new Promise((resolve) => {
    if (skipping || duration <= 0) {
      update(1)
      resolve()
      return
    }
    tweens.add({ start: clock, duration, update, curve, resolve })
  })
}
/** A movement: brief under reduced motion. */
const tween = (seconds, update, curve = curves.inOut) => run(reduce ? Math.min(seconds, 0.35) : seconds, update, curve)
/** A pause to read: the same for everyone. */
const hold = (seconds) => run(seconds, () => {}, curves.linear)

/** «Пропустить»: everything still moving arrives at once, and whatever follows comes instantly. */
function flush() {
  skipping = true
  for (const item of [...tweens]) {
    item.update(1)
    item.resolve()
  }
  tweens.clear()
}

/* ---- The camera ---- */

const want = { az: -90, el: 58, dist: 140, lx: 0, ly: 0, cx: 0, cy: 0 }
let follow = true
let turning = 0

/** The whole sky slowly turning, or the step's sign straight ahead with the constellation behind it. */
function aimCamera(snap = false) {
  if (!scene || !follow) return
  const { x0, y0, x1, y1 } = box.value
  const w = x1 - x0
  const h = y1 - y0
  want.cx = (x0 + x1) / 2
  want.cy = (y0 + y1) / 2
  const s = ui.phase === 'play' || ui.phase === 'found' ? step.value : null
  if (!s) {
    turning = reduce || (ui.phase === 'finale' && ui.finale !== 'flight') ? 0 : 3
    Object.assign(want, { el: 58, lx: 0, ly: 0 })
    want.dist = scene.fit({ az: want.az, el: 58, w, h })
  } else {
    turning = 0
    want.az = wrap(aimAt(EARTH, s.lon) + 180)
    if (s.id === 'moon' || s.id === 'asc') {
      // Closer: the Earth near the bottom, the sector and its constellation at the top.
      const mid = s.sign * 30 + 15
      const [lx, ly] = mixPoint(EARTH, toward(mid, BELT.mid), 0.5)
      const r = MOON_ORBIT * EARTH_SCALE[s.id] + 1.2
      const top = FIGURE.foot + FIGURE.size
      const points = [
        [EARTH[0] + r, EARTH[1], 0],
        [EARTH[0] - r, EARTH[1], 0],
        [EARTH[0], EARTH[1] + r, 0],
        [EARTH[0], EARTH[1] - r, 0],
        ...[s.sign * 30, s.sign * 30 + 30].flatMap((deg) => [[...toward(deg, BELT.inner), 0], [...toward(deg, BELT.outer + 1), 0]]),
        [...toward(mid - 7, FIGURE.radius), top],
        [...toward(mid + 7, FIGURE.radius), top],
      ]
      Object.assign(want, { el: 50, lx, ly, dist: scene.fit({ az: want.az, el: 50, lx, ly, points, w, h }) })
    } else {
      Object.assign(want, { el: 55, lx: 0, ly: 0, dist: scene.fit({ az: want.az, el: 55, w, h }) })
    }
  }
  if (snap) Object.assign(view, want)
}

function easeCamera(dt) {
  if (!follow) return false
  if (turning) want.az = wrap(want.az + turning * dt)
  const k = 1 - Math.exp(-dt * 2.2)
  const turn = gap(view.az, want.az)
  view.az = wrap(view.az + turn * k)
  let left = turning ? 0 : Math.abs(turn)
  for (const key of ['el', 'dist', 'lx', 'ly', 'cx', 'cy']) {
    const d = want[key] - view[key]
    view[key] += d * k
    left = Math.max(left, Math.abs(d))
  }
  return left > 0.05
}

/* ---- The frame ---- */

function frame(now) {
  raf = requestAnimationFrame(frame)
  if (document.hidden) {
    lastFrame = now
    return
  }
  // Full rate while anything moves under the hand or on its own; a calm sky is drawn less often.
  const busy = drag || tweens.size || moving || clock < liveUntil
  if (!busy && now - lastFrame < 1000 / (LITE ? 20 : 30) - 2) return
  const dt = Math.min(0.1, Math.max(0, (now - lastFrame) / 1000))
  lastFrame = now
  clock += dt
  tick(dt)
}

function tick(dt) {
  for (const item of [...tweens]) {
    const p = Math.min(1, (clock - item.start) / item.duration)
    item.update(item.curve(p))
    if (p >= 1) {
      tweens.delete(item)
      item.resolve()
    }
  }
  const s = ui.phase === 'play' || ui.phase === 'found' ? step.value : null
  if (!reduce && ui.phase !== 'finale') {
    for (const [body, speed] of Object.entries(DRIFT)) {
      if (s?.body === body || fixed(body)) continue
      ang[body] = wrap(ang[body] + speed * dt)
    }
  }
  const fade = Math.exp(-dt * 1.4)
  for (let i = 0; i < 12; i += 1) flares[i] *= fade
  flash.power *= Math.exp(-dt * 0.9)
  look.sunGlow *= fade
  moving = easeCamera(dt)

  const pos = where()
  if (ui.phase === 'play') {
    const ray = rayOf(s.id, pos)
    const hit = beltHit(ray.from, ray.heading)
    const now = signAt(hit.lon)
    live = { id: s.id, from: ray.from, to: hit.point, lon: hit.lon, sign: now, match: now === s.sign }
    if (now !== liveSign) {
      liveSign = now
      ui.readout = `${SIGN_LIST[now].glyph} ${SIGN_LIST[now].name}`
      ui.match = live.match
      if (drag && LITE) navigator.vibrate?.(4)
    }
  } else {
    live = null
  }
  draw(pos, s)
  scene.render(clock)
  placeTags(pos, s)
}

function draw(pos, s) {
  const mover = ui.phase === 'play' ? s.body : null
  const glowOf = (body) => (body === mover ? 0.6 : fixed(body) ? 0.35 : 0)

  scene.setBody('sun', pos.sun, { glow: look.sunGlow })
  scene.setBody('earth', pos.earth, {
    scale: look.earthScale * look.earthShrink,
    glow: mover === 'asc' ? 0.6 : glowOf('earth'),
  })
  scene.setBody('moon', pos.moon, { scale: look.earthScale * look.shrink, glow: glowOf('moon') })
  for (const id of ['mercury', 'venus', 'mars']) scene.setBody(id, pos[id], { scale: look.shrink, glow: glowOf(id) })
  for (const id of OUTER) {
    scene.setBody(id, pos[id], { scale: look.outer[id] * look.shrink, alpha: look.outer[id], glow: placed.has(id) ? 0.3 : 0 })
  }
  scene.setSpin('earth', ang.asc)
  // The Moon keeps one face to the Earth.
  scene.setSpin('moon', ang.moon + 180)
  for (const [id, speed] of Object.entries(SPIN)) scene.setSpin(id, clock * speed)

  const orbitAlpha = (body) => look.orbits * (body === mover ? 0.34 : fixed(body) ? 0.24 : 0.13)
  for (const id of ['mercury', 'venus', 'earth', 'mars']) scene.setOrbit(id, { alpha: orbitAlpha(id), gold: gold[id] || 0 })
  scene.setOrbit('moon', { alpha: orbitAlpha('moon'), gold: gold.moon || 0, radius: MOON_ORBIT * look.earthScale })
  for (const id of OUTER) scene.setOrbit(id, { alpha: look.orbits * 0.12 * look.outer[id] })

  for (let i = 0; i < 12; i += 1) lit[i] = (signLit[i] ? 1 : 0) + flares[i]
  if (live) lit[live.sign] = Math.max(lit[live.sign], live.match ? 0.9 : 0.45)
  const hit = live ? [live.lon, live.match ? 1.1 : 0.7] : flash.power > 0.02 ? [flash.lon, flash.power] : null
  scene.setBelt({ lit, target: hint.sign, pulse: hint.pulse, hit })
  for (let i = 0; i < 12; i += 1) {
    const hover = live && live.sign === i ? (live.match ? 0.7 : 0.35) : 0
    scene.setFigure(i, { light: Math.max(signLit[i] ? 1 : 0, hover), pop: pops[i], show: look.figures })
  }

  for (const [id, k] of Object.entries(BEAM)) {
    if (live && live.id === id) {
      scene.setBeam(k, live.from, live.to, { power: drag ? 1 : 0.7, color: live.match ? GOLD : PALE, width: 0.5 })
      continue
    }
    const ray = rays[id]
    if (!ray || ray.power * look.rays <= 0.003) {
      scene.setBeam(k, null)
      continue
    }
    const r = rayOf(id, pos)
    scene.setBeam(k, r.from, beltHit(r.from, r.heading).point, { power: ray.power * look.rays, head: ray.head, width: 0.42 })
  }

  scene.setMarker(look.marker > 0.01 ? pos.asc : null, look.marker)
  scene.setGhost(hint.alpha > 0.01 && s ? ghostAt(s, pos) : null, hint.alpha * (0.65 + 0.35 * Math.sin(clock * 3)))
  scene.setSky(look.sky)
}

function ghostAt(s, pos) {
  if (s.id === 'sun') return toward(hint.target, ORBITS.earth)
  if (s.id === 'moon') return add(pos.earth, toward(hint.target, MOON_ORBIT * look.earthScale))
  if (s.id === 'asc') return add(pos.earth, toward(hint.target, markRadius(look.earthScale)))
  return toward(hint.target, ORBITS[s.id])
}

/* ---- The names under the bodies, the cue to grab, the sign the ray reaches ---- */

/** [opacity, with the name] */
function tagState(id, s) {
  if (ui.phase === 'intro') {
    if (id === 'sun' || id === 'earth') return [0.8, true]
    return ['moon', 'mercury', 'venus', 'mars'].includes(id) ? [0.45, false] : [0, false]
  }
  if (OUTER.includes(id)) return [look.outer[id] * 0.8, true]
  if (id === 'asc') return [ui.phase !== 'finale' && s?.id === 'asc' ? 0.9 : 0, true]
  if (ui.phase === 'play') {
    if (id === (s.body === 'asc' ? 'earth' : s.body)) return [1, true]
    if (s.id === 'sun' && id === 'sun') return [0.9, true]
  }
  // A placed body keeps its name, but the Moon hugs the Earth, and on a narrow screen the inner
  // system is too tight: a glyph is enough there, the Earth alone named.
  const named = id === 'earth' || (id !== 'moon' && !narrow.value)
  return fixed(id === 'sun' ? 'earth' : id) ? [0.7, named] : [0.4, false]
}

function bodyRadius(id) {
  if (id === 'asc') return 0.25
  if (id === 'sun') return LOOKS.sun.radius
  if (id === 'earth') return LOOKS.earth.radius * look.earthScale * look.earthShrink
  if (id === 'moon') return LOOKS.moon.radius * look.earthScale * look.shrink
  return LOOKS[id].radius * (OUTER.includes(id) ? look.outer[id] : 1) * look.shrink
}

let hitText = ''
function placeTags(pos, s) {
  for (const label of LABELS) {
    const el = tagEls[label.id]
    if (!el) continue
    const [alpha, full] = tagState(label.id, s)
    const shown = alpha * look.labels
    if (shown < 0.02) {
      el.style.opacity = '0'
      continue
    }
    const xy = pos[label.id]
    const r = bodyRadius(label.id)
    const p = scene.project(xy)
    const a = scene.project(add(xy, [r, 0]))
    const b = scene.project(add(xy, [0, r]))
    const below = Math.max(Math.hypot(a.x - p.x, a.y - p.y), Math.hypot(b.x - p.x, b.y - p.y))
    el.style.transform = `translate3d(${p.x.toFixed(1)}px, ${(p.y + below + 4).toFixed(1)}px, 0)`
    el.style.opacity = p.front ? shown.toFixed(2) : '0'
    el.classList.toggle('is-short', !full)
  }

  const cue = cueEl.value
  if (cue) {
    const show = ui.phase === 'play' && !ui.grabbed && !ui.busy
    if (show) {
      const p = scene.project(pos[s.body])
      cue.style.transform = `translate3d(${p.x.toFixed(1)}px, ${p.y.toFixed(1)}px, 0)`
    }
    cue.classList.toggle('is-on', show)
  }

  const tag = hitEl.value
  if (tag) {
    const show = Boolean(live) && ui.grabbed
    if (show) {
      const p = scene.project(toward(live.lon, BELT.outer + 2.6))
      tag.style.transform = `translate3d(${p.x.toFixed(1)}px, ${p.y.toFixed(1)}px, 0)`
      if (ui.readout !== hitText) {
        hitText = ui.readout
        tag.textContent = hitText
      }
      tag.classList.toggle('is-match', live.match)
    }
    tag.classList.toggle('is-on', show)
  }
}

/* ---- The steps ---- */

/* What the figures learn of a game (admin → «Аналитика»): its start, every planet found or missed
   (game:found:moon, its number for the order), the hints, the finale, the landing with the seconds
   it took, or where it was left (game:quit:intro … game:quit:finale). */
let began = 0
let landed = false
const stepNo = () => (ui.phase === 'intro' ? 0 : ui.phase === 'finale' ? steps.length + 1 : ui.index + 1)
const stepId = () => (ui.phase === 'intro' || ui.phase === 'finale' ? ui.phase : steps[ui.index]?.id || 'other')
const stepAct = (act) => queue('act', `game:${act}:${stepId()}`, stepNo())

function begin() {
  began = performance.now()
  queue('act', 'game:begin')
  startStep(0)
}

function startStep(index) {
  const s = steps[index]
  Object.assign(ui, { phase: 'play', index, hint: '', helped: false, grabbed: false, keyed: false, why: false, readout: '', match: false })
  liveSign = -1
  Object.assign(hint, { alpha: 0, pulse: 0, sign: -1 })
  const from = look.earthScale
  const to = EARTH_SCALE[s.id] ?? EARTH_SCALE.planet
  tween(0.9, (t) => {
    look.earthScale = from + (to - from) * t
  })
  if (s.id === 'asc') {
    tween(0.6, (t) => {
      look.marker = t
    })
  }
  if (!(s.id in ui.essence)) {
    reading(s.id)
      .then((data) => {
        ui.essence[s.id] = data?.reading?.essence || ''
      })
      .catch(() => {
        ui.essence[s.id] = ''
      })
  }
  aimCamera()
  clearAway(s)
}

/** A body that happens to stand on its answer already steps aside first: the player finds it. */
async function clearAway(s) {
  const start = ang[s.body]
  let offset = 0
  for (let i = 0; i < 7; i += 1) {
    ang[s.body] = wrap(start + offset)
    const ray = rayOf(s.id, where())
    if (signAt(beltHit(ray.from, ray.heading).lon) !== s.sign && Math.abs(gap(ang[s.body], targetOf(s))) > 35) break
    offset += 55
  }
  ang[s.body] = start
  if (!offset) return
  ui.busy = true
  await tween(0.8, (t) => {
    ang[s.body] = wrap(start + offset * t)
  })
  ui.busy = false
}

function centerOf(s) {
  return s.body === 'moon' || s.body === 'asc' ? where().earth : [0, 0]
}

function onDown(event) {
  if (ui.phase !== 'play' || ui.busy || drag || !scene) return
  const s = step.value
  const p = scene.groundAt(event.clientX, event.clientY)
  if (!p) return
  // The body keeps its place relative to the finger: grabbing anywhere turns it from where it is.
  drag = { id: event.pointerId, offset: gap(angleOf(sub(p, centerOf(s))), ang[s.body]) }
  canvas.value.setPointerCapture?.(event.pointerId)
  Object.assign(ui, { dragging: true, grabbed: true, keyed: false, hint: '' })
}

function onMove(event) {
  if (!drag || event.pointerId !== drag.id) return
  const s = step.value
  const p = scene.groundAt(event.clientX, event.clientY)
  if (!p) return
  const d = sub(p, centerOf(s))
  if (Math.hypot(d[0], d[1]) < 0.4) return
  ang[s.body] = wrap(angleOf(d) + drag.offset)
}

function onUp(event) {
  if (!drag || event.pointerId !== drag.id) return
  drag = null
  ui.dragging = false
  if (event.type !== 'pointercancel') check()
}

function nudge(deg) {
  const s = step.value
  ang[s.body] = wrap(ang[s.body] + deg)
  Object.assign(ui, { grabbed: true, keyed: true, hint: '' })
  liveUntil = clock + 0.6
}

/** Anywhere in the right sign counts: the body then settles on the exact degree. */
function check() {
  const s = step.value
  const ray = rayOf(s.id, where())
  const now = signAt(beltHit(ray.from, ray.heading).lon)
  const target = targetOf(s)
  if (now === s.sign || Math.abs(gap(ang[s.body], target)) < 3) {
    succeed(target)
    return
  }
  const k = (s.sign - now + 12) % 12
  const n = k <= 6 ? k : 12 - k
  const way = k <= 6 ? 'против часовой стрелки' : 'по часовой стрелке'
  stepAct('miss')
  ui.hint = `${n === 1 ? 'Совсем рядом. ' : ''}Луч сейчас ${SIGN_LIST[now].in}. До ${SIGN_LIST[s.sign].of} — ${NUMBERS[n]} ${way}.`
}

async function succeed(target, seconds = 0.6) {
  const s = step.value
  ui.busy = true
  ui.hint = ''
  const from = ang[s.body]
  const turn = gap(from, target)
  await tween(seconds, (t) => {
    ang[s.body] = wrap(from + turn * t)
  }, curves.out)
  if (!alive || ui.phase !== 'play') return
  celebrate(s)
  ui.busy = false
}

function celebrate(s) {
  const pos = where()
  const ray = rayOf(s.id, pos)
  const hit = beltHit(ray.from, ray.heading)
  placed.add(s.id)
  signLit[s.sign] += 1
  rays[s.id] = { power: 0.5, head: 1 }
  live = null
  scene.shock(pos[s.body], { color: PALE, scale: 6 })
  scene.shock(hit.point, { color: GOLD, scale: 12, duration: 1.6 })
  scene.burst(s.id === 'sun' ? pos.sun : pos[s.body], { color: s.id === 'sun' ? 0xffd79a : PALE })
  flares[s.sign] = 1.6
  Object.assign(flash, { lon: hit.lon, power: 1.8 })
  if (s.id === 'sun') look.sunGlow = 1.5
  pops[s.sign] = 0
  tween(1.8, (t) => {
    pops[s.sign] = t
  }, curves.linear)
  const orbitId = s.id === 'sun' ? 'earth' : s.id
  if (orbitId !== 'asc') {
    tween(0.8, (t) => {
      gold[orbitId] = t
    })
  }
  Object.assign(hint, { alpha: 0, pulse: 0, sign: -1 })
  liveUntil = clock + 2.5
  if (LITE) navigator.vibrate?.(12)
  ui.phase = 'found'
  stepAct('found')
}

function next() {
  if (ui.index + 1 < steps.length) startStep(ui.index + 1)
  else finale()
}

function showHint() {
  const s = step.value
  stepAct('hint')
  Object.assign(ui, { helped: true, grabbed: false, hint: '' })
  hint.target = targetOf(s)
  hint.sign = s.sign
  tween(0.5, (t) => {
    hint.alpha = t
    hint.pulse = t
  })
}

function placeForMe() {
  if (ui.busy) return
  succeed(targetOf(step.value), 1.2)
}

/* ---- The finale ---- */

async function fly(id, delay) {
  await hold(delay)
  if (!alive) return
  const target = ang[id]
  const sector = signAt(pointOf(id).lon)
  await tween(1.8, (t) => {
    ang[id] = wrap(target - 200 * (1 - t))
    orbit[id] = 60 + (ORBITS[id] - 60) * t
    look.outer[id] = Math.min(1, t * 1.6)
  }, curves.out)
  if (!alive) return
  placed.add(id)
  rays[id] = { power: 0.5, head: 0 }
  await tween(0.5, (t) => {
    rays[id].head = t
  }, curves.out)
  if (!alive) return
  const r = rayOf(id, where())
  scene.shock(beltHit(r.from, r.heading).point, { color: GOLD, scale: 10 })
  signLit[sector] += 1
  flares[sector] = Math.max(flares[sector], 1.2)
  pops[sector] = 0
  tween(1.8, (t) => {
    pops[sector] = t
  }, curves.linear)
  liveUntil = clock + 2
}

function birthStamp() {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(props.user?.birth?.date || props.chart.moment || '')
  return match ? new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3])).getTime() : null
}
const dateFormat = new Intl.DateTimeFormat('ru-RU', { dateStyle: 'long' })

async function finale() {
  Object.assign(ui, { phase: 'finale', finale: 'flight' })
  queue('act', 'game:finale')
  live = null
  aimCamera()
  await Promise.all(OUTER.map((id, i) => fly(id, i * 0.45)))
  if (!alive) return
  await hold(3)
  if (!alive) return

  // Back to the birthday: the rays go out, the quick bodies wind back whole turns.
  ui.finale = 'rewind'
  turning = 0
  await tween(0.5, (t) => {
    look.rays = 1 - t
  })
  const start = { ...ang }
  const birth = birthStamp()
  const today = Date.now()
  await tween(3.2, (t) => {
    for (const [body, turns] of Object.entries(REWIND)) ang[body] = wrap(start[body] + turns * 360 * (1 - t))
    if (birth !== null) ui.date = dateFormat.format(today - (today - birth) * t)
  })
  for (const body of Object.keys(REWIND)) ang[body] = start[body]
  if (!alive) return

  ui.finale = 'flash'
  ui.date = birth !== null ? dateFormat.format(birth) : formatDate(props.chart.moment) || ui.date
  ui.birth = [props.user?.birth?.time, props.user?.birth?.place].filter(Boolean).join(' · ')
  scene.shock(where().earth, { color: PALE, scale: 30, duration: 2 })
  for (let i = 0; i < 12; i += 1) if (signLit[i]) flares[i] = 0.9
  liveUntil = clock + 2.5
  tween(0.6, (t) => {
    look.rays = t
  }, curves.out)
  await hold(2.4)
  if (!alive) return

  // Straight above, turned and sized as the wheel beneath: the Ascendant on the left.
  ui.finale = 'rise'
  follow = false
  const spot = wheelSpot(geo.value)
  const base = props.chart.angles ? props.chart.angles.asc.lon : 0
  const from = { ...view }
  const az = from.az + gap(from.az, base + 90)
  const dist = scene.wheelDistance(spot.r)
  await tween(2.2, (t) => {
    view.az = from.az + (az - from.az) * t
    view.el = from.el + (89.9 - from.el) * t
    view.dist = from.dist * (dist / from.dist) ** t
    view.lx = from.lx * (1 - t)
    view.ly = from.ly * (1 - t)
    view.cx = from.cx + (spot.x - from.cx) * t
    view.cy = from.cy + (spot.y - from.cy) * t
    look.figures = 1 - 0.75 * t
    look.labels = 1 - t
  })
  if (!alive) return

  // The Earth to the middle, the bodies onto the wheel's ring where its glyphs stand.
  ui.finale = 'flip'
  const houses = Boolean(props.chart.houses)
  const ring = spot.r * (houses ? 0.635 : 0.68)
  const shown = spread(props.chart.points, (clamp(spot.r * 0.085, 12, 24) * 1.15) / ring / RAD)
  for (const id of ['sun', 'moon', 'mercury', 'venus', 'mars', ...OUTER]) wheelAt[id] = toward(shown[id], wheelRadius(houses))
  await tween(2, (t) => {
    look.slide = curves.inOut(Math.min(1, t * 1.6))
    look.flip = curves.inOut(clamp((t - 0.3) / 0.7, 0, 1))
    look.rays = 1 - Math.min(1, t * 2.5)
    look.orbits = 1 - Math.min(1, t * 1.5)
    look.figures = 0.25 * (1 - t)
    look.sky = 1 - t
    look.shrink = 1 - 0.4 * t
    look.earthShrink = 1 - t
    look.marker = Math.min(look.marker, 1 - t)
  }, curves.linear)
  if (!alive) return

  ui.finale = 'land'
  landed = true
  queue('act', 'game:land', (performance.now() - began) / 1000)
  reachGoal('astra.game@done')
  emit('land')
  ui.leaving = true
  document.documentElement.classList.remove('game-on')
  setTimeout(done, 1600)
}

function skip() {
  if (ui.finale !== 'land') flush()
}

/* ---- Leaving ---- */

function done() {
  if (closed) return
  closed = true
  emit('close')
}

function close() {
  if (ui.closing) return
  ui.closing = true
  if (!landed) stepAct('quit')
  alive = false
  tweens.clear()
  document.documentElement.classList.remove('game-on')
  setTimeout(done, reduce ? 0 : 450)
}

function onKey(event) {
  if (event.key === 'Escape') {
    event.preventDefault()
    event.stopPropagation()
    close()
    return
  }
  if (ui.phase !== 'play' || ui.busy) return
  const by = event.shiftKey ? 10 : 2
  if (event.key === 'ArrowRight' || event.key === 'ArrowUp') nudge(by)
  else if (event.key === 'ArrowLeft' || event.key === 'ArrowDown') nudge(-by)
  else if ((event.key === 'Enter' || event.key === ' ') && !(event.target instanceof HTMLButtonElement)) check()
  else return
  event.preventDefault()
}

function focusCard() {
  const target = ui.phase === 'intro' ? goEl.value : ui.phase === 'found' ? nextEl.value : titleEl.value
  target?.focus({ preventScroll: true })
}

function measure() {
  const el = root.value
  if (!el || !scene) return
  size.W = el.clientWidth
  size.H = el.clientHeight
  scene.resize(size.W, size.H, Math.min(window.devicePixelRatio || 1, LITE ? 1.25 : DPR[quality.value] ?? 1.25))
  aimCamera()
  liveUntil = clock + 0.3
}

watch(quality, measure)

onMounted(() => {
  scene = createScene(canvas.value, { lite: LITE, onLost: close })
  if (!scene) {
    queue('act', 'game:fail')
    done()
    return
  }
  view = scene.view
  measure()
  aimCamera(true)
  // The first look comes from a little farther and higher.
  view.dist *= 1.4
  view.el = 72
  observer = new ResizeObserver(measure)
  observer.observe(root.value)
  window.addEventListener('keydown', onKey, true)
  // The site's own sky rests once the backdrop has covered it.
  darkTimer = setTimeout(() => document.documentElement.classList.add('game-on'), 650)
  lastFrame = performance.now()
  raf = requestAnimationFrame(frame)
})

onBeforeUnmount(() => {
  alive = false
  cancelAnimationFrame(raf)
  clearTimeout(darkTimer)
  observer?.disconnect()
  window.removeEventListener('keydown', onKey, true)
  document.documentElement.classList.remove('game-on')
  tweens.clear()
  scene?.dispose()
  scene = null
  setTimeout(() => {
    if (opener?.isConnected && !document.activeElement?.closest?.('[role="dialog"]')) opener.focus?.({ preventScroll: true })
  })
})
</script>

<template>
  <div
    ref="root"
    class="natal-game"
    :class="{ 'is-narrow': narrow, 'is-leaving': ui.leaving, 'is-closing': ui.closing }"
    role="dialog"
    aria-modal="true"
    aria-label="Соберите своё небо"
  >
    <div class="backdrop" aria-hidden="true" />
    <canvas
      ref="canvas"
      class="scene"
      :class="{ 'can-drag': ui.phase === 'play' && !ui.busy, 'is-dragging': ui.dragging }"
      aria-label="Солнечная система и пояс знаков. Тяните, чтобы повернуть; стрелки тоже работают."
      @pointerdown="onDown"
      @pointermove="onMove"
      @pointerup="onUp"
      @pointercancel="onUp"
      @lostpointercapture="onUp"
    />

    <div class="tags" aria-hidden="true">
      <span v-for="label in LABELS" :key="label.id" :ref="(el) => setTag(label.id, el)" class="tag">
        <b v-if="label.glyph">{{ label.glyph }}</b><span class="tag-name">{{ label.name }}</span>
      </span>
      <span ref="cueEl" class="cue">
        <svg viewBox="-30 -30 60 60">
          <circle class="ring" r="20" />
          <g class="turn">
            <path class="arc" d="M20 0A20 20 0 0 0 -14.14 -14.14" />
            <path class="head" d="M-18.4 -9.9L-11.3 -11.3L-17 -17Z" />
          </g>
        </svg>
      </span>
      <span ref="hitEl" class="hit-tag" />
    </div>

    <div class="hud" :style="hudStyle">
      <Transition name="card" mode="out-in" appear @after-enter="focusCard">
        <section v-if="ui.phase === 'intro'" key="intro" class="card">
          <p class="kicker">Ваше небо</p>
          <h2 ref="titleEl" class="title" tabindex="-1">Соберите своё <em>небо</em></h2>
          <p class="text">
            Натальная карта — снимок неба в минуту вашего рождения. Знак планеты — это направление,
            в котором её видно с Земли. Расставьте Солнце, Луну и планеты по местам — и луч с Земли
            покажет знак каждой.
          </p>
          <div class="actions">
            <button ref="goEl" type="button" class="go" @click="begin">Начать</button>
            <button type="button" class="skip" @click="close">Сразу к карте</button>
          </div>
        </section>

        <section v-else-if="ui.phase !== 'finale'" :key="cardKey" class="card">
          <p class="kicker">
            Шаг {{ ui.index + 1 }} из {{ steps.length }}
            <span class="dots" aria-hidden="true">
              <i
                v-for="(item, i) in steps"
                :key="item.id"
                :class="{ done: i < ui.index || (i === ui.index && ui.phase === 'found'), now: i === ui.index }"
              />
            </span>
          </p>

          <template v-if="ui.phase === 'play'">
            <h2 ref="titleEl" class="title" tabindex="-1">
              <span v-if="glyphOf(step.id)" class="glyph">{{ glyphOf(step.id) }}</span>
              {{ POINTS[step.id].name }}
              <span class="chip">{{ sign.glyph }} {{ sign.name }}</span>
            </h2>
            <p class="text">{{ step.task }}</p>
            <p v-if="!narrow || ui.why" class="why">{{ step.why }}</p>
            <p class="readout" :class="{ 'is-match': ui.grabbed && ui.match && !ui.hint }" aria-live="polite">
              <template v-if="ui.hint">{{ ui.hint }}</template>
              <template v-else-if="ui.helped && !ui.grabbed">
                Нужный знак мерцает на поясе, а кольцо показывает, куда поставить {{ step.what }}.
              </template>
              <template v-else-if="!ui.grabbed">
                Тяните в любом месте экрана — {{ step.grab }}.<template v-if="!narrow"> Или стрелками ← →.</template>
              </template>
              <template v-else>
                Луч сейчас — {{ ui.readout }}.{{ ui.match ? (ui.keyed ? ' Нажмите Enter.' : ' Отпускайте!') : '' }}
              </template>
            </p>
            <div class="actions">
              <button v-if="!ui.helped" type="button" class="back" :disabled="ui.busy" @click="showHint">Подсказка</button>
              <button v-else type="button" class="back" :disabled="ui.busy" @click="placeForMe">Поставить за меня</button>
              <button v-if="narrow" type="button" class="skip" @click="ui.why = !ui.why">
                {{ ui.why ? 'Скрыть' : 'Почему так?' }}
              </button>
            </div>
          </template>

          <template v-else>
            <h2 class="title">
              <span v-if="glyphOf(step.id)" class="glyph">{{ glyphOf(step.id) }}</span>
              {{ POINTS[step.id].name }} {{ sign.in }}
            </h2>
            <p class="degree">{{ degrees(step.deg) }} {{ sign.of }}</p>
            <p v-if="essence(step.id)" class="essence">«{{ essence(step.id) }}»</p>
            <p v-else-if="!(step.id in ui.essence)" class="essence loading" aria-hidden="true"><span /><span /></p>
            <p v-if="step.approx" class="note">Время рождения не указано, поэтому положение Луны — примерное.</p>
            <div class="actions">
              <button ref="nextEl" type="button" class="go" @click="next">{{ last ? 'Остальные планеты' : 'Дальше' }}</button>
            </div>
          </template>
        </section>

        <section v-else key="finale" class="card">
          <p class="kicker">{{ finaleCopy.kicker }}</p>
          <h2 ref="titleEl" class="title sr-only" tabindex="-1">Ваша натальная карта</h2>
          <p v-if="ui.date" class="date">{{ ui.date }}</p>
          <p v-if="ui.birth && ui.finale !== 'rewind'" class="lead">{{ ui.birth }}</p>
          <Transition name="line" mode="out-in">
            <p :key="finaleCopy.text" class="text" aria-live="polite">{{ finaleCopy.text }}</p>
          </Transition>
          <div class="actions">
            <button v-if="ui.finale !== 'land'" type="button" class="skip" @click="skip">Пропустить</button>
          </div>
        </section>
      </Transition>
    </div>

    <button type="button" class="close" aria-label="Закрыть игру" @click="close">×</button>
  </div>
</template>

<style scoped>
.natal-game {
  position: fixed;
  inset: 0;
  z-index: 40;
  overflow: hidden;
  color: #efe7d8;
  transition: opacity 0.45s ease;
}
.natal-game.is-closing { opacity: 0; pointer-events: none; }
.natal-game.is-leaving { pointer-events: none; }

.backdrop {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(55% 45% at 28% 38%, rgba(74, 62, 128, 0.2), transparent 70%),
    radial-gradient(45% 40% at 72% 72%, rgba(128, 74, 52, 0.12), transparent 70%),
    radial-gradient(120% 90% at 50% 50%, #070a14, #03040a);
  animation: game-fade 0.6s ease both;
  transition: opacity 1s ease;
}
.scene {
  position: absolute;
  inset: 0;
  display: block;
  width: 100%;
  height: 100%;
  touch-action: none;
  animation: game-fade 1s ease 0.2s both;
  transition: opacity 1.4s ease;
}
.scene.can-drag { cursor: grab; }
.scene.is-dragging { cursor: grabbing; }
.is-leaving .backdrop,
.is-leaving .scene { opacity: 0; }
.is-leaving .hud,
.is-leaving .close,
.is-leaving .tags { opacity: 0; }

/* ---- Over the sky ---- */

.tags { position: absolute; inset: 0; pointer-events: none; transition: opacity 0.6s ease; }
.tag {
  position: absolute;
  left: 0;
  top: 0;
  display: inline-flex;
  align-items: baseline;
  gap: 5px;
  white-space: nowrap;
  font-size: 12px;
  letter-spacing: 0.04em;
  color: #f4e9d4;
  text-shadow: 0 1px 6px rgba(0, 0, 0, 0.95);
  opacity: 0;
  translate: -50% 0;
  will-change: transform, opacity;
}
.tag b { font-weight: 400; font-size: 14px; color: #f0cd8a; }
.tag.is-short .tag-name { display: none; }

.cue { position: absolute; left: 0; top: 0; opacity: 0; transition: opacity 0.4s ease; }
.cue.is-on { opacity: 1; }
.cue svg { position: absolute; left: -34px; top: -34px; width: 68px; height: 68px; overflow: visible; }
.cue .ring { fill: none; stroke: rgba(255, 226, 168, 0.7); stroke-width: 1.2; transform-box: view-box; transform-origin: 0 0; animation: cue-pulse 1.8s ease-out infinite; }
.cue .arc { fill: none; stroke: #ffe2a8; stroke-width: 1.6; stroke-linecap: round; }
.cue .head { fill: #ffe2a8; }
.cue .turn { transform-box: view-box; transform-origin: 0 0; animation: cue-turn 4s linear infinite; }

.hit-tag {
  position: absolute;
  left: 0;
  top: 0;
  padding: 3px 10px 4px;
  border-radius: 999px;
  border: 1px solid rgba(240, 205, 138, 0.35);
  background: rgba(8, 10, 18, 0.72);
  font-size: 13px;
  white-space: nowrap;
  color: #f4e9d4;
  opacity: 0;
  translate: -50% -50%;
  transition: opacity 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease, color 0.25s ease;
}
.hit-tag.is-on { opacity: 1; }
.hit-tag.is-match { border-color: rgba(240, 205, 138, 0.95); color: #fff1d4; box-shadow: 0 0 18px rgba(240, 190, 100, 0.45); }

/* ---- The card ---- */

.hud {
  position: absolute;
  top: 50%;
  translate: 0 -50%;
  max-height: calc(100% - 112px);
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-width: thin;
  transition: opacity 0.8s ease;
  animation: hud-in 0.7s cubic-bezier(0.3, 0.7, 0.2, 1) 0.35s both;
}
.is-narrow .hud { top: auto; bottom: 0; left: 0; right: 0; translate: none; max-height: none; }

.card {
  box-sizing: border-box;
  padding: 22px 26px 20px;
  border-radius: 22px;
  border: 1px solid rgba(240, 210, 150, 0.32);
  background:
    radial-gradient(120% 70% at 50% 0%, rgba(255, 196, 120, 0.12), transparent 60%),
    linear-gradient(160deg, rgba(26, 23, 26, 0.86), rgba(8, 10, 18, 0.92));
  box-shadow: 0 24px 70px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 240, 210, 0.1);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}
.is-narrow .card {
  min-height: 100%;
  padding: 16px 18px calc(14px + env(safe-area-inset-bottom));
  border-radius: 20px 20px 0 0;
  border-bottom: 0;
}

.kicker {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0;
  font-size: 10px;
  letter-spacing: 0.26em;
  text-transform: uppercase;
  color: rgba(233, 194, 124, 0.8);
}
.dots { display: inline-flex; gap: 5px; }
.dots i { width: 6px; height: 6px; border-radius: 50%; background: rgba(240, 205, 138, 0.2); transition: background 0.3s ease, box-shadow 0.3s ease; }
.dots i.now { background: rgba(240, 205, 138, 0.6); box-shadow: 0 0 0 3px rgba(240, 205, 138, 0.14); }
.dots i.done { background: #f0cd8a; }

.title { margin: 8px 0 10px; font-family: var(--serif); font-weight: 400; font-size: 28px; line-height: 1.15; color: #fff3da; outline: none; }
.title em { color: #f0cd8a; }
.glyph { color: #f0cd8a; }
.chip {
  display: inline-block;
  margin-left: 4px;
  padding: 2px 10px 3px;
  border-radius: 999px;
  border: 1px solid rgba(240, 205, 138, 0.45);
  background: rgba(240, 205, 138, 0.08);
  font-family: var(--book);
  font-size: 14px;
  vertical-align: 4px;
  color: #f6deae;
}
.text { margin: 0; font-family: var(--book); font-size: 15.5px; line-height: 1.5; color: rgba(239, 231, 216, 0.92); }
.why { margin: 10px 0 0; font-size: 13.5px; line-height: 1.5; color: rgba(226, 220, 210, 0.66); }
.readout {
  margin: 14px 0 0;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(240, 210, 150, 0.14);
  background: rgba(255, 240, 210, 0.05);
  font-size: 14px;
  line-height: 1.45;
  color: #f3e6cc;
  transition: border-color 0.3s ease, background 0.3s ease;
}
.readout.is-match { border-color: rgba(240, 205, 138, 0.6); background: rgba(240, 205, 138, 0.1); }
.degree { margin: -4px 0 12px; font-size: 13px; letter-spacing: 0.08em; color: rgba(233, 194, 124, 0.85); }
.essence { margin: 0; font-family: var(--serif); font-style: italic; font-size: 19px; line-height: 1.4; color: #f6ead2; }
.essence.loading span {
  display: block;
  height: 12px;
  margin: 9px 0;
  border-radius: 6px;
  background: linear-gradient(90deg, rgba(255, 240, 210, 0.05), rgba(255, 240, 210, 0.14), rgba(255, 240, 210, 0.05));
  background-size: 200% 100%;
  animation: shimmer 1.4s linear infinite;
}
.essence.loading span:last-child { width: 62%; }
.note { margin: 10px 0 0; font-size: 13px; line-height: 1.45; color: rgba(226, 220, 210, 0.66); }
.date { margin: 10px 0 4px; font-family: var(--serif); font-size: 34px; line-height: 1.1; color: #fff3da; font-variant-numeric: tabular-nums; }
.lead { margin: 0 0 10px; font-size: 14px; letter-spacing: 0.04em; color: rgba(233, 194, 124, 0.85); }
.sr-only { position: absolute; width: 1px; height: 1px; margin: -1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }

.actions { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 14px; margin-top: 16px; }
.go, .back, .skip { font: inherit; cursor: pointer; transition: background 0.25s ease, border-color 0.25s ease, color 0.25s ease, box-shadow 0.25s ease, opacity 0.25s ease; }
.go {
  min-width: 150px;
  padding: 10px 24px;
  border-radius: 999px;
  border: 1px solid rgba(240, 205, 138, 0.7);
  background: linear-gradient(180deg, rgba(240, 205, 138, 0.3), rgba(240, 205, 138, 0.12));
  font-size: 15px;
  color: #fff1d4;
}
.go:hover { background: linear-gradient(180deg, rgba(240, 205, 138, 0.42), rgba(240, 205, 138, 0.18)); box-shadow: 0 6px 24px rgba(230, 170, 80, 0.28); }
.back { padding: 9px 20px; border-radius: 999px; border: 1px solid rgba(240, 210, 150, 0.4); background: rgba(255, 240, 210, 0.04); font-size: 14px; color: #f3e6cc; }
.back:hover { border-color: rgba(240, 205, 138, 0.8); color: #fff1d4; }
.skip { padding: 8px 6px; border: 0; background: none; font-size: 13px; color: rgba(226, 220, 210, 0.65); }
.skip:hover { color: #f0cd8a; }
button:disabled { opacity: 0.45; cursor: default; }
.go:focus-visible, .back:focus-visible, .skip:focus-visible, .close:focus-visible { outline: 2px solid #ffe2a8; outline-offset: 3px; }
.is-narrow .go, .is-narrow .back, .is-narrow .skip { min-height: 44px; }

.close {
  position: absolute;
  top: 14px;
  right: 14px;
  width: 44px;
  height: 44px;
  padding: 0;
  border-radius: 50%;
  border: 1px solid rgba(240, 210, 150, 0.3);
  background: rgba(8, 10, 18, 0.55);
  font: inherit;
  font-size: 24px;
  line-height: 1;
  color: #f3e6cc;
  cursor: pointer;
  animation: game-fade 0.6s ease 0.4s both;
  transition: opacity 0.6s ease, border-color 0.25s ease, color 0.25s ease;
}
.close:hover { border-color: rgba(240, 205, 138, 0.8); color: #fff1d4; }
.is-narrow .close { top: 8px; right: 8px; }

.card-enter-active { transition: opacity 0.35s ease, translate 0.45s cubic-bezier(0.3, 0.7, 0.2, 1); }
.card-leave-active { transition: opacity 0.2s ease; }
.card-enter-from { opacity: 0; translate: 0 10px; }
.card-leave-to { opacity: 0; }
.line-enter-active, .line-leave-active { transition: opacity 0.3s ease; }
.line-enter-from, .line-leave-to { opacity: 0; }

@keyframes game-fade { from { opacity: 0; } }
@keyframes hud-in { from { opacity: 0; filter: blur(4px); } }
@keyframes shimmer { to { background-position: -200% 0; } }
@keyframes cue-turn { to { transform: rotate(-360deg); } }
@keyframes cue-pulse { from { transform: scale(0.6); opacity: 1; } to { transform: scale(1.5); opacity: 0; } }

@media (prefers-reduced-motion: reduce) {
  .backdrop, .scene, .hud, .close { animation-duration: 0.3s; animation-delay: 0s; }
  .cue .ring, .cue .turn, .essence.loading span { animation: none; }
  .card-enter-active { transition: opacity 0.2s ease; }
  .card-enter-from { translate: none; }
}
</style>
