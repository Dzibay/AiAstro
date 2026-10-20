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
