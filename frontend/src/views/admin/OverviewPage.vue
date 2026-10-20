<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import ColumnChart from '../../components/admin/ColumnChart.vue'
import { adminApi } from '../../api/admin.js'
import { PAYMENT_STATUS, PRODUCTS, failed, fmt } from './shared.js'

const PERIODS = [
  { days: 7, label: '7 дней' },
  { days: 30, label: '30 дней' },
  { days: 90, label: '90 дней' },
  { days: 365, label: 'Год' },
]
const days = ref(30)
const data = ref(null)
const recent = ref([])
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  const asked = days.value
  try {
    const answer = await adminApi.stats(asked)
    if (asked === days.value) data.value = answer
  } catch (caught) {
    error.value = failed(caught)
  } finally {
    loading.value = false
  }
}
watch(days, load)
onMounted(async () => {
  load()
  try {
    recent.value = (await adminApi.payments({ status: 'succeeded' })).items.slice(0, 6)
  } catch (caught) {
    failed(caught)
  }
})

const short = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'short' })
const full = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })
const monthShort = new Intl.DateTimeFormat('ru-RU', { month: 'short' })
const monthLong = new Intl.DateTimeFormat('ru-RU', { month: 'long', year: 'numeric' })
const asDay = (iso) => new Date(`${iso}T12:00:00`)
const clean = (text) => text.replace('.', '')

/**
 * Days for a week or a month; weeks for 90 days, months for a year,
 * so that a column never shrinks to a hair.
 */
