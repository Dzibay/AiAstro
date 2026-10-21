<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import ColumnChart from '../../components/admin/ColumnChart.vue'
import { adminApi } from '../../api/admin.js'
import { PERIODS, PRODUCTS, STEP_NAMES, buckets, failed, fmt, pageName, pct, stepOf, tourName } from './shared.js'

/**
 * The site's own figures: who came, from where, how far the people registered in the period have
 * gone by now, where they stopped, which tours they walked, what they bought.
 */

const days = ref(30)
const data = ref(null)
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  const asked = days.value
  try {
    const answer = await adminApi.analytics(asked)
    if (asked === days.value) data.value = answer
  } catch (caught) {
    error.value = failed(caught)
  } finally {
    loading.value = false
  }
}
watch(days, load)
onMounted(load)

const t = computed(() => data.value?.totals || {})
const step = computed(() => stepOf(days.value))
const visitors = computed(() => buckets(data.value?.series || [], 'visitors', days.value))
const signups = computed(() => buckets(data.value?.series || [], 'signups', days.value))
const hours = (value) => (!value ? '—' : value < 1 ? `${Math.max(1, Math.round(value * 60))} мин` : value < 48 ? `${Math.round(value)} ч` : `${Math.round(value / 24)} дн`)

const tiles = computed(() => {
  const x = t.value
  return [
    { label: 'Посетители', value: fmt.count(x.visitors), hint: `новых ${fmt.count(x.new_visitors)} · вернулись ${pct(x.returning, x.new_visitors)}` },
    { label: 'Визиты', value: fmt.count(x.visits), hint: `${x.visits ? (x.views / x.visits).toLocaleString('ru-RU', { maximumFractionDigits: 1 }) : 0} стр. за визит · отказы ${pct(x.bounced, x.new_visitors)}` },
    { label: 'Регистрации', value: fmt.count(x.signups), hint: `${pct(x.fresh_signups, x.new_visitors)} новых посетителей` },
    { label: 'Платящие', value: fmt.count(x.paying), hint: `${fmt.count(x.payments)} оплат · до оплаты ${hours(x.hours_to_pay)}` },
    { label: 'Выручка', value: fmt.rub(x.revenue), hint: `на платящего ${fmt.rub(x.paying ? Math.round(x.revenue / x.paying) : 0)}` },
    { label: '«Небосвод» сейчас', value: fmt.count(x.sky_now), hint: `закончился у ${fmt.count(x.sky_lapsed)} · продлили ${fmt.count(x.sky_renewed)}` },
  ]
})

/* ---- The funnel: the period's new visitors, then the people registered in it and how far they went ---- */

const FUNNEL = [
  { key: 'signup', label: 'Регистрация', hint: 'кабинет заведён' },
  { key: 'birth', label: 'Дата рождения', hint: 'небо нарисовало знак' },
  { key: 'intro', label: 'Знакомство', hint: 'тур по кабинету пройден или закрыт' },
  { key: 'section', label: 'Открыл раздел', hint: 'карта, прогноз, пара, астролог или «Небосвод»' },
  { key: 'pair', label: 'Добавил пару', hint: 'сам или приглашением' },
  { key: 'chat', label: 'Спросил астролога', hint: 'хотя бы один вопрос' },
  { key: 'checkout', label: 'Начал оплату', hint: 'перешёл в ЮKassa' },
  { key: 'paid', label: 'Оплатил', hint: 'хоть что-нибудь' },
  { key: 'sky', label: 'Купил «Небосвод»', hint: 'любой срок' },
  { key: 'pair_bought', label: 'Купил разбор пары', hint: 'хотя бы один' },
]

const funnel = computed(() => {
  const f = data.value?.funnel
  if (!f) return []
  const top = Math.max(f.signup, 1)
  // Accounts made before the counting began have no visitor: the bars measure against the larger.
  const visitorsTop = Math.max(t.value.new_visitors, top)
  const rows = [{ key: 'visitors', label: 'Новые посетители', hint: 'впервые открыли сайт', value: t.value.new_visitors, width: (t.value.new_visitors / visitorsTop) * 100, ofFirst: '', ofPrev: '' }]
  let previous = null
  for (const item of FUNNEL) {
    const value = f[item.key]
    rows.push({
      ...item,
      value,
      width: (value / visitorsTop) * 100,
      ofFirst: item.key === 'signup' ? pct(t.value.fresh_signups, t.value.new_visitors) : pct(value, f.signup),
      ofPrev: item.key === 'signup' ? '' : pct(value, previous),
      // The checkout and the purchases are not one after another: each counts from the registrations.
      paid: ['checkout', 'paid', 'sky', 'pair_bought'].includes(item.key),
    })
    if (!['sky', 'pair_bought'].includes(item.key)) previous = value
  }
  return rows
})

