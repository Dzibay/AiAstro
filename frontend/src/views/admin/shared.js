import { onBeforeUnmount, ref, watch } from 'vue'
import { errorText } from '../../api/http.js'
import { readSession } from '../../composables/useSession.js'

/** One sign-in for every page: a 401 anywhere takes the operator back to the password. */
export const authed = ref(Boolean(readSession('admin')))
/** The open errors of the journal, for the number by «Ошибки» in the menu; null until known. */
export const openFaults = ref(null)

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

/** The kinds of letters, as the server's journal names them (app/outbox.py). */
export const LETTER_KINDS = {
  confirm: 'Подтверждение почты',
  confirm_change: 'Подтверждение новой почты',
  reset: 'Новый пароль',
  paid_sky: 'Оплата «Небосвода»',
  paid_pair: 'Оплата разбора пары',
  pay_left: 'Незавершённая оплата',
  sky_end: 'Скорый конец «Небосвода»',
  partner_filled: 'Партнёр ответил на приглашение',
  pair_linked: 'Пара стала общей',
  pair_bought: 'Партнёр открыл разбор пары',
  pair_gift: 'Подарок: разбор пары',
  pair_left: 'Партнёр удалил пару',
  test: 'Пробное письмо',
}

export const LETTER_STATUS = {
  sending: { text: 'отправляется', tone: 'is-warn' },
  sent: { text: 'ушло', tone: 'is-ok' },
  failed: { text: 'не ушло', tone: 'is-bad' },
  off: { text: 'почта не настроена', tone: 'is-warn' },
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
  'cabinet-chat': 'ИИ-астролог',
  'cabinet-sky': '«Небосвод»',
  'lp-natal': 'Посадочная: натальная карта',
  'lp-pair': 'Посадочная: совместимость',
  'lp-forecast': 'Посадочная: личный гороскоп',
  'lp-asc': 'Посадочная: Асцендент',
  'lp-lilith': 'Посадочная: Лилит',
  'lp-chiron': 'Посадочная: Хирон',
  other: 'Другие адреса',
}
const LEGAL = { offer: 'оферта', privacy: 'политика', consent: 'согласие', cookies: 'cookie' }

export function pageName(name) {
  if (!name) return 'не открывал страниц'
  if (name.startsWith('legal:')) return `Документы: ${LEGAL[name.slice(6)] || name.slice(6)}`
  return PAGE_NAMES[name] || name
}

const SECTION_NAMES = { chart: 'Карта', forecast: 'Прогноз', pair: 'Пара', chat: 'ИИ-астролог', sky: '«Небосвод»' }

export function tourName(name) {
  if (name === 'intro') return 'Знакомство с кабинетом'
  if (name === 'sky') return 'Что открыл «Небосвод»'
  if (name.startsWith('section-')) return `Раздел «${(SECTION_NAMES[name.slice(8)] || name.slice(8)).replace(/[«»]/g, '')}»`
  return name
}

export const STEP_NAMES = { sun: 'Прочитал своё Солнце', chat: 'Спросил ИИ-астролога' }

/** A share in per cent with one decimal below ten: «4,2%», «38%»; nothing to divide by gives «—». */
export function pct(part, whole) {
  if (!whole) return '—'
  const value = (part / whole) * 100
  return `${value.toLocaleString('ru-RU', { maximumFractionDigits: value < 10 ? 1 : 0 })}%`
}

/* ---- What a page gathers (track.js): the offers, the buttons, the game, one person's actions ---- */

const OFFER_NAMES = {
  'sky:portrait': 'Портрет за замком',
  'sky:chart': 'Карта: строка про «Небосвод»',
  'sky:chat': 'ИИ-астролог: замок',
  'sky:chat-hint': 'ИИ-астролог: подсказка про счёт',
  'sky:month': 'Прогноз на месяц',
  'sky:forecast-stories': 'Прогноз: истории дня',
  'sky:forecast': 'Прогноз: замок',
  'sky:overview': 'Обзор: строка «Небосвода»',
  'sky:profile': 'Профиль: «Зажечь» / «Продлить»',
  'sky:pair-price': 'Пара: дешевле с «Небосводом»',
  'sky:pair-day': 'Пара: день пары',
  'sky:panel': 'Раздел «Небосвод» напрямую',
  'pair:stories': 'Пара: кнопка в историях',
  'pair:panel': 'Пара: кнопка разбора',
}

/** Where a payment came from: the offer last pressed before it; '' — the payments before the places were kept. */
export function offerName(name) {
  if (!name) return 'Без места (раньше учёта)'
  return OFFER_NAMES[name] || name
}

