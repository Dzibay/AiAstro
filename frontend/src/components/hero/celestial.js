/** Decorative sky geometry. Star figures follow real asterisms, scaled for the hero, not a chart. */

export const MOON_OFFSET = 1.65
export const FRAME_W = 1280
export const FRAME_H = 720
export const ORBIT_CX = 640
export const ORBIT_CY = 631.36
export const ORBIT_R = 551
/** Half-width of the visible arc, radians, clockwise from the apex. */
export const ARC_LIMIT = 1.370091005590015
const TAU = Math.PI * 2

const SKY = [
  [0, '#070a16'],
  [0.18, '#0b1224'],
  [0.34, '#141a33'],
  [0.46, '#241c36'],
  [0.56, '#4a3040'],
  [0.66, '#a45b3a'],
  [0.76, '#e7c59a'],
  [0.88, '#f1e4cc'],
  [1, '#f6efe3'],
]

const INK_LIGHT = '#f3efe6'
const INK_DARK = '#2a2116'
const MUTED_LIGHT = '#d5d0c6'
const MUTED_DARK = '#6d6254'
const LINE_NIGHT = '#c6b89a'
const LINE_DAY = '#8d6a32'
const STAR_NIGHT = '#d5e2f4'
const STAR_DAY = '#b08948'

export const CONSTELLATIONS = [
  {
    id: 'aries',
    name: 'Овен',
    text: 'Прямой старт и собственный импульс: где вам легче начать, чем ждать удобного часа.',
    interactive: true,
    stars: [
      { x: 0.055, y: 0.22, r: 1.35, glow: 0.35 },
      { x: 0.098, y: 0.175, r: 1.7, glow: 0.55 },
      { x: 0.148, y: 0.142, r: 2.35, glow: 0.9 },
      { x: 0.198, y: 0.168, r: 1.45, glow: 0.4 },
      { x: 0.118, y: 0.232, r: 1.55, glow: 0.5 },
    ],
    edges: [
      [0, 1],
      [1, 2],
      [2, 3],
      [1, 4],
    ],
  },
  {
    id: 'taurus',
    name: 'Телец',
    text: 'Устойчивость и вкус к вещественному: что держит форму, когда вокруг меняется темп.',
    interactive: true,
    stars: [
      { x: 0.036, y: 0.4, r: 1.05, glow: 0.3 },
      { x: 0.052, y: 0.372, r: 1.1, glow: 0.35 },
      { x: 0.068, y: 0.398, r: 1.15, glow: 0.4 },
      { x: 0.1, y: 0.432, r: 1.45, glow: 0.45 },
      { x: 0.142, y: 0.478, r: 2.45, glow: 1 },
      { x: 0.182, y: 0.438, r: 1.5, glow: 0.5 },
      { x: 0.2, y: 0.512, r: 1.4, glow: 0.4 },
      { x: 0.228, y: 0.362, r: 1.85, glow: 0.7 },
      { x: 0.252, y: 0.488, r: 1.5, glow: 0.45 },
    ],
    edges: [
      [0, 3],
      [1, 3],
      [2, 3],
      [3, 4],
      [4, 5],
      [5, 7],
      [4, 6],
      [6, 8],
    ],
  },
  {
    id: 'capricorn',
    name: 'Козерог',
    text: 'Долгий контур: срок, ответственность и собранный ход без лишнего шума.',
    interactive: true,
    stars: [
      { x: 0.735, y: 0.168, r: 1.45, glow: 0.4 },
      { x: 0.79, y: 0.128, r: 1.7, glow: 0.6 },
      { x: 0.848, y: 0.15, r: 1.4, glow: 0.4 },
      { x: 0.912, y: 0.118, r: 1.65, glow: 0.55 },
      { x: 0.888, y: 0.205, r: 1.5, glow: 0.45 },
      { x: 0.808, y: 0.214, r: 2.15, glow: 0.85 },
      { x: 0.748, y: 0.228, r: 1.3, glow: 0.35 },
    ],
    edges: [
      [0, 1],
      [1, 2],
      [2, 3],
      [2, 4],
      [4, 5],
      [5, 6],
      [6, 0],
      [5, 1],
    ],
  },
  {
    id: 'scorpio',
    name: 'Скорпион',
    text: 'Глубина и предел: где разговор лучше довести до ясной точки, а не оборвать.',
    interactive: true,
    stars: [
      { x: 0.772, y: 0.318, r: 1.35, glow: 0.35 },
      { x: 0.828, y: 0.292, r: 1.3, glow: 0.3 },
      { x: 0.812, y: 0.358, r: 1.6, glow: 0.5 },
      { x: 0.858, y: 0.402, r: 2.5, glow: 1 },
      { x: 0.9, y: 0.452, r: 1.5, glow: 0.45 },
      { x: 0.932, y: 0.508, r: 1.45, glow: 0.4 },
      { x: 0.948, y: 0.568, r: 1.4, glow: 0.4 },
      { x: 0.9, y: 0.598, r: 1.9, glow: 0.75 },
      { x: 0.862, y: 0.552, r: 1.35, glow: 0.35 },
    ],
    edges: [
      [0, 2],
      [1, 2],
      [2, 3],
      [3, 4],
      [4, 5],
      [5, 6],
      [6, 7],
      [6, 8],
    ],
  },
  {
    id: 'lyra',
    name: 'Лира',
    text: '',
    interactive: false,
    stars: [
      { x: 0.4, y: 0.09, r: 1.15, glow: 0.2 },
      { x: 0.438, y: 0.07, r: 1.7, glow: 0.45 },
      { x: 0.47, y: 0.1, r: 1.1, glow: 0.2 },
      { x: 0.432, y: 0.122, r: 1.15, glow: 0.2 },
    ],
    edges: [
      [0, 1],
      [1, 2],
      [2, 3],
      [3, 0],
      [0, 2],
    ],
  },
  {
    id: 'cup',
    name: 'Чаша',
    text: '',
    interactive: false,
    stars: [
      { x: 0.56, y: 0.078, r: 1.05, glow: 0.15 },
      { x: 0.598, y: 0.06, r: 1.2, glow: 0.25 },
      { x: 0.63, y: 0.09, r: 1.05, glow: 0.15 },
      { x: 0.6, y: 0.118, r: 1.1, glow: 0.2 },
      { x: 0.555, y: 0.112, r: 1, glow: 0.12 },
    ],
    edges: [
      [0, 1],
      [1, 2],
      [2, 3],
      [3, 4],
      [4, 0],
    ],
  },
]

