import { onBeforeUnmount, ref, watch } from 'vue'
import { errorText } from '../../api/http.js'
import { readSession } from '../../composables/useSession.js'

/** One sign-in for every page: a 401 anywhere takes the operator back to the password. */
export const authed = ref(Boolean(readSession('admin')))

export function failed(error) {
  if (error?.status === 401) authed.value = false
  return errorText(error)
}

const day = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'short', year: 'numeric' })
const moment = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
const long = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })

export const fmt = {
  day: (value) => (value ? day.format(new Date(value)) : '—'),
  moment: (value) => (value ? moment.format(new Date(value)) : '—'),
  long: (value) => (value ? long.format(new Date(value)) : '—'),
  /** A birth date stored as YYYY-MM-DD: read as a calendar day, not as UTC midnight. */
  birth: (value) => (value ? day.format(new Date(`${value}T12:00:00`)) : '—'),
  rub: (value) => `${Number(value || 0).toLocaleString('ru-RU')} ₽`,
  count: (value) => Number(value || 0).toLocaleString('ru-RU'),
  /** 1 200 → «1,2 тыс.», for the axes. */
  compact: (value) =>
    new Intl.NumberFormat('ru-RU', { notation: 'compact', maximumFractionDigits: 1 }).format(value),
}

/* ---- The charts' columns ---- */

const shortDay = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'short' })
const fullDay = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })
const monthShort = new Intl.DateTimeFormat('ru-RU', { month: 'short' })
const monthLong = new Intl.DateTimeFormat('ru-RU', { month: 'long', year: 'numeric' })
const asDay = (iso) => new Date(`${iso}T12:00:00`)
const clean = (text) => text.replace('.', '')

/**
 * Days for a week or a month; weeks for 90 days, months for a year,
 * so that a column never shrinks to a hair.
 */
export function buckets(series, field, days) {
  if (!series.length) return []
  if (days <= 30) {
    return series.map((row) => ({ key: row.day, label: clean(shortDay.format(asDay(row.day))), title: fullDay.format(asDay(row.day)), value: row[field] }))
  }
  const groups = new Map()
  if (days <= 90) {
    // Seven-day weeks ending today: the last column is the current week.
    const n = series.length
    series.forEach((row, i) => {
      const k = Math.floor((n - 1 - i) / 7)
      const g = groups.get(k) || { first: row.day, last: row.day, value: 0 }
      g.first = g.first < row.day ? g.first : row.day
      g.last = g.last > row.day ? g.last : row.day
      g.value += row[field]
      groups.set(k, g)
    })
    return [...groups.entries()]
      .sort((a, b) => b[0] - a[0])
      .map(([k, g]) => ({
        key: `w${k}`,
        label: clean(shortDay.format(asDay(g.first))),
        title: `${shortDay.format(asDay(g.first))} — ${shortDay.format(asDay(g.last))}`,
        value: g.value,
      }))
  }
  series.forEach((row) => {
    const month = row.day.slice(0, 7)
    const g = groups.get(month) || { value: 0 }
    g.value += row[field]
    groups.set(month, g)
  })
  return [...groups.entries()].map(([month, g]) => ({
    key: month,
    label: clean(monthShort.format(asDay(`${month}-15`))),
    title: monthLong.format(asDay(`${month}-15`)),
    value: g.value,
  }))
}

export const PAYMENT_STATUS = {
  succeeded: 'оплачен',
  pending: 'ждёт оплаты',
  new: 'создан',
  canceled: 'отменён',
  failed: 'не создан',
}

export const PRODUCTS = {
  sky1: '«Небосвод», 1 месяц',
  sky3: '«Небосвод», 3 месяца',
  sky12: '«Небосвод», 12 месяцев',
  synastry: 'Разбор пары',
}

export function plural(n, one, few, many) {
  const mod10 = n % 10
  const mod100 = n % 100
  const word = mod10 === 1 && mod100 !== 11 ? one : mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14) ? few : many
  return word
}

/** When this person was last on the site, in Moscow time: «сегодня, 14:32», «3 дня назад». */
export function seen(value) {
  if (!value) return 'не заходил'
  const stamp = (at) => {
    const parts = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'Europe/Moscow', year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
    }).formatToParts(new Date(at))
    const get = (type) => parts.find((part) => part.type === type)?.value || ''
    return { day: `${get('year')}-${get('month')}-${get('day')}`, time: `${get('hour')}:${get('minute')}` }
  }
  const then = stamp(value)
  const now = stamp(Date.now())
  if (then.day === now.day) return `сегодня, ${then.time}`
  const diff = Math.round((Date.parse(`${now.day}T12:00:00Z`) - Date.parse(`${then.day}T12:00:00Z`)) / 864e5)
  if (diff === 1) return `вчера, ${then.time}`
  if (diff > 1 && diff < 7) return `${diff} ${plural(diff, 'день', 'дня', 'дней')} назад`
  return new Intl.DateTimeFormat('ru-RU', { timeZone: 'Europe/Moscow', day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(value))
}

