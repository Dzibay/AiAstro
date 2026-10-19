<script setup>
import { computed, ref } from 'vue'
import { ASPECTS, POINTS } from '../cabinet/astro.js'

/**
 * The star calendar: thirty days from today on a Monday-first grid, each day a star that burns
 * gold when the sky is kind, red when it asks for care, and stays pale when it is even. The
 * first week is open to everyone; the rest lies in the haze until «Небосвод» lights it.
 */

const props = defineProps({
  /** GET /me/forecast/month: { start, days: [{ date, tone, score, top }], open, locked } */
  month: { type: Object, required: true },
})

const day = (iso) => new Date(`${iso}T00:00:00Z`)
const dayFormat = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long', timeZone: 'UTC' })
const weekdayFormat = new Intl.DateTimeFormat('ru-RU', { weekday: 'long', timeZone: 'UTC' })
const monthFormat = new Intl.DateTimeFormat('ru-RU', { month: 'short', timeZone: 'UTC' })
const WEEKDAYS = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс']

const TONES = {
  easy: { name: 'лёгкий день', hint: 'хорош для начинаний, встреч и просьб' },
  tense: { name: 'бережный день', hint: 'меньше спешки, больше пауз — и не спорить сгоряча' },
  calm: { name: 'ровный день', hint: 'небо не торопит: время для обычных дел' },
}

const cells = computed(() => {
  const days = props.month.days
  if (!days.length) return []
  const lead = (day(days[0].date).getUTCDay() + 6) % 7
  return [
    ...Array.from({ length: lead }, (_, index) => ({ key: `blank-${index}`, blank: true })),
    ...days.map((entry, index) => {
      const date = day(entry.date)
      const veiled = entry.tone == null
      return {
        key: entry.date,
        ...entry,
        index,
        veiled,
        number: date.getUTCDate(),
        // The month's name where it turns, so «1» is not read as the first of this month.
        monthMark: index === 0 || date.getUTCDate() === 1 ? monthFormat.format(date).replace('.', '') : '',
        label: `${dayFormat.format(date)}, ${weekdayFormat.format(date)}${veiled ? ', в тумане' : `: ${TONES[entry.tone].name}`}`,
      }
    }),
  ]
})

const selected = ref(0)
const current = computed(() => cells.value.find((cell) => !cell.blank && cell.index === selected.value) || null)
const transit = computed(() => {
  const top = current.value?.top
  if (!top) return ''
  return `${POINTS[top.a].name}: ${ASPECTS[top.type].name.toLowerCase()} с ${POINTS[top.b].with}`
})
const currentDate = computed(() => {
  if (!current.value) return ''
  const date = day(current.value.date)
  const prefix = current.value.index === 0 ? 'Сегодня, ' : current.value.index === 1 ? 'Завтра, ' : ''
  return `${prefix}${dayFormat.format(date)}, ${weekdayFormat.format(date)}`
})
</script>

<template>
  <div class="star-calendar">
    <ol class="grid" aria-label="Звёздный календарь на тридцать дней">
      <li v-for="name in WEEKDAYS" :key="name" class="weekday" aria-hidden="true">{{ name }}</li>
      <li v-for="cell in cells" :key="cell.key" :class="{ 'is-blank': cell.blank }" :aria-hidden="cell.blank ? 'true' : undefined">
        <button
          v-if="!cell.blank"
          type="button"
          class="cell"
          :class="[cell.veiled ? 'is-veiled' : `tone-${cell.tone}`, { 'is-on': selected === cell.index, 'is-today': cell.index === 0 }]"
          :aria-label="cell.label"
          :aria-pressed="selected === cell.index"
          @click="selected = cell.index"
        >
          <span class="cell-month" aria-hidden="true">{{ cell.monthMark }}</span>
          <span class="cell-number" aria-hidden="true">{{ cell.number }}</span>
          <svg class="cell-star" viewBox="0 0 20 20" aria-hidden="true"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg>
        </button>
      </li>
    </ol>

    <div v-if="current" class="detail" aria-live="polite">
      <p class="detail-date">{{ currentDate }}</p>
      <template v-if="current.veiled">
        <p class="detail-tone">в тумане</p>
        <p class="detail-text">Этот день ещё скрыт облаками. «Небосвод» откроет все тридцать дней и главный транзит каждого.</p>
      </template>
      <template v-else>
        <p class="detail-tone" :class="`tone-${current.tone}`">{{ TONES[current.tone].name }}</p>
        <p class="detail-text">{{ TONES[current.tone].hint }}.</p>
        <p v-if="transit" class="detail-transit">Главный транзит — {{ transit }}</p>
      </template>
    </div>

    <p class="legend" aria-hidden="true">
      <span class="legend-item tone-easy"><svg viewBox="0 0 20 20"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg> легче</span>
      <span class="legend-item tone-tense"><svg viewBox="0 0 20 20"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg> бережнее</span>
      <span class="legend-item tone-calm"><svg viewBox="0 0 20 20"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg> ровно</span>
      <span v-if="month.locked" class="legend-item is-veiled"><svg viewBox="0 0 20 20"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg> в тумане</span>
    </p>
  </div>
