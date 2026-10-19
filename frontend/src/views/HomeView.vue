<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import SiteFrame from '../components/SiteFrame.vue'
import HeroOrbit from '../components/HeroOrbit.vue'
import StopHead from '../components/home/StopHead.vue'
import { useSession } from '../composables/useSession.js'
import { fallbackConfig, useSiteConfig } from '../composables/useSiteConfig.js'
import { useHead } from '../utils/useHead.js'

const steps = [
  { num: 'I', title: 'Дата, время и место', text: 'Чем точнее минута рождения, тем точнее дома и асцендент.' },
  { num: 'II', title: 'Карта неба', text: 'Солнце, Луна и планеты встают туда, где стояли в ваш первый вдох.' },
  { num: 'III', title: 'Разбор', text: 'Что эти положения значат для характера, работы и любви.' },
]

const spheres = [
  { title: 'Характер', text: 'Сильные стороны, привычные реакции и то, что даётся труднее.' },
  { title: 'Работа и деньги', text: 'В каком ритме и в какой среде вам проще расти.' },
  { title: 'Отношения', text: 'Чего вы ждёте от близких и где чаще возникают споры.' },
  { title: 'Дом и быт', text: 'Что помогает восстанавливаться и чувствовать опору.' },
]

const plans = [
  { title: 'Натальная карта', text: 'Полный разбор карты рождения.' },
  { title: 'Прогноз на период', text: 'Темы выбранных месяцев и важные даты.' },
  { title: 'Совместимость', text: 'Две карты рядом: где ритмы совпадают.' },
]

const faq = [
  {
    q: 'Что, если я не знаю точное время рождения?',
    a: 'Разбор всё равно получится, но без домов и асцендента. Это будет видно в тексте.',
  },
  {
    q: 'Чем разбор отличается от гороскопа по знаку?',
    a: 'Гороскоп смотрит только на Солнце. Разбор учитывает все планеты, дома и связи между ними.',
  },
  {
    q: 'Что уже работает?',
    a: 'Сейчас открыт кабинет: можно зарегистрироваться и войти. Расчёт карты ещё не подключён.',
  },
]

const { webToken } = useSession()
const chartTo = computed(() => (webToken.value ? '/cabinet' : '/login'))
const openFaq = ref(-1)

// The form only collects for now: the chart itself is built in the cabinet.
const router = useRouter()
const birth = reactive({ date: '', time: '', noTime: false, city: '' })
function buildChart() {
  router.push(chartTo.value)
}

// A stop's content shows once the page has mostly scrolled onto it, when the sky arrives too.
let arrival = null
function watchArrival() {
  const stops = document.querySelectorAll('.stop')
  if (!('IntersectionObserver' in window)) {
    stops.forEach((node) => node.classList.add('is-here'))
    return
  }
  arrival = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return
      entry.target.classList.add('is-here')
      arrival.unobserve(entry.target)
    })
  }, { threshold: 0.35 })
  stops.forEach((node) => arrival.observe(node))
}
onBeforeUnmount(() => arrival?.disconnect())

const { config, load } = useSiteConfig()
const name = computed(() => config.value?.site_name || fallbackConfig.site_name)
const tagline = computed(() => config.value?.tagline || fallbackConfig.tagline)

onMounted(async () => {
  watchArrival()
  await load()
  useHead({
    title: `${name.value} — ${tagline.value}`,
    description: tagline.value,
  })
})
</script>

