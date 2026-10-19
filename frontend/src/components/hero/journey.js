/**
 * The home page is one trip along the ecliptic. Each section is a stop: the sky band pans east
 * (to the left, so everything on screen drifts right) by one screen width per stop, the planet
 * flies to its corner for that stop, and the Sun takes its place on the orbit.
 *
 * `journey` is a float: 2.5 means halfway between the third and the fourth stop.
 */
import { clamp, smoothstep } from './sky.js'
import { PROJECTED, ZODIAC, ZODIAC_BY_ID } from './zodiac.js'

/**
 * `frame`: where the orbit centre goes, as fractions of the screen, and the planet scale.
 * `signs`: east to west, so the first one is on the left. Positions are screen fractions at rest.
 * `theta`: the Sun on the orbit; null keeps the angle the visitor dragged it to.
 */
export const STOPS = [
  { id: 'hero', theta: null, frame: null },
  { id: 'how', theta: -0.95, frame: [0.8, 0.8, 0.44], signs: [['virgo', 0.58, 0.3], ['leo', 0.83, 0.22]] },
  { id: 'services', theta: 0.35, frame: [0.17, 0.87, 0.44], signs: [['scorpio', 0.14, 0.34], ['libra', 0.38, 0.2]] },
  { id: 'forecasts', theta: -1.5, frame: [0.86, 0.5, 0.32], signs: [['capricorn', 0.14, 0.2], ['sagittarius', 0.4, 0.17]] },
  { id: 'about', theta: -0.15, frame: [0.13, 0.94, 0.38], signs: [['pisces', 0.2, 0.2], ['aquarius', 0.45, 0.28]] },
  { id: 'start', theta: null, frame: null, loop: ['aries'] },
]

export const LAST_STOP = STOPS.length - 1

/** On phones the planet just waits in the corner between the hero and the finale. */
const NARROW_FRAME = [0.84, 0.97, 0.38]
const NARROW_SIGNS = [[0.28, 0.15], [0.72, 0.25]]
const HERO_NARROW = ['taurus', 'gemini']

/** Star radius in reference pixels from visual magnitude. */
export function starRadius(mag) {
  return clamp(0.9 + (4.6 - mag) * 0.62, 0.8, 3.4)
}

function build(figure, key, stop, cx, cy, size, scale, u) {
  const pts = PROJECTED[figure.id]
  const stars = figure.stars.map((star, index) => ({
    ...star,
    x: cx + pts[index].x * size,
    y: cy + pts[index].y * size,
    r: starRadius(star.mag) * Math.max(0.75, scale),
  }))
  const xs = stars.map((s) => s.x)
  const ys = stars.map((s) => s.y)
  const top = Math.min(...ys)
  const box = {
    x: Math.min(...xs) - 22 * u,
    y: top - 22 * u,
    w: Math.max(...xs) - Math.min(...xs) + 44 * u,
    h: Math.max(...ys) - top + 44 * u,
  }
  return {
    ...figure,
    key,
    stop,
    cx,
    cy,
    span: size,
    stars,
    box,
    labelX: figure.label ? cx + figure.label[0] * scale : cx,
    labelY: figure.label ? cy + figure.label[1] * scale : top - 16 * Math.max(scale, 0.7),
  }
}

/** Half width of a placed figure, to keep it inside the screen. */
function halfWidth(figure, size) {
  return Math.max(...PROJECTED[figure.id].map((p) => Math.abs(p.x))) * size
}

/**
 * All figures in band coordinates: screen coordinates at the hero. A figure shows at `x + pan`.
 */
export function placeBand(geo) {
  const { u, orbit, W, H, narrow } = geo
  const margin = 18 + 40 * u
  const list = []

  const heroScale = narrow ? u * 0.82 : u
  const hero = ZODIAC.filter((figure) => figure.at && (!narrow || HERO_NARROW.includes(figure.id)))
  const heroPlace = (figure, key, stop, shift) => {
    const size = figure.size * heroScale
    const half = halfWidth(figure, size)
    const cx = clamp(orbit.cx + figure.at[0] * u, margin + half, W - margin - half) - shift
    return build(figure, key, stop, cx, orbit.cy + figure.at[1] * u, size, heroScale, u)
  }
  hero.forEach((figure) => list.push(heroPlace(figure, figure.id, 0, 0)))

  STOPS.forEach((stop, index) => {
    stop.signs?.forEach(([id, fx, fy], order) => {
      const figure = ZODIAC_BY_ID[id]
      const scale = narrow ? u * 0.6 : u
      const size = figure.size * scale
      const half = halfWidth(figure, size)
      const [nx, ny] = narrow ? NARROW_SIGNS[order] : [fx, fy]
      const x = clamp(nx * W, margin + half, W - margin - half)
      const y = Math.max(ny * H, 90 + size / 2)
      list.push(build(figure, id, index, x - index * W, y, size, scale, u))
    })
    stop.loop?.forEach((id) => list.push(heroPlace(ZODIAC_BY_ID[id], `${id}@loop`, index, index * W)))
  })
  return list
}

/** Holds still around each stop and moves in between, so a section is read on a calm sky. */
function settle(f) {
  const t = clamp((f - 0.12) / 0.76, 0, 1)
  return t * t * t * (t * (t * 6 - 15) + 10)
}

function frameOf(geo, index) {
  const stop = STOPS[index]
  const spec = geo.narrow && index > 0 && index < LAST_STOP ? NARROW_FRAME : stop.frame
  if (!spec) return { s: 1, tx: 0, ty: 0 }
  const [fx, fy, s] = spec
  return { s, tx: fx * geo.W - geo.orbit.cx * s, ty: fy * geo.H - geo.orbit.cy * s }
}

const mix = (a, b, t) => a + (b - a) * t

/** Everything the sky needs at a point of the journey. */
export function sceneAt(geo, journey, userTheta) {
  const j = clamp(journey, 0, LAST_STOP)
  const k = Math.min(Math.floor(j), LAST_STOP - 1)
  const e = settle(j - k)
  const a = frameOf(geo, k)
  const b = frameOf(geo, k + 1)
  const ta = STOPS[k].theta ?? userTheta
  const tb = STOPS[k + 1].theta ?? userTheta
  return {
    pan: geo.W * (k + e),
    frame: { s: mix(a.s, b.s, e), tx: mix(a.tx, b.tx, e), ty: mix(a.ty, b.ty, e) },
    theta: mix(ta, tb, e),
    // 1 on the hero, fading to 0 as soon as the planet leaves.
    hero: 1 - smoothstep(0.05, 0.35, j),
  }
}

/** Applies the planet frame to a point of the hero layout. */
export function framed(frame, point) {
  return { x: point.x * frame.s + frame.tx, y: point.y * frame.s + frame.ty }
}
