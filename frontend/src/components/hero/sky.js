/**
 * Hero geometry. The reference frame is 1770×889: orbit r = 554, planet R = 1180,
 * planet top 640, orbit centre 36 px below it. Everything scales with `u`.
 */

export const TAU = Math.PI * 2

/** Moon trails the Sun along the orbit by this angle, radians. */
export const MOON_OFFSET = 1.1
/** Sun angle limits, radians clockwise from the apex. At the ends one body sets behind the planet. */
export const SUN_MIN = -1.86
export const SUN_MAX = 0.76
export const SUN_HOME = -0.4

export function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

export function smoothstep(edge0, edge1, value) {
  const t = clamp((value - edge0) / (edge1 - edge0), 0, 1)
  return t * t * (3 - 2 * t)
}

export function signedAngle(theta) {
  let turn = ((theta % TAU) + TAU) % TAU
  if (turn > Math.PI) turn -= TAU
  return turn
}

export function layout(width, height) {
  const W = Math.max(width, 1)
  const H = Math.max(height, 1)
  const narrow = W < 760
  let u
  let planetTop
  if (narrow) {
    u = W / 700
    // Copy sits on top; the orbit opens below it so the Sun and Moon never cover the text.
    planetTop = Math.max(H * 0.78, 470 + 560 * u)
  } else {
    u = Math.min(H / 889, W / 1500)
    const orbitTop = Math.max(H * 0.137, 92)
    planetTop = orbitTop + 518 * u
  }
  const cx = W / 2
  const planetR = 1180 * u
  return {
    W,
    H,
    u,
    narrow,
    cx,
    orbit: { cx, cy: planetTop + 36 * u, r: 554 * u },
    planet: { cx, cy: planetTop + planetR, r: planetR, top: planetTop },
  }
}

export function onOrbit(orbit, theta, inset = 0) {
  const r = orbit.r - inset
  return { x: orbit.cx + r * Math.sin(theta), y: orbit.cy - r * Math.cos(theta) }
}

export function angleAt(orbit, x, y) {
  return Math.atan2(x - orbit.cx, -(y - orbit.cy))
}

/** 0 = cold night (Moon high, Sun set), 1 = warm (Sun high, Moon set). */
export function warmthOf(sunTheta) {
  const sunUp = Math.cos(sunTheta)
  const moonUp = Math.cos(sunTheta + MOON_OFFSET)
  return smoothstep(-0.9, 0.9, sunUp - moonUp + 0.15)
}

/**
 * Zodiac figures from the Hipparcos positions (J2000, degrees) and the usual IAU stick figures.
 * `at` is the figure centre relative to the orbit centre in reference pixels, `size` the larger side.
 */