<template>
  <SiteFrame>
    <HeroOrbit />

    <section id="how" class="stop stop-how" data-sky-stop="how">
      <div class="wrap stop-grid">
        <div class="stop-body body-how">
          <StopHead num="II" signs="♌ ♍" label="Как это работает">Небо в <em>минуту</em> вашего рождения</StopHead>
          <p class="stop-lead" data-reveal style="--r: 3">
            Звёзды не повторяют своего узора. Мы восстановим тот, что был над вами в первый вдох,
            и прочтём его простыми словами.
          </p>

          <ol class="steps">
            <li v-for="(step, index) in steps" :key="step.num" data-reveal :style="{ '--r': 4 + index }">
              <span class="step-star" aria-hidden="true">
                <svg viewBox="0 0 20 20"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg>
              </span>
              <span class="step-num">{{ step.num }}</span>
              <span class="step-copy">
                <strong>{{ step.title }}</strong>
                <span>{{ step.text }}</span>
              </span>
            </li>
          </ol>

          <form class="chart-form" data-reveal style="--r: 7" @submit.prevent="buildChart">
            <div class="form-row">
              <label class="field">
                <span class="field-label">Дата рождения</span>
                <input v-model="birth.date" type="date" min="1900-01-01" />
              </label>
              <div class="field">
                <span class="field-head">
                  <label class="field-label" for="birth-time">Время</label>
                  <label class="check">
                    <input v-model="birth.noTime" type="checkbox" />
                    <span class="check-box" aria-hidden="true" />
                    <span>не знаю</span>
                  </label>
                </span>
                <input id="birth-time" v-model="birth.time" type="time" :disabled="birth.noTime" />
              </div>
            </div>
            <label class="field">
              <span class="field-label">Город рождения</span>
              <input v-model="birth.city" type="text" placeholder="Например, Казань" autocomplete="off" />
            </label>
            <button class="gold-cta form-cta" type="submit">Построить карту — бесплатно</button>
            <p class="form-note">
              <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg>
              Натальная карта бесплатна навсегда
            </p>
          </form>
        </div>
      </div>
    </section>

    <section id="services" class="stop stop-services" data-sky-stop="services">
      <div class="wrap stop-grid">
        <div class="stop-body">
          <StopHead num="III" signs="♎ ♏" label="Натальная карта">Что расскажет <em>ваша</em> карта</StopHead>
          <div class="tiles" data-reveal style="--r: 3">
            <article v-for="sphere in spheres" :key="sphere.title" class="tile">
              <h3>{{ sphere.title }}</h3>
              <p>{{ sphere.text }}</p>
            </article>
          </div>
        </div>
      </div>
    </section>

    <section id="forecasts" class="stop stop-forecasts" data-sky-stop="forecasts">
      <div class="wrap stop-grid">
        <div class="stop-body">
          <StopHead num="IV" signs="♐ ♑" label="Прогнозы и тарифы">Небо меняется <em>каждый день</em></StopHead>
          <p class="placeholder" data-reveal style="--r: 3">Здесь будут прогноз дня и чат с ИИ-астрологом.</p>
          <div class="tiles tiles-plans" data-reveal style="--r: 4">
            <article v-for="plan in plans" :key="plan.title" class="tile">
              <h3>{{ plan.title }}</h3>
              <p>{{ plan.text }}</p>
              <p class="tile-price">Цена появится позже</p>
            </article>
          </div>
        </div>
      </div>
    </section>

    <section id="about" class="stop stop-about" data-sky-stop="about">
      <div class="wrap stop-grid">
        <div class="stop-body">
          <StopHead num="V" signs="♒ ♓" label="Вопросы">Вопросы, которые задают <em>звёздам</em></StopHead>
          <div class="faq" data-reveal style="--r: 3">
            <div v-for="(item, index) in faq" :key="item.q" class="faq-item" :class="{ 'is-open': openFaq === index }">
              <button
                type="button"
                class="faq-q"
                :aria-expanded="openFaq === index"
                @click="openFaq = openFaq === index ? -1 : index"
              >
                <span>{{ item.q }}</span>
                <span class="faq-sign" aria-hidden="true" />
              </button>
              <p v-show="openFaq === index" class="faq-a">{{ item.a }}</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section id="start" class="stop stop-start" data-sky-stop="start">
      <div class="stop-body start-copy">
        <StopHead num="VI" signs="♈" label="Круг замкнулся" align="center">Солнце снова <em>в Овне</em></StopHead>
        <p data-reveal style="--r: 3">
          Год прошёл за один вдох. Теперь — ваше небо: каким оно было в день, когда вы пришли в мир?
        </p>
        <RouterLink class="gold-cta" :to="chartTo" data-reveal style="--r: 4">Построить карту — бесплатно</RouterLink>
      </div>
    </section>
  </SiteFrame>
</template>

<style scoped>
/* Every stop fills the screen so the sky can rest on it. Only the copy catches the pointer;
   the rest of the section lets clicks through to the constellations behind. */
.stop {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  min-height: 100vh;
  min-height: 100svh;
  padding: 110px 0 72px;
  color: #f3ece0;
  pointer-events: none;
  /* The shade under the copy reaches past the screen edge on phones. */
  overflow-x: clip;
}
.stop-grid { display: flex; }
.stop-how .stop-grid, .stop-forecasts .stop-grid { justify-content: flex-start; }
.stop-services .stop-grid, .stop-about .stop-grid { justify-content: flex-end; }
/* Their signs sit at the top of the screen, so the copy keeps to the lower part. */
.stop-forecasts, .stop-about { align-items: flex-end; }

/* Copy lies on the sky itself. A soft, borderless shadow under it keeps it readable
   over bright stars and engravings without turning it into a card. */