</template>

<style scoped>
.star-calendar { display: grid; gap: 14px; }

.grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 3px; margin: 0; padding: 0; list-style: none; }
.weekday { padding-bottom: 2px; text-align: center; font-family: var(--caps); font-size: 13.5px; letter-spacing: 0.06em; color: rgba(226, 220, 210, 0.5); }

.cell {
  position: relative;
  display: grid;
  justify-items: center;
  gap: 2px;
  width: 100%;
  padding: 12px 0 6px;
  border-radius: 10px;
  border: 1px solid transparent;
  background: none;
  font: inherit;
  color: #f6efe2;
  cursor: pointer;
  transition: background 0.25s ease, border-color 0.25s ease;
}
.cell:hover { background: rgba(240, 205, 138, 0.06); }
.cell.is-on { border-color: rgba(240, 205, 138, 0.5); background: rgba(240, 205, 138, 0.08); }
.cell:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 1px; }
.cell-month { position: absolute; top: 1px; left: 0; right: 0; font-family: var(--serif); font-style: italic; font-size: 11px; line-height: 1; color: rgba(240, 205, 138, 0.7); }
.cell-number { font-family: var(--serif); font-size: 17px; line-height: 1; font-variant-numeric: lining-nums; }
.is-today .cell-number { color: #f0cd8a; font-weight: 600; }
.cell-star { width: 11px; height: 11px; fill: rgba(226, 220, 210, 0.4); }

.tone-easy .cell-star, .legend .tone-easy svg { fill: #f6dfa6; filter: drop-shadow(0 0 5px rgba(255, 205, 120, 0.9)); }
.tone-tense .cell-star, .legend .tone-tense svg { fill: #e09a88; filter: drop-shadow(0 0 5px rgba(230, 130, 110, 0.75)); }
.tone-calm .cell-star, .legend .tone-calm svg { fill: rgba(214, 226, 244, 0.7); }

/* The haze: the locked days are there, but read as a cloud over the sky. */
.cell.is-veiled .cell-number { color: rgba(226, 220, 210, 0.32); }
.cell.is-veiled .cell-star, .legend .is-veiled svg { fill: none; stroke: rgba(226, 220, 210, 0.25); stroke-width: 1.2; }
.cell.is-veiled { background: radial-gradient(circle at 50% 60%, rgba(200, 200, 220, 0.05), transparent 70%); }
.cell.is-veiled.is-on { border-color: rgba(226, 220, 210, 0.3); background: rgba(226, 220, 210, 0.05); }

.detail { display: grid; gap: 4px; padding: 12px 14px; border-radius: 14px; border: 1px solid rgba(240, 210, 150, 0.14); background: rgba(255, 240, 210, 0.02); }
.detail p { margin: 0; }
.detail-date { font-family: var(--caps); font-size: 14px; letter-spacing: 0.08em; color: rgba(226, 220, 210, 0.6); }
.detail-tone { font-family: var(--serif); font-style: italic; font-size: 20px; line-height: 1.2; color: rgba(226, 220, 210, 0.6); }
.detail-tone.tone-easy { color: #f6dfa6; }
.detail-tone.tone-tense { color: #e8a594; }
.detail-tone.tone-calm { color: #dfe6f2; }
.detail-text { font-family: var(--book); font-size: 14.5px; line-height: 1.55; color: #efe7d8; }
.detail-text::first-letter { text-transform: uppercase; }
.detail-transit { font-family: var(--book); font-size: 13.5px; color: rgba(233, 194, 124, 0.85); }

.legend { display: flex; flex-wrap: wrap; gap: 14px; margin: 0; font-family: var(--serif); font-style: italic; font-size: 15px; color: rgba(226, 220, 210, 0.55); }
.legend-item { display: inline-flex; align-items: center; gap: 6px; }
.legend svg { width: 10px; height: 10px; }

@media (max-width: 760px) {
  .cell { min-height: 44px; }
}
</style>
