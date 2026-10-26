import { pageName } from './shared.js'

/**
 * The way from a first visit to a payment (pulse.py): the steps' names for the funnel (people in
 * plural), for one person's card, for the table heads, and the words the insights are put in.
 * Registration begins with the address: the letter's link or code opens the cabinet, the birth
 * data and the chart come there.
 */
export const WAY = [
  { key: 'visit', label: 'Первый визит', one: 'Первый визит', short: 'Визит', hint: 'впервые открыли сайт за срок' },
  { key: 'start', label: 'Начали вводить почту', one: 'Начал вводить почту', short: 'Почта', hint: 'в любой форме входа', verb: 'начинают вводить почту', of: 'зашедших на сайт' },
  { key: 'signup', label: 'Запросили письмо', one: 'Запросил письмо', short: 'Письмо', hint: 'аккаунт создан, письмо ушло', verb: 'запрашивают письмо', of: 'начавших вводить почту' },
  { key: 'confirm', label: 'Открыли кабинет', one: 'Открыл кабинет', short: 'Кабинет', hint: 'по ссылке или коду из письма', verb: 'открывают кабинет по письму', of: 'запросивших письмо' },
  { key: 'birth', label: 'Указали рождение', one: 'Указал рождение', short: 'Рождение', hint: 'дата, время, город', verb: 'указывают данные рождения', of: 'открывших кабинет' },
  { key: 'chart', label: 'Увидели карту', one: 'Увидел карту', short: 'Карта', hint: 'натальная карта построена', verb: 'смотрят свою карту', of: 'указавших рождение' },
  { key: 'checkout', label: 'Начали оплату', one: 'Начал оплату', short: 'Оплата', hint: 'перешли в ЮKassa', verb: 'начинают оплату', of: 'увидевших карту' },
  { key: 'paid', label: 'Оплатили', one: 'Оплатил', short: 'Оплатили', hint: 'хоть что-нибудь', verb: 'оплачивают', of: 'начавших оплату' },
]
export const WAY_BY_KEY = Object.fromEntries(WAY.map((step) => [step.key, step]))

/** The period before, for the comparisons: «прошлые 30 дней», «прошлый год». */
export const periodName = (days) => (days === 365 ? 'прошлый год' : `прошлые ${days} дней`)

/** Fewer people than this at a step's start say nothing about its share (as MIN_BASE in pulse.py). */
export const MIN_BASE = 20

/** A share from 0 to 1 in per cent: «4,2%», «38%». */
export function share(rate) {
  if (rate == null || Number.isNaN(rate)) return '—'
  const value = rate * 100
  const digits = value === 0 || value >= 10 ? 0 : value < 1 ? 2 : 1
  return `${value.toLocaleString('ru-RU', { maximumFractionDigits: digits })}%`
}

/** The share of a step from the one before it; null if nobody reached the one before. */
export function rateOf(steps, index) {
  const base = steps?.[WAY[index - 1]?.key]
  return base ? steps[WAY[index].key] / base : null
}

/** A change of a share in percentage points, with its sign: «+3,2 п.п.», «−12 п.п.». */
export function points(diff) {
  const value = Math.abs(diff * 100)
  const text = value.toLocaleString('ru-RU', { maximumFractionDigits: value < 10 ? 1 : 0 })
  return `${diff > 0 ? '+' : diff < 0 ? '−' : '±'}${text} п.п.`
}

/** A change of a count against the period before: «+12%», «новое». */
export function growth(now, before) {
  if (!before) return now ? { text: 'было 0', tone: 'up' } : null
  const change = Math.round(((now - before) / before) * 100)
  return { text: `${change > 0 ? '+' : change < 0 ? '−' : '±'}${Math.abs(change)}%`, tone: change > 0 ? 'up' : change < 0 ? 'down' : 'flat' }
}

export const DEVICE_NAMES = { phone: 'Телефон', desktop: 'Компьютер', unknown: 'Не определено' }
const DEVICE_WHERE = { phone: 'на телефоне', desktop: 'на компьютере', unknown: 'на неопределённых устройствах' }

/** A channel key of pulse.py: 'ref:<id>', 'site:<host>' or 'direct'; label — the link's name or the host. */
export function channelName(key, label) {
  if (key === 'direct') return 'Прямые заходы'
  if (key?.startsWith('ref:')) return `Ссылка «${label}»`
  if (key?.startsWith('site:')) return label || key.slice(5)
  return label || key
}

/** One row of a split: a channel, a first page or a device; the rest lumped together has no key. */
export function segmentName(by, row) {
  if (!row.key) return `Остальные (${row.others})`
  if (by === 'channel') return channelName(row.key, row.label)
  if (by === 'device') return DEVICE_NAMES[row.key] || row.key
  return row.key === 'unknown' ? 'Не определено' : pageName(row.key)
}

const capital = (text) => text.charAt(0).toUpperCase() + text.slice(1)

/** What stands out (pulse.py, _insights), in words: { tone, text }. period — «прошлые 30 дней». */
export function insightText(item, period) {
  const step = WAY_BY_KEY[item.step]
  const what = `${share(item.rate)} из ${step.of} ${step.verb}`
  switch (item.kind) {
    case 'shift':
      return `${capital(what)} — за ${period} было ${share(item.other)}`
    case 'narrow':
      return `Самый узкий шаг: ${what}, дальше не идут ${item.lost.toLocaleString('ru-RU')} чел.`
    case 'device':
      return `${capital(DEVICE_WHERE[item.segment])} ${what} — ${DEVICE_WHERE[item.against]} ${share(item.other)}`
    case 'segment': {
      const who = item.by === 'channel'
        ? channelName(item.segment, item.label)
        : `Вход через «${pageName(item.segment).replace(/[«»]/g, '')}»`
      return `${who}: ${what} — у остальных ${share(item.other)}`
    }
    default:
      return ''
  }
}

/* ---- Week by week (pulse.py, weeks): three shares, each its own small chart ---- */

export const WEEK_LINES = [
  { key: 'signup', from: 'visit', name: 'Визит → письмо', hint: 'запросили письмо из новых посетителей недели', of: 'посетителей', color: '#3987e5' },
  { key: 'confirm', from: 'signup', name: 'Письмо → кабинет', hint: 'открыли кабинет по письму из запросивших его', of: 'запросивших', color: '#d95926' },
  { key: 'paid', from: 'confirm', name: 'Кабинет → оплата', hint: 'оплатили из открывших кабинет', of: 'открывших', color: '#199e70' },
]

const weekDay = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'short' })
const asDay = (iso) => new Date(`${iso}T12:00:00`)

/** The points of one line for LineChart: the week's share, of how many, finished or still counted. */
export function weekPoints(items, line) {
  return items.map((row) => {
    const start = asDay(row.week)
    const end = new Date(start.getTime() + 6 * 864e5)
    const whole = row[line.from]
    return {
      key: row.week,
      label: weekDay.format(start).replace('.', ''),
      title: `${weekDay.format(start).replace('.', '')} — ${weekDay.format(end).replace('.', '')}`,
      value: whole ? row[line.key] / whole : null,
      part: row[line.key],
      whole,
      done: row.done,
    }
  })
}