/** The steps the most people fall off at, among the ones in order. */
const drops = computed(() => {
  const ordered = funnel.value.filter((row) => !['sky', 'pair_bought'].includes(row.key) && row.key !== 'visitors')
  return ordered.slice(1).map((row, index) => ({ key: row.key, lost: ordered[index].value - row.value }))
    .filter((row) => row.lost > 0)
    .sort((a, b) => b.lost - a.lost)
    .slice(0, 2)
    .map((row) => row.key)
})

/* ---- Where people stop, the pages, the sources ---- */

const barsOf = (rows, field) => {
  const top = Math.max(...rows.map((row) => row[field]), 1)
  return rows.map((row) => ({ ...row, width: (row[field] / top) * 100 }))
}
const stuck = computed(() => barsOf(data.value?.stuck || [], 'people'))
const pages = computed(() => data.value?.pages || [])
const landings = computed(() => data.value?.landings || [])
/** The landing pages for search and ads, with their own goals: a calculation made, a step to the account. */
const adLandings = computed(() => landings.value.filter((row) => row.name?.startsWith('lp-')))

const SOURCE_KIND = { ref: 'по ссылке', site: 'с сайта', direct: 'напрямую' }
const sources = computed(() => (data.value?.sources || []).map((row) => ({
  ...row,
  label: row.label || (row.kind === 'direct' ? 'Без источника' : '—'),
})))
const DEVICES = { phone: 'Телефон', desktop: 'Компьютер', unknown: 'Не определено' }
const devices = computed(() => {
  const rows = data.value?.devices || []
  const total = rows.reduce((sum, row) => sum + row.visitors, 0)
  return rows.map((row) => ({ ...row, label: DEVICES[row.device] || row.device, share: total ? (row.visitors / total) * 100 : 0 }))
})

/* ---- Tours and newcomer steps ---- */

const TOUR_ORDER = ['intro', 'sky', 'section-chart', 'section-forecast', 'section-pair', 'section-chat', 'section-sky']
const tours = computed(() => {
  const events = Object.fromEntries((data.value?.tours || []).map((row) => [row.tour, row]))
  const marks = Object.fromEntries((data.value?.marks || []).map((row) => [row.mark, row.users]))
  const names = [...new Set([...TOUR_ORDER, ...Object.keys(events)])]
  return names.map((name) => {
    const row = events[name] || {}
    return {
      name,
      label: tourName(name),
      started: row.started || 0,
      done: row.done || 0,
      skipped: row.skipped || 0,
      skipStep: row.skip_step || 0,
      steps: row.steps || 0,
      seen: marks[`tour:${name}`] || 0,
    }
  }).filter((row) => row.started || row.seen || TOUR_ORDER.includes(row.name))
})
const steps = computed(() => (data.value?.marks || [])
  .filter((row) => row.mark.startsWith('step:'))
  .map((row) => ({ ...row, label: STEP_NAMES[row.mark.slice(5)] || row.mark.slice(5) })))

/* ---- What people do and buy ---- */

const actions = computed(() => {
  const a = data.value?.actions
  if (!a) return []
  return [
    { label: 'Указали дату рождения', value: a.births, hint: `${pct(a.births, t.value.signups)} регистраций` },
    { label: 'Добавили партнёров', value: a.partners, hint: `из них приглашением ${fmt.count(a.invites)}` },
    { label: 'Ответили на приглашение', value: a.answered, hint: `завели кабинет ${fmt.count(a.joined)}` },
    { label: 'Вопросов астрологу', value: a.questions, hint: `спрашивали ${fmt.count(a.askers)} чел.` },
    { label: 'Открытий карты', value: a.chart_views, hint: 'просмотры раздела' },
    { label: 'Открытий прогноза', value: a.forecast_views, hint: 'просмотры раздела' },
    { label: 'Подарено разборов', value: a.gifts, hint: 'из админки' },
  ]
})
const products = computed(() => (data.value?.products || []).map((row) => ({ ...row, label: PRODUCTS[row.product] || row.product })))
</script>