/** The «Небосвод» date field works in Moscow days, as the server does. */
export function moscowDay(value) {
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Moscow', year: 'numeric', month: '2-digit', day: '2-digit' })
  return parts.format(value ? new Date(value) : new Date())
}

/**
 * A searchable, filterable list fetched a page at a time.
 * fetchPage({ q, state, offset }) gives { items, more }.
 */
export function usePagedList(fetchPage, { state = '' } = {}) {
  const q = ref('')
  const filter = ref(state)
  const items = ref([])
  const more = ref(false)
  const loading = ref(false)
  const error = ref('')
  let asked = 0
  let timer = 0

  async function load(append = false) {
    const ticket = ++asked
    loading.value = true
    error.value = ''
    try {
      const data = await fetchPage({ q: q.value, state: filter.value, offset: append ? items.value.length : 0 })
      // An older answer must not overwrite the list of a newer query.
      if (ticket !== asked) return
      items.value = append ? [...items.value, ...data.items] : data.items
      more.value = data.more
    } catch (caught) {
      if (ticket === asked) error.value = failed(caught)
    } finally {
      if (ticket === asked) loading.value = false
    }
  }

  watch(q, () => {
    clearTimeout(timer)
    timer = setTimeout(() => load(), 300)
  })
  watch(filter, () => load())
  onBeforeUnmount(() => clearTimeout(timer))

  return { q, filter, items, more, loading, error, load, loadMore: () => load(true) }
}

/* ---- What the analytics' names mean ---- */

export const PERIODS = [
  { days: 7, label: '7 дней' },
  { days: 30, label: '30 дней' },
  { days: 90, label: '90 дней' },
  { days: 365, label: 'Год' },
]

export const stepOf = (days) => (days <= 30 ? 'по дням' : days <= 90 ? 'по неделям' : 'по месяцам')

const PAGE_NAMES = {
  home: 'Главная',
  login: 'Вход и регистрация',
  invite: 'Приглашение в пару',
  legal: 'Документы',
  cabinet: 'Кабинет: обзор',
  'cabinet-birth': 'Кабинет: данные рождения',
  'cabinet-profile': 'Кабинет: профиль',
  'cabinet-chart': 'Карта',
  'cabinet-forecast': 'Прогноз',
  'cabinet-pair': 'Пара',
  'cabinet-chat': 'Астролог',
  'cabinet-sky': '«Небосвод»',
  'lp-natal': 'Посадочная: натальная карта',
  'lp-pair': 'Посадочная: совместимость',
  'lp-forecast': 'Посадочная: личный гороскоп',
  'lp-asc': 'Посадочная: Асцендент',
  'lp-lilith': 'Посадочная: Лилит',
  'lp-chiron': 'Посадочная: Хирон',
  other: 'Другие адреса',
}
const LEGAL = { offer: 'оферта', privacy: 'политика', consent: 'согласие' }

export function pageName(name) {
  if (!name) return 'не открывал страниц'
  if (name.startsWith('legal:')) return `Документы: ${LEGAL[name.slice(6)] || name.slice(6)}`
  return PAGE_NAMES[name] || name
}

const SECTION_NAMES = { chart: 'Карта', forecast: 'Прогноз', pair: 'Пара', chat: 'Астролог', sky: '«Небосвод»' }

export function tourName(name) {
  if (name === 'intro') return 'Знакомство с кабинетом'
  if (name === 'sky') return 'Что открыл «Небосвод»'
  if (name.startsWith('section-')) return `Раздел «${(SECTION_NAMES[name.slice(8)] || name.slice(8)).replace(/[«»]/g, '')}»`
  return name
}

export const STEP_NAMES = { sun: 'Прочитал своё Солнце', chat: 'Спросил астролога' }

/** A share in per cent with one decimal below ten: «4,2%», «38%»; nothing to divide by gives «—». */
export function pct(part, whole) {
  if (!whole) return '—'
  const value = (part / whole) * 100
  return `${value.toLocaleString('ru-RU', { maximumFractionDigits: value < 10 ? 1 : 0 })}%`
}