export function wrap01(value) {
  return ((value % 1) + 1) % 1
}

export function wrapDelta(from, to) {
  let delta = to - from
  if (delta > 0.5) delta -= 1
  if (delta < -0.5) delta += 1
  return delta
}

export function smoothstep(edge0, edge1, value) {
  const t = clamp01((value - edge0) / (edge1 - edge0))
  return t * t * (3 - 2 * t)
}

export function clamp01(value) {
  return Math.min(1, Math.max(0, value))
}

export function hexToRgb(hex) {
  const value = Number.parseInt(hex.slice(1), 16)
  return [(value >> 16) & 255, (value >> 8) & 255, value & 255]
}

export function mixHex(from, to, amount) {
  const left = hexToRgb(from)
  const right = hexToRgb(to)
  const t = clamp01(amount)
  const channels = left.map((channel, index) => Math.round(channel + (right[index] - channel) * t))
  return `rgb(${channels.join(' ')})`
}

export function rgba(hex, alpha) {
  const [r, g, b] = hexToRgb(hex)
  return `rgba(${r}, ${g}, ${b}, ${clamp01(alpha)})`
}

function sample(stops, amount) {
  const t = clamp01(amount)
  for (let index = 1; index < stops.length; index += 1) {
    if (t <= stops[index][0]) {
      const [start, from] = stops[index - 1]
      const [end, to] = stops[index]
      return mixHex(from, to, (t - start) / (end - start || 1))
    }
  }
  return stops[stops.length - 1][1]
}

function parseColor(color) {
  if (color.startsWith('#')) return hexToRgb(color)
  const channels = color.match(/\d+/g)
  if (!channels) return [0, 0, 0]
  return channels.slice(0, 3).map(Number)
}

