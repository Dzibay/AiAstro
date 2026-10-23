<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import ColumnChart from '../../components/admin/ColumnChart.vue'
import WayFunnel from '../../components/admin/WayFunnel.vue'
import WeekLines from '../../components/admin/WeekLines.vue'
import { adminApi } from '../../api/admin.js'
import { PAYMENT_STATUS, PERIODS, PRODUCTS, buckets, failed, fmt, stepOf } from './shared.js'
import { MIN_BASE, channelName, growth, insightText, points, share } from './way.js'

/**
 * The first screen: the period's figures against the same span before, what stands out, the way
 * from a first visit to a payment with its changes, the shares week by week and the money.
 */

const days = ref(30)
const pulse = ref(null)
const stats = ref(null)
const money = ref(null)
const weeks = ref(null)
const recent = ref([])
const loading = ref(false)
const error = ref('')

async function load() {
  const asked = days.value
  loading.value = true
  error.value = ''
  try {
    const [p, s, m] = await Promise.all([adminApi.pulse(asked), adminApi.stats(asked), adminApi.money(asked)])
    if (asked !== days.value) return
    pulse.value = p
    stats.value = s
    money.value = m
  } catch (caught) {
    error.value = failed(caught)
  } finally {
    if (asked === days.value) loading.value = false
  }
}
watch(days, load)
onMounted(async () => {
  load()
  try {
    const [w, pay] = await Promise.all([adminApi.weeks({ weeks: 12 }), adminApi.payments({ status: 'succeeded' })])
    weeks.value = w
    recent.value = pay.items.slice(0, 5)
  } catch (caught) {
    error.value = failed(caught)
  }
})

const period = computed(() => (days.value === 365 ? 'прошлый год' : `прошлые ${days.value} дней`))
const against = computed(() => (days.value === 365 ? 'К прошлому году' : `К прошлым ${days.value} дням`))
const step = computed(() => stepOf(days.value))

const tiles = computed(() => {
  const p = pulse.value
  if (!p) return []
  const f = p.figures
  const check = f.payments ? Math.round(f.revenue / f.payments) : 0
  const checkBefore = f.payments_before ? Math.round(f.revenue_before / f.payments_before) : 0
  const rate = p.now.visit ? p.now.paid / p.now.visit : null
  const was = p.before.visit ? p.before.paid / p.before.visit : null
  const rateDelta = rate == null || was == null ? null
    : { text: points(rate - was), tone: Math.abs(rate - was) < 0.0005 ? 'flat' : rate > was ? 'up' : 'down' }
  return [
    { label: 'Новые посетители', value: fmt.count(f.visitors), delta: growth(f.visitors, f.visitors_before), was: fmt.count(f.visitors_before) },
    { label: 'Регистрации', value: fmt.count(f.signups), delta: growth(f.signups, f.signups_before), was: fmt.count(f.signups_before) },
    { label: 'Первые оплаты', value: fmt.count(f.new_payers), delta: growth(f.new_payers, f.new_payers_before), was: fmt.count(f.new_payers_before) },
    { label: 'Выручка', value: fmt.rub(f.revenue), delta: growth(f.revenue, f.revenue_before), was: fmt.rub(f.revenue_before) },
    { label: 'Средний чек', value: check ? fmt.rub(check) : '—', delta: check ? growth(check, checkBefore) : null, was: checkBefore ? fmt.rub(checkBefore) : '—' },
    { label: 'Визит → оплата', value: share(rate), delta: rateDelta, was: share(was) },
    { label: '«Небосвод» сейчас', value: fmt.count(f.sky_now), hint: `продлили за срок: ${fmt.count(f.renewals)}` },
  ]
})

const TONES = {
  bad: { badge: 'is-bad', label: 'проседает' },
  info: { badge: 'is-warn', label: 'узкое место' },
  good: { badge: 'is-ok', label: 'растёт' },
}
const insights = computed(() => (pulse.value?.insights || []).map((item, index) => ({
  key: index,
  ...TONES[item.tone],
  text: insightText(item, period.value),
})))

const revenue = computed(() => buckets(stats.value?.series || [], 'revenue', days.value))
const products = computed(() => {
  const rows = stats.value?.products || []
  const top = Math.max(...rows.map((row) => row.revenue), 1)
  return rows.map((row) => ({ ...row, label: PRODUCTS[row.product] || row.product, width: (row.revenue / top) * 100 }))
})
const sources = computed(() => {
  const rows = (money.value?.items || []).filter((row) => row.revenue > 0).slice(0, 6)
  const top = Math.max(...rows.map((row) => row.revenue), 1)
  return rows.map((row) => ({ ...row, label: channelName(row.key, row.label), width: (row.revenue / top) * 100 }))
})
</script>

