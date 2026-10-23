<script setup>
/**
 * The way split by source, first page or device: a row a segment, a column a step's share of the
 * step before. A cell is tinted by how far it is from everyone's share — warm below, cool above —
 * the biggest falls (weighed by how many people stand behind them) are framed, and a share of
 * too few people is pale.
 */
import { computed } from 'vue'
import { fmt } from '../../views/admin/shared.js'
import { MIN_BASE, WAY, rateOf, segmentName, share } from '../../views/admin/way.js'

const props = defineProps({
  /** pulse.py segments().items */
  items: { type: Array, required: true },
  /** The whole, for the comparison. */
  total: { type: Object, required: true },
  /** channel | landing | device */
  by: { type: String, required: true },
})

const COLUMNS = [
  ...WAY.slice(1).map((step, index) => ({ key: step.key, label: step.short, title: `${step.label} — из ${step.of}`, index: index + 1 })),
  { key: 'end', label: 'Визит → оплата', title: 'Оплатили — из всех зашедших', index: null },
]

function cell(row, column) {
  const base = column.index == null ? row.visit : row[WAY[column.index - 1].key]
  const value = column.index == null ? row.paid : row[column.key]
  const rate = base ? value / base : null
  const all = column.index == null ? (props.total.visit ? props.total.paid / props.total.visit : null) : rateOf(props.total, column.index)
  return { key: column.key, base, value, rate, all, small: base < MIN_BASE, diff: rate == null || all == null ? 0 : rate - all }
}

const rows = computed(() => {
  const list = props.items.map((row) => ({
    key: row.key || 'rest',
    name: segmentName(props.by, row),
    visit: row.visit,
    cells: COLUMNS.map((column) => cell(row, column)),
  }))
  // The biggest falls among the steps (the whole way is their sum, not a step of its own): the share
  // below everyone's, weighed by the people behind it, three at most.
  const falls = list.flatMap((row) => row.cells
    .filter((c) => c.key !== 'end' && !c.small && c.diff < 0 && c.all)
    .map((c) => ({ c, weight: (-c.diff / c.all) * Math.sqrt(c.base / MIN_BASE) })))
  falls.sort((a, b) => b.weight - a.weight).slice(0, 3).forEach(({ c }) => { c.worst = true })
  for (const row of list) {
    for (const c of row.cells) {
      const strength = c.all ? Math.min(1, Math.abs(c.diff) / c.all) : 0
      c.tint = c.small || !c.diff ? null
        : c.diff < 0 ? `rgba(231, 160, 144, ${0.07 + strength * 0.33})` : `rgba(159, 211, 168, ${0.05 + strength * 0.25})`
      c.title = `${share(c.rate)}: ${fmt.count(c.value)} из ${fmt.count(c.base)} · у всех ${share(c.all)}${c.small ? ' · мало людей для выводов' : ''}`
    }
  }
  return list
})

const totalRow = computed(() => ({ visit: props.total.visit, cells: COLUMNS.map((column) => cell(props.total, column)) }))
</script>

<template>
  <div class="sm">
    <div class="sm-scroll">
      <table class="adm-table sm-table">
        <thead>
          <tr>
            <th>{{ by === 'channel' ? 'Источник' : by === 'landing' ? 'Первая страница' : 'Устройство' }}</th>
            <th class="num">Посетители</th>
            <th v-for="column in COLUMNS" :key="column.key" class="num" :title="column.title">{{ column.label }}</th>
          </tr>
        </thead>
        <tbody>
          <tr class="sm-total">
            <td>Все</td>
            <td class="num">{{ fmt.count(totalRow.visit) }}</td>
            <td v-for="c in totalRow.cells" :key="c.key" class="num" :title="`${fmt.count(c.value)} из ${fmt.count(c.base)}`">{{ share(c.rate) }}</td>
          </tr>
          <tr v-for="row in rows" :key="row.key">
            <td class="sm-name">{{ row.name }}</td>
            <td class="num">{{ fmt.count(row.visit) }}</td>
            <td
              v-for="c in row.cells"
              :key="c.key"
              class="num sm-cell"
              :class="{ 'is-small': c.small, 'is-worst': c.worst }"
              :style="c.tint ? { background: c.tint } : null"
              :title="c.title"
            >
              <svg v-if="c.worst" viewBox="0 0 10 10" aria-hidden="true"><path d="M5 8 1 2h8Z" /></svg>{{ c.base ? share(c.rate) : '—' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p class="adm-note sm-legend">
      <span>каждая доля — из дошедших до прошлого шага</span>
      <span><i class="sm-key is-low" /> ниже, чем у всех</span>
      <span><i class="sm-key is-high" /> выше</span>
      <span><i class="sm-key is-worst" /> самые большие провалы с учётом числа людей</span>
      <span class="sm-pale">бледные — меньше {{ MIN_BASE }} человек на прошлом шаге</span>
    </p>
  </div>
</template>

<style scoped>
.sm-scroll { overflow-x: auto; }
.sm-table { font-size: 14px; }
.sm-table th, .sm-table td { padding: 8px 10px; white-space: nowrap; }
.sm-table th { font-size: 13px; }
.num { text-align: right; font-variant-numeric: tabular-nums; }
.sm-name { max-width: 18em; overflow: hidden; text-overflow: ellipsis; }
.sm-total td { color: var(--ink); font-weight: 600; background: rgba(244, 239, 230, 0.03); }
.sm-cell { position: relative; }
.sm-cell svg { width: 8px; height: 8px; margin-right: 4px; fill: var(--danger); vertical-align: 1px; }
.sm-cell.is-small { color: var(--soft); opacity: 0.55; }
.sm-cell.is-worst { outline: 2px solid var(--danger); outline-offset: -3px; border-radius: 6px; font-weight: 600; }
.sm-legend { display: flex; flex-wrap: wrap; gap: 6px 18px; margin: 12px 0 0; }
.sm-legend span { display: inline-flex; align-items: center; gap: 6px; }
.sm-key { display: inline-block; width: 14px; height: 10px; border-radius: 3px; }
.sm-key.is-low { background: rgba(231, 160, 144, 0.35); }
.sm-key.is-high { background: rgba(159, 211, 168, 0.3); }
.sm-key.is-worst { outline: 2px solid var(--danger); outline-offset: -2px; }
.sm-pale { opacity: 0.7; }
</style>
