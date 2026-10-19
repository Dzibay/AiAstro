<script setup>
import { computed, watch } from 'vue'
import { RouterLink } from 'vue-router'
import PanelHead from '../../components/cabinet/PanelHead.vue'
import { useSky } from '../../composables/useSky.js'
import { useForecast } from '../../composables/useForecast.js'
import { ROMAN } from '../../components/cabinet/astro.js'
import { SIGNS } from '../../utils/skyToday.js'
import { formatDate } from '../../utils/format.js'

/** The overview: a greeting, the birth data and the way out. The sections are on the sky. */

const props = defineProps({
  user: { type: Object, required: true },
})
const emit = defineEmits(['logout'])

const { mark } = useSky()
const SIGN_BY_ID = Object.fromEntries(SIGNS.map((sign) => [sign.id, sign]))

const signLine = computed(() => {
  const sun = SIGN_BY_ID[mark.sun]
  if (!sun) return ''
  const moon = SIGN_BY_ID[mark.moon]
  return moon ? `Солнце ${sun.in}, Луна ${moon.in}` : `Солнце ${sun.in}`
})

const birthLine = computed(() => {
  const birth = props.user.birth
  if (!birth) return ''
  return [formatDate(birth.date), birth.time, birth.place].filter(Boolean).join(' · ')
})

/** «Сегодня Луна в Раке и проходит ваш IV дом»: the day's forecast, asked once the birth date is there. */
const { forecasts, load } = useForecast()
watch(() => props.user.birth?.date, (date) => {
  if (date) load('day')
}, { immediate: true })
const moonLine = computed(() => {
  const moon = forecasts.day.data?.moon
  if (!moon) return ''
  const sign = SIGN_BY_ID[moon.sign]
  return moon.house ? `Сегодня Луна ${sign.in} и проходит ваш ${ROMAN[moon.house - 1]} дом` : `Сегодня Луна ${sign.in}`
})

const untilFormat = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long' })
const skyLine = computed(() => (props.user.sky ? `открыт до ${untilFormat.format(new Date(props.user.sky_until))}` : ''))

/** A city typed without picking a suggestion: the chart will need its coordinates. */
const unplaced = computed(() => Boolean(props.user.birth?.place && props.user.birth.lat == null))
</script>

<template>
  <div class="overview">
    <PanelHead :level="1" :lead="signLine || 'Добавьте дату рождения — и небо нарисует ваш знак.'">
      Здравствуйте, <em>{{ user.name }}</em>
    </PanelHead>

    <RouterLink v-if="!user.birth" class="add-birth" :to="{ name: 'cabinet-birth' }">
      <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg>
      Добавить дату рождения
    </RouterLink>

    <RouterLink v-if="moonLine" class="today" :to="{ name: 'cabinet-forecast' }">
      <span class="today-moon" aria-hidden="true">☽︎</span>
      <span>{{ moonLine }}</span>
      <span class="today-more">Прогноз дня</span>
    </RouterLink>

    <dl class="facts">
      <div v-if="birthLine" class="fact-birth">
        <dt>Рождение</dt>
        <dd>
          {{ birthLine }}
          <RouterLink class="edit" :to="{ name: 'cabinet-birth' }" aria-label="Изменить данные рождения">Изменить</RouterLink>
        </dd>
      </div>
      <div><dt>Почта</dt><dd>{{ user.email }}</dd></div>
      <div class="fact-sky">
        <dt>Небосвод</dt>
        <dd>
          <template v-if="skyLine">{{ skyLine }}</template>
          <template v-else>
            не подключён
            <RouterLink class="edit" :to="{ name: 'checkout', params: { product: 'sky' } }">Открыть — от … ₽</RouterLink>
          </template>
        </dd>
      </div>
      <div><dt>С нами</dt><dd>с {{ formatDate(user.created_at) }}</dd></div>
    </dl>
    <p v-if="unplaced" class="hint">
      Город записан словом, без координат.
      <RouterLink class="inline" :to="{ name: 'cabinet-birth' }">Выберите его из подсказок</RouterLink>,
      чтобы карта посчитала дома.
    </p>

    <p class="guide">
      Созвездия рядом с вашей звездой — разделы кабинета: карта, прогноз, пара и астролог.
      Сама звезда открывает данные рождения.
    </p>

    <button type="button" class="quiet" @click="emit('logout')">Выйти</button>
  </div>