export const ZODIAC = [
  {
    id: 'aries',
    name: 'Овен',
    glyph: '♈',
    dates: '21 марта — 19 апреля',
    element: 'Огонь',
    ruler: 'Марс',
    alpha: 'Хамаль',
    text: 'Прямой старт и собственный импульс: где вам легче начать, чем ждать удобного часа.',
    animal: 'Баран',
    modality: 'Кардинальный',
    traits: ['Смелость', 'Инициатива', 'Прямота'],
    myth: 'Золотой баран, унёсший Фрикса за море. За его руном потом отправились аргонавты.',
    at: [-628, -500],
    size: 128,
    label: [26, -10],
    stars: [
      { name: 'Мезартим', ra: 28.383, dec: 19.294, mag: 3.9 },
      { name: 'Шератан', ra: 28.66, dec: 20.808, mag: 2.64 },
      { name: 'Хамаль', ra: 31.793, dec: 23.462, mag: 2.0 },
      { name: '41 Овна', ra: 42.496, dec: 27.26, mag: 3.6 },
      { name: '39 Овна', ra: 41.977, dec: 29.247, mag: 4.5 },
      { name: '35 Овна', ra: 40.863, dec: 27.707, mag: 4.6 },
    ],
    edges: [[0, 1], [1, 2], [2, 3], [3, 4], [3, 5]],
  },
  {
    id: 'taurus',
    name: 'Телец',
    glyph: '♉',
    dates: '20 апреля — 20 мая',
    element: 'Земля',
    ruler: 'Венера',
    alpha: 'Альдебаран',
    text: 'Устойчивость и вкус к вещественному: что держит форму, когда вокруг меняется темп.',
    animal: 'Бык',
    modality: 'Фиксированный',
    traits: ['Надёжность', 'Чувственность', 'Терпение'],
    myth: 'Зевс в облике белого быка, похитивший Европу. На плече у него Плеяды, глазом горит Альдебаран.',
    at: [-724, -270],
    size: 238,
    label: [60, -34],
    stars: [
      { name: 'Альдебаран', ra: 68.98, dec: 16.509, mag: 0.85 },
      { name: 'Эльнат', ra: 81.573, dec: 28.608, mag: 1.65 },
      { name: 'Тяньгуань', ra: 84.411, dec: 21.143, mag: 3.0 },
      { name: 'Тета² Тельца', ra: 67.166, dec: 15.871, mag: 3.4 },
      { name: 'Прима Гиад', ra: 64.948, dec: 15.628, mag: 3.65 },
      { name: 'Дельта¹ Тельца', ra: 65.734, dec: 17.543, mag: 3.76 },
      { name: 'Аин', ra: 67.154, dec: 19.18, mag: 3.53 },
      { name: 'Лямбда Тельца', ra: 60.17, dec: 12.49, mag: 3.4 },
      { name: 'Омикрон Тельца', ra: 51.203, dec: 9.029, mag: 3.6 },
      { name: 'Кси Тельца', ra: 51.792, dec: 9.733, mag: 3.7 },
      { name: 'Альциона', ra: 56.871, dec: 24.105, mag: 2.87, cluster: true },
      { name: 'Атлас', ra: 57.29, dec: 24.053, mag: 3.62, cluster: true },
      { name: 'Электра', ra: 56.219, dec: 24.113, mag: 3.7, cluster: true },
      { name: 'Майя', ra: 56.457, dec: 24.368, mag: 3.87, cluster: true },
      { name: 'Меропа', ra: 56.581, dec: 23.948, mag: 4.18, cluster: true },
      { name: 'Тайгета', ra: 56.302, dec: 24.467, mag: 4.3, cluster: true },
    ],
    edges: [[1, 6], [6, 5], [5, 4], [2, 0], [0, 3], [3, 4], [4, 7], [7, 8], [8, 9]],
  },
  {
    id: 'capricorn',
    name: 'Козерог',
    glyph: '♑',
    dates: '22 декабря — 19 января',
    element: 'Земля',
    ruler: 'Сатурн',
    alpha: 'Денеб Альгеди',
    text: 'Долгий контур: срок, ответственность и собранный ход без лишнего шума.',
    animal: 'Козерыба',
    modality: 'Кардинальный',
    traits: ['Дисциплина', 'Амбиции', 'Выдержка'],
    myth: 'Пан, прыгнувший в Нил от Тифона: голова козла, хвост рыбы. Одно из древнейших созвездий.',
    at: [540, -478],
    size: 150,
    label: [92, -14],
    stars: [
      { name: 'Альгеди', ra: 304.514, dec: -12.545, mag: 3.57 },
      { name: 'Дабих', ra: 305.253, dec: -14.781, mag: 3.05 },
      { name: 'Пси Козерога', ra: 311.524, dec: -25.271, mag: 4.13 },
      { name: 'Омега Козерога', ra: 312.955, dec: -26.919, mag: 4.1 },
      { name: 'Дзета Козерога', ra: 321.667, dec: -22.411, mag: 3.74 },
      { name: 'Денеб Альгеди', ra: 326.76, dec: -16.127, mag: 2.85 },
      { name: 'Нашира', ra: 325.023, dec: -16.662, mag: 3.67 },
      { name: 'Йота Козерога', ra: 320.562, dec: -16.834, mag: 4.27 },
      { name: 'Тета Козерога', ra: 316.487, dec: -17.232, mag: 4.07 },
    ],
    edges: [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7], [7, 8], [8, 1]],
  },
  {
    id: 'scorpio',
    name: 'Скорпион',
    glyph: '♏',
    dates: '23 октября — 21 ноября',
    element: 'Вода',
    ruler: 'Плутон и Марс',
    alpha: 'Антарес',
    text: 'Глубина и предел: где разговор лучше довести до ясной точки, а не оборвать.',
    animal: 'Скорпион',
    modality: 'Фиксированный',
    traits: ['Интенсивность', 'Проницательность', 'Верность'],
    myth: 'Скорпион, посланный против Ориона. С тех пор они никогда не стоят на небе вместе.',
    at: [668, -262],
    size: 236,
    label: [96, -60],
    stars: [
      { name: 'Акраб', ra: 241.359, dec: -19.805, mag: 2.62 },
      { name: 'Дшубба', ra: 240.083, dec: -22.622, mag: 2.29 },
      { name: 'Пи Скорпиона', ra: 239.713, dec: -26.114, mag: 2.89 },
      { name: 'Ро Скорпиона', ra: 239.221, dec: -29.214, mag: 3.87 },
      { name: 'Сигма Скорпиона', ra: 245.297, dec: -25.593, mag: 2.89 },
      { name: 'Антарес', ra: 247.352, dec: -26.432, mag: 1.06 },
      { name: 'Тау Скорпиона', ra: 248.971, dec: -28.216, mag: 2.82 },
      { name: 'Эпсилон Скорпиона', ra: 252.541, dec: -34.293, mag: 2.29 },
      { name: 'Мю¹ Скорпиона', ra: 252.968, dec: -38.047, mag: 3.0 },
      { name: 'Дзета² Скорпиона', ra: 253.646, dec: -42.362, mag: 3.62 },
      { name: 'Эта Скорпиона', ra: 258.038, dec: -43.239, mag: 3.33 },
      { name: 'Саргас', ra: 264.33, dec: -42.998, mag: 1.86 },
      { name: 'Йота¹ Скорпиона', ra: 266.896, dec: -40.127, mag: 2.99 },
      { name: 'Каппа Скорпиона', ra: 265.622, dec: -39.03, mag: 2.39 },
      { name: 'Шаула', ra: 263.402, dec: -37.104, mag: 1.62 },
      { name: 'Лесат', ra: 262.691, dec: -37.296, mag: 2.7 },
    ],
    edges: [
      [0, 1], [1, 2], [2, 3], [1, 4], [4, 5], [5, 6], [6, 7], [7, 8],
      [8, 9], [9, 10], [10, 11], [11, 12], [12, 13], [13, 14], [14, 15],
    ],
  },
]

