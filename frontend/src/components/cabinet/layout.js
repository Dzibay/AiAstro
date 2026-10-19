import { clamp } from '../hero/sky.js'

/**
 * The cabinet as a sky: the person's star and four small constellations around it, one per
 * section. On the overview they stand in a ring about the star; once a section is open the
 * star steps back to the corner and the four gather in a fan beside it, so the middle of the
 * sky is free for the section itself. Both NameMark and CabinetSky place themselves from here.
 */

/**
 * `stars`: [x, y, size] in a unit box around the point; `edges` join them.
 * Each figure hints at its section: a wheel, a sunrise arc, two stars, a line of speech.
 */
export const SECTIONS = [
  {
    id: 'chart',
    route: 'cabinet-chart',
    label: 'Карта',
    title: 'Натальная карта',
    stars: [[0, -0.95, 1.2], [0.9, -0.3, 0.8], [0.56, 0.8, 0.9], [-0.56, 0.8, 0.7], [-0.9, -0.3, 0.9]],
    edges: [[0, 1], [1, 2], [2, 3], [3, 4], [4, 0]],
  },
  {
    id: 'forecast',
    route: 'cabinet-forecast',
    label: 'Прогноз',
    title: 'Прогноз на день и неделю',
    stars: [[-1, 0.55, 0.7], [-0.45, -0.25, 0.9], [0.3, -0.6, 1.2], [0.95, -0.15, 0.8]],
    edges: [[0, 1], [1, 2], [2, 3]],
  },
  {
    id: 'pair',
    route: 'cabinet-pair',
    label: 'Пара',
    title: 'Совместимость',
    stars: [[-0.75, 0.15, 1.2], [0.75, -0.15, 1.15], [0.05, 0.85, 0.55]],
    edges: [[0, 1]],
  },
  {
    id: 'chat',
    route: 'cabinet-chat',
    label: 'Астролог',
    title: 'Разговор с астрологом',
    stars: [[-0.95, -0.35, 0.8], [-0.1, -0.85, 1.15], [0.9, -0.2, 0.9], [0.2, 0.55, 0.7], [-0.35, 0.95, 0.55]],
    edges: [[0, 1], [1, 2], [2, 3], [3, 4]],
  },
]

export const SECTION_BY_ID = Object.fromEntries(SECTIONS.map((section) => [section.id, section]))

/** The overview first, then the sections: the order of swipes on the phone sheet. */
export const ROUTE_ORDER = ['cabinet', ...SECTIONS.map((section) => section.route)]

/** The panel hugs the right edge (CabinetView): its width and its gap to the edge. */
const PANEL_WIDTH = 420
export function panelLeft(W) {
  return W - clamp(W * 0.08, 20, 150) - PANEL_WIDTH
}

/** On phones the sky is kept at least 780px tall for the home page; the sheet follows the window. */
export function skyHeight(geo) {
  return geo.narrow ? Math.min(geo.H, window.innerHeight || geo.H) : geo.H
}

/** Where the phone sheet starts when lowered, as a share of the window (CabinetView: 58svh tall). */
export const SHEET_TOP = 0.42

/** The size of the Sun sign engraving around the star before the camera's zoom `k`. */
export function markSpan(geo) {
  const V = skyHeight(geo)
  return geo.narrow ? clamp(V * 0.34 - 114, 90, Math.min(geo.W * 0.44, 170)) : clamp(geo.H * 0.4, 220, 330)
}

/** FNV-1a: the same name always finds the same point of the sky. */
function hash(text) {
  let h = 0x811c9dc5
  for (const char of text) {
    h ^= char.codePointAt(0)
    h = Math.imul(h, 0x01000193)
  }
  return h >>> 0
}

/**
 * The person's star on the login sky ({ x, y, span, k }), found by `key` (the name): in the free
 * sky beside the card, the same name always at the same point. NameMark and the invitation use it.
 */
export function loginSpot(geo, key) {
  const { W, H, narrow } = geo
  const h = hash(key.toLocaleLowerCase('ru'))
  const a = (h & 0xffff) / 0xffff
  const b = (h >>> 16) / 0xffff
  const span = markSpan(geo)
  let x0
  let x1
  let y0
  let y1
  const V = skyHeight(geo)
  if (narrow) {
    // Phones: the strip of sky above the sheet (LoginView: 34vh), with room for the caption.
    x0 = W * 0.1 + span / 2
    x1 = W * 0.72 - span / 2
    y0 = 70 + span / 2
    y1 = Math.max(y0, V * 0.34 - 40 - span / 2)
  } else {
    // Between the orbit's left half and the card, which hugs the right edge.
    const cardLeft = W - clamp(W * 0.08, 20, 150) - 392
    x0 = W * 0.3 + span / 2
    x1 = Math.max(x0, cardLeft - 40 - span / 2)
    y0 = 96 + span / 2
    y1 = Math.max(y0, H * 0.62 - span / 2)
  }
  return { x: x0 + (x1 - x0) * a, y: y0 + (y1 - y0) * b, span, k: 1 }
}

