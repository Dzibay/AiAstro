<script setup>
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import SiteFrame from '../components/SiteFrame.vue'
import PlaceInput from '../components/ui/PlaceInput.vue'
import PairSpheres from '../components/sky/PairSpheres.vue'
import { POINTS, SIGN_BY_ID } from '../components/cabinet/astro.js'
import { SPHERES, SPHERE_TONES } from '../components/sky/forecastWords.js'
import { useSession } from '../composables/useSession.js'
import { siteApi } from '../api/site.js'
import { errorText } from '../api/http.js'
import { useHead } from '../utils/useHead.js'
import { track } from '../utils/track.js'
import { LANDINGS, LANDING_BY_NAME, plain } from '../landing/pages.js'
import SIGN_READINGS from '../landing/signs.json'

/**
 * A landing page for search and ads: one calculation on the live sky, its taste right here
 * (backend app/landing.py), then the way to the whole of it through registration, which picks up
 * what was typed. The words come from landing/pages.js, the same ones the prerender writes.
 *
 * Goals for admin → «Аналитика → Посадочные»: `<page>:calc` when the taste is shown,
 * `<page>:cta` when the person goes on to the account.
 */

const route = useRoute()
const router = useRouter()
const { webToken } = useSession()

const page = computed(() => LANDING_BY_NAME[route.name] || LANDINGS[0])
const others = computed(() => LANDINGS.filter((other) => other.name !== page.value.name))
const signs = computed(() => (page.value.signs ? SIGN_READINGS[page.value.signs] : []))

/* ---- The form: one birth, or two for the pair ---- */

function blank() {
  return { date: '', time: '', noTime: false, city: '', place: null }
}
const mine = reactive(blank())
const theirs = reactive({ ...blank(), name: '' })

const latest = new Date().toISOString().slice(0, 10)
const dateOk = (birth) => /^\d{4}-\d{2}-\d{2}$/.test(birth.date) && birth.date >= '1900-01-01' && birth.date <= latest
const timeOf = (birth) => (!birth.noTime && /^\d{2}:\d{2}$/.test(birth.time) ? birth.time : null)

/** What the preview takes: the coordinates only when a city was picked from the suggestions. */
function body(birth) {
  const out = { date: birth.date, time: timeOf(birth) }
  if (birth.place && birth.place.label === birth.city) Object.assign(out, { lat: birth.place.lat, lon: birth.place.lon })
  return out
}

const pending = ref(false)
const message = ref('')
const result = ref(null)
const resultNode = ref(null)

async function calculate() {
  message.value = ''
  if (!dateOk(mine) || (page.value.form === 'pair' && !dateOk(theirs))) {
    message.value = page.value.form === 'pair' ? 'Укажите обе даты рождения' : 'Укажите дату рождения'
    return
  }
  pending.value = true
  try {
    const kind = page.value.form
    if (kind === 'pair') result.value = await siteApi.previewPair({ mine: body(mine), theirs: body(theirs) })
    else if (kind === 'forecast') result.value = await siteApi.previewForecast(body(mine))
    else result.value = await siteApi.previewNatal({ ...body(mine), focus: page.value.focus || '' })
    track('goal', `${page.value.name}:calc`)
    await nextTick()
    resultNode.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  } catch (error) {
    message.value = errorText(error)
  } finally {
    pending.value = false
  }
}

/* ---- On to the account, with everything typed carried over ---- */

const NEXT = { natal: '/cabinet/chart', forecast: '/cabinet/forecast', pair: '/cabinet/pair?add' }

function carried(birth) {
  const found = birth.place && birth.place.label === birth.city ? birth.place : null
  return { date: birth.date, time: timeOf(birth) || '', noTime: !timeOf(birth), city: birth.city.trim(), place: found }
}

