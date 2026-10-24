<script setup>
import { computed, onMounted } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import BrandMark from './BrandMark.vue'
import { fallbackConfig, useSiteConfig } from '../composables/useSiteConfig.js'
import { skyOn } from '../utils/skyToday.js'
import { LANDINGS } from '../landing/pages.js'

const { config, load } = useSiteConfig()
const route = useRoute()

// On the home page the footer lies on the planet's horizon; elsewhere it is just the columns.
const onSky = computed(() => route.name === 'home')

// The support's contacts from the admin; the column is shown once there is at least one.
const telegram = computed(() => config.value?.support_telegram || '')
const mail = computed(() => config.value?.support_email || '')

const sections = [
  { label: 'Как это работает', to: { path: '/', hash: '#how' } },
  { label: 'Натальная карта', to: { path: '/', hash: '#services' } },
  { label: 'Прогнозы', to: { path: '/', hash: '#forecasts' } },
  { label: 'Вопросы', to: { path: '/', hash: '#about' } },
  { label: 'Кабинет', to: '/cabinet' },
]
// The landing pages: every page of the site links to them, so search finds them from anywhere.
const calculations = LANDINGS.map((page) => ({ label: page.crumb, to: `/${page.slug}` }))
const documents = [
  { label: 'Конфиденциальность', to: '/legal/privacy' },
  { label: 'Оферта', to: '/legal/offer' },
  { label: 'Согласие', to: '/legal/consent' },
  { label: 'Cookie', to: '/legal/cookies' },
]

const now = new Date()
const year = now.getFullYear()
const sky = skyOn(now)
const today = `Сегодня, ${now.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' })}`

// The lit part of the Moon: a half disc on the lit side closed by the terminator, an ellipse.
const MOON_R = 9
const moonPath = computed(() => {
  const r = MOON_R
  const rx = Math.abs(Math.cos((sky.elongation * Math.PI) / 180)) * r
  const gibbous = sky.lit > 50
  const rim = sky.waxing ? 1 : 0
  const terminator = sky.waxing === gibbous ? 1 : 0
  return `M12 ${12 - r}A${r} ${r} 0 0 ${rim} 12 ${12 + r}A${rx.toFixed(2)} ${r} 0 0 ${terminator} 12 ${12 - r}Z`
})

onMounted(() => {
  load()
})
</script>

<template>
  <footer class="footer" :class="{ 'is-sky': onSky }">
    <svg v-if="onSky" class="horizon" viewBox="0 0 1440 120" preserveAspectRatio="none" aria-hidden="true">
      <defs>
        <linearGradient id="horizon-line" x1="0" x2="1">
          <stop offset="0" stop-color="#f0cd8a" stop-opacity="0" />
          <stop offset="0.5" stop-color="#ffe2a8" stop-opacity="0.75" />
          <stop offset="1" stop-color="#f0cd8a" stop-opacity="0" />
        </linearGradient>
      </defs>
      <path d="M0 118Q720 -40 1440 118" fill="none" stroke="url(#horizon-line)" stroke-width="1" vector-effect="non-scaling-stroke" />
    </svg>

    <div class="wrap">
      <div v-if="onSky" class="sky-today">
        <span class="sky-kicker">Небо сегодня</span>
        <p class="sky-line">
          <svg class="moon" viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="12" cy="12" :r="MOON_R" class="moon-dark" />
            <path :d="moonPath" class="moon-lit" />
          </svg>
          <span>{{ today }}</span>
          <span class="sky-dot" aria-hidden="true">·</span>
          <span>Солнце {{ sky.sun.in }}</span>
          <span class="sky-dot" aria-hidden="true">·</span>
          <span>Луна {{ sky.moon.in }}, {{ sky.phase }}, {{ sky.lit }}%</span>
        </p>
      </div>

      <div class="cols" :class="{ 'is-short': !telegram && !mail }">
        <div class="col-brand">
          <RouterLink to="/" class="footer-brand" aria-label="На главную">
            <BrandMark class="footer-mark" />
            <span>{{ config?.site_name || fallbackConfig.site_name }}</span>
          </RouterLink>
          <p>{{ config?.tagline || fallbackConfig.tagline }}</p>
        </div>

        <nav class="col" aria-label="Разделы">
          <p class="col-title">Разделы</p>
          <RouterLink v-for="link in sections" :key="link.label" :to="link.to">{{ link.label }}</RouterLink>
        </nav>

        <nav class="col" aria-label="Расчёты">
          <p class="col-title">Расчёты</p>
          <RouterLink v-for="link in calculations" :key="link.to" :to="link.to">{{ link.label }}</RouterLink>
        </nav>

        <div v-if="telegram || mail" class="col">
          <p class="col-title">Связь</p>
          <a v-if="telegram" :href="`https://t.me/${telegram}`" target="_blank" rel="noopener">Telegram @{{ telegram }}</a>
          <a v-if="mail" :href="`mailto:${mail}`">{{ mail }}</a>
        </div>

        <nav class="col" aria-label="Документы">
          <p class="col-title">Документы</p>
          <RouterLink v-for="link in documents" :key="link.label" :to="link.to">{{ link.label }}</RouterLink>
        </nav>
      </div>

      <div class="bottom">
        <p>© {{ year }} {{ config?.site_name || fallbackConfig.site_name }}</p>
        <div class="disclaimers">
          <p>
            Информация на сайте не является публичной офертой. Настоящий интернет-сайт носит исключительно
            информационный и рекламный характер. Вся информация, размещённая на нём (включая каталоги товаров,
            цены, описания и условия оплаты), не является публичной офертой в смысле статьи 437 Гражданского
            кодекса РФ.
          </p>
          <p>
            Все материалы, расчеты и прогнозы сервиса «{{ config?.site_name || fallbackConfig.site_name }}» носят
            исключительно информационно-развлекательный характер. Они не являются медицинской, психологической,
            юридической, финансовой или иной профессиональной консультацией и не заменяют ее. Ответы
            генерируются алгоритмически и могут содержать неточности. Пользователь самостоятельно несет полную
            ответственность за любые решения, принятые на основе полученной информации. Администрация сервиса
            не несет ответственности за последствия таких решений.
          </p>
        </div>
      </div>
    </div>
  </footer>