<template>
  <header class="adm-head">
    <div>
      <h1>Сводка</h1>
      <p>Срок против такого же прошлого — и где теряются люди на пути от первого визита до оплаты. Дни — по Москве.</p>
    </div>
    <div class="adm-seg" role="group" aria-label="Период">
      <button v-for="p in PERIODS" :key="p.days" type="button" :aria-pressed="days === p.days" @click="days = p.days">{{ p.label }}</button>
    </div>
  </header>

  <p v-if="error" class="error">{{ error }}</p>

  <div v-if="pulse" class="ps" :class="{ 'adm-loading': loading }">
    <div class="ps-tiles">
      <div v-for="tile in tiles" :key="tile.label" class="adm-panel ps-tile">
        <span class="ps-tile-label">{{ tile.label }}</span>
        <strong class="ps-tile-value num">{{ tile.value }}</strong>
        <span class="ps-tile-hint">
          <template v-if="tile.delta">
            <span class="ps-delta" :class="`is-${tile.delta.tone}`">
              <svg v-if="tile.delta.tone !== 'flat'" viewBox="0 0 10 10" aria-hidden="true"><path :d="tile.delta.tone === 'up' ? 'M5 2 9 8H1Z' : 'M5 8 1 2h8Z'" /></svg>{{ tile.delta.text }}
            </span>
            <span>было {{ tile.was }}</span>
          </template>
          <template v-else>{{ tile.hint || `было ${tile.was}` }}</template>
        </span>
      </div>
    </div>

    <section class="adm-panel">
      <div class="adm-panel-head">
        <h2>Что заметно</h2>
        <p>{{ against }} и между источниками, страницами входа и устройствами; шаг считается, если до него дошли от {{ MIN_BASE }} человек</p>
      </div>
      <ul v-if="insights.length" class="ps-insights">
        <li v-for="item in insights" :key="item.key">
          <span class="adm-badge" :class="item.badge">{{ item.label }}</span>
          <span>{{ item.text }}</span>
        </li>
      </ul>
      <p v-else class="adm-empty">Ничего не выделяется: шаги идут ровно или людей пока мало для выводов.</p>
      <RouterLink :to="{ name: 'admin-analytics' }" class="ps-link">Разобрать по источникам, страницам и устройствам →</RouterLink>
    </section>

    <section class="adm-panel">
      <div class="adm-panel-head">
        <h2>Путь от визита до оплаты</h2>
        <p>браузеры, впервые зашедшие за срок, — докуда дошли; прошлый срок взят в том же возрасте</p>
      </div>
      <WayFunnel :now="pulse.now" :before="pulse.before" :period="period" />
    </section>

    <section class="adm-panel">
      <div class="adm-panel-head">
        <h2>По неделям</h2>
        <p>новые посетители недели и что они сделали в первые 7 дней; пунктир — неделя ещё досчитывается</p>
      </div>
      <WeekLines v-if="weeks" :items="weeks.items" />
      <p v-else class="adm-empty">Загружаю недели…</p>
    </section>

    <section class="adm-panel">
      <div class="adm-panel-head">
        <h2>Выручка {{ step }}</h2>
        <p>оплаченные платежи, ₽</p>
      </div>
      <ColumnChart :points="revenue" name="Выручка" color="#b8882c" :format="fmt.rub" :axis-format="fmt.compact" :height="200" />
    </section>

    <div class="ps-pair">
      <section class="adm-panel">
        <div class="adm-panel-head">
          <h2>По продуктам</h2>
          <p>за срок</p>
        </div>
        <ul v-if="products.length" class="ps-bars">
          <li v-for="row in products" :key="row.product">
            <span class="ps-bars-label">{{ row.label }}</span>
            <span class="ps-bars-track"><i :style="{ width: `${row.width}%` }" /></span>
            <span class="ps-bars-value"><strong>{{ fmt.rub(row.revenue) }}</strong> · {{ row.payments }} опл.</span>
          </li>
        </ul>
        <p v-else class="adm-empty">За этот срок оплат не было.</p>
      </section>

      <section class="adm-panel">
        <div class="adm-panel-head">
          <h2>По источникам</h2>
          <p>откуда пришли те, кто платил</p>
        </div>
        <ul v-if="sources.length" class="ps-bars">
          <li v-for="row in sources" :key="row.key">
            <span class="ps-bars-label">{{ row.label }}</span>
            <span class="ps-bars-track"><i :style="{ width: `${row.width}%` }" /></span>
            <span class="ps-bars-value"><strong>{{ fmt.rub(row.revenue) }}</strong> · платили {{ row.payers }} · на посетителя {{ row.visitors ? fmt.rub(Math.round(row.revenue / row.visitors)) : '—' }}</span>
          </li>
        </ul>
        <p v-else class="adm-empty">За этот срок оплат не было.</p>
        <RouterLink :to="{ name: 'admin-analytics', query: { tab: 'sources' } }" class="ps-link">Все источники, расходы и окупаемость →</RouterLink>
      </section>
    </div>

    <section class="adm-panel">
      <div class="adm-panel-head">
        <h2>Последние оплаты</h2>
        <RouterLink :to="{ name: 'admin-payments' }" class="ps-link is-head">Все платежи →</RouterLink>
      </div>
      <ul v-if="recent.length" class="ps-recent">
        <li v-for="p in recent" :key="p.id">
          <span class="adm-dim">{{ fmt.moment(p.paid_at || p.created_at) }}</span>
          <RouterLink v-if="p.user_id" :to="{ name: 'admin-user', params: { id: p.user_id } }" class="ps-who">{{ p.email }}</RouterLink>
          <span v-else class="ps-who">{{ p.email }}</span>
          <span class="adm-dim ps-what">{{ PRODUCTS[p.product] || p.title }}</span>
          <strong class="num">{{ fmt.rub(p.amount) }}</strong>
          <span class="adm-badge is-ok">{{ PAYMENT_STATUS[p.status] }}</span>
        </li>
      </ul>
      <p v-else class="adm-empty">Оплат пока не было.</p>
    </section>
  </div>