function goOn() {
  track('goal', `${page.value.name}:cta`)
  try {
    // LoginView reads the person's own birth for its second step; PairPanel reads the partner.
    if (!webToken.value) sessionStorage.setItem('astra-birth', JSON.stringify(carried(mine)))
    if (page.value.form === 'pair') {
      const partner = carried(theirs)
      sessionStorage.setItem('astra-partner', JSON.stringify({
        name: theirs.name.trim(),
        birth: { date: partner.date, time: partner.time || null, place: partner.city || null, ...(partner.place ? { lat: partner.place.lat, lon: partner.place.lon, tz: partner.place.tz } : {}) },
      }))
    }
  } catch {
    /* private mode: the forms start empty */
  }
  const next = page.value.focus && page.value.focus !== 'sun' ? `${NEXT.natal}/${page.value.focus}` : NEXT[page.value.form]
  if (webToken.value) router.push(next)
  else router.push({ path: '/login', query: { mode: 'register', next } })
}

/* ---- The taste, in words ---- */

const glyph = (id) => POINTS[id]?.glyph || ''
const signOf = (id) => SIGN_BY_ID[id] || null
const focusSign = computed(() => {
  if (!result.value?.points || !page.value.signs) return ''
  return result.value.points.find((point) => point.id === page.value.focus)?.sign || ''
})

const PAIR_TONES = { easy: 'Пара лёгкая', tense: 'Пара с искрой', mixed: 'Пара многогранная', calm: 'Пара спокойная' }
const DAY_TONES = { easy: 'Лёгкий день', tense: 'День бережности', calm: 'Ровный день', mixed: 'Многогранный день' }
const daySpheres = computed(() => SPHERES.map((sphere) => ({ ...sphere, tone: result.value?.spheres?.[sphere.id] || 'calm' })))
const more = computed(() => Math.max(0, (result.value?.total || 0) - 1))
const dayOf = (iso) => new Date(`${iso}T12:00:00`).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' })

/* ---- The page itself ---- */

const openFaq = ref(-1)

watch(page, (next) => {
  result.value = null
  message.value = ''
  openFaq.value = -1
  useHead({ title: next.title, description: next.description })
}, { immediate: true })
</script>

