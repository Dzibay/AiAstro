<script setup>
/**
 * The way from a first visit to a payment, one row a step: how many reached it, the share of the
 * step before (the bar — so a late step is as readable as an early one), its change against the
 * period before in percentage points, the share of all visitors, who did not go on, and the median
 * time from the first visit. The narrowest step is marked.
 */
import { computed } from 'vue'
import { fmt } from '../../views/admin/shared.js'
import { MIN_BASE, WAY, points, rateOf, share } from '../../views/admin/way.js'

const props = defineProps({
  /** { visit, reg_open, …, paid } — the period's browsers at each step. */
  now: { type: Object, required: true },
  /** The same for the period before, at the same age; null — no comparison. */
  before: { type: Object, default: null },
  /** Median hours from the first visit to each step; null — no time column. */
  hours: { type: Object, default: null },
  /** «прошлые 30 дней», for the hints. */
  period: { type: String, default: 'прошлый срок' },
  /** The first row's name, when the browsers are only some of them (a first page, a device). */
  first: { type: String, default: '' },
})

const time = (value) => {
  if (value == null) return ''
  if (value < 1 / 60) return 'сразу'
  if (value < 1) return `${Math.max(1, Math.round(value * 60))} мин`
  return value < 48 ? `${Math.round(value)} ч` : `${Math.round(value / 24)} дн`
}

const rows = computed(() => {
  const now = props.now
  const visit = now.visit
  const list = WAY.map((step, index) => {
    const value = now[step.key]
    if (!index) return { ...step, label: props.first || step.label, value, first: true }
    const base = now[WAY[index - 1].key]
    const rate = rateOf(now, index)
    let delta = null
    if (props.before) {
      const was = rateOf(props.before, index)
      const enough = base >= MIN_BASE && props.before[WAY[index - 1].key] >= MIN_BASE
      if (!enough) delta = { text: '—', tone: 'none', title: `мало людей для сравнения (меньше ${MIN_BASE} на прошлом шаге)` }
      else {
        const diff = rate - was
        const tone = Math.abs(diff) < 0.01 ? 'flat' : diff > 0 ? 'up' : 'down'
        delta = { text: points(diff), tone, title: `сейчас ${share(rate)}, за ${props.period} ${share(was)}` }
      }
    }
    return {
      ...step,
      value,
      base,
      rate,
      width: rate == null ? 0 : rate * 100,
      ofVisit: visit ? share(value / visit) : '—',
      lost: Math.max(base - value, 0),
      delta,
      time: props.hours ? time(props.hours[step.key]) : '',
      money: step.key === 'checkout' || step.key === 'paid',
      small: base < MIN_BASE,
    }
  })
  // The narrowest step past the first one (opening the form is always the widest fall), as in pulse.py.
  let narrow = null
  list.forEach((row, index) => {
    if (index < 2 || row.small || row.rate == null) return
    if (!narrow || row.rate < narrow.rate) narrow = row
  })
  if (narrow) narrow.narrow = true
  return list
})

const total = computed(() => {
  const rate = props.now.visit ? props.now.paid / props.now.visit : null
  const was = props.before?.visit ? props.before.paid / props.before.visit : null
  return { rate, was, diff: rate != null && was != null ? rate - was : null }
})
</script>

<template>
  <div class="wf" :class="{ 'has-time': hours, 'has-before': before }">
    <div class="wf-row wf-head" aria-hidden="true">
      <span>Шаг</span>
      <span class="num">Людей</span>
      <span>Перешли с прошлого шага</span>
      <span v-if="before" class="num">К прошлому сроку</span>
      <span class="num">От визитов</span>
      <span class="num">Не дошли</span>
      <span v-if="hours" class="num">Время</span>
    </div>
    <ol class="wf-list">
      <li v-for="row in rows" :key="row.key" class="wf-row" :class="{ 'is-first': row.first, 'is-money': row.money, 'is-narrow': row.narrow, 'is-small': row.small }">
        <span class="wf-name">
          <strong>{{ row.label }}</strong>
          <span>{{ row.hint }}</span>
        </span>
        <span class="wf-value num">{{ fmt.count(row.value) }}</span>
        <span v-if="row.first" class="wf-rate-cell adm-dim">все, кто впервые зашёл</span>
        <span v-else class="wf-rate-cell" :title="`${fmt.count(row.value)} из ${fmt.count(row.base)}${row.small ? ' — мало людей для выводов' : ''}`">
          <span class="wf-track"><i :style="{ width: `${Math.max(row.width, row.value ? 1 : 0)}%` }" /></span>
          <span class="wf-rate num">{{ share(row.rate) }}</span>
          <span v-if="row.narrow" class="adm-badge is-bad wf-narrow">узкое место</span>
        </span>
        <span v-if="before" class="wf-delta num">
          <span v-if="row.delta" class="wf-chip" :class="`is-${row.delta.tone}`" :title="row.delta.title">
            <svg v-if="row.delta.tone === 'up' || row.delta.tone === 'down'" viewBox="0 0 10 10" aria-hidden="true"><path :d="row.delta.tone === 'up' ? 'M5 2 9 8H1Z' : 'M5 8 1 2h8Z'" /></svg>
            {{ row.delta.text }}
          </span>
        </span>
        <span class="wf-visit num">{{ row.first ? '100%' : row.ofVisit }}</span>
        <span class="wf-lost num">{{ row.first || !row.lost ? '' : `−${fmt.count(row.lost)}` }}</span>
        <span v-if="hours" class="wf-time num" title="медиана: сколько прошло от первого визита до шага">{{ row.time }}</span>
      </li>
    </ol>
    <p class="wf-total">
      Из визита в оплату: <strong>{{ share(total.rate) }}</strong>
      <template v-if="before && total.was != null">
        · за {{ period }} {{ share(total.was) }}
        <span v-if="total.diff" class="wf-chip" :class="Math.abs(total.diff) < 0.001 ? 'is-flat' : total.diff > 0 ? 'is-up' : 'is-down'">{{ points(total.diff) }}</span>
      </template>
    </p>
  </div>