const CLICK_NAMES = {
  'home:form': 'Главная: форма даты',
  'home:sample': 'Главная: пример карты',
  'home:span-day': 'Главная: прогноз на день',
  'home:span-week': 'Главная: прогноз на неделю',
  'home:final': 'Главная: последняя кнопка',
  'header:login': 'Шапка: вход',
  'header:menu': 'Шапка: меню',
  'menu:login': 'Меню: вход',
  'landing:calc': 'Посадочная: расчёт',
  'landing:cta': 'Посадочная: в кабинет',
  'pay:sky': '«Небосвод»: оплатить',
  'out:mail': 'Письмо на почту',
  'out:phone': 'Звонок',
}

/** A pressed button or link: its own name, an offer, a page it leads to (to:…), another site (out:…). */
export function clickName(name) {
  if (CLICK_NAMES[name]) return CLICK_NAMES[name]
  if (OFFER_NAMES[name]) return OFFER_NAMES[name]
  if (name.startsWith('home:faq-')) return `Главная: вопрос ${name.slice(9)}`
  if (name.startsWith('to:')) return `→ ${pageName(name.slice(3))}`
  if (name.startsWith('out:')) return `↗ ${name.slice(4)}`
  return name
}

export const GAME_STEPS = {
  intro: 'Заставка',
  sun: 'Солнце',
  moon: 'Луна',
  asc: 'Асцендент',
  mercury: 'Меркурий',
  venus: 'Венера',
  mars: 'Марс',
  finale: 'Финал',
}

/** Seconds of attention: «45 с», «2 мин 10 с». */
export function duration(seconds) {
  const s = Math.round(Number(seconds) || 0)
  if (!s) return '—'
  if (s < 60) return `${s} с`
  const m = Math.floor(s / 60)
  return s % 60 ? `${m} мин ${s % 60} с` : `${m} мин`
}

const GAME_ACTS = {
  offer: 'Игра: предложена',
  play: 'Игра: согласился сыграть',
  skip: 'Игра: отложил',
  replay: 'Игра: сыграть ещё раз',
  begin: 'Игра: началась',
  finale: 'Игра: финал',
  fail: 'Игра: не запустилась на устройстве',
}
/** The steps on the way into the cabinet: registration and the confirmation letter. */
const WAY_ACTS = {
  'reg:open': 'Открыл регистрацию',
  'reg:who': 'Прошёл первый шаг регистрации',
  'confirm:resend': 'Попросил письмо ещё раз',
  'confirm:change': 'Исправил почту для письма',
  'confirm:mailbox': 'Перешёл в свою почту',
}
const GAME_STEP_ACTS = { found: 'нашёл', miss: 'промах', hint: 'подсказка', quit: 'вышел на шаге' }
const TOUR_STEPS = { start: 'показан', done: 'пройден', skip: 'закрыт' }
const GOALS = { calc: 'расчёт', cta: 'переход в кабинет' }

/** One line of a person's actions in their card. */
export function eventText(item) {
  const name = item.name || ''
  switch (item.kind) {
    case 'view': return `Открыл: ${pageName(name)}`
    case 'visit': return `Новый визит — ${pageName(name)}`
    case 'ref': return 'Пришёл по рекламной ссылке'
    case 'signup': return 'Зарегистрировался'
    case 'confirm': return 'Подтвердил почту'
    case 'birth': return 'Указал дату рождения'
    case 'tour': {
      const [tour, step] = name.split(':')
      return `Тур «${tourName(tour).replace(/[«»]/g, '')}»: ${TOUR_STEPS[step] || step}`
    }
    case 'goal': {
      const [page, goal] = name.split(':')
      return `${pageName(page)}: ${GOALS[goal] || goal}`
    }
    case 'click': return `Нажал: ${clickName(name)}`
    case 'offer': return `Увидел предложение: ${offerName(name)}`
    case 'pick': return `Выбрал срок: ${PRODUCTS[name] || name}`
    case 'scroll': return `Долистал до ${item.value}%`
    case 'time': return `Провёл на странице ${duration(item.value)}`
    case 'act': {
      if (WAY_ACTS[name]) return WAY_ACTS[name]
      const [, act, step] = name.split(':')
      if (act === 'land') return `Игра: собрал карту за ${duration(item.value)}`
      if (step) return `Игра: ${GAME_STEP_ACTS[act] || act} — ${GAME_STEPS[step] || step}`
      return GAME_ACTS[act] || name
    }
    case 'payment': return `Платёж: ${PRODUCTS[name] || name} · ${fmt.rub(item.value)} · ${PAYMENT_STATUS[item.status] || item.status}`
    case 'letter': return `Письмо: ${LETTER_KINDS[name] || name} · ${LETTER_STATUS[item.status]?.text || item.status}`
    case 'letter_click': return `Нажал кнопку в письме: ${LETTER_KINDS[name] || name}`
    default: return `${item.kind}: ${name}`
  }
}
