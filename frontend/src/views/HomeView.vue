<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import SiteFrame from '../components/SiteFrame.vue'
import HeroOrbit from '../components/HeroOrbit.vue'
import { useSession } from '../composables/useSession.js'
import { fallbackConfig, useSiteConfig } from '../composables/useSiteConfig.js'
import { useHead } from '../utils/useHead.js'

// Placeholder copy: the design and the interactive parts of each section come next.
const steps = [
  { glyph: '☉', title: 'Дата, время и место', text: 'Чем точнее время рождения, тем точнее дома и асцендент.' },
  { glyph: '☽', title: 'Карта неба', text: 'Положения Солнца, Луны и планет на момент рождения.' },
  { glyph: '✦', title: 'Разбор', text: 'Что эти положения значат в работе, отношениях и быту.' },
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

const { config, load } = useSiteConfig()
const name = computed(() => config.value?.site_name || fallbackConfig.site_name)
const tagline = computed(() => config.value?.tagline || fallbackConfig.tagline)

onMounted(async () => {
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
        <div class="sky-panel">
          <p class="stop-kicker">Как это работает</p>
          <h2>Три шага до вашей карты</h2>
          <ol class="steps">
            <li v-for="(step, index) in steps" :key="step.title">
              <span class="step-mark" aria-hidden="true">{{ step.glyph }}</span>
              <span>
                <strong>{{ index + 1 }}. {{ step.title }}</strong>
                <span>{{ step.text }}</span>
              </span>
            </li>
          </ol>
          <p class="placeholder">Здесь будет форма: дата и место, и Солнце с Луной встанут на свои места.</p>
        </div>
      </div>
    </section>

    <section id="services" class="stop stop-services" data-sky-stop="services">
      <div class="wrap stop-grid">
        <div class="sky-panel">
          <p class="stop-kicker">Что в разборе</p>
          <h2>Карта о том, как вы живёте</h2>
          <div class="tiles">
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
        <div class="sky-panel">
          <p class="stop-kicker">Прогнозы и тарифы</p>
          <h2>Что ждёт в ближайшие месяцы</h2>
          <p class="placeholder">Здесь будет ползунок месяцев: Солнце и Луна поедут по орбите.</p>
          <div class="tiles tiles-plans">
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
        <div class="sky-panel">
          <p class="stop-kicker">Отзывы и вопросы</p>
          <h2>Частые вопросы</h2>
          <p class="placeholder">Здесь будут отзывы: звёзды на небе, которые раскрываются по наведению.</p>
          <div class="faq">
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
      <div class="start-copy">
        <p class="stop-kicker">Круг замкнулся</p>
        <h2>Солнце снова в Овне</h2>
        <p>Год прошёл за один скролл. Посмотрим, где стояли планеты в день вашего рождения?</p>
        <RouterLink class="start-cta" :to="chartTo">Построить карту</RouterLink>
      </div>
    </section>
  </SiteFrame>
</template>

<style scoped>
/* Every stop fills the screen so the sky can rest on it. Only the panels catch the pointer;
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
}
.stop-grid { display: flex; }
.stop-how .stop-grid, .stop-forecasts .stop-grid { justify-content: flex-start; }
.stop-services .stop-grid, .stop-about .stop-grid { justify-content: flex-end; }
/* Their signs sit at the top of the screen, so the panels keep to the lower part. */
.stop-forecasts, .stop-about { align-items: flex-end; }

.sky-panel {
  width: min(520px, 100%);
  padding: 28px 30px 30px;
  border-radius: 22px;
  border: 1px solid rgba(240, 210, 150, 0.18);
  background: linear-gradient(160deg, rgba(22, 20, 22, 0.62), rgba(8, 10, 18, 0.72));
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 240, 210, 0.06);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  pointer-events: auto;
}

.stop-kicker {
  margin: 0 0 10px;
  font-size: 11px;
  letter-spacing: 0.32em;
  text-transform: uppercase;
  color: rgba(233, 194, 124, 0.8);
}
.stop h2 {
  margin: 0 0 20px;
  font-family: var(--serif);
  font-weight: 500;
  font-size: clamp(30px, 3.4vw, 42px);
  line-height: 1.05;
  color: #f6efe2;
}

.steps { display: grid; gap: 14px; margin: 0; padding: 0; list-style: none; }
.steps li { display: flex; gap: 14px; align-items: flex-start; }
.steps li > span:last-child { display: grid; gap: 3px; }
.steps strong { font-weight: 500; color: #f2ebdf; }
.steps li > span:last-child > span { font-size: 14px; line-height: 1.5; color: rgba(226, 220, 210, 0.7); }
.step-mark {
  display: grid;
  place-items: center;
  flex: none;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: 1px solid rgba(240, 210, 150, 0.4);
  color: #ffd998;
  font-family: 'Segoe UI Symbol', 'Noto Sans Symbols', sans-serif;
}

.tiles { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.tiles-plans { grid-template-columns: repeat(3, 1fr); }
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
  margin: 0 0 18px;
  padding: 10px 14px;
  border: 1px dashed rgba(240, 210, 150, 0.25);
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.5;
  color: rgba(226, 214, 192, 0.6);
}
.steps + .placeholder { margin: 20px 0 0; }

.faq { display: grid; gap: 8px; }
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
.start-copy {
  width: min(560px, calc(100% - 32px));
  text-align: center;
  pointer-events: auto;
}
.start-copy p:not(.stop-kicker) { margin: 0 0 26px; font-size: 15.5px; line-height: 1.55; color: rgba(226, 220, 210, 0.78); }
.start-cta {
  display: inline-flex;
  padding: 14px 36px;
  border-radius: 999px;
  text-decoration: none;
  font-weight: 600;
  color: #2b1d0b;
  background: linear-gradient(180deg, #f4dba6 0%, #e3bd78 55%, #cf9f55 100%);
  box-shadow: inset 0 1px 0 rgba(255, 248, 228, 0.8), 0 8px 30px rgba(230, 170, 80, 0.32);
}

@media (max-width: 760px) {
  /* The pair of signs takes the top of the screen and the planet waits in the corner. */
  .stop { align-items: flex-end; padding: 34svh 0 120px; }
  .stop-grid { justify-content: stretch !important; }
  .sky-panel { padding: 22px 20px 24px; }
  .tiles, .tiles-plans { grid-template-columns: 1fr; }
  .stop-start { align-items: flex-start; padding-top: 110px; }
}
</style>