function buckets(series, field) {
  if (!series.length) return []
  if (days.value <= 30) {
    return series.map((row) => ({ key: row.day, label: clean(short.format(asDay(row.day))), title: full.format(asDay(row.day)), value: row[field] }))
  }
  const groups = new Map()
  if (days.value <= 90) {
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
        label: clean(short.format(asDay(g.first))),
        title: `${short.format(asDay(g.first))} — ${short.format(asDay(g.last))}`,
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

const revenue = computed(() => buckets(data.value?.series || [], 'revenue'))
const signups = computed(() => buckets(data.value?.series || [], 'signups'))
const step = computed(() => (days.value <= 30 ? 'по дням' : days.value <= 90 ? 'по неделям' : 'по месяцам'))

function delta(now, before) {
  if (!before) return now ? { text: 'новое', up: true } : null
  const change = Math.round(((now - before) / before) * 100)
  return { text: `${change > 0 ? '+' : change < 0 ? '−' : '±'}${Math.abs(change)}%`, up: change >= 0 }
}

const tiles = computed(() => {
  const t = data.value?.totals
  if (!t) return []
  const conversion = t.users ? Math.round((t.paying / t.users) * 1000) / 10 : 0
  return [
    { label: 'Выручка', value: fmt.rub(t.revenue), delta: delta(t.revenue, t.revenue_before), hint: 'к прошлому такому же сроку' },
    { label: 'Регистрации', value: fmt.count(t.signups), delta: delta(t.signups, t.signups_before), hint: `всего ${fmt.count(t.users)}` },
    { label: '«Небосвод» сейчас', value: fmt.count(t.sky), hint: t.users ? `${Math.round((t.sky / t.users) * 100)}% пользователей` : '' },
    { label: 'Платящие', value: fmt.count(t.paying), hint: `${conversion.toLocaleString('ru-RU')}% от всех` },
    { label: 'Пары', value: fmt.count(t.pairs), hint: `разбор открыт у ${fmt.count(t.pairs_bought)}` },
  ]
})

const products = computed(() => {
  const rows = data.value?.products || []
  const total = rows.reduce((sum, row) => sum + row.revenue, 0)
  const top = Math.max(...rows.map((row) => row.revenue), 1)
  return rows.map((row) => ({
    ...row,
    label: PRODUCTS[row.product] || row.product,
    width: (row.revenue / top) * 100,
    share: total ? Math.round((row.revenue / total) * 100) : 0,
  }))
})
</script>

<template>
  <header class="adm-head">
    <div>
      <h1>Обзор</h1>
      <p>Деньги и люди за выбранный срок. Дни — по Москве, платёж считается в день оплаты.</p>
    </div>
    <div class="adm-seg" role="group" aria-label="Период">
      <button v-for="p in PERIODS" :key="p.days" type="button" :aria-pressed="days === p.days" @click="days = p.days">{{ p.label }}</button>
    </div>
  </header>

  <p v-if="error" class="error">{{ error }}</p>

  <div v-if="data" class="ov" :class="{ 'adm-loading': loading }">
    <div class="ov-tiles">
      <div v-for="tile in tiles" :key="tile.label" class="adm-panel ov-tile">
        <span class="ov-tile-label">{{ tile.label }}</span>
        <strong class="ov-tile-value">{{ tile.value }}</strong>
        <span class="ov-tile-hint">
          <span v-if="tile.delta" class="ov-delta" :class="tile.delta.up ? 'is-up' : 'is-down'">
            <svg viewBox="0 0 10 10" aria-hidden="true"><path :d="tile.delta.up ? 'M5 2 9 8H1Z' : 'M5 8 1 2h8Z'" /></svg>{{ tile.delta.text }}
          </span>
          {{ tile.hint }}
        </span>
      </div>
    </div>

    <section class="adm-panel">
      <div class="adm-panel-head">
        <h2>Выручка {{ step }}</h2>
        <p>оплаченные платежи, ₽</p>
      </div>
      <ColumnChart :points="revenue" name="Выручка" color="#b8882c" :format="fmt.rub" :axis-format="fmt.compact" />
    </section>

    <div class="ov-pair">
      <section class="adm-panel">
        <div class="adm-panel-head">
          <h2>Регистрации {{ step }}</h2>
          <p>новые кабинеты</p>
        </div>
        <ColumnChart :points="signups" name="Регистрации" color="#3987e5" :format="fmt.count" :axis-format="fmt.compact" :height="200" />
      </section>

      <section class="adm-panel">
        <div class="adm-panel-head">
          <h2>Выручка по продуктам</h2>
          <p>за срок</p>
        </div>
        <ul v-if="products.length" class="ov-bars">
          <li v-for="row in products" :key="row.product" :title="`${row.label}: ${fmt.rub(row.revenue)}, оплат — ${row.payments}`">
            <span class="ov-bars-label">{{ row.label }}</span>
            <span class="ov-bars-track"><i :style="{ width: `${row.width}%` }" /></span>
            <span class="ov-bars-value"><strong>{{ fmt.rub(row.revenue) }}</strong> · {{ row.share }}% · {{ row.payments }} опл.</span>
          </li>
        </ul>
        <p v-else class="adm-empty">За этот срок оплат не было.</p>
      </section>
    </div>

    <section class="adm-panel">
      <div class="adm-panel-head">
        <h2>Последние оплаты</h2>
        <RouterLink :to="{ name: 'admin-payments' }" class="ov-link">Все платежи →</RouterLink>
      </div>
      <ul v-if="recent.length" class="ov-recent">
        <li v-for="p in recent" :key="p.id">
          <span class="adm-dim">{{ fmt.moment(p.paid_at || p.created_at) }}</span>
          <RouterLink v-if="p.user_id" :to="{ name: 'admin-user', params: { id: p.user_id } }" class="ov-who">{{ p.email }}</RouterLink>
          <span v-else class="ov-who">{{ p.email }}</span>
          <span class="adm-dim ov-what">{{ PRODUCTS[p.product] || p.title }}</span>
          <strong class="num">{{ fmt.rub(p.amount) }}</strong>
          <span class="adm-badge is-ok">{{ PAYMENT_STATUS[p.status] }}</span>
        </li>
      </ul>
      <p v-else class="adm-empty">Оплат пока не было.</p>
    </section>
  </div>
</template>

<style scoped>
.ov { display: grid; gap: 18px; }
.ov-tiles { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 12px; }
.ov-tile { display: grid; align-content: start; gap: 4px; padding: 16px 18px; }
.ov-tile-label { color: var(--muted); font-size: 14px; }
.ov-tile-value { font-size: 28px; font-weight: 600; line-height: 1.15; }
.ov-tile-hint { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 8px; color: var(--soft); font-size: 13px; }
.ov-delta { display: inline-flex; align-items: center; gap: 4px; font-weight: 600; }
.ov-delta svg { width: 9px; height: 9px; fill: currentColor; }
.ov-delta.is-up { color: #9fd3a8; }
.ov-delta.is-down { color: var(--danger); }

.ov-pair { display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr); gap: 18px; }

.ov-bars { display: grid; gap: 14px; margin: 4px 0 0; padding: 0; list-style: none; }
.ov-bars li { display: grid; gap: 6px; }
.ov-bars-label { font-size: 15px; }
.ov-bars-track { display: block; height: 10px; }
.ov-bars-track i { display: block; height: 100%; min-width: 4px; border-radius: 0 4px 4px 0; background: #b8882c; transition: width 0.3s ease; }
.ov-bars li:hover .ov-bars-track i { filter: brightness(1.15); }
.ov-bars-value { color: var(--soft); font-size: 13px; }
.ov-bars-value strong { color: var(--ink); font-size: 14px; }

.ov-link { color: var(--gold); font-size: 14px; text-decoration: none; }
.ov-link:hover { text-decoration: underline; }
.ov-recent { display: grid; margin: 0; padding: 0; list-style: none; }
.ov-recent li {
  display: grid;
  grid-template-columns: 8.5em minmax(0, 1.2fr) minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 4px 16px;
  padding: 10px 0;
  border-top: 1px solid var(--panel-line);
  font-size: 15px;
}
.ov-recent li:first-child { border-top: 0; }
.ov-who { color: var(--ink); text-decoration: none; overflow-wrap: anywhere; }
a.ov-who:hover { text-decoration: underline; }
.ov-what { font-size: 14px; }
.num { font-variant-numeric: tabular-nums; text-align: right; }

@media (max-width: 1100px) {
  .ov-tiles { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .ov-pair { grid-template-columns: minmax(0, 1fr); }
}
@media (max-width: 640px) {
  .ov-tiles { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .ov-tile-value { font-size: 23px; }
  .ov-recent li { grid-template-columns: 1fr auto; }
  .ov-recent .ov-who { grid-column: 1 / -1; grid-row: 1; }
  .ov-recent .adm-badge { display: none; }
}
</style>
