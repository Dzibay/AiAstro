<script setup>
import { computed, ref, watch } from 'vue'
import { adminApi } from '../../api/admin.js'
import { failed, moscowDay, pageName, plural } from '../../views/admin/shared.js'

/**
 * A month of one account, Moscow days. A day burns gold by how many pages were opened;
 * the open day lists those pages.
 */

const props = defineProps({
  userId: { type: Number, required: true },
  lastSeen: { type: String, default: '' },
})

const WEEKDAYS = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс']
const EARLIEST = '2024-01'

const month = ref('')
const data = ref(null)
const error = ref('')
const loading = ref(false)
const picked = ref('')
let ticket = 0

const today = computed(() => moscowDay())
const canPrev = computed(() => month.value > EARLIEST)
const canNext = computed(() => month.value < today.value.slice(0, 7))

const title = computed(() => {
  if (!month.value) return ''
  const [year, mon] = month.value.split('-').map(Number)
  const text = new Intl.DateTimeFormat('ru-RU', { month: 'long', year: 'numeric', timeZone: 'UTC' }).format(new Date(Date.UTC(year, mon - 1, 1)))
  return (text.charAt(0).toUpperCase() + text.slice(1)).replace(/\s*г\.$/, '')
})

const byDate = computed(() => {
  const map = new Map()
  for (const day of data.value?.days || []) map.set(day.date, day)
  return map
})

const cells = computed(() => {
  if (!month.value) return []
  const [year, mon] = month.value.split('-').map(Number)
  const lead = (new Date(Date.UTC(year, mon - 1, 1)).getUTCDay() + 6) % 7
  const count = new Date(Date.UTC(year, mon, 0)).getUTCDate()
  const out = Array.from({ length: lead }, (_, index) => ({ key: `blank-${index}`, blank: true }))
  for (let day = 1; day <= count; day += 1) {
    const date = `${month.value}-${String(day).padStart(2, '0')}`
    const info = byDate.value.get(date)
    const views = info?.views || 0
    const visits = info?.visits || 0
    const heat = views || visits
    out.push({
      key: date,
      date,
      number: day,
      views,
      visits,
      info,
      future: date > today.value,
      today: date === today.value,
      level: heat >= 8 ? 3 : heat >= 3 ? 2 : heat ? 1 : 0,
    })
  }
  return out
})

const current = computed(() => cells.value.find((cell) => cell.date === picked.value) || null)

const summary = computed(() => {
  if (!data.value || data.value.month !== month.value) return loading.value ? 'Считаем…' : ''
  const days = data.value.days.filter((day) => day.views || day.visits)
  if (!days.length) return 'В этом месяце не заходил'
  const views = days.reduce((sum, day) => sum + day.views, 0)
  const active = `${days.length} ${plural(days.length, 'день', 'дня', 'дней')}`
  if (!views) return active
  return `${active} · ${views} ${plural(views, 'страница', 'страницы', 'страниц')}`
})

const dayTitle = computed(() => {
  if (!current.value) return ''
  const text = new Intl.DateTimeFormat('ru-RU', { weekday: 'long', day: 'numeric', month: 'long', timeZone: 'UTC' }).format(new Date(`${current.value.date}T12:00:00Z`))
  return text.charAt(0).toUpperCase() + text.slice(1)
})

const dayLine = computed(() => {
  const cell = current.value
  if (!cell) return ''
  if (!cell.views && !cell.visits) return 'В этот день не заходил'
  const parts = []
  if (cell.views) parts.push(`${cell.views} ${plural(cell.views, 'страница', 'страницы', 'страниц')}`)
  if (cell.visits) parts.push(`${cell.visits} ${plural(cell.visits, 'визит', 'визита', 'визитов')}`)
  const span = timeSpan(cell.info)
  if (span) parts.push(span)
  return parts.join(' · ')
})

function timeSpan(info) {
  if (!info?.first_at) return ''
  const clock = new Intl.DateTimeFormat('ru-RU', { timeZone: 'Europe/Moscow', hour: '2-digit', minute: '2-digit' })
  const from = clock.format(new Date(info.first_at))
  const to = clock.format(new Date(info.last_at))
  return from === to ? from : `${from}–${to}`
}

function label(cell) {
  const when = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long', timeZone: 'UTC' }).format(new Date(`${cell.date}T12:00:00Z`))
  if (cell.future) return when
  if (!cell.views && !cell.visits) return `${when}, не заходил`
  return `${when}, ${cell.views} ${plural(cell.views, 'страница', 'страницы', 'страниц')}`
}

async function load() {
  const mine = ++ticket
  const id = props.userId
  loading.value = true
  error.value = ''
  try {
    const result = await adminApi.activity(id, month.value)
    if (mine !== ticket || id !== props.userId) return
    data.value = result
    const latest = [...result.days].reverse().find((day) => day.views || day.visits)
    picked.value = latest?.date || ''
  } catch (caught) {
    if (mine !== ticket) return
    error.value = failed(caught)
  } finally {
    if (mine === ticket) loading.value = false
  }
}

function shift(delta) {
  const [year, mon] = month.value.split('-').map(Number)
  const next = new Date(Date.UTC(year, mon - 1 + delta, 1))
  const value = `${next.getUTCFullYear()}-${String(next.getUTCMonth() + 1).padStart(2, '0')}`
  if (value < EARLIEST || value > today.value.slice(0, 7)) return
  month.value = value
  load()
}

watch(() => props.userId, (id) => {
  if (!id) return
  month.value = (props.lastSeen ? moscowDay(props.lastSeen) : moscowDay()).slice(0, 7)
  if (month.value < EARLIEST) month.value = EARLIEST
  if (month.value > today.value.slice(0, 7)) month.value = today.value.slice(0, 7)
  data.value = null
  picked.value = ''
  load()
}, { immediate: true })
</script>

