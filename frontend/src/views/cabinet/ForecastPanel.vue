<script setup>
import { computed, onUnmounted, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import PanelHead from '../../components/cabinet/PanelHead.vue'
import ReadingText from '../../components/cabinet/ReadingText.vue'
import StarCalendar from '../../components/sky/StarCalendar.vue'
import SkyNudge from '../../components/sky/SkyNudge.vue'
import { useChart } from '../../composables/useChart.js'
import { PERIODS, useForecast } from '../../composables/useForecast.js'
import { ASPECTS, POINTS } from '../../components/cabinet/astro.js'
import { usePrices } from '../../utils/prices.js'

/**
 * The forecast beside the wheel: a day, a week or the star calendar of the month. The transits
 * are a calculation and open to everyone; the text is «Небосвод», so without it the first lines
 * fade into the haze, and the calendar shows its first week only.
 */

defineProps({
  user: { type: Object, required: true },
})

const route = useRoute()
const router = useRouter()
const { hot } = useChart()
const { forecasts, load } = useForecast()

const MODES = [
  { id: 'day', name: 'День' },
  { id: 'week', name: 'Неделя' },
  { id: 'month', name: 'Месяц' },
]
const period = computed(() => (MODES.some((mode) => mode.id === route.query.period) ? route.query.period : 'day'))
const { sky: skyPrice } = usePrices()
const entry = computed(() => forecasts[period.value])
const data = computed(() => entry.value.data)

// The open period first, then the other two in the background: the toggle never waits for them.
watch(period, (value) => {
  load(value)
  for (const other of PERIODS) {
    if (other !== value) load(other)
  }
}, { immediate: true })
onUnmounted(() => {
  hot.value = ''
})

function choose(value) {
  if (value === period.value) return
  router.replace({ query: value === 'day' ? {} : { period: value } })
}

const dayFormat = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long', timeZone: 'UTC' })
const weekdayFormat = new Intl.DateTimeFormat('ru-RU', { weekday: 'long', timeZone: 'UTC' })
const shortWeekday = new Intl.DateTimeFormat('ru-RU', { weekday: 'short', timeZone: 'UTC' })
// The dates are calendar days of the person's zone: read them as such, not as moments.
const day = (iso) => new Date(`${iso}T00:00:00Z`)

/** «19 октября, понедельник» or «19 — 25 октября». */
const dateLine = computed(() => {
  if (!data.value) return ''
  const start = day(data.value.start)
  if (data.value.period === 'day') return `${dayFormat.format(start)}, ${weekdayFormat.format(start)}`
  const end = day(data.value.end)
  const sameMonth = start.getUTCMonth() === end.getUTCMonth()
  return `${sameMonth ? start.getUTCDate() : dayFormat.format(start)} — ${dayFormat.format(end)}`
})

const TONES = { easy: 'лёгкий', tense: 'напряжённый', calm: 'ровный' }

const transits = computed(() => (data.value ? data.value.transits : []).map((transit) => ({
  key: `${transit.a}-${transit.b}-${transit.type}`,
  from: POINTS[transit.a].glyph,
  aspect: ASPECTS[transit.type],
  to: POINTS[transit.b].glyph,
  // «Марс: квадрат с Венерой»
  label: `${POINTS[transit.a].name}: ${ASPECTS[transit.type].name.toLowerCase()} с ${POINTS[transit.b].with}`,
  when: transit.date ? shortWeekday.format(day(transit.date)) : '',
})))

const week = computed(() => (data.value?.days || []).map((entry) => {
  const date = day(entry.date)
  return {
    date: entry.date,
    weekday: shortWeekday.format(date),
    number: date.getUTCDate(),
    tone: entry.tone,
    label: `${weekdayFormat.format(date)}, ${dayFormat.format(date)}: ${TONES[entry.tone]} день`,
  }
}))

function setHot(key) {
  hot.value = key
}
</script>

<template>
  <div class="forecast-panel">
    <div class="mode-toggle" role="group" aria-label="Прогноз на день, неделю или месяц">
      <span class="mode-thumb" :style="{ transform: `translateX(${MODES.findIndex((mode) => mode.id === period) * 100}%)` }" aria-hidden="true" />
      <button v-for="mode in MODES" :key="mode.id" type="button" :aria-pressed="period === mode.id" @click="choose(mode.id)">{{ mode.name }}</button>
    </div>

    <template v-if="entry.status === 'empty'">
      <PanelHead lead="Прогноз читает небо дня поверх вашей карты, а карте нужна дата рождения.">
        Ваш <em>прогноз</em>
      </PanelHead>
      <RouterLink class="add-birth" :to="{ name: 'cabinet-birth' }">
        <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg>
        Добавить дату рождения
      </RouterLink>
    </template>

    <p v-else-if="entry.status === 'error'" class="error">{{ entry.message }}</p>
    <p v-else-if="!data" class="loading">Смотрим, что небо готовит…</p>

    <template v-else-if="period === 'month'">
      <PanelHead lead="Тридцать дней вперёд: у каждого своя звезда.">Звёздный <em>календарь</em></PanelHead>
      <StarCalendar :month="data" />
      <div v-if="data.locked" class="unlock">
        <p class="unlock-note">Открыта первая неделя. Остальные дни месяца и главный транзит каждого — в «Небосводе».</p>
        <RouterLink class="unlock-cta" :to="{ name: 'cabinet-sky' }">
          <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg>
          Рассеять туман — {{ skyPrice }}
        </RouterLink>
      </div>
    </template>

    <template v-else>
      <PanelHead :lead="dateLine">{{ data.title }}</PanelHead>

      <div class="text" :class="{ 'is-locked': data.locked }">
        <ReadingText :reading="data.reading" />
      </div>
      <div v-if="data.locked" class="unlock">
        <p class="unlock-note">Транзиты открыты всем. Полный текст дня и недели — в «Небосводе».</p>
        <RouterLink class="unlock-cta" :to="{ name: 'cabinet-sky' }">
          <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg>
          Зажечь Небосвод — {{ skyPrice }}
        </RouterLink>
      </div>

      <section v-if="week.length" class="block" aria-labelledby="week-title">
        <h3 id="week-title" class="block-title">Семь дней</h3>
        <ol class="week">
          <li v-for="entry in week" :key="entry.date" class="week-day" :class="`tone-${entry.tone}`" :aria-label="entry.label" :title="entry.label">
            <span class="week-name" aria-hidden="true">{{ entry.weekday }}</span>
            <span class="week-number" aria-hidden="true">{{ entry.number }}</span>
            <span class="week-dot" aria-hidden="true" />
          </li>
        </ol>
        <p class="legend" aria-hidden="true">
          <span class="legend-item tone-easy"><span class="week-dot" /> легче</span>
          <span class="legend-item tone-tense"><span class="week-dot" /> бережнее</span>
          <span class="legend-item tone-calm"><span class="week-dot" /> ровно</span>
        </p>
      </section>

      <section class="block" aria-labelledby="transits-title">
        <h3 id="transits-title" class="block-title">Ключевые транзиты</h3>
        <ul v-if="transits.length" class="chips">
          <li v-for="transit in transits" :key="transit.key">
            <button
              type="button"
              class="chip"
              :class="{ 'is-on': hot === transit.key }"
              :aria-label="transit.when ? `${transit.label}, ${transit.when}` : transit.label"
              @pointerenter="setHot(transit.key)"
              @pointerleave="setHot('')"
              @focus="setHot(transit.key)"
              @blur="setHot('')"
            >
              <span class="chip-glyphs" aria-hidden="true">
                <span class="glyph-sky">{{ transit.from }}</span>
                <span :class="`tone-${transit.aspect.tone}`">{{ transit.aspect.glyph }}</span>
                <span class="glyph-natal">{{ transit.to }}</span>
              </span>
              <span class="chip-text" aria-hidden="true">{{ transit.label }}</span>
              <span v-if="transit.when" class="chip-when" aria-hidden="true">{{ transit.when }}</span>
            </button>
          </li>
        </ul>
        <p v-else class="quiet-text">Тесных транзитов нет: небо оставляет вам свободу.</p>
      </section>

      <SkyNudge v-if="period === 'week'" :to="{ query: { period: 'month' } }" action="Открыть календарь">
        Хотите видеть дальше недели? В звёздном календаре у каждого дня месяца своя звезда — лёгкая, бережная или ровная.
      </SkyNudge>
    </template>
  </div>
</template>

<style scoped>
.forecast-panel { display: grid; gap: 18px; }

.loading { margin: 0; font-family: var(--serif); font-style: italic; font-size: 17px; color: rgba(242, 228, 200, 0.75); }
.error { margin: 0; font-size: 14px; color: #f2a48c; }
.quiet-text { margin: 0; font-size: 14.5px; line-height: 1.5; color: rgba(226, 220, 210, 0.62); }

/* The login's toggle: a gold thumb sliding under two words. */
.mode-toggle {
  position: relative;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  padding: 3px;
  border-radius: 999px;
  border: 1px solid rgba(240, 210, 150, 0.22);
  background: rgba(255, 240, 210, 0.03);
}
.mode-toggle button {
  position: relative;
  padding: 7px 14px;
  border: 0;
  background: none;
  font: inherit;
  font-size: 13px;
  letter-spacing: 0.04em;
  color: rgba(226, 220, 210, 0.7);
  cursor: pointer;
  transition: color 0.3s ease;
}
.mode-toggle button[aria-pressed='true'] { color: #2b1d0b; }
.mode-toggle button:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 2px; border-radius: 999px; }
.mode-thumb {
  position: absolute;
  top: 3px;
  bottom: 3px;
  left: 3px;
  width: calc((100% - 6px) / 3);
  border-radius: 999px;
  background: linear-gradient(180deg, #f4dba6, #dcb36c);
  transition: transform 0.45s cubic-bezier(0.3, 0.7, 0.2, 1);
}

.text { display: grid; gap: 12px; }
/* Without «Небосвод» the first lines dissolve into the haze. */
.text.is-locked {
  max-height: 10.5em;
  overflow: hidden;
  -webkit-mask-image: linear-gradient(180deg, #000 30%, transparent);
  mask-image: linear-gradient(180deg, #000 30%, transparent);
  user-select: none;
}

.unlock { display: grid; gap: 12px; justify-items: start; margin-top: -8px; }
.unlock-note { margin: 0; font-size: 13.5px; line-height: 1.5; color: rgba(233, 194, 124, 0.8); }
.unlock-cta {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 11px 20px;
  border-radius: 999px;
  background: linear-gradient(180deg, #f4dba6, #dcb36c);
  color: #2b1d0b;
  font-size: 14.5px;
  font-weight: 600;
  text-decoration: none;
  box-shadow: 0 8px 26px rgba(230, 170, 80, 0.22);
  transition: box-shadow 0.25s ease, transform 0.25s ease;
}
.unlock-cta svg { width: 10px; height: 10px; fill: #5a3d12; }
.unlock-cta:hover { box-shadow: 0 10px 34px rgba(230, 170, 80, 0.38); transform: translateY(-1px); }
.unlock-cta:focus-visible { outline: 2px solid #ffe2a8; outline-offset: 3px; }


.week { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; margin: 0; padding: 0; list-style: none; }
.week-day { display: grid; justify-items: center; gap: 3px; padding: 6px 0; }
.week-name { font-family: var(--caps); font-size: 14px; letter-spacing: 0.06em; color: rgba(226, 220, 210, 0.55); }
.week-number { font-family: var(--serif); font-size: 18px; color: #f6efe2; }
.week-dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: rgba(226, 220, 210, 0.35); }
.tone-easy .week-dot { background: #f0cd8a; box-shadow: 0 0 8px rgba(255, 205, 120, 0.7); }
.tone-tense .week-dot { background: #d98b7a; box-shadow: 0 0 8px rgba(230, 130, 110, 0.6); }
.legend { display: flex; flex-wrap: wrap; gap: 14px; margin: 0; font-family: var(--serif); font-style: italic; font-size: 15px; color: rgba(226, 220, 210, 0.55); }
.legend-item { display: inline-flex; align-items: center; gap: 6px; }

.chips { display: grid; gap: 6px; margin: 0; padding: 0; list-style: none; }
.chip {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px 12px;
  border-radius: 14px;
  border: 1px solid rgba(240, 210, 150, 0.14);
  background: rgba(255, 240, 210, 0.02);
  font: inherit;
  text-align: left;
  color: #efe7d8;
  cursor: default;
  transition: border-color 0.25s ease, background 0.25s ease;
}
.chip:hover, .chip.is-on { border-color: rgba(240, 205, 138, 0.5); background: rgba(240, 205, 138, 0.06); }
.chip:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 2px; }
.chip-glyphs { display: inline-flex; gap: 5px; font-family: 'Segoe UI Symbol', 'Noto Sans Symbols', sans-serif; font-size: 16px; }
.glyph-sky { color: #d6e2f4; }
.glyph-natal { color: #f0cd8a; }
.chip-glyphs .tone-easy, .chip-glyphs .tone-joint { color: #f0cd8a; }
.chip-glyphs .tone-tense { color: #d98b7a; }
.chip-text { font-family: var(--book); font-size: 14px; }
.chip-when { font-family: var(--serif); font-style: italic; font-size: 14.5px; color: rgba(226, 220, 210, 0.55); }

.add-birth {
  justify-self: start;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 11px 20px;
  border-radius: 999px;
  border: 1px solid rgba(240, 205, 138, 0.5);
  background: rgba(240, 205, 138, 0.06);
  font-size: 14.5px;
  color: #f3dcae;
  text-decoration: none;
  transition: background 0.25s ease, border-color 0.25s ease;
}
.add-birth svg { width: 10px; height: 10px; fill: #f0cd8a; filter: drop-shadow(0 0 5px rgba(255, 200, 110, 0.8)); }
.add-birth:hover { background: rgba(240, 205, 138, 0.12); border-color: rgba(240, 205, 138, 0.8); }
.add-birth:focus-visible { outline: 2px solid #ffe2a8; outline-offset: 3px; }

@media (max-width: 760px) {
  .mode-toggle button, .chip, .unlock-cta, .add-birth { min-height: 44px; }
}
@media (prefers-reduced-motion: reduce) {
  .mode-thumb, .unlock-cta { transition: none; }
}
</style>