<template>
  <SiteFrame>
    <div class="landing">
      <nav class="wrap crumbs" aria-label="Навигация">
        <RouterLink to="/">Главная</RouterLink>
        <span aria-hidden="true">·</span>
        <span aria-current="page">{{ page.crumb }}</span>
      </nav>

      <section class="wrap hero">
        <div class="hero-copy">
          <p class="kicker">{{ page.kicker }}</p>
          <!-- The headings come from landing/pages.js; <em> is their only markup. -->
          <h1 v-html="page.h1" />
          <p class="lead">{{ page.lead }}</p>
          <p class="promise">
            <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg>
            Без регистрации, прямо на этой странице
          </p>
        </div>

        <!-- The form is the one thing here you can touch, so it alone is glass. -->
        <form class="calc" novalidate @submit.prevent="calculate">
          <fieldset v-for="(birth, index) in page.form === 'pair' ? [mine, theirs] : [mine]" :key="index" class="who">
            <legend v-if="page.form === 'pair'" class="who-title">{{ index === 0 ? 'Вы' : 'Партнёр' }}</legend>
            <label v-if="index === 1" class="field">
              <span class="field-label">Имя</span>
              <input v-model="theirs.name" type="text" maxlength="60" placeholder="Как его или её зовут" autocomplete="off" />
            </label>
            <div class="form-row">
              <label class="field">
                <span class="field-label">Дата рождения</span>
                <input v-model="birth.date" type="date" min="1900-01-01" :max="latest" required />
              </label>
              <div class="field">
                <span class="field-head">
                  <label class="field-label" :for="`lp-time-${index}`">Время</label>
                  <label class="check">
                    <input v-model="birth.noTime" type="checkbox" />
                    <span class="check-box" aria-hidden="true" />
                    <span>не знаю</span>
                  </label>
                </span>
                <input :id="`lp-time-${index}`" v-model="birth.time" type="time" :disabled="birth.noTime" />
              </div>
            </div>
            <div class="field">
              <label class="field-label" :for="`lp-city-${index}`">Город рождения</label>
              <PlaceInput :id="`lp-city-${index}`" v-model="birth.city" v-model:place="birth.place" />
            </div>
          </fieldset>
          <p v-if="message" class="calc-message" role="alert">{{ message }}</p>
          <button class="gold-cta calc-cta" type="submit" :disabled="pending" data-track="landing:calc">
            {{ pending ? 'Читаем небо…' : page.form === 'pair' ? 'Рассчитать совместимость' : page.form === 'forecast' ? 'Показать мой день' : 'Рассчитать' }}
          </button>
          <p class="calc-note">Город уточняет дома и Асцендент. Без времени карта верна в главном.</p>
        </form>
      </section>

      <!-- ---- The taste ---- -->
      <section v-if="result" ref="resultNode" class="wrap result" aria-live="polite">
        <template v-if="page.form === 'natal'">
          <h2 class="result-title">Ваше небо</h2>
          <p v-if="!result.time_known || !result.place_known" class="result-note">
            {{ !result.time_known ? 'Без времени рождения нет Асцендента и домов, а Луна приблизительна.' : 'Без города нет Асцендента и домов.' }}
          </p>
          <ol class="points">
            <li v-for="(point, index) in result.points" :key="point.id" class="point" :class="{ 'is-focus': index === 0 }">
              <span class="point-glyph" aria-hidden="true">{{ glyph(point.id) }}</span>
              <div class="point-copy">
                <h3>{{ point.title }}<span v-if="point.approx" class="approx"> · приблизительно</span></h3>
                <p class="essence">{{ point.essence }}</p>
                <template v-if="index === 0">
                  <p v-for="part in point.parts.slice(1)" :key="part.label" class="part"><b>{{ part.label }}.</b> {{ part.text }}</p>
                </template>
              </div>
            </li>
          </ol>
        </template>

        <template v-else-if="page.form === 'pair'">
          <h2 class="result-title">{{ PAIR_TONES[result.tone] || 'Ваша пара' }}</h2>
          <p class="essence big">{{ result.phrase }}</p>
          <PairSpheres :spheres="result.spheres" />
          <ul class="aspects">
            <li v-for="aspect in result.key" :key="aspect.title" :class="aspect.lean < 0 ? 'is-tense' : 'is-easy'">{{ aspect.title }}</li>
          </ul>
          <p class="essence">{{ result.reading.essence }}</p>
          <template v-for="part in result.reading.parts" :key="part.label">
            <p class="part"><b>{{ part.label }}.</b> {{ part.text }}</p>
            <p v-if="part.todo" class="part todo"><b>✦ Что делать:</b> {{ part.todo }}</p>
          </template>
        </template>

        <template v-else>
          <h2 class="result-title">{{ DAY_TONES[result.tone] || 'Ваш день' }} · {{ dayOf(result.start) }}</h2>
          <dl class="day-spheres">
            <div v-for="sphere in daySpheres" :key="sphere.id" :class="`is-${sphere.tone}`">
              <dt>{{ sphere.name }}</dt>
              <dd>{{ SPHERE_TONES[sphere.tone] }}</dd>
            </div>
          </dl>
          <ul class="aspects">
            <li v-for="transit in result.transits" :key="transit.phrase" :class="transit.lean < 0 ? 'is-tense' : 'is-easy'">{{ transit.phrase }}</li>
          </ul>
          <p class="essence">{{ result.reading.essence }}</p>
          <template v-for="part in result.reading.parts" :key="part.label">
            <p class="part"><b>{{ part.label }}.</b> {{ part.text }}</p>
            <p v-if="part.todo" class="part todo"><b>✦ Что делать:</b> {{ part.todo }}</p>
          </template>
        </template>

        <div class="result-next">
          <p v-if="page.form === 'natal'">В кабинете — колесо карты, все планеты в знаках и домах, аспекты и стихии.</p>
          <p v-else-if="more">Ещё {{ more }} {{ more === 1 ? 'глава' : more < 5 ? 'главы' : 'глав' }} — в полном разборе.</p>
          <button class="gold-cta" type="button" data-track="landing:cta" @click="goOn">{{ page.cta }}</button>
        </div>
      </section>

      <!-- ---- The words around it ---- -->
      <article class="wrap copy">
        <section v-for="section in page.sections" :key="section.h2" class="copy-block">
          <h2>{{ section.h2 }}</h2>
          <p v-for="(text, index) in section.text" :key="index">{{ text }}</p>
        </section>

        <section v-if="signs.length" class="copy-block signs">
          <h2>{{ page.signsTitle }}</h2>
          <div class="sign-list">
            <section v-for="sign in signs" :id="sign.sign" :key="sign.sign" class="sign" :class="{ 'is-mine': sign.sign === focusSign }">
              <h3>
                <span class="sign-glyph" aria-hidden="true">{{ signOf(sign.sign)?.glyph }}</span>
                {{ sign.title }}
                <span v-if="sign.sign === focusSign" class="mine">ваш</span>
              </h3>
              <p class="essence">{{ sign.essence }}</p>
              <p>{{ sign.text }}</p>
            </section>
          </div>
        </section>

        <section class="copy-block">
          <h2>Вопросы</h2>
          <div class="faq">
            <div v-for="(item, index) in page.faq" :key="item.q" class="faq-item" :class="{ 'is-open': openFaq === index }">
              <button class="faq-q" type="button" :aria-expanded="openFaq === index" @click="openFaq = openFaq === index ? -1 : index">
                <span class="faq-text">{{ item.q }}</span>
                <span class="faq-sign" aria-hidden="true" />
              </button>
              <div class="faq-a"><p>{{ item.a }}</p></div>
            </div>
          </div>
        </section>

        <nav class="copy-block others" aria-label="Другие расчёты">
          <h2>Другие расчёты</h2>
          <ul>
            <li v-for="other in others" :key="other.name">
              <RouterLink :to="`/${other.slug}`">
                <b>{{ other.crumb }}</b>
                <span>{{ plain(other.lead).split('.')[0] }}.</span>
              </RouterLink>
            </li>
          </ul>
        </nav>
      </article>
    </div>
  </SiteFrame>