</template>

<style scoped>
.ps { display: grid; gap: 18px; }
.num { font-variant-numeric: tabular-nums; }
.ps-tiles { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 12px; }
.ps-tile { display: grid; align-content: start; gap: 4px; padding: 14px 16px; }
.ps-tile-label { color: var(--muted); font-size: 13px; }
.ps-tile-value { font-size: 24px; font-weight: 600; line-height: 1.15; white-space: nowrap; }
.ps-tile-hint { display: flex; flex-wrap: wrap; align-items: center; gap: 2px 8px; color: var(--soft); font-size: 12px; }
.ps-delta { display: inline-flex; align-items: center; gap: 4px; font-size: 13px; font-weight: 600; }
.ps-delta svg { width: 9px; height: 9px; fill: currentColor; }
.ps-delta.is-up { color: var(--ok); }
.ps-delta.is-down { color: var(--danger); }
.ps-delta.is-flat { color: var(--soft); }

.ps-insights { display: grid; gap: 0; margin: 0; padding: 0; list-style: none; }
.ps-insights li { display: grid; grid-template-columns: 8.5em minmax(0, 1fr); align-items: baseline; gap: 12px; padding: 9px 0; border-top: 1px solid var(--panel-line); font-size: 15px; }
.ps-insights li:first-child { border-top: 0; padding-top: 2px; }
.ps-insights .adm-badge { justify-self: start; }

.ps-link { display: inline-block; margin-top: 12px; color: var(--gold); font-size: 14px; text-decoration: none; }
.ps-link.is-head { margin-top: 0; }
.ps-link:hover { text-decoration: underline; }

.ps-pair { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 18px; }
.ps-bars { display: grid; gap: 14px; margin: 4px 0 0; padding: 0; list-style: none; }
.ps-bars li { display: grid; gap: 6px; }
.ps-bars-label { font-size: 15px; overflow-wrap: anywhere; }
.ps-bars-track { display: block; height: 10px; }
.ps-bars-track i { display: block; height: 100%; min-width: 4px; border-radius: 0 4px 4px 0; background: var(--money); transition: width 0.3s ease; }
.ps-bars-value { color: var(--soft); font-size: 13px; }
.ps-bars-value strong { color: var(--ink); font-size: 14px; }

.ps-recent { display: grid; margin: 0; padding: 0; list-style: none; }
.ps-recent li {
  display: grid;
  grid-template-columns: 8.5em minmax(0, 1.2fr) minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 4px 16px;
  padding: 10px 0;
  border-top: 1px solid var(--panel-line);
  font-size: 15px;
}
.ps-recent li:first-child { border-top: 0; }
.ps-who { color: var(--ink); text-decoration: none; overflow-wrap: anywhere; }
a.ps-who:hover { text-decoration: underline; }
.ps-what { font-size: 14px; }

@media (max-width: 1300px) {
  .ps-tiles { grid-template-columns: repeat(4, minmax(0, 1fr)); }
}
@media (max-width: 1000px) {
  .ps-pair { grid-template-columns: minmax(0, 1fr); }
}
@media (max-width: 640px) {
  .ps-tiles { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .ps-tile-value { font-size: 21px; }
  .ps-insights li { grid-template-columns: minmax(0, 1fr); gap: 4px; }
  .ps-recent li { grid-template-columns: 1fr auto; }
  .ps-recent .ps-who { grid-column: 1 / -1; grid-row: 1; }
  .ps-recent .adm-badge { display: none; }
}
</style>