</template>

<style scoped>
.wf { display: grid; gap: 0; }
.num { font-variant-numeric: tabular-nums; text-align: right; }
.wf-list { display: grid; margin: 0; padding: 0; list-style: none; }
.wf-row {
  display: grid;
  grid-template-columns: minmax(170px, 14em) 4.5em minmax(160px, 1fr) 5em 5em;
  align-items: center;
  gap: 14px;
  padding: 8px 0;
}
.has-before .wf-row { grid-template-columns: minmax(170px, 14em) 4.5em minmax(160px, 1fr) 7.5em 5em 5em; }
.has-time .wf-row { grid-template-columns: minmax(170px, 14em) 4.5em minmax(160px, 1fr) 5em 5em 4.5em; }
.has-before.has-time .wf-row { grid-template-columns: minmax(170px, 14em) 4.5em minmax(160px, 1fr) 7.5em 5em 5em 4.5em; }
.wf-head { padding: 0 0 8px; border-bottom: 1px solid var(--panel-line); color: var(--soft); font-size: 12px; }
.wf-list .wf-row { border-bottom: 1px solid rgba(244, 239, 230, 0.05); }
.wf-list .wf-row:last-child { border-bottom: 0; }
.wf-name { display: grid; gap: 1px; min-width: 0; }
.wf-name strong { font-size: 15px; font-weight: 500; }
.wf-name span { color: var(--soft); font-size: 12px; }
.wf-value { font-size: 16px; font-weight: 600; }
.wf-rate-cell { display: flex; align-items: center; gap: 10px; min-width: 0; font-size: 13px; }
.wf-track { flex: 1 1 auto; display: block; height: 14px; border-radius: 4px; background: rgba(244, 239, 230, 0.05); overflow: hidden; }
.wf-track i { display: block; height: 100%; border-radius: 4px; background: var(--people); transition: width 0.35s ease; }
.is-money .wf-track i { background: var(--money); }
.is-narrow .wf-track i { background: var(--danger); }
.is-small .wf-track i { opacity: 0.45; }
.wf-rate { flex: none; width: 3.4em; color: var(--ink); font-size: 14px; font-weight: 600; }
.wf-narrow { flex: none; font-size: 12px; }
.wf-chip { display: inline-flex; align-items: center; gap: 4px; color: var(--soft); font-size: 13px; font-weight: 600; white-space: nowrap; }
.wf-chip svg { width: 9px; height: 9px; fill: currentColor; }
.wf-chip.is-up { color: var(--ok); }
.wf-chip.is-down { color: var(--danger); }
.wf-chip.is-flat, .wf-chip.is-none { color: var(--soft); font-weight: 400; }
.wf-visit { color: var(--soft); font-size: 13px; }
.wf-lost { color: var(--soft); font-size: 13px; }
.is-narrow .wf-lost { color: var(--danger); font-weight: 600; }
.wf-time { color: var(--soft); font-size: 12px; }
.wf-total { margin: 12px 0 0; padding-top: 12px; border-top: 1px dashed var(--panel-line); color: var(--soft); font-size: 14px; }
.wf-total strong { color: var(--ink); font-size: 16px; }
.wf-total .wf-chip { margin-left: 6px; }

@media (max-width: 860px) {
  .wf-head { display: none; }
  .wf .wf-row { grid-template-columns: minmax(0, 1fr) 4em 6.5em; gap: 6px 10px; }
  .wf-rate-cell { grid-column: 1 / -1; grid-row: 2; }
  .wf-visit, .wf-lost, .wf-time { display: none; }
  .wf:not(.has-before) .wf-row { grid-template-columns: minmax(0, 1fr) 4em; }
}
</style>