function luminance(color) {
  const [r, g, b] = parseColor(color).map((channel) => {
    const value = channel / 255
    return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

export function sunTheta(phase) {
  return wrap01(phase) * Math.PI * 2
}

export function moonTheta(phase) {
  return sunTheta(phase) + MOON_OFFSET
}

export function pointOnOrbit(cx, cy, radius, theta) {
  return {
    x: cx + radius * Math.sin(theta),
    y: cy - radius * Math.cos(theta),
  }
}

export function thetaFromPointer(x, y, cx, cy) {
  return Math.atan2(x - cx, -(y - cy))
}

export function phaseLabel(phase) {
  const theta = sunTheta(phase)
  const elev = Math.cos(theta)
  const side = Math.sin(theta)
  if (elev > 0.86) return 'День'
  if (elev > 0.55) return side < 0 ? 'Утро' : 'После полудня'
  if (elev > 0.18) return side < 0 ? 'Рассвет' : 'Закат'
  if (elev > -0.35) return 'Сумерки'
  return 'Ночь'
}

export function sceneFromPhase(phase) {
  const safe = wrap01(phase)
  const theta = sunTheta(safe)
  const elev = Math.cos(theta)
  const light = smoothstep(0.84, 0.995, elev)
  const horizon = Math.exp(-((light - 0.6) ** 2) / 0.045)
  const sky = sample(SKY, light)
  const inkMix = smoothstep(0.22, 0.58, luminance(sky))
  const ink = mixHex(INK_LIGHT, INK_DARK, inkMix)
  const muted = mixHex(MUTED_LIGHT, MUTED_DARK, inkMix)
  const line = mixHex(LINE_NIGHT, LINE_DAY, smoothstep(0.45, 0.82, light))
  const star = mixHex(STAR_NIGHT, STAR_DAY, light)
  const night = 1 - light
  const pageBg = mixHex('#101614', '#f4efe4', smoothstep(0.58, 0.86, light))
  const pageInk = mixHex('#f4efe6', '#241c14', smoothstep(0.52, 0.78, light))
  const pageMuted = mixHex('#b7c2b8', '#6e6256', smoothstep(0.52, 0.8, light))
  const raised = mixHex('#1a2420', '#fffaf3', smoothstep(0.58, 0.88, light))

  return {
    phase: safe,
    theta,
    moon: moonTheta(safe),
    elev,
    light,
    horizon,
    night,
    label: phaseLabel(safe),
    sky,
    ink,
    muted,
    line,
    star,
    layers: {
      base: 1 - light * 0.9,
      warm: 0.8 - light * 0.52,
      cool: 0.62 * (1 - light),
      mist: 0.22 + night * 0.12,
      dust: 0.12 + night * 0.1,
      haze: 0.16 + night * 0.1,
      stars: 0.28 + night * 0.72,
      atmosphere: 0.5 + night * 0.45,
      clouds: 0.35 + night * 0.4,
    },
    vars: {
      '--sky': sky,
      '--hero-ink': ink,
      '--hero-muted': muted,
      '--hero-line': line,
      '--hero-star': star,
      '--hero-shadow': inkMix > 0.55 ? 'rgba(255, 250, 240, 0.72)' : 'rgba(5, 8, 20, 0.55)',
      '--sun-wash': `rgba(255, 168, 84, ${(horizon * 0.42 + light * 0.05).toFixed(3)})`,
      '--moon-wash': `rgba(158, 186, 214, ${(night * 0.28).toFixed(3)})`,
      '--bg': pageBg,
      '--ink': pageInk,
      '--muted': pageMuted,
      '--bg-raised': raised,
      '--line': inkMix > 0.5 ? 'rgba(42, 33, 22, 0.12)' : 'rgba(244, 239, 230, 0.16)',
    },
  }
}

export function orbitLayout(width, height) {
  const apexY = Math.max(78, height * 0.105)
  const sideY = height * 0.66
  const sideX = Math.min(width * 0.44, height * 0.7)
  const cy = (sideX * sideX + sideY * sideY - apexY * apexY) / (2 * (sideY - apexY))
  const orbitR = Math.max(120, cy - apexY)
  const planetTop = height * 0.63
  const planetR = Math.max(width * 0.72, height * 0.98)
  const planetCy = planetTop + planetR
  const unit = Math.min(Math.max(Math.min(width, height) / 860, 0.72), 1.18)
  return {
    w: width,
    h: height,
    cx: width / 2,
    cy,
    orbitR,
    planetR,
    planetCy,
    planetTop,
    apexY,
    unit,
  }
}

export function visualQuality() {
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const cores = navigator.hardwareConcurrency || 8
  const memory = navigator.deviceMemory || 8
  const narrow = window.matchMedia('(max-width: 760px)').matches
  const saveData = navigator.connection?.saveData
  const low = narrow || cores <= 4 || memory <= 4 || saveData
  return {
    reduce,
    low,
    stars: reduce ? 0.28 : low ? 0.48 : 1,
    clouds: !reduce,
    twinkle: !reduce,
    parallax: !reduce,
    dpr: Math.min(window.devicePixelRatio || 1, low ? 1.25 : 1.7),
  }
}

export function mulberry32(seed) {
  let state = seed
  return () => {
    state |= 0
    state = (state + 0x6d2b79f5) | 0
    let value = Math.imul(state ^ (state >>> 15), 1 | state)
    value = (value + Math.imul(value ^ (value >>> 7), 61 | value)) ^ value
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296
  }
}

export function signedTheta(theta) {
  let turn = ((theta % TAU) + TAU) % TAU
  if (turn > Math.PI) turn -= TAU
  return turn
}

export function clampSharedPhase(phase) {
  const min = -ARC_LIMIT
  const max = ARC_LIMIT - MOON_OFFSET
  let signed = signedTheta(sunTheta(phase))
  if (signed < min) signed = min
  if (signed > max) signed = max
  return wrap01(signed / TAU)
}

export function frameFit(stageW, stageH) {
  const aspect = FRAME_W / FRAME_H
  let w
  let h
  let x
  let y
  if (stageW < 760) {
    const scale = (stageW * 0.94) / 1080
    w = FRAME_W * scale
    h = w / aspect
    x = (stageW - w) / 2
    y = stageH * 0.02
    const horizon = y + (395 / FRAME_H) * h
    if (horizon > stageH * 0.78) y -= horizon - stageH * 0.78
  } else if (stageW / Math.max(stageH, 1) > aspect) {
    w = stageW
    h = stageW / aspect
    x = 0
    y = (stageH - h) / 2
  } else {
    h = stageH
    w = stageH * aspect
    x = (stageW - w) / 2
    y = 0
  }
  return { x, y, w, h, scale: w / FRAME_W }
}

export function initialPhase() {
  try {
    const saved = sessionStorage.getItem('astra-phase')
    if (saved != null && saved !== '' && !Number.isNaN(Number(saved))) return clampSharedPhase(Number(saved))
  } catch {
    /* private mode */
  }
  return 0.887
}

export function placeFigures(width, height, compact) {
  return CONSTELLATIONS.filter((item) => (compact ? item.interactive : true)).map((item) => {
    const stars = item.stars.map((star) => {
      let x = star.x
      let y = star.y
      if (compact) {
        x = x < 0.5 ? x * 0.9 : 1 - (1 - x) * 0.9
        y = y * 0.88 + 0.03
      }
      return { ...star, x: x * width, y: y * height }
    })
    const top = stars.reduce((best, star) => (star.y < best.y ? star : best), stars[0])
    const midX = stars.reduce((sum, star) => sum + star.x, 0) / stars.length
    return {
      ...item,
      stars,
      labelX: midX,
      labelY: top.y - 16,
      edges: item.edges.map(([from, to], index) => {
        const a = stars[from]
        const b = stars[to]
        return {
          index,
          d: `M ${a.x} ${a.y} L ${b.x} ${b.y}`,
          length: Math.hypot(a.x - b.x, a.y - b.y),
        }
      }),
    }
  })
}

export function angDiff(a, b) {
  let delta = Math.abs(a - b) % (Math.PI * 2)
  if (delta > Math.PI) delta = Math.PI * 2 - delta
  return delta
}
