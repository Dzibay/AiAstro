import { POINTS, SIGN_BY_ID } from '../cabinet/astro.js'

/** Words for what the forecast adds beyond the transits (backend app/astro/forecast.py). */

export const SPHERES = [
  { id: 'love', name: 'Любовь и близкие' },
  { id: 'work', name: 'Дела и цели' },
  { id: 'talk', name: 'Разговоры и учёба' },
  { id: 'energy', name: 'Силы и тело' },
]

export const SPHERE_TONES = { easy: 'легко', tense: 'бережно', calm: 'ровно' }

/** The Moon's eight phases: a name and a glyph that draws it. */
export const PHASES = {
  new: { name: 'Новолуние', glyph: '●' },
  crescent: { name: 'Молодая Луна', glyph: '☽' },
  first_quarter: { name: 'Первая четверть', glyph: '◐' },
  gibbous: { name: 'Растущая Луна', glyph: '◐' },
  full: { name: 'Полнолуние', glyph: '○' },
  disseminating: { name: 'Убывающая Луна', glyph: '◑' },
  last_quarter: { name: 'Последняя четверть', glyph: '◑' },
  balsamic: { name: 'Старая Луна', glyph: '☾' },
}

/** «Полнолуние в Тельце», «Меркурий разворачивается попятно». */
export function eventLine(event) {
  const sign = SIGN_BY_ID[event.sign]
  const name = POINTS[event.planet].name
  switch (event.kind) {
    case 'new_moon': return `Новолуние ${sign.in}`
    case 'full_moon': return `Полнолуние ${sign.in}`
    case 'retro': return `${name} разворачивается попятно ${sign.in}`
    case 'direct': return `${name} снова идёт прямо ${sign.in}`
    case 'ingress': return `${name} входит в знак ${sign.of}`
    default: return ''
  }
}

/** The mark of an event in the calendar: the Moon's disc or the planet's glyph. */
export function eventGlyph(event) {
  if (event.kind === 'new_moon') return '●'
  if (event.kind === 'full_moon') return '○'
  return POINTS[event.planet].glyph
}
