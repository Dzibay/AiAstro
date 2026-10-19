import { SIGNS } from '../../utils/skyToday.js'

/** Words and glyphs for the chart that GET /me/chart returns (backend app/astro/chart.py). */

// U+FE0E keeps every glyph a glyph instead of a coloured emoji on Windows and iOS.
const text = (glyph) => `${glyph}\uFE0E`

/** `with`: the instrumental case, for «трин с Венерой». */
export const POINTS = {
  sun: { glyph: text('☉'), name: 'Солнце', with: 'Солнцем' },
  moon: { glyph: text('☽'), name: 'Луна', with: 'Луной' },
  mercury: { glyph: text('☿'), name: 'Меркурий', with: 'Меркурием' },
  venus: { glyph: text('♀'), name: 'Венера', with: 'Венерой' },
  mars: { glyph: text('♂'), name: 'Марс', with: 'Марсом' },
  jupiter: { glyph: text('♃'), name: 'Юпитер', with: 'Юпитером' },
  saturn: { glyph: text('♄'), name: 'Сатурн', with: 'Сатурном' },
  uranus: { glyph: text('♅'), name: 'Уран', with: 'Ураном' },
  neptune: { glyph: text('♆'), name: 'Нептун', with: 'Нептуном' },
  pluto: { glyph: text('♇'), name: 'Плутон', with: 'Плутоном' },
  node: { glyph: text('☊'), name: 'Лунный узел', with: 'Лунным узлом' },
  asc: { glyph: 'Asc', name: 'Асцендент', with: 'Асцендентом' },
  mc: { glyph: 'MC', name: 'Середина неба', with: 'Серединой неба' },
}

/** `tone`: gold for the easy ones, muted red for the tense, a dot for the conjunction. */
export const ASPECTS = {
  conjunction: { glyph: text('☌'), name: 'Соединение', tone: 'joint' },
  sextile: { glyph: text('⚹'), name: 'Секстиль', tone: 'easy' },
  square: { glyph: text('□'), name: 'Квадрат', tone: 'tense' },
  trine: { glyph: text('△'), name: 'Трин', tone: 'easy' },
  opposition: { glyph: text('☍'), name: 'Оппозиция', tone: 'tense' },
}

export const SIGN_BY_ID = Object.fromEntries(SIGNS.map((sign) => [sign.id, { ...sign, glyph: text(sign.glyph) }]))
export const SIGN_LIST = SIGNS.map((sign) => SIGN_BY_ID[sign.id])

export const ELEMENTS = [
  { id: 'fire', name: 'Огонь' },
  { id: 'earth', name: 'Земля' },
  { id: 'air', name: 'Воздух' },
  { id: 'water', name: 'Вода' },
]
export const MODES = [
  { id: 'cardinal', name: 'Кардинальный' },
  { id: 'fixed', name: 'Фиксированный' },
  { id: 'mutable', name: 'Мутабельный' },
]

export const ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII']

/** 18.4 → «18°24′». */
export function degrees(deg) {
  let whole = Math.floor(deg)
  let minutes = Math.round((deg - whole) * 60)
  if (minutes === 60) {
    whole += 1
    minutes = 0
  }
  return `${whole}°${String(minutes).padStart(2, '0')}′`
}

/** The planets, the node and, when the time is known, the two angles: everything a reading exists for. */
export function chartItems(chart) {
  const items = chart.points.map((point) => ({ ...point }))
  if (chart.angles) {
    for (const id of ['asc', 'mc']) items.push({ id, ...chart.angles[id] })
  }
  return items
}