</template>

<style scoped>
.overview { display: grid; gap: 16px; }

.facts { display: grid; gap: 8px; margin: 0; padding: 14px 0; border-block: 1px solid rgba(240, 210, 150, 0.12); }
.facts div { display: flex; justify-content: space-between; gap: 16px; font-size: 14px; }
.facts dt { color: rgba(226, 220, 210, 0.55); }
.facts dd { margin: 0; text-align: right; color: #efe7d8; overflow-wrap: anywhere; }

.fact-birth dd, .fact-sky dd { display: grid; justify-items: end; gap: 2px; }

/* The day in one line: the Moon's passage, and the way into the forecast. */
.today {
  display: grid;
  grid-template-columns: auto 1fr;
  align-items: center;
  column-gap: 12px;
  row-gap: 2px;
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid rgba(240, 210, 150, 0.14);
  background: rgba(255, 240, 210, 0.02);
  font-family: var(--serif);
  font-style: italic;
  font-size: 17px;
  line-height: 1.3;
  color: #f6efe2;
  text-decoration: none;
  transition: border-color 0.25s ease, background 0.25s ease;
}
.today:hover { border-color: rgba(240, 205, 138, 0.5); background: rgba(240, 205, 138, 0.06); }
.today:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 2px; }
.today-moon { grid-row: span 2; font-family: 'Segoe UI Symbol', 'Noto Sans Symbols', sans-serif; font-style: normal; font-size: 22px; color: #d6e2f4; filter: drop-shadow(0 0 6px rgba(180, 210, 255, 0.6)); }
.today-more { font-family: var(--sans); font-style: normal; font-size: 12px; letter-spacing: 0.04em; color: #f0cd8a; }
.edit, .inline {
  color: #f0cd8a;
  text-decoration: underline;
  text-decoration-color: rgba(240, 205, 138, 0.35);
  text-underline-offset: 3px;
  transition: text-decoration-color 0.25s ease;
}
.edit { font-size: 12.5px; }
.edit:hover, .inline:hover { text-decoration-color: currentColor; }
.edit:focus-visible, .inline:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 2px; border-radius: 4px; }
.hint { margin: -6px 0 0; font-size: 12.5px; line-height: 1.5; color: rgba(233, 194, 124, 0.75); }

.guide { margin: 0; font-size: 14px; line-height: 1.5; color: rgba(226, 220, 210, 0.7); }

/* The one thing to do when the sky is still empty: an outlined gold pill, the main CTA is the form's. */
.add-birth {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 11px 20px;
  border-radius: 999px;
  border: 1px solid rgba(240, 205, 138, 0.5);
  background: rgba(240, 205, 138, 0.06);
  font-size: 14.5px;
  color: #f3dcae;
  text-decoration: none;
  transition: background 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease;
}
.add-birth svg { width: 10px; height: 10px; fill: #f0cd8a; filter: drop-shadow(0 0 5px rgba(255, 200, 110, 0.8)); }
.add-birth:hover { background: rgba(240, 205, 138, 0.12); border-color: rgba(240, 205, 138, 0.8); box-shadow: 0 6px 26px rgba(230, 170, 80, 0.2); }
.add-birth:focus-visible { outline: 2px solid #ffe2a8; outline-offset: 3px; }

.quiet {
  justify-self: start;
  padding: 6px 4px;
  border: 0;
  background: none;
  font: inherit;
  font-size: 13.5px;
  color: rgba(226, 220, 210, 0.72);
  cursor: pointer;
  transition: color 0.25s ease;
}
.quiet:hover { color: #f0cd8a; }
.quiet:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 2px; border-radius: 6px; }

@media (max-width: 760px) {
  .quiet, .add-birth { min-height: 44px; }
  /* A finger-sized target without making the rows taller. */
  .edit { padding-block: 12px; margin-block: -6px; }
}
</style>