const rad = (deg) => (deg * Math.PI) / 180

/** The star ({ x, y, k, span }) and the section points ({ id, x, y, s }) for a section, '' for the overview. */
export function cabinetLayout(geo, section) {
  const { W, H, narrow } = geo
  const V = skyHeight(geo)
  const span = markSpan(geo)
  const open = Boolean(section)
  let star
  let points

  if (narrow) {
    // The sky is a strip above the sheet; the four stand in a row along its lower edge.
    const sheet = V * SHEET_TOP
    const rowY = sheet - 46
    if (open) {
      const k = 0.5
      star = { x: 26 + (span * k) / 2, y: 70 + (span * k) / 2, k }
    } else {
      const k = clamp((sheet - 170) / span, 0.55, 1.3)
      star = { x: W / 2, y: 74 + (span * k) / 2, k }
    }
    points = SECTIONS.map((item, index) => ({ id: item.id, x: W * (0.14 + index * 0.24), y: rowY, s: 0.78 }))
  } else if (open) {
    const k = 0.42
    star = { x: clamp(W * 0.07, 70, 120), y: clamp(H * 0.2, 140, 170), k }
    const reach = clamp(H * 0.28, 160, 210)
    points = SECTIONS.map((item, index) => {
      const angle = rad(20 + index * 25)
      return { id: item.id, x: star.x + reach * Math.cos(angle), y: star.y + reach * Math.sin(angle), s: 0.85 }
    })
  } else {
    const k = clamp((H * 0.52) / span, 1.15, 1.6)
    const half = (span * k) / 2
    const right = panelLeft(W) - 40
    star = { x: clamp(W * 0.3, half + 24, right - half), y: clamp(H * 0.42, 100 + half, H - half - 60), k }
    const reach = half + 56
    points = SECTIONS.map((item, index) => {
      const angle = rad([-140, -40, 40, 140][index])
      return {
        id: item.id,
        x: clamp(star.x + reach * Math.cos(angle), 70, right - 20),
        y: clamp(star.y + reach * Math.sin(angle), 120, H - 80),
        s: 1,
      }
    })
  }
  return { W, H, star: { ...star, span }, points }
}

/**
 * The natal wheel's centre and outer radius ({ x, y, r }), drawn on the sky while the chart is open.
 * On a phone it fills the strip beside the star; on a desktop it takes the room between the fan
 * of sections and the panel, as large as it goes without touching either.
 */
export function wheelSpot(geo) {
  const { W, H, narrow } = geo
  const { star, points } = cabinetLayout(geo, 'chart')
  const starHalf = (star.span * star.k) / 2
  if (narrow) {
    const top = 80
    const bottom = skyHeight(geo) * SHEET_TOP - 92
    const r = Math.max(60, Math.min((bottom - top) / 2, W * 0.42))
    const x = clamp(Math.max(W / 2, star.x + starHalf + r + 6), r + 8, W - r - 8)
    return { x, y: (top + bottom) / 2, r }
  }
  const right = panelLeft(W) - 36
  const top = 100
  const bottom = H - 36
  const place = (r) => ({ x: right - r, y: clamp(H * 0.54, top + r, bottom - r), r })
  let r = Math.min((bottom - top) / 2, (right - star.x - 40) / 2)
  for (; r > 120; r -= 4) {
    const spot = place(r)
    const clear = points.every((point) => Math.hypot(point.x - spot.x, point.y - spot.y) > r + 46)
      && Math.hypot(star.x - spot.x, star.y - spot.y) > r + starHalf + 12
    if (clear) return spot
  }
  return place(r)
}

const mix = (a, b, t) => a + (b - a) * t

/** A layout part way between two, for the flight from one section to another. */
export function mixLayout(a, b, t) {
  return {
    W: b.W,
    H: b.H,
    star: { x: mix(a.star.x, b.star.x, t), y: mix(a.star.y, b.star.y, t), k: mix(a.star.k, b.star.k, t), span: b.star.span },
    points: b.points.map((point, index) => {
      const from = a.points[index] || point
      return { id: point.id, x: mix(from.x, point.x, t), y: mix(from.y, point.y, t), s: mix(from.s, point.s, t) }
    }),
  }
}

/** The star itself is drawn at a readable size whatever the zoom of its engraving. */
export function starScale(k) {
  return clamp(k, 0.9, 1.3)
}
