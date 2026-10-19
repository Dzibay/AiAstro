<script setup>
import { computed, watch } from 'vue'
import { RouterLink } from 'vue-router'
import PanelHead from '../../components/cabinet/PanelHead.vue'
import StarPassport from '../../components/sky/StarPassport.vue'
import NewcomerPath from '../../components/sky/NewcomerPath.vue'
import { useSky } from '../../composables/useSky.js'
import { useForecast } from '../../composables/useForecast.js'
import { ROMAN } from '../../components/cabinet/astro.js'
import { SIGNS } from '../../utils/skyToday.js'
import { skyEnding, skyLine } from '../../utils/skyTerm.js'

/**
 * The overview: a greeting, the star passport, the first steps, a line about «Небосвод» and the
 * way out. The sections themselves are on the sky.
 */

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

/* ---- «Небосвод» ---- */

/** One line about the subscription; its own section on the sky says the rest. */
const skyState = computed(() => (props.user.sky ? `Небосвод ${skyLine(props.user)}` : 'Небосвод пока не зажжён — горит одна ваша карта'))
const skyMore = computed(() => {
  if (!props.user.sky) return 'Что он зажжёт'
  return skyEnding(props.user) ? 'Продлить' : 'Что входит'
})

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
    <StarPassport v-else :user="user" />
    <p v-if="unplaced" class="hint">
      Город записан словом, без координат.
      <RouterLink class="inline" :to="{ name: 'cabinet-birth' }">Выберите его из подсказок</RouterLink>,
      чтобы карта посчитала дома.
    </p>

    <RouterLink v-if="moonLine" class="today" :to="{ name: 'cabinet-forecast' }">
      <span class="today-moon" aria-hidden="true">☽︎</span>
      <span>{{ moonLine }}</span>
      <span class="today-more">Прогноз дня</span>
    </RouterLink>

    <NewcomerPath :user="user" />

    <RouterLink class="today sky-line" :class="{ 'is-lit': user.sky, 'is-ending': user.sky && skyMore === 'Продлить' }" :to="{ name: 'cabinet-sky' }">
      <svg class="sky-crown" viewBox="0 0 20 20" aria-hidden="true"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg>
      <span>{{ skyState }}</span>
      <span class="today-more">{{ skyMore }}</span>
    </RouterLink>

    <div class="leave">
      <RouterLink class="settings" :to="{ name: 'cabinet-profile' }">
        <svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="5.5" r="2.6" /><path d="M2.8 13.5c.7-2.6 2.8-4 5.2-4s4.5 1.4 5.2 4" /></svg>
        Профиль и настройки
      </RouterLink>
      <button type="button" class="logout" @click="emit('logout')">
        <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M6 2.5H3.5v11H6M10 4.5L13.5 8L10 11.5M13.5 8H6.5" /></svg>
        Выйти
      </button>
    </div>
  </div>
</template>

<style scoped>
.overview { display: grid; gap: 16px; }
.overview > * { min-width: 0; }

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
.inline {
  color: #f0cd8a;
  text-decoration: underline;
  text-decoration-color: rgba(240, 205, 138, 0.35);
  text-underline-offset: 3px;
  transition: text-decoration-color 0.25s ease;
}
.inline:hover { text-decoration-color: currentColor; }
.inline:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 2px; border-radius: 4px; }
.hint { margin: -8px 0 0; font-size: 12.5px; line-height: 1.5; color: rgba(233, 194, 124, 0.75); }

/* «Небосвод» in one line, the same as the day's: gold once it burns. */
.sky-crown { grid-row: span 2; width: 18px; height: 18px; fill: rgba(214, 222, 238, 0.45); transition: fill 0.4s ease; }
.sky-line.is-lit .sky-crown { fill: #f0cd8a; filter: drop-shadow(0 0 6px rgba(255, 205, 120, 0.8)); }
.sky-line:not(.is-lit) { font-size: 16px; color: rgba(239, 231, 216, 0.8); }
.sky-line.is-ending { border-color: rgba(240, 205, 138, 0.45); }

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

/* The profile and the way out: rare, so they close the page, quieter than everything above. */
.leave { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 10px; padding-top: 14px; border-top: 1px solid rgba(240, 210, 150, 0.12); }
.settings {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13.5px;
  color: #efe7d8;
  text-decoration: none;
  transition: color 0.25s ease;
}
.settings svg { width: 15px; height: 15px; fill: none; stroke: currentColor; stroke-width: 1.3; stroke-linecap: round; }
.settings:hover { color: #f0cd8a; }
.settings:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 3px; border-radius: 4px; }
.logout {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px 8px 13px;
  border: 1px solid rgba(240, 210, 150, 0.26);
  border-radius: 999px;
  background: rgba(255, 240, 210, 0.04);
  font: inherit;
  font-size: 13.5px;
  color: #efe7d8;
  cursor: pointer;
  transition: border-color 0.25s ease, color 0.25s ease, background 0.25s ease;
}
.logout svg { width: 14px; height: 14px; fill: none; stroke: currentColor; stroke-width: 1.4; stroke-linecap: round; stroke-linejoin: round; }
.logout:hover { border-color: rgba(240, 205, 138, 0.6); background: rgba(255, 240, 210, 0.08); color: #f0cd8a; }
.logout:focus-visible { outline: 2px solid #f0cd8a; outline-offset: 3px; }

@media (max-width: 760px) {
  .logout, .add-birth, .settings { min-height: 44px; }
}
</style>