</template>

<style scoped>
.landing { position: relative; z-index: 1; padding: 104px 0 80px; }

/* The text lies on the sky; a soft night behind the left column keeps it legible over the stars. */
.landing::before {
  content: '';
  position: fixed;
  inset: 0;
  z-index: -1;
  pointer-events: none;
  background: linear-gradient(90deg, rgba(4, 6, 12, 0.7), rgba(4, 6, 12, 0.35) 55%, transparent 80%);
}

.crumbs { display: flex; gap: 10px; font-size: 12.5px; letter-spacing: 0.06em; color: rgba(226, 214, 192, 0.55); }
.crumbs a { color: inherit; text-decoration: none; }
.crumbs a:hover { color: #f0cd8a; }

.hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 440px);
  align-items: start;
  gap: 56px;
  margin-top: 34px;
}
.hero-copy { padding-top: 18px; }
.kicker { margin: 0 0 16px; font-size: 11px; letter-spacing: 0.28em; text-transform: uppercase; color: rgba(240, 205, 138, 0.82); }
h1 {
  margin: 0;
  font-family: var(--serif);
  font-size: clamp(38px, 4.6vw, 62px);
  font-weight: 500;
  line-height: 1.04;
  color: #f6efe2;
  text-wrap: balance;
}
h1 :deep(em) { font-style: italic; color: #f0cd8a; }
.lead { max-width: 34em; margin: 22px 0 0; font-size: 17px; line-height: 1.6; color: rgba(232, 226, 216, 0.82); }
.promise { display: flex; align-items: center; gap: 9px; margin: 22px 0 0; font-size: 12.5px; letter-spacing: 0.06em; color: rgba(226, 214, 192, 0.62); }
.promise svg, .calc-note svg { width: 9px; height: 9px; fill: #f0cd8a; }

/* ---- The form, as on the home page ---- */
.calc {
  display: grid;
  gap: 14px;
  padding: 20px 20px 16px;
  border-radius: 20px;
  border: 1px solid rgba(240, 210, 150, 0.2);
  background: linear-gradient(160deg, rgba(26, 23, 26, 0.6), rgba(8, 10, 18, 0.72));
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.38), inset 0 1px 0 rgba(255, 240, 210, 0.07);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}
.who { display: grid; gap: 12px; min-width: 0; margin: 0; padding: 0; border: 0; }
.who + .who { padding-top: 14px; border-top: 1px solid rgba(240, 210, 150, 0.12); }
.who-title { padding: 0; margin-bottom: 2px; font-family: var(--serif); font-size: 19px; color: #f6efe2; }
.form-row { display: grid; grid-template-columns: 1.3fr 1fr; gap: 12px; }
.field { display: grid; gap: 7px; min-width: 0; }
.field-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.field-label { line-height: 16px; font-size: 10.5px; letter-spacing: 0.24em; text-transform: uppercase; color: rgba(226, 214, 192, 0.66); }
.field > input {
  min-width: 0;
  height: 44px;
  padding: 0 14px;
  border-radius: 12px;
  border: 1px solid rgba(240, 210, 150, 0.18);
  background: rgba(255, 240, 210, 0.04);
  color: #f6efe2;
  font: inherit;
  font-size: 15px;
  color-scheme: dark;
  outline: none;
  transition: border-color 0.25s ease, background 0.25s ease, box-shadow 0.25s ease;
}
.field > input::placeholder { color: rgba(226, 220, 210, 0.38); }
.field > input:hover:not(:disabled) { border-color: rgba(240, 210, 150, 0.32); }
.field > input:focus { border-color: rgba(240, 205, 138, 0.7); background: rgba(255, 240, 210, 0.06); box-shadow: 0 0 0 3px rgba(240, 205, 138, 0.12); }
.field > input:disabled { opacity: 0.4; cursor: not-allowed; }
.field > input::-webkit-calendar-picker-indicator { opacity: 0.6; cursor: pointer; }

.check { position: relative; display: inline-flex; align-items: center; gap: 10px; font-size: 12px; line-height: 16px; color: rgba(226, 220, 210, 0.7); cursor: pointer; }
.check input { position: absolute; opacity: 0; pointer-events: none; }
.check-box { position: relative; width: 13px; height: 13px; border-radius: 4px; border: 1px solid rgba(240, 210, 150, 0.4); transition: background 0.2s ease, border-color 0.2s ease; }
.check-box::after {
  content: '';
  position: absolute;
  left: 4px;
  top: 1.5px;
  width: 3px;
  height: 6px;
  border: solid #2b1d0b;
  border-width: 0 1.5px 1.5px 0;
  transform: rotate(45deg) scale(0);
  transition: transform 0.2s ease;
}
.check input:checked + .check-box { background: #e9c47e; border-color: #e9c47e; }
.check input:checked + .check-box::after { transform: rotate(45deg) scale(1); }
.check input:focus-visible + .check-box { box-shadow: 0 0 0 3px rgba(240, 205, 138, 0.25); }

.gold-cta {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 14px 34px;
  border: 0;
  border-radius: 999px;
  font: inherit;
  font-weight: 600;
  color: #2b1d0b;
  background: linear-gradient(180deg, #f4dba6 0%, #e3bd78 55%, #cf9f55 100%);
  box-shadow: inset 0 1px 0 rgba(255, 248, 228, 0.8), 0 8px 30px rgba(230, 170, 80, 0.32);
  cursor: pointer;
  transition: box-shadow 0.3s ease, filter 0.3s ease;
}
.gold-cta:hover { filter: brightness(1.05); box-shadow: inset 0 1px 0 rgba(255, 248, 228, 0.8), 0 10px 38px rgba(230, 170, 80, 0.48); }
.gold-cta:disabled { opacity: 0.7; cursor: progress; }
.calc-cta { width: 100%; padding-block: 13px; }
.calc-message { margin: 0; font-size: 13.5px; color: #f2b6a0; }
.calc-note { margin: 0; text-align: center; font-size: 11.5px; line-height: 1.5; color: rgba(226, 214, 192, 0.56); }

/* ---- The taste: text on the sky, the button the one thing to press ---- */
.result { max-width: 760px; margin-top: 72px; margin-left: max(20px, calc((100% - var(--max)) / 2)); scroll-margin-top: 96px; }
.result-title, .copy h2 { margin: 0 0 14px; font-family: var(--serif); font-size: clamp(28px, 3vw, 38px); font-weight: 500; line-height: 1.12; color: #f6efe2; }
.result-note { margin: 0 0 18px; font-size: 13.5px; color: rgba(226, 214, 192, 0.66); }
.points { display: grid; gap: 4px; margin: 0; padding: 0; list-style: none; }
.point { display: grid; grid-template-columns: 34px 1fr; gap: 14px; padding: 14px 0; border-top: 1px solid rgba(240, 210, 150, 0.12); }
.point-glyph { font-family: 'Segoe UI Symbol', 'Noto Sans Symbols', var(--serif); font-size: 22px; line-height: 1.2; color: #f0cd8a; text-align: center; }
.point.is-focus .point-glyph { text-shadow: 0 0 14px rgba(255, 210, 130, 0.8); }
.point h3, .sign h3 { margin: 0; font-family: var(--serif); font-size: 22px; font-weight: 500; line-height: 1.2; color: #f6efe2; }
.approx { font-family: var(--sans, inherit); font-size: 12px; color: rgba(226, 214, 192, 0.55); }
.essence { margin: 6px 0 0; font-family: var(--serif); font-size: 18px; font-style: italic; line-height: 1.4; color: #f0cd8a; }
.essence.big { margin: 0 0 18px; font-size: 21px; }
.part { margin: 10px 0 0; font-size: 15px; line-height: 1.65; color: rgba(232, 226, 216, 0.82); }
.part b { font-weight: 600; color: #f2ebdf; }
.part.todo { font-family: var(--serif); font-style: italic; font-size: 16.5px; color: #f6e2b4; }
.part.todo b { font-style: normal; color: #f0cd8a; }

.aspects { display: grid; gap: 8px; margin: 20px 0 6px; padding: 0; list-style: none; }
.aspects li { position: relative; padding-left: 20px; font-size: 15px; line-height: 1.45; color: #f2ebdf; }
.aspects li::before { content: ''; position: absolute; left: 2px; top: 0.55em; width: 7px; height: 7px; border-radius: 50%; }
.aspects .is-easy::before { background: #f0cd8a; box-shadow: 0 0 8px rgba(255, 210, 130, 0.8); }
.aspects .is-tense::before { background: #d98f7a; }

.day-spheres { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 6px 0 4px; }
.day-spheres div { padding: 10px 0; border-top: 1px solid rgba(240, 210, 150, 0.14); }
.day-spheres dt { font-size: 10.5px; letter-spacing: 0.2em; text-transform: uppercase; color: rgba(226, 214, 192, 0.6); }
.day-spheres dd { margin: 6px 0 0; font-family: var(--serif); font-size: 19px; color: #f6efe2; }
.day-spheres .is-easy dd { color: #f0cd8a; }
.day-spheres .is-tense dd { color: #e7a995; }

.result-next { display: flex; flex-wrap: wrap; align-items: center; gap: 16px 24px; margin-top: 26px; padding-top: 22px; border-top: 1px solid rgba(240, 210, 150, 0.16); }
.result-next p { flex: 1 1 260px; margin: 0; font-size: 14.5px; line-height: 1.55; color: rgba(232, 226, 216, 0.76); }

/* ---- The words around it ---- */
.copy { display: grid; gap: 64px; margin-top: 96px; }
.copy-block { max-width: 760px; }
.copy-block > p { margin: 0 0 14px; font-size: 16px; line-height: 1.7; color: rgba(232, 226, 216, 0.8); }

.sign-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px 40px; }
.signs { max-width: none; }
.sign { padding: 18px 0; border-top: 1px solid rgba(240, 210, 150, 0.12); scroll-margin-top: 96px; }
.sign p:not(.essence) { margin: 10px 0 0; font-size: 15px; line-height: 1.65; color: rgba(232, 226, 216, 0.78); }
.sign-glyph { margin-right: 6px; font-family: 'Segoe UI Symbol', 'Noto Sans Symbols', var(--serif); color: #f0cd8a; }
.sign.is-mine h3 { color: #ffe2a8; }
.mine { margin-left: 8px; padding: 2px 8px; border-radius: 999px; border: 1px solid rgba(240, 205, 138, 0.5); font-family: inherit; font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase; vertical-align: middle; color: #f0cd8a; }

.faq { border-top: 1px solid rgba(240, 210, 150, 0.14); }
.faq-item { border-bottom: 1px solid rgba(240, 210, 150, 0.14); }
.faq-q { display: flex; width: 100%; align-items: center; gap: 14px; padding: 14px 0; border: 0; background: none; color: #f2ebdf; font: inherit; font-size: 15.5px; line-height: 1.35; text-align: left; cursor: pointer; }
.faq-q:hover, .faq-item.is-open .faq-q { color: #ffe2a8; }
.faq-q:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 2px; border-radius: 6px; }
.faq-text { flex: 1; }
.faq-sign { position: relative; flex: none; width: 12px; height: 12px; }
.faq-sign::before, .faq-sign::after { content: ''; position: absolute; top: 50%; left: 0; width: 12px; height: 1px; background: currentColor; transition: transform 0.3s ease; }
.faq-sign::after { transform: rotate(90deg); }
.faq-item.is-open .faq-sign::after { transform: rotate(0deg); }
.faq-a { display: grid; grid-template-rows: 0fr; opacity: 0; transition: grid-template-rows 0.4s ease, opacity 0.4s ease; }
.faq-item.is-open .faq-a { grid-template-rows: 1fr; opacity: 1; }
.faq-a p { overflow: hidden; min-height: 0; margin: 0; font-size: 14.5px; line-height: 1.6; color: rgba(226, 220, 210, 0.76); }
.faq-item.is-open .faq-a p { padding-bottom: 16px; }

.others { max-width: none; }
.others ul { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; margin: 0; padding: 0; list-style: none; }
.others a {
  display: grid;
  gap: 6px;
  height: 100%;
  padding: 16px 18px;
  border-radius: 16px;
  border: 1px solid rgba(240, 210, 150, 0.16);
  background: rgba(12, 12, 20, 0.5);
  text-decoration: none;
  transition: border-color 0.3s ease, background 0.3s ease;
}
.others a:hover { border-color: rgba(240, 205, 138, 0.5); background: rgba(24, 20, 22, 0.6); }
.others b { font-family: var(--serif); font-size: 20px; font-weight: 500; color: #f6efe2; }
.others span { font-size: 13.5px; line-height: 1.5; color: rgba(226, 220, 210, 0.66); }

@media (max-width: 900px) {
  .hero { grid-template-columns: 1fr; gap: 28px; }
  .hero-copy { padding-top: 0; }
  .landing::before { background: rgba(4, 6, 12, 0.55); }
  .sign-list { grid-template-columns: 1fr; }
}
@media (max-width: 560px) {
  .landing { padding-top: 88px; }
  .lead { font-size: 16px; }
  .calc { padding: 18px 16px 14px; }
  .form-row { grid-template-columns: 1fr 1fr; gap: 10px; }
  .day-spheres { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .copy { gap: 48px; margin-top: 72px; }
  .result { margin-top: 56px; }
}
</style>