.stop-body {
  position: relative;
  isolation: isolate;
  width: min(520px, 100%);
  pointer-events: auto;
}
.stop-body::before {
  content: '';
  position: absolute;
  inset: -70px -90px;
  z-index: -1;
  background: radial-gradient(closest-side, rgba(4, 6, 12, 0.62), rgba(4, 6, 12, 0.38) 62%, transparent);
  pointer-events: none;
}

/* Content rises in when the sky arrives at its stop, line after line. */
.stop :deep([data-reveal]) {
  opacity: 0;
  transform: translateY(12px);
  transition: opacity 0.9s ease, transform 0.9s cubic-bezier(0.2, 0.7, 0.2, 1);
  transition-delay: calc(var(--r, 0) * 90ms + 120ms);
}
.stop.is-here :deep([data-reveal]) { opacity: 1; transform: none; }

.stop-lead {
  margin: 14px 0 24px;
  max-width: 500px;
  font-size: 15.5px;
  line-height: 1.6;
  color: rgba(232, 224, 210, 0.82);
}

/* The three steps are a small constellation: stars on one thread, lit one after another. */
.steps {
  position: relative;
  display: grid;
  gap: 15px;
  margin: 0 0 26px;
  padding: 0;
  list-style: none;
}
.steps::before {
  content: '';
  position: absolute;
  top: 10px;
  bottom: 10px;
  left: 9.5px;
  width: 1px;
  background: linear-gradient(180deg, rgba(240, 205, 138, 0.7), rgba(240, 205, 138, 0.25));
  transform: scaleY(0);
  transform-origin: top;
  transition: transform 1.4s cubic-bezier(0.3, 0.6, 0.2, 1) 0.5s;
}
.stop.is-here .steps::before { transform: none; }
.steps li { display: grid; grid-template-columns: 20px 30px 1fr; align-items: baseline; column-gap: 12px; }
.step-star { position: relative; align-self: start; width: 20px; height: 20px; margin-top: 2px; }
.step-star svg {
  width: 20px;
  height: 20px;
  fill: #ffe4ad;
  opacity: 0.35;
  transform: scale(0.6);
  transition: opacity 0.6s ease, transform 0.6s ease, filter 0.6s ease;
}
.steps li:nth-child(1) .step-star svg { transition-delay: 0.6s; }
.steps li:nth-child(2) .step-star svg { transition-delay: 1.1s; }
.steps li:nth-child(3) .step-star svg { transition-delay: 1.6s; }
.stop.is-here .step-star svg {
  opacity: 1;
  transform: none;
  filter: drop-shadow(0 0 6px rgba(255, 200, 110, 0.9));
}
.step-num { font-family: var(--serif); font-size: 15px; letter-spacing: 0.12em; color: rgba(240, 205, 138, 0.85); }
.step-copy { display: grid; gap: 2px; }
.step-copy strong { font-family: var(--serif); font-size: 21px; font-weight: 500; line-height: 1.15; color: #f6efe2; }
.step-copy span { font-size: 14px; line-height: 1.5; color: rgba(226, 220, 210, 0.72); }

/* The form is the one thing here you can touch, so it alone is glass. */
.chart-form {
  display: grid;
  gap: 12px;
  padding: 18px 20px 14px;
  border-radius: 20px;
  border: 1px solid rgba(240, 210, 150, 0.2);
  background: linear-gradient(160deg, rgba(26, 23, 26, 0.55), rgba(8, 10, 18, 0.66));
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.38), inset 0 1px 0 rgba(255, 240, 210, 0.07);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}
.form-row { display: grid; grid-template-columns: 1.3fr 1fr; gap: 12px; }
.field { display: grid; gap: 7px; min-width: 0; transition: opacity 0.3s ease; }
.field-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.field-label { line-height: 16px; font-size: 10.5px; letter-spacing: 0.24em; text-transform: uppercase; color: rgba(226, 214, 192, 0.66); }
.field input {
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
.field input::placeholder { color: rgba(226, 220, 210, 0.38); }
.field input:hover:not(:disabled) { border-color: rgba(240, 210, 150, 0.32); }
.field input:focus {
  border-color: rgba(240, 205, 138, 0.7);
  background: rgba(255, 240, 210, 0.06);
  box-shadow: 0 0 0 3px rgba(240, 205, 138, 0.12);
}
.field input:disabled { opacity: 0.4; cursor: not-allowed; }
.field input::-webkit-calendar-picker-indicator { opacity: 0.6; cursor: pointer; }

.check {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  line-height: 16px;
  color: rgba(226, 220, 210, 0.7);
  cursor: pointer;
}
.check input { position: absolute; opacity: 0; pointer-events: none; }
.check-box {
  position: relative;
  width: 13px;
  height: 13px;
  border-radius: 4px;
  border: 1px solid rgba(240, 210, 150, 0.4);
  transition: background 0.2s ease, border-color 0.2s ease;
}
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
  text-decoration: none;
  font: inherit;
  font-weight: 600;
  color: #2b1d0b;
  background: linear-gradient(180deg, #f4dba6 0%, #e3bd78 55%, #cf9f55 100%);
  box-shadow: inset 0 1px 0 rgba(255, 248, 228, 0.8), 0 8px 30px rgba(230, 170, 80, 0.32);
  cursor: pointer;
  transition: box-shadow 0.3s ease, filter 0.3s ease;
}
.gold-cta:hover { filter: brightness(1.05); box-shadow: inset 0 1px 0 rgba(255, 248, 228, 0.8), 0 10px 38px rgba(230, 170, 80, 0.48); }
.form-cta { width: 100%; margin-top: 2px; padding-block: 13px; }
.form-note {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin: 0;
  font-size: 11.5px;
  letter-spacing: 0.06em;
  color: rgba(226, 214, 192, 0.6);
}
.form-note svg { width: 9px; height: 9px; fill: #f0cd8a; }

/* Placeholder blocks below wait for their own sections' turn. */
.tiles { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 26px; }
.tiles-plans { grid-template-columns: repeat(3, 1fr); margin-top: 0; }
.tile {
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid rgba(240, 210, 150, 0.14);
  background: rgba(255, 214, 150, 0.035);
}
.tile h3 { margin: 0 0 6px; font-size: 15px; font-weight: 500; color: #f3dcae; }
.tile p { margin: 0; font-size: 13px; line-height: 1.5; color: rgba(226, 220, 210, 0.7); }
.tile .tile-price { margin-top: 10px; font-size: 12px; color: rgba(233, 194, 124, 0.7); }

.placeholder {
  margin: 26px 0 18px;
  padding: 10px 14px;
  border: 1px dashed rgba(240, 210, 150, 0.25);
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.5;
  color: rgba(226, 214, 192, 0.6);
}

.faq { display: grid; gap: 8px; margin-top: 22px; }
.faq-item { border-bottom: 1px solid rgba(240, 210, 150, 0.14); }
.faq-q {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 0;
  border: 0;
  background: none;
  color: #f2ebdf;
  font: inherit;
  font-size: 15px;
  text-align: left;
  cursor: pointer;
}
.faq-q:hover { color: #ffe2a8; }
.faq-sign { position: relative; flex: none; width: 12px; height: 12px; }
.faq-sign::before, .faq-sign::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 0;
  width: 12px;
  height: 1px;
  background: currentColor;
  transition: transform 0.3s ease;
}
.faq-sign::after { transform: rotate(90deg); }
.faq-item.is-open .faq-sign::after { transform: rotate(0deg); }
.faq-a { margin: 0 0 12px; font-size: 14px; line-height: 1.55; color: rgba(226, 220, 210, 0.72); }

/* The finale mirrors the hero: copy above the planet, which is back at home. */
/* Same line as the hero copy: just inside the top of the orbit (see layout() in sky.js). */
.stop-start {
  align-items: flex-start;
  justify-content: center;
  padding-top: calc(max(13.7vh, 92px) + min(100vh / 8.89, 100vw / 15));
}
.start-copy { width: min(560px, calc(100% - 32px)); text-align: center; }
.start-copy p { margin: 16px 0 26px; font-size: 16px; line-height: 1.6; color: rgba(226, 220, 210, 0.8); }

@media (max-width: 760px) {
  /* The pair of signs takes the top of the screen and the planet waits in the corner. */
  .stop { align-items: flex-end; padding: 34svh 0 120px; }
  .stop-grid { justify-content: stretch !important; }
  .stop-body::before { inset: -50px -40px; }
  .stop-lead { margin-bottom: 26px; font-size: 15px; }
  .steps { gap: 18px; margin-bottom: 28px; }
  .step-copy strong { font-size: 20px; }
  .chart-form { padding: 18px 16px 16px; }
  .form-cta { padding-inline: 12px; }
  .form-row { gap: 10px; }
  .tiles, .tiles-plans { grid-template-columns: 1fr; }
  .stop-start { align-items: flex-start; padding-top: 110px; }
}

@media (prefers-reduced-motion: reduce) {
  .stop :deep([data-reveal]) { opacity: 1; transform: none; transition: none; }
  .steps::before, .step-star svg { transition: none; }
}
</style>
