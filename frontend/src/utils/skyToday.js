/**
 * The sky of a given day, computed in the browser. Low-precision series (about a degree),
 * enough to name the signs of the Sun and Moon and the Moon's phase.
 */

const RAD = Math.PI / 180

export const SIGNS = [
  { id: 'aries', glyph: '♈', name: 'Овен', in: 'в Овне', of: 'Овна' },
  { id: 'taurus', glyph: '♉', name: 'Телец', in: 'в Тельце', of: 'Тельца' },
  { id: 'gemini', glyph: '♊', name: 'Близнецы', in: 'в Близнецах', of: 'Близнецов' },
  { id: 'cancer', glyph: '♋', name: 'Рак', in: 'в Раке', of: 'Рака' },
  { id: 'leo', glyph: '♌', name: 'Лев', in: 'во Льве', of: 'Льва' },
  { id: 'virgo', glyph: '♍', name: 'Дева', in: 'в Деве', of: 'Девы' },
  { id: 'libra', glyph: '♎', name: 'Весы', in: 'в Весах', of: 'Весов' },
  { id: 'scorpio', glyph: '♏', name: 'Скорпион', in: 'в Скорпионе', of: 'Скорпиона' },
  { id: 'sagittarius', glyph: '♐', name: 'Стрелец', in: 'в Стрельце', of: 'Стрельца' },
  { id: 'capricorn', glyph: '♑', name: 'Козерог', in: 'в Козероге', of: 'Козерога' },
  { id: 'aquarius', glyph: '♒', name: 'Водолей', in: 'в Водолее', of: 'Водолея' },
  { id: 'pisces', glyph: '♓', name: 'Рыбы', in: 'в Рыбах', of: 'Рыб' },
]

const wrap360 = (deg) => ((deg % 360) + 360) % 360
const sin = (deg) => Math.sin(deg * RAD)

/** Days since J2000.0 (2000-01-01 12:00 TT). */
function daysSinceJ2000(date) {
  return date.getTime() / 86400000 + 2440587.5 - 2451545
}

/** Ecliptic longitudes of the Sun and Moon, degrees. */
export function longitudes(date = new Date()) {
  const n = daysSinceJ2000(date)
  const g = 357.528 + 0.9856003 * n
  const sun = wrap360(280.46 + 0.9856474 * n + 1.915 * sin(g) + 0.02 * sin(2 * g))
  const l = 218.316 + 13.176396 * n
  const m = 134.963 + 13.064993 * n
  const d = 297.85 + 12.190749 * n
  const moon = wrap360(l + 6.289 * sin(m) - 1.274 * sin(2 * d - m) + 0.658 * sin(2 * d) - 0.186 * sin(g))
  return { sun, moon }
}

export const signOf = (longitude) => SIGNS[Math.floor(wrap360(longitude) / 30)]

function phaseName(elongation) {
  if (elongation < 12 || elongation > 348) return 'новолуние'
  if (Math.abs(elongation - 180) < 12) return 'полнолуние'
  if (Math.abs(elongation - 90) < 12) return 'первая четверть'
  if (Math.abs(elongation - 270) < 12) return 'последняя четверть'
  return elongation < 180 ? 'растущая' : 'убывающая'
}

/** Signs of the Sun and Moon and the Moon's phase for a date. */
export function skyOn(date = new Date()) {
  const { sun, moon } = longitudes(date)
  const elongation = wrap360(moon - sun)
  return {
    sun: signOf(sun),
    moon: signOf(moon),
    elongation,
    waxing: elongation < 180,
    lit: Math.round(((1 - Math.cos(elongation * RAD)) / 2) * 100),
    phase: phaseName(elongation),
  }
}