<template>
  <header class="adm-head">
    <div>
      <h1>Аналитика</h1>
      <p>Посетители, воронка и поведение за выбранный срок. Дни — по Москве; посетитель — один браузер.</p>
    </div>
    <div class="adm-seg" role="group" aria-label="Период">
      <button v-for="p in PERIODS" :key="p.days" type="button" :aria-pressed="days === p.days" @click="days = p.days">{{ p.label }}</button>
    </div>
  </header>

  <p v-if="error" class="error">{{ error }}</p>

  <div v-if="data" class="an" :class="{ 'adm-loading': loading }">
    <div class="an-tiles">
      <div v-for="tile in tiles" :key="tile.label" class="adm-panel an-tile">
        <span class="an-tile-label">{{ tile.label }}</span>
        <strong class="an-tile-value">{{ tile.value }}</strong>
        <span class="an-tile-hint">{{ tile.hint }}</span>
      </div>
    </div>

    <section class="adm-panel">
      <div class="adm-panel-head">
        <h2>Воронка</h2>
        <p>люди, зарегистрированные за срок, — и докуда каждый дошёл к сегодняшнему дню</p>
      </div>
      <ol class="an-funnel">
        <li v-for="row in funnel" :key="row.key" :class="{ 'is-paid': row.paid, 'is-drop': drops.includes(row.key) }">
          <span class="an-funnel-name">
            <strong>{{ row.label }}</strong>
            <span>{{ row.hint }}</span>
          </span>
          <span class="an-funnel-track"><i :style="{ width: `${Math.max(row.width, row.value ? 0.6 : 0)}%` }" /></span>
          <span class="an-funnel-value num">{{ fmt.count(row.value) }}</span>
          <span class="an-funnel-share num" :title="row.key === 'signup' ? 'от новых посетителей' : 'от регистраций'">{{ row.ofFirst }}</span>
          <span class="an-funnel-prev num" :title="'от предыдущего шага'">
            <template v-if="row.ofPrev">→ {{ row.ofPrev }}</template>
          </span>
        </li>
      </ol>
      <p class="adm-note an-legend">
        <span><i class="an-dot" /> шаги по порядку</span>
        <span><i class="an-dot is-paid" /> покупки — доля от регистраций</span>
        <span><i class="an-dot is-drop" /> больше всего теряем здесь</span>
      </p>
    </section>

    <div class="an-pair">
      <section class="adm-panel">
        <div class="adm-panel-head">
          <h2>Посетители {{ step }}</h2>
          <p>разные браузеры</p>
        </div>
        <ColumnChart :points="visitors" name="Посетители" color="#3987e5" :format="fmt.count" :axis-format="fmt.compact" :height="200" />
      </section>
      <section class="adm-panel">
        <div class="adm-panel-head">
          <h2>Регистрации {{ step }}</h2>
          <p>новые кабинеты</p>
        </div>
        <ColumnChart :points="signups" name="Регистрации" color="#b8882c" :format="fmt.count" :axis-format="fmt.compact" :height="200" />
      </section>
    </div>

    <div class="an-pair">
      <section class="adm-panel">
        <div class="adm-panel-head">
          <h2>Где останавливаются</h2>
          <p>последняя страница тех, кто ещё не платил</p>
        </div>
        <ul v-if="stuck.length" class="an-bars">
          <li v-for="row in stuck" :key="row.name">
            <span class="an-bars-label">{{ pageName(row.name) }}</span>
            <span class="an-bars-track"><i :style="{ width: `${row.width}%` }" /></span>
            <span class="an-bars-value num">{{ fmt.count(row.people) }} · {{ pct(row.people, t.signups) }}</span>
          </li>
        </ul>
        <p v-else class="adm-empty">Все, кто зарегистрировался, уже что-то оплатили — или регистраций не было.</p>
      </section>

      <section class="adm-panel">
        <div class="adm-panel-head">
          <h2>Покупки</h2>
          <p>начато оплат {{ fmt.count(t.checkouts) }} · брошено {{ pct(t.abandoned, t.checkouts) }}</p>
        </div>
        <table v-if="products.length" class="adm-table an-table">
          <thead><tr><th>Продукт</th><th class="num">Начали</th><th class="num">Оплатили</th><th class="num">Доходимость</th><th class="num">Выручка</th></tr></thead>
          <tbody>
            <tr v-for="row in products" :key="row.product">
              <td>{{ row.label }}</td>
              <td class="num">{{ fmt.count(row.started) }}</td>
              <td class="num">{{ fmt.count(row.paid) }}</td>
              <td class="num">{{ pct(row.paid, row.started) }}</td>
              <td class="num"><strong>{{ fmt.rub(row.revenue) }}</strong></td>
            </tr>
          </tbody>
        </table>
        <p v-else class="adm-empty">За этот срок никто не начинал оплату.</p>
      </section>
    </div>

    <section class="adm-panel">
      <div class="adm-panel-head">
        <h2>Туры</h2>
        <p>показы и прохождения за срок; «видели» — аккаунты с отметкой за всё время</p>
      </div>
      <table class="adm-table an-table">
        <thead>
          <tr>
            <th>Тур</th><th class="num">Показан</th><th class="num">Пройден</th><th class="num">Пропущен</th>
            <th>Доходимость</th><th class="num">Бросают на шаге</th><th class="num">Видели</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in tours" :key="row.name">
            <td>{{ row.label }}</td>
            <td class="num">{{ fmt.count(row.started) }}</td>
            <td class="num">{{ fmt.count(row.done) }}</td>
            <td class="num">{{ fmt.count(row.skipped) }}</td>
            <td>
              <span class="an-meter" :title="pct(row.done, row.started)">
                <i :style="{ width: `${row.started ? Math.min(100, (row.done / row.started) * 100) : 0}%` }" />
              </span>
              <span class="an-meter-value num">{{ pct(row.done, row.started) }}</span>
            </td>
            <td class="num">
              <template v-if="row.skipped">{{ row.skipStep.toLocaleString('ru-RU', { maximumFractionDigits: 1 }) }}<span v-if="row.steps" class="adm-dim"> из {{ row.steps }}</span></template>
              <span v-else class="adm-dim">—</span>
            </td>
            <td class="num">{{ fmt.count(row.seen) }}</td>
          </tr>
        </tbody>
      </table>
      <p v-if="steps.length" class="adm-note an-steps">
        Шаги новичка:
        <span v-for="row in steps" :key="row.mark">{{ row.label }} — <strong>{{ fmt.count(row.users) }}</strong></span>
      </p>
    </section>

    <section class="adm-panel">
      <div class="adm-panel-head">
        <h2>Действия</h2>
        <p>за срок</p>
      </div>
      <div class="an-actions">
        <div v-for="item in actions" :key="item.label" class="an-action">
          <strong class="num">{{ fmt.count(item.value) }}</strong>
          <span>{{ item.label }}</span>
          <span class="adm-dim">{{ item.hint }}</span>
        </div>
      </div>
    </section>

    <div class="an-pair">
      <section class="adm-panel">
        <div class="adm-panel-head">
          <h2>Откуда приходят</h2>
          <p>новые посетители за срок</p>
        </div>
        <table v-if="sources.length" class="adm-table an-table">
          <thead><tr><th>Источник</th><th class="num">Посетители</th><th class="num">Регистрации</th><th class="num">Конверсия</th><th class="num">Платят</th></tr></thead>
          <tbody>
            <tr v-for="row in sources" :key="`${row.kind}:${row.label}`">
              <td>
                <span class="an-source">
                  <span class="adm-badge is-plain" :class="{ 'is-warn': row.kind === 'ref', 'is-ok': row.kind === 'site' }">{{ SOURCE_KIND[row.kind] }}</span>
                  <span>{{ row.label }}</span>
                </span>
              </td>
              <td class="num">{{ fmt.count(row.visitors) }}</td>
              <td class="num">{{ fmt.count(row.signups) }}</td>
              <td class="num">{{ pct(row.signups, row.visitors) }}</td>
              <td class="num">{{ fmt.count(row.paying) }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="adm-empty">Новых посетителей за этот срок не было.</p>
        <RouterLink :to="{ name: 'admin-links' }" class="an-link">Рекламные ссылки →</RouterLink>
      </section>

      <section class="adm-panel">
        <div class="adm-panel-head">
          <h2>Устройства</h2>
          <p>новые посетители</p>
        </div>
        <div v-if="devices.length" class="an-split" role="img" :aria-label="devices.map((row) => `${row.label} ${Math.round(row.share)}%`).join(', ')">
          <i v-for="row in devices" :key="row.device" :class="`is-${row.device}`" :style="{ width: `${row.share}%` }" />
        </div>
        <ul v-if="devices.length" class="an-devices">
          <li v-for="row in devices" :key="row.device">
            <i class="an-dot" :class="`is-${row.device}`" />
            <strong>{{ row.label }}</strong>
            <span class="num">{{ Math.round(row.share) }}%</span>
            <span class="adm-dim">{{ fmt.count(row.visitors) }} посет. · рег. {{ pct(row.signups, row.visitors) }} · платят {{ fmt.count(row.paying) }}</span>
          </li>
        </ul>
        <p v-else class="adm-empty">Нет данных.</p>

        <div class="adm-panel-head an-sub">
          <h2>Первая страница</h2>
          <p>куда попадают впервые</p>
        </div>
        <ul v-if="landings.length" class="an-list">
          <li v-for="row in landings" :key="row.name">
            <span>{{ pageName(row.name) }}</span>
            <span class="num">{{ fmt.count(row.visitors) }}</span>
            <span class="num adm-dim">рег. {{ pct(row.signups, row.visitors) }}</span>
          </li>
        </ul>
        <p v-else class="adm-empty">Нет данных.</p>
      </section>
    </div>

    <section class="adm-panel">
      <div class="adm-panel-head">
        <h2>Посадочные</h2>
        <p>первая страница визита · расчёт и переход к регистрации — цели страницы</p>
      </div>
      <table v-if="adLandings.length" class="adm-table an-table">
        <thead><tr><th>Страница</th><th class="num">Посетители</th><th class="num">Расчёт</th><th class="num">К регистрации</th><th class="num">Регистрации</th><th class="num">Платят</th></tr></thead>
        <tbody>
          <tr v-for="row in adLandings" :key="row.name">
            <td>{{ pageName(row.name) }}</td>
            <td class="num">{{ fmt.count(row.visitors) }}</td>
            <td class="num">{{ fmt.count(row.calcs) }} <span class="adm-dim">· {{ pct(row.calcs, row.visitors) }}</span></td>
            <td class="num">{{ fmt.count(row.ctas) }} <span class="adm-dim">· {{ pct(row.ctas, row.visitors) }}</span></td>
            <td class="num">{{ fmt.count(row.signups) }} <span class="adm-dim">· {{ pct(row.signups, row.visitors) }}</span></td>
            <td class="num">{{ fmt.count(row.paying) }} <span class="adm-dim">· {{ pct(row.paying, row.visitors) }}</span></td>
          </tr>
        </tbody>
      </table>
      <p v-else class="adm-empty">На посадочные за этот срок не заходили.</p>
    </section>

    <section class="adm-panel">
      <div class="adm-panel-head">
        <h2>Страницы</h2>
        <p>просмотры за срок</p>
      </div>
      <table v-if="pages.length" class="adm-table an-table">
        <thead><tr><th>Страница</th><th class="num">Просмотры</th><th class="num">Посетители</th><th class="num">Из них вошли</th><th class="num">На посетителя</th></tr></thead>
        <tbody>
          <tr v-for="row in pages" :key="row.name">
            <td>{{ pageName(row.name) }}</td>
            <td class="num">{{ fmt.count(row.views) }}</td>
            <td class="num">{{ fmt.count(row.visitors) }}</td>
            <td class="num">{{ fmt.count(row.users) }}</td>
            <td class="num">{{ row.visitors ? (row.views / row.visitors).toLocaleString('ru-RU', { maximumFractionDigits: 1 }) : '—' }}</td>
          </tr>
        </tbody>
      </table>
      <p v-else class="adm-empty">Просмотров за этот срок не было.</p>
    </section>
  </div>
</template>

<style scoped>
.an { display: grid; gap: 18px; }
.num { font-variant-numeric: tabular-nums; text-align: right; }

.an-tiles { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 12px; }
.an-tile { display: grid; align-content: start; gap: 4px; padding: 16px 18px; }
.an-tile-label { color: var(--muted); font-size: 14px; }
.an-tile-value { font-size: 26px; font-weight: 600; line-height: 1.15; }
.an-tile-hint { color: var(--soft); font-size: 13px; }

.an-pair { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 18px; }

/* The funnel: one row a step, the bar against the period's new visitors. */
.an-funnel { display: grid; gap: 2px; margin: 4px 0 0; padding: 0; list-style: none; }
.an-funnel li {
  display: grid;
  grid-template-columns: minmax(170px, 15em) minmax(0, 1fr) 4.5em 4.5em 5em;
  align-items: center;
  gap: 14px;
  padding: 7px 0;
}
.an-funnel-name { display: grid; gap: 1px; }
.an-funnel-name strong { font-size: 15px; font-weight: 500; }
.an-funnel-name span { color: var(--soft); font-size: 12px; }
.an-funnel-track { display: block; height: 14px; border-radius: 4px; background: rgba(244, 239, 230, 0.04); overflow: hidden; }
.an-funnel-track i { display: block; height: 100%; border-radius: 4px; background: var(--people); transition: width 0.35s ease; }
.an-funnel li.is-paid .an-funnel-track i { background: var(--money); }
.an-funnel li.is-drop .an-funnel-prev { color: var(--danger); font-weight: 600; }
.an-funnel li.is-drop .an-funnel-name strong::after { content: ' ↓'; color: var(--danger); }
.an-funnel-value { font-size: 16px; font-weight: 600; }
.an-funnel-share { color: var(--ink); font-size: 14px; }
.an-funnel-prev { color: var(--soft); font-size: 13px; }
.an-funnel li:first-child { padding-bottom: 12px; margin-bottom: 6px; border-bottom: 1px dashed var(--panel-line); }

.an-legend { display: flex; flex-wrap: wrap; gap: 6px 18px; margin: 12px 0 0; }
.an-legend span { display: inline-flex; align-items: center; gap: 6px; }
.an-dot { display: inline-block; width: 9px; height: 9px; border-radius: 3px; background: var(--people); flex: none; }
.an-dot.is-paid { background: var(--money); }
.an-dot.is-drop { background: var(--danger); }
.an-dot.is-desktop { background: var(--people); }
.an-dot.is-phone { background: var(--money); }
.an-dot.is-unknown { background: rgba(244, 239, 230, 0.25); }

.an-bars { display: grid; gap: 12px; margin: 4px 0 0; padding: 0; list-style: none; }
.an-bars li { display: grid; grid-template-columns: minmax(0, 13em) minmax(0, 1fr) 7em; align-items: center; gap: 12px; font-size: 14px; }
.an-bars-track { display: block; height: 10px; }
.an-bars-track i { display: block; height: 100%; min-width: 3px; border-radius: 0 4px 4px 0; background: var(--people); }
.an-bars-value { color: var(--soft); font-size: 13px; }

.an-table td, .an-table th { padding-left: 8px; padding-right: 8px; }
.an-meter { display: inline-block; width: 70px; height: 6px; margin-right: 8px; border-radius: 3px; background: rgba(244, 239, 230, 0.08); vertical-align: middle; overflow: hidden; }
.an-meter i { display: block; height: 100%; background: var(--ok); }
.an-meter-value { font-size: 13px; color: var(--soft); }
.an-steps { display: flex; flex-wrap: wrap; gap: 4px 18px; margin: 12px 0 0; }

.an-actions { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 16px 20px; }
.an-action { display: grid; gap: 2px; font-size: 14px; }
.an-action strong { font-size: 22px; font-weight: 600; text-align: left; }
.an-action .adm-dim { font-size: 12px; }

.an-source { display: inline-flex; align-items: center; gap: 8px; }
.an-link { display: inline-block; margin-top: 12px; color: var(--gold); font-size: 14px; text-decoration: none; }
.an-link:hover { text-decoration: underline; }

.an-split { display: flex; height: 12px; margin: 4px 0 14px; border-radius: 6px; overflow: hidden; gap: 2px; }
.an-split i { display: block; height: 100%; }
.an-split i.is-desktop { background: var(--people); }
.an-split i.is-phone { background: var(--money); }
.an-split i.is-unknown { background: rgba(244, 239, 230, 0.25); }
.an-devices { display: grid; gap: 8px; margin: 0; padding: 0; list-style: none; font-size: 14px; }
.an-devices li { display: grid; grid-template-columns: auto auto auto 1fr; align-items: center; gap: 8px; }
.an-devices .adm-dim { font-size: 13px; }
.an-sub { margin-top: 22px; }
.an-list { display: grid; margin: 0; padding: 0; list-style: none; font-size: 14px; }
.an-list li { display: grid; grid-template-columns: minmax(0, 1fr) 4em 6em; gap: 10px; padding: 7px 0; border-top: 1px solid var(--panel-line); }
.an-list li:first-child { border-top: 0; }

@media (max-width: 1200px) {
  .an-tiles { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .an-pair { grid-template-columns: minmax(0, 1fr); }
}
@media (max-width: 760px) {
  .an-tiles { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .an-tile-value { font-size: 22px; }
  .an-funnel li { grid-template-columns: minmax(0, 1fr) 3.5em 4em; gap: 4px 10px; }
  .an-funnel-track { grid-column: 1 / -1; grid-row: 2; }
  .an-funnel-prev { display: none; }
  .an-bars li { grid-template-columns: minmax(0, 1fr) 6em; }
  .an-bars-track { grid-column: 1 / -1; grid-row: 2; }
}
</style>