</template>

<style scoped>
.footer {
  position: relative;
  border-top: 1px solid var(--line);
  color: rgba(226, 220, 210, 0.66);
  font-size: 14px;
}
.footer p { margin: 0; }

/* Home: no flat band — the night thickens towards the bottom, over the planet. */
.footer.is-sky {
  z-index: 1;
  padding-top: 72px;
  border-top: 0;
  background: linear-gradient(180deg, transparent, rgba(4, 6, 12, 0.72) 90px, rgba(4, 6, 12, 0.94) 260px, #04060c);
}
.horizon { position: absolute; top: 0; left: 0; width: 100%; height: 120px; pointer-events: none; }

.sky-today { display: grid; justify-items: center; gap: 10px; margin-bottom: 52px; text-align: center; }
.sky-kicker {
  font-size: 10.5px;
  letter-spacing: 0.32em;
  text-transform: uppercase;
  color: rgba(240, 205, 138, 0.7);
}
.sky-line {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 4px 10px;
  font-family: var(--serif);
  font-size: 19px;
  color: #f2ebdf;
}
.sky-dot { color: rgba(240, 205, 138, 0.6); }
.moon { width: 22px; height: 22px; margin-right: 2px; filter: drop-shadow(0 0 6px rgba(255, 236, 200, 0.45)); }
.moon-dark { fill: rgba(255, 240, 210, 0.08); stroke: rgba(255, 240, 210, 0.25); stroke-width: 0.6; }
.moon-lit { fill: #f6ead2; }

.cols {
  display: grid;
  grid-template-columns: 1.4fr 1fr 1fr 1fr 1fr;
  gap: 32px;
  padding: 28px 0 32px;
}
/* No contacts yet: four columns, not a gap where «Связь» would stand. */
.cols.is-short { grid-template-columns: 1.4fr 1fr 1fr 1fr; }
.is-sky .cols { border-top: 1px solid rgba(240, 210, 150, 0.12); }
.col { display: grid; align-content: start; gap: 9px; }
.col-title {
  margin-bottom: 4px !important;
  font-size: 10.5px;
  letter-spacing: 0.24em;
  text-transform: uppercase;
  color: rgba(240, 205, 138, 0.75);
}
.col a, .footer-brand { color: rgba(236, 228, 214, 0.8); text-decoration: none; transition: color 0.25s ease; }
.col a:hover, .footer-brand:hover { color: #ffe2a8; }
.col a:focus-visible, .footer-brand:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 3px; border-radius: 4px; }

.col-brand { display: grid; align-content: start; gap: 10px; }
.footer-brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  justify-self: start;
  font-family: var(--serif);
  font-size: 22px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: #f2ebdf;
}
.footer-mark { width: 34px; height: 34px; }
.col-brand p { max-width: 220px; line-height: 1.5; }

.bottom {
  display: flex;
  justify-content: space-between;
  gap: 28px;
  padding: 16px 0 22px;
  border-top: 1px solid rgba(240, 210, 150, 0.1);
  font-size: 12.5px;
  color: rgba(226, 220, 210, 0.5);
}
.bottom > p:first-child { flex: 0 0 auto; }
.disclaimers {
  display: grid;
  gap: 10px;
  max-width: 720px;
  text-align: right;
  line-height: 1.55;
  font-size: 11.5px;
  color: rgba(226, 220, 210, 0.42);
}

@media (max-width: 760px) {
  .footer.is-sky { padding-top: 56px; }
  .sky-today { margin-bottom: 36px; }
  .sky-line { flex-direction: column; gap: 4px; font-size: 17px; }
  .sky-dot { display: none; }
  .moon { margin: 0 0 4px; }
  .cols, .cols.is-short { grid-template-columns: 1fr 1fr; gap: 26px 20px; }
  .col-brand { grid-column: 1 / -1; }
  .bottom { flex-direction: column; gap: 12px; }
  .disclaimers { max-width: none; text-align: left; }
}
</style>