/** Tangent-plane projection, east to the left as on a sky map. Returns points in -0.5..0.5 of the larger side. */
function project(figure) {
  const ra0 = figure.stars.reduce((sum, star) => sum + star.ra, 0) / figure.stars.length
  const dec0 = figure.stars.reduce((sum, star) => sum + star.dec, 0) / figure.stars.length
  const toRad = Math.PI / 180
  const raw = figure.stars.map((star) => {
    const dra = (star.ra - ra0) * toRad
    const dec = star.dec * toRad
    const d0 = dec0 * toRad
    const cosc = Math.sin(d0) * Math.sin(dec) + Math.cos(d0) * Math.cos(dec) * Math.cos(dra)
    const x = (Math.cos(dec) * Math.sin(dra)) / cosc
    const y = (Math.cos(d0) * Math.sin(dec) - Math.sin(d0) * Math.cos(dec) * Math.cos(dra)) / cosc
    return { x: -x, y: -y }
  })
  const xs = raw.map((p) => p.x)
  const ys = raw.map((p) => p.y)
  const minX = Math.min(...xs)
  const minY = Math.min(...ys)
  const span = Math.max(Math.max(...xs) - minX, Math.max(...ys) - minY)
  const w = (Math.max(...xs) - minX) / span
  const h = (Math.max(...ys) - minY) / span
  return raw.map((p) => ({ x: (p.x - minX) / span - w / 2, y: (p.y - minY) / span - h / 2 }))
}

const PROJECTED = Object.fromEntries(ZODIAC.map((figure) => [figure.id, project(figure)]))

/** Star radius in reference pixels from visual magnitude. */
export function starRadius(mag) {
  return clamp(0.9 + (4.6 - mag) * 0.62, 0.8, 3.4)
}

export function placeZodiac(geo) {
  const { u, orbit, W } = geo
  const scale = geo.narrow ? u * 0.82 : u
  // Phones only have room inside the orbit, where the small figures would collide with the bodies.
  const list = geo.narrow ? ZODIAC.filter((figure) => figure.id === 'taurus' || figure.id === 'scorpio') : ZODIAC
  return list.map((figure) => {
    const size = figure.size * scale
    let cx = orbit.cx + figure.at[0] * u
    const cy = orbit.cy + figure.at[1] * u
    const pts = PROJECTED[figure.id]
    const half = Math.max(...pts.map((p) => Math.abs(p.x))) * size
    const margin = 18 + 40 * u
    cx = clamp(cx, margin + half, W - margin - half)
    const stars = figure.stars.map((star, index) => ({
      ...star,
      x: cx + pts[index].x * size,
      y: cy + pts[index].y * size,
      r: starRadius(star.mag) * Math.max(0.75, scale),
    }))
    const xs = stars.map((s) => s.x)
    const ys = stars.map((s) => s.y)
    const box = {
      x: Math.min(...xs) - 22 * u,
      y: Math.min(...ys) - 22 * u,
      w: Math.max(...xs) - Math.min(...xs) + 44 * u,
      h: Math.max(...ys) - Math.min(...ys) + 44 * u,
    }
    return {
      ...figure,
      cx,
      cy,
      span: size,
      stars,
      box,
      labelX: cx + figure.label[0] * scale,
      labelY: cy + figure.label[1] * scale,
    }
  })
}