<template>
  <div class="cal" :class="{ 'is-loading': loading && data }">
    <div class="cal-nav">
      <button type="button" class="cal-arrow" aria-label="Предыдущий месяц" :disabled="!canPrev || loading" @click="shift(-1)">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 6 8 12l6 6" /></svg>
      </button>
      <div class="cal-title">
        <strong>{{ title }}</strong>
        <span>{{ summary }}</span>
      </div>
      <button type="button" class="cal-arrow" aria-label="Следующий месяц" :disabled="!canNext || loading" @click="shift(1)">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m10 6 6 6-6 6" /></svg>
      </button>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <div v-if="cells.length" class="cal-grid">
      <span v-for="name in WEEKDAYS" :key="name" class="cal-week" aria-hidden="true">{{ name }}</span>
      <template v-for="cell in cells" :key="cell.key">
        <span v-if="cell.blank" class="cal-blank" />
        <button
          v-else
          type="button"
          class="cal-day"
          :class="[`is-${cell.level}`, { 'is-today': cell.today, 'is-future': cell.future }]"
          :aria-pressed="cell.date === picked"
          :aria-label="label(cell)"
          :disabled="cell.future"
          @click="picked = cell.date"
        >{{ cell.number }}</button>
      </template>
    </div>

    <p class="cal-legend" aria-hidden="true">
      <span class="cal-swatch is-1" />
      <span class="cal-swatch is-2" />
      <span class="cal-swatch is-3" />
      больше страниц
    </p>

    <div v-if="current" class="cal-detail">
      <strong>{{ dayTitle }}</strong>
      <span>{{ dayLine }}</span>
      <ul v-if="current.info?.pages?.length">
        <li v-for="page in current.info.pages" :key="page.name">
          <span>{{ pageName(page.name) }}</span>
          <strong class="num">{{ page.views }}</strong>
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.cal { display: grid; gap: 12px; }
.cal.is-loading { opacity: 0.55; }
.cal-nav { display: flex; align-items: center; gap: 8px; }
.cal-title { flex: 1; display: grid; gap: 1px; min-width: 0; text-align: center; }
.cal-title strong { font-size: 15px; font-weight: 600; }
.cal-title span { color: var(--soft); font-size: 13px; }
.cal-arrow {
  flex: none;
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  padding: 0;
  border: 1px solid rgba(244, 239, 230, 0.14);
  border-radius: 50%;
  background: transparent;
  color: var(--ink);
  cursor: pointer;
}
.cal-arrow svg { width: 16px; height: 16px; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
.cal-arrow:hover { border-color: rgba(224, 193, 122, 0.5); }
.cal-arrow:disabled { opacity: 0.35; cursor: default; }
.cal-arrow:focus-visible { outline: 2px solid rgba(224, 193, 122, 0.7); outline-offset: 2px; }

.cal-grid { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 4px; }
.cal-week { display: grid; place-items: center; height: 22px; color: var(--soft); font-size: 12px; }
.cal-blank { aspect-ratio: 1; }
.cal-day {
  position: relative;
  display: grid;
  place-items: center;
  aspect-ratio: 1;
  padding: 0;
  border: 0;
  border-radius: 8px;
  background: rgba(244, 239, 230, 0.04);
  color: var(--soft);
  font: inherit;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
  cursor: pointer;
}
.cal-day.is-1 { background: rgba(224, 193, 122, 0.28); color: var(--ink); }
.cal-day.is-2 { background: rgba(224, 193, 122, 0.62); color: #23190a; }
.cal-day.is-3 { background: var(--gold); color: #23190a; font-weight: 600; }
.cal-day.is-today::after {
  content: '';
  position: absolute;
  bottom: 5px;
  left: 50%;
  width: 4px;
  height: 4px;
  translate: -50% 0;
  border-radius: 50%;
  background: currentColor;
}
.cal-day[aria-pressed='true'] { box-shadow: inset 0 0 0 2px #f4efe6; }
.cal-day.is-2[aria-pressed='true'], .cal-day.is-3[aria-pressed='true'] { box-shadow: inset 0 0 0 2px #23190a; }
.cal-day.is-future { background: transparent; color: rgba(244, 239, 230, 0.28); }
.cal-day:disabled { cursor: default; }
.cal-day:focus-visible { outline: 2px solid rgba(224, 193, 122, 0.7); outline-offset: 1px; }

.cal-legend { display: flex; align-items: center; flex-wrap: wrap; gap: 4px; margin: 0; color: var(--soft); font-size: 12px; }
.cal-swatch { width: 12px; height: 12px; border-radius: 3px; }
.cal-swatch.is-1 { background: rgba(224, 193, 122, 0.28); }
.cal-swatch.is-2 { background: rgba(224, 193, 122, 0.62); }
.cal-swatch.is-3 { background: var(--gold); margin-right: 4px; }

.cal-detail { display: grid; gap: 2px; padding-top: 4px; border-top: 1px solid rgba(244, 239, 230, 0.07); }
.cal-detail > strong { font-size: 14px; font-weight: 600; }
.cal-detail > span { color: var(--soft); font-size: 13px; }
.cal-detail ul { display: grid; gap: 4px; margin: 8px 0 0; padding: 0; list-style: none; }
.cal-detail li { display: flex; justify-content: space-between; gap: 12px; font-size: 14px; }
.cal-detail li span { min-width: 0; }
.num { font-variant-numeric: tabular-nums; }
</style>
