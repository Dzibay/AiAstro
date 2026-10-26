<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import SiteFrame from '../components/SiteFrame.vue'
import HeroOrbit from '../components/HeroOrbit.vue'
import StopHead from '../components/home/StopHead.vue'
import PageSigns from '../components/home/PageSigns.vue'
import ChartSample from '../components/home/ChartSample.vue'
import StartForm from '../components/home/StartForm.vue'
import { useSession } from '../composables/useSession.js'
import { HOUSE_SECTORS, useSkyFocus } from '../composables/useSkyFocus.js'
import { useSkyJourney } from '../composables/useSkyJourney.js'
import { fallbackConfig, useSiteConfig } from '../composables/useSiteConfig.js'
import { useHead } from '../utils/useHead.js'
import { usePrices } from '../utils/prices.js'
import { skyOn } from '../utils/skyToday.js'
import { siteApi } from '../api/site.js'
import { POINTS } from '../components/cabinet/astro.js'
import { PHASES, eventLine } from '../components/sky/forecastWords.js'

// II. The way to your own chart, in the order the site asks: the address first, the birth after.
const steps = [
  { num: 'I', title: 'Почта', text: 'Ссылка для входа вместо пароля' },
  { num: 'II', title: 'Дата рождения', text: 'Время и город уточнят дома' },
  { num: 'III', title: 'Ваша карта', text: 'С разбором — сразу и навсегда' },
]

const spheres = [
  { title: 'Характер', text: 'Каким вас видят и каким вы себя знаете.' },
  { title: 'Деньги', text: 'Где ваша опора и как к вам приходит достаток.' },
  { title: 'Дом', text: 'Что даёт вам корни и силы.' },
  { title: 'Любовь', text: 'Как вы влюбляетесь и что зажигает вас.' },
  { title: 'Работа', text: 'В каком ритме вам расти.' },
  { title: 'Партнёрство', text: 'Кого вы выбираете и почему.' },
].map((sphere, index) => ({ ...sphere, house: HOUSE_SECTORS[index].label }))

// The spheres sit on an arc around the planet's orbit, lower left of the screen.
// Row k moves right as the circle bends: x(y) = sqrt(ARC_R² - (ARC_DY - y)²).
const ROW = 70
const ARC_R = 1000
const ARC_DY = 453
const arcX = (y) => Math.sqrt(ARC_R ** 2 - (ARC_DY - y) ** 2) - Math.sqrt(ARC_R ** 2 - ARC_DY ** 2)
const sphereShift = spheres.map((_, index) => Math.round(arcX(index * ROW)))
// The hairline through the stars: the same circle, a little past the first and last row.
const arcPath = (() => {
  const top = -34
  const bottom = (spheres.length - 1) * ROW + 44
  const x = (y) => (14 + arcX(y)).toFixed(1)
  return `M${x(top)} ${top + 14}A${ARC_R} ${ARC_R} 0 0 1 ${x(bottom)} ${bottom + 14}`
})()
const { skyHouse, turnSky } = useSkyFocus()
// The sky behind the page (SkyStage) follows the scroll from stop to stop.
useSkyJourney()

// IV. A sample forecast for the real sky of today: the Moon's sign sets the mood of the day.
const MOOD = {
  aries: 'День быстрых решений: начните то, что давно откладывали.',
  taurus: 'Хорошо всё, что делается неторопливо и своими руками.',
  gemini: 'Разговоры складываются легко — напишите тому, о ком думаете.',
  cancer: 'Тянет домой. Не спорьте с этим: день для своих.',
  leo: 'Хочется быть замеченными — покажите то, что сделали.',
  virgo: 'День для порядка: мелкие дела сегодня не сопротивляются.',
  libra: 'Ищите согласия, а не победы — сегодня оно ближе.',
  scorpio: 'Чувства глубже обычного. Не торопитесь с выводами.',
  sagittarius: 'Тянет вдаль: новый маршрут, книга или план на год.',
  capricorn: 'День длинных дел: сделанное сегодня простоит долго.',
  aquarius: 'Удаются необычные идеи и встречи со старыми друзьями.',
  pisces: 'Слушайте интуицию и позвольте себе отдохнуть.',
}
const WEEK_TURN = 0.6
const today = new Date()
const weekEnd = new Date(today.getTime() + 6 * 86400000)
const dayMonth = (date) => date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' })
const capital = (text) => text.charAt(0).toUpperCase() + text.slice(1)
const skyNow = skyOn(today)
const skyMidweek = skyOn(new Date(today.getTime() + 3 * 86400000))
const skyWeekEnd = skyOn(weekEnd)
const forecasts = {
  day: {
    title: capital(today.toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' })),
    sky: `Луна ${skyNow.moon.in} · ${skyNow.phase}, ${skyNow.lit}%`,
    text: MOOD[skyNow.moon.id],
  },
  week: {
    title: today.getMonth() === weekEnd.getMonth()
      ? `Неделя ${today.getDate()}–${dayMonth(weekEnd)}`
      : `Неделя ${dayMonth(today)} – ${dayMonth(weekEnd)}`,
    sky: `Луна пройдёт от ${skyNow.moon.of} до ${skyWeekEnd.moon.of}`,
    text: `Середина недели: ${MOOD[skyMidweek.moon.id].charAt(0).toLowerCase()}${MOOD[skyMidweek.moon.id].slice(1)}`,
  },
}
const span = ref('day')
// The real sky from the server: the phase, the nearest lunation, the retrograde planets and the week's events.
// Until it answers (or if it does not), the card keeps what the browser itself computed.
const liveSky = ref(null)
const shortWeekday = (iso) => new Date(`${iso}T12:00:00`).toLocaleDateString('ru-RU', { weekday: 'short' })
const lunationLine = (next) => {
  if (!next) return ''
  const name = next.kind === 'full' ? 'Полнолуние' : 'Новолуние'
  const when = dayMonth(new Date(`${next.date}T12:00:00`))
  if (next.in === 0) return `${name} сегодня`
  if (next.in === 1) return `${name} завтра, ${when}`
  return `${name} ${when}`
}
const forecast = computed(() => {
  const base = forecasts[span.value]
  const live = liveSky.value
  if (!live) return base
  if (span.value === 'day') {
    const lines = [lunationLine(live.next)]
    if (live.retro.length) lines.push(`Попятно: ${live.retro.map((id) => POINTS[id].name).join(', ')}`)
    return {
      ...base,
      sky: `Луна ${skyNow.moon.in} · ${PHASES[live.moon.phase].name.toLowerCase()}`,
      lines: lines.filter(Boolean),
    }
  }
  const lines = live.events.slice(0, 4).map((event) => `${shortWeekday(event.date)} — ${eventLine(event)}`)
  return { ...base, lines }
})
function showSpan(next) {
  span.value = next
  turnSky(next === 'week' ? WEEK_TURN : 0)
}

const prices = usePrices()
const plans = computed(() => [
  { title: 'Натальная карта', price: '0 ₽', term: 'навсегда', text: 'Планеты в знаках и домах с толкованием, аспекты и стихии' },
  { title: 'Совместимость', price: prices.synastry.value, term: 'разово', text: 'Две карты рядом: пять сфер жизни, сильные и спорные места' },
  {
    title: 'Небосвод',
    price: prices.skyMonthly.value,
    term: 'в месяц',
    text: 'Портрет карты целиком, полные прогнозы на день и неделю, звёздный календарь на месяц, ИИ-астролог каждый день и разбор пары дешевле',
    star: true,
  },
])

// V. Reviews stay hidden until there are real ones: invented voices on a live site mislead.
const SHOW_VOICES = false
const voices = []

const faq = [
  {
    glyph: '♈︎',
    q: 'Что, если я не знаю точное время рождения?',
    a: 'Карта всё равно получится: положения планет в знаках почти не зависят от часа. '
      + 'Без времени не будет домов и асцендента — мы честно отметим это в разборе.',
  },
  {
    glyph: '♉︎',
    q: 'Зачем почта и нужен ли пароль?',
    a: 'Почта — ваш ключ: на неё приходит ссылка для входа и шесть цифр кода, а пароль не нужен. '
      + 'Если удобнее входить с паролем, его можно задать в кабинете в любой момент.',
  },
  {
    glyph: '♊︎',
    q: 'Чем это отличается от гороскопа по знаку?',
    a: 'Гороскоп по знаку смотрит только на Солнце и одинаков для двенадцатой части людей. '
      + 'Натальная карта учитывает все планеты, дома и связи между ними — она только ваша.',
  },
  {
    glyph: '♋︎',
    q: 'Натальная карта правда бесплатна?',
    a: 'Да, навсегда: планеты в знаках и домах с толкованием, аспекты, стихии и кресты — бесплатно. '
      + 'Портрет карты целиком и смысл каждого аспекта, полные прогнозы и ИИ-астролог каждый день входят в «Небосвод», '
      + 'а разбор пары оплачивается отдельно.',
  },
  {
    glyph: '♌︎',
    q: 'Что умеет ИИ-астролог и чем он не является?',
    a: 'Это нейросеть, которая знает вашу карту и сегодняшнее небо и объясняет их простыми словами. '
      + 'Она не врач, не юрист и не финансовый советник, а решения остаются за вами.',
  },
  {
    glyph: '♍︎',
    q: '«Небосвод» продлевается сам?',
    a: 'Нет: вы оплачиваете месяц, три месяца или год — и всё. Автоматических списаний нет, '
      + 'а за несколько дней до конца мы напомним письмом.',
  },
  {
    glyph: '♎︎',
    q: 'Где хранятся мои данные?',
    a: 'Дата, время и место рождения нужны только для расчёта карты. '
      + 'Мы не продаём и не передаём их третьим лицам.',
  },
]

const principles = [
  'Считаем по положению планет, а не по одному знаку',
  'Не пугаем и не предсказываем судьбу',
  'Ваши данные — только ваши',
]

const { webToken } = useSession()
// The compatibility link opens the login page's address step; its place counts in the funnel.
const compatTo = computed(() => (webToken.value ? '/cabinet' : '/login?mode=register&from=compat'))
const openFaq = ref(-1)

// A stop's content shows once a fifth of it is on screen, when the sky arrives too.
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
  }, { threshold: 0.2 })
  stops.forEach((node) => arrival.observe(node))
}
onBeforeUnmount(() => {
  arrival?.disconnect()
  skyHouse.value = -1
  turnSky(0, 0)
})

const { config, load } = useSiteConfig()
const name = computed(() => config.value?.site_name || fallbackConfig.site_name)
const tagline = computed(() => config.value?.tagline || fallbackConfig.tagline)

onMounted(async () => {
  watchArrival()
  siteApi.sky().then((sky) => { liveSky.value = sky }).catch(() => {})
  await load()
  // «Астра — натальная карта…», as in index.html: after the dash the tagline goes on in lower case
  // (an acronym like «ИИ» keeps its capitals).
  const rest = /^\p{Lu}\p{Ll}/u.test(tagline.value) ? tagline.value[0].toLowerCase() + tagline.value.slice(1) : tagline.value
  useHead({
    title: `${name.value} — ${rest}`,
    description: tagline.value,
  })
})
</script>

<template>
  <SiteFrame>
    <HeroOrbit />

    <section id="how" class="stop stop-how" data-sky-stop="how">
      <PageSigns :signs="['cancer', 'leo']" />
      <div class="wrap stop-grid">
        <div class="stop-body body-how">
          <StopHead num="II" phone-signs="♋ ♌" signs="♌ ♍" label="Пример карты">Каждая планета — <em>о вас</em></StopHead>
          <p class="stop-lead" data-reveal style="--r: 3">
            Так выглядит натальная карта в Астре. Выберите планету — и прочтите её разбор.
          </p>

          <ChartSample data-reveal style="--r: 4" />

          <ol class="steps">
            <li v-for="(step, index) in steps" :key="step.num" data-reveal :style="{ '--r': 5 + index }">
              <span class="step-star" aria-hidden="true">
                <svg viewBox="0 0 20 20"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg>
              </span>
              <span class="step-copy">
                <strong><span class="step-num">{{ step.num }}</span>{{ step.title }}</strong>
                <span>{{ step.text }}</span>
              </span>
            </li>
          </ol>

          <div class="how-start" data-reveal style="--r: 8">
            <StartForm place="how" cta="Получить свою карту" />
          </div>
        </div>
      </div>
    </section>

    <section id="services" class="stop stop-services" data-sky-stop="services">
      <PageSigns :signs="['virgo', 'libra']" />
      <div class="wrap stop-grid">
        <div class="stop-body">
          <StopHead num="III" phone-signs="♍ ♎" signs="♎ ♏" label="Натальная карта">Что расскажет <em>ваша</em> карта</StopHead>

          <div class="spheres">
            <svg class="spheres-arc" aria-hidden="true"><path :d="arcPath" /></svg>
            <ul>
              <li
                v-for="(sphere, index) in spheres"
                :key="sphere.title"
                class="sphere"
                :class="{ 'is-lit': skyHouse === index }"
                data-reveal
                :style="{ '--r': 3 + index, '--shift': sphereShift[index] + 'px' }"
                @mouseenter="skyHouse = index"
                @mouseleave="skyHouse = -1"
              >
                <span class="sphere-star" aria-hidden="true">
                  <svg viewBox="0 0 20 20"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg>
                </span>
                <span class="sphere-copy">
                  <span class="sphere-title">
                    <strong>{{ sphere.title }}</strong>
                    <span class="sphere-house">{{ sphere.house }} дом</span>
                  </span>
                  <span class="sphere-text">{{ sphere.text }}</span>
                </span>
              </li>
            </ul>
          </div>

          <div class="compat" data-reveal style="--r: 9">
            <div class="compat-rule" aria-hidden="true">
              <span />
              <svg viewBox="0 0 20 20"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg>
              <span />
            </div>
            <div class="compat-row">
              <svg class="compat-orbits" viewBox="0 0 120 84" aria-hidden="true">
                <path class="compat-lens" d="M60 16.6A30 30 0 0 1 60 67.4A30 30 0 0 1 60 16.6Z" />
                <circle cx="44" cy="42" r="30" />
                <circle cx="76" cy="42" r="30" />
                <circle class="compat-sun" cx="23" cy="21" r="3.4" />
                <circle class="compat-moon" cx="104" cy="56" r="3" />
                <path class="compat-spark" d="M60 34Q60.6 41.4 68 42Q60.6 42.6 60 50Q59.4 42.6 52 42Q59.4 41.4 60 34Z" />
              </svg>
              <div class="compat-copy">
                <p class="compat-title">Совместимость</p>
                <p class="compat-text">Две карты рядом: где ваши ритмы совпадают, а где спорят.</p>
                <div class="compat-foot">
                  <span class="compat-price">{{ prices.synastry.value }}</span>
                  <RouterLink class="line-cta" :to="compatTo" data-track="home:sample">
                    Проверить совместимость
                    <span aria-hidden="true">→</span>
                  </RouterLink>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section id="forecasts" class="stop stop-forecasts" data-sky-stop="forecasts">
      <PageSigns :signs="['scorpio', 'sagittarius']" />
      <div class="wrap stop-grid">
        <div class="stop-body body-forecasts">
          <div class="forecasts-copy">
            <StopHead num="IV" phone-signs="♏ ♐" signs="♐ ♑" label="Прогнозы и тарифы">Небо меняется <em>каждый день</em></StopHead>
            <p class="stop-lead" data-reveal style="--r: 3">
              «Небосвод» каждый день сверяет ваше небо с нынешним и отвечает на вопросы,
              когда звёзды молчат.
            </p>

            <div class="plans" data-reveal style="--r: 4">
              <div v-for="plan in plans" :key="plan.title" class="plan" :class="{ 'is-star': plan.star }">
                <span v-if="plan.star" class="plan-badge">★ выбор звёзд</span>
                <p class="plan-title">{{ plan.title }}</p>
                <p class="plan-price">{{ plan.price }}<span>{{ plan.term }}</span></p>
                <p class="plan-text">{{ plan.text }}</p>
              </div>
            </div>
          </div>

          <div class="previews">
            <div class="sky-card" data-reveal style="--r: 5">
              <div class="card-top">
                <span class="card-kicker">Пример прогноза</span>
                <div class="span-toggle" role="group" aria-label="Период прогноза">
                  <span class="span-thumb" :class="{ 'is-week': span === 'week' }" aria-hidden="true" />
                  <button type="button" :aria-pressed="span === 'day'" data-track="home:span-day" @click="showSpan('day')">День</button>
                  <button type="button" :aria-pressed="span === 'week'" data-track="home:span-week" @click="showSpan('week')">Неделя</button>
                </div>
              </div>
              <Transition name="swap" mode="out-in">
                <div :key="span" class="forecast">
                  <p class="forecast-title">{{ forecast.title }}</p>
                  <p class="forecast-sky"><span aria-hidden="true">☽</span> {{ forecast.sky }}</p>
                  <p class="forecast-text">{{ forecast.text }}</p>
                  <ul v-if="forecast.lines?.length" class="forecast-lines">
                    <li v-for="line in forecast.lines" :key="line">{{ line }}</li>
                  </ul>
                </div>
              </Transition>
            </div>

            <div class="sky-card chat" data-reveal style="--r: 6">
              <div class="card-top">
                <span class="card-kicker">Чат с ИИ-астрологом</span>
                <span class="soon">2 вопроса бесплатно</span>
              </div>
              <p class="bubble from-you">Почему на этой неделе всё валится из рук?</p>
              <p class="bubble from-astra">
                Луна идёт по вашему шестому дому: дела просят точности, а не скорости.
                Закончите одно, прежде чем браться за следующее.
              </p>
              <div class="chat-input" aria-hidden="true">
                <span>Спросите о своём небе…</span>
                <span class="chat-send">↑</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section id="about" class="stop stop-about" data-sky-stop="about">
      <PageSigns :signs="['capricorn', 'aquarius']" />
      <div class="wrap stop-grid">
        <div class="stop-body body-about">
          <StopHead num="V" phone-signs="♑ ♒" signs="♒ ♓" label="Вопросы">Вопросы, которые задают <em>звёздам</em></StopHead>

          <!-- Reviews as bright stars, each opening its quote; waits for real reviews. -->
          <ul v-if="SHOW_VOICES && voices.length" class="voices" data-reveal style="--r: 3">
            <li v-for="voice in voices" :key="voice.name" class="voice" tabindex="0">
              <span class="voice-star" aria-hidden="true" />
              <span class="voice-quote">«{{ voice.text }}» <cite>{{ voice.name }}, {{ voice.sign }}</cite></span>
            </li>
          </ul>

          <div class="faq">
            <div
              v-for="(item, index) in faq"
              :key="item.q"
              class="faq-item"
              :class="{ 'is-open': openFaq === index }"
              data-reveal
              :style="{ '--r': 3 + index }"
            >
              <button
                :id="`faq-q-${index}`"
                type="button"
                class="faq-q"
                :aria-expanded="openFaq === index"
                :aria-controls="`faq-a-${index}`"
                :data-track="`home:faq-${index + 1}`"
                @click="openFaq = openFaq === index ? -1 : index"
              >
                <span class="faq-glyph" aria-hidden="true">{{ item.glyph }}</span>
                <span class="faq-text">{{ item.q }}</span>
                <span class="faq-sign" aria-hidden="true" />
              </button>
              <div
                :id="`faq-a-${index}`"
                class="faq-a"
                role="region"
                :aria-labelledby="`faq-q-${index}`"
                :inert="openFaq !== index"
              >
                <p>{{ item.a }}</p>
              </div>
            </div>
          </div>

          <ul class="principles" data-reveal style="--r: 9">
            <li v-for="line in principles" :key="line">
              <svg viewBox="0 0 12 12" aria-hidden="true"><path d="M6 0 7 5 12 6 7 7 6 12 5 7 0 6 5 5Z" /></svg>
              {{ line }}
            </li>
          </ul>
        </div>
      </div>
    </section>

    <section id="start" class="stop stop-start" data-sky-stop="start">
      <PageSigns :signs="['pisces', 'aries']" />
      <div class="stop-body start-copy">
        <StopHead num="VI" phone-signs="♓ ♈" signs="♈" label="Круг замкнулся" align="center">Солнце снова <em>в Овне</em></StopHead>
        <p data-reveal style="--r: 3">
          Год прошёл за один вдох. Укажите почту — и увидите небо, под которым родились.
        </p>
        <div data-reveal style="--r: 4">
          <StartForm place="final" />
        </div>
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

/* Content rises in when the sky arrives at its stop, line after line, quickly enough not to be waited for. */
.stop :deep([data-reveal]) {
  opacity: 0;
  transform: translateY(10px);
  transition: opacity 0.6s ease, transform 0.6s cubic-bezier(0.2, 0.7, 0.2, 1);
  transition-delay: calc(var(--r, 0) * 60ms + 40ms);
}
.stop.is-here :deep([data-reveal]) { opacity: 1; transform: none; }

.stop-lead {
  margin: 16px 0 24px;
  max-width: 520px;
  font-size: 17px;
  line-height: 1.55;
  color: rgba(238, 231, 219, 0.88);
}

/* II. The sample, the way to your own chart and the address: one column on the sky's dark side. */
.body-how { width: min(600px, 100%); }
.how-start :deep(.start) { margin: 0; }

/* The three steps are a small constellation: stars on one thread, lit one after another. */
.steps {
  position: relative;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin: 26px 0 22px;
  padding: 0;
  list-style: none;
}
.steps::before {
  content: '';
  position: absolute;
  top: 9.5px;
  left: 10px;
  right: 10px;
  height: 1px;
  background: linear-gradient(90deg, rgba(240, 205, 138, 0.7), rgba(240, 205, 138, 0.2));
  transform: scaleX(0);
  transform-origin: left;
  transition: transform 1.2s cubic-bezier(0.3, 0.6, 0.2, 1) 0.4s;
}
.stop.is-here .steps::before { transform: none; }
.steps li { display: grid; gap: 10px; }
.step-star { position: relative; width: 20px; height: 20px; }
.step-star svg {
  width: 20px;
  height: 20px;
  fill: #ffe4ad;
  opacity: 0.35;
  transform: scale(0.6);
  transition: opacity 0.6s ease, transform 0.6s ease, filter 0.6s ease;
}
.steps li:nth-child(1) .step-star svg { transition-delay: 0.4s; }
.steps li:nth-child(2) .step-star svg { transition-delay: 0.8s; }
.steps li:nth-child(3) .step-star svg { transition-delay: 1.2s; }
.stop.is-here .step-star svg {
  opacity: 1;
  transform: none;
  filter: drop-shadow(0 0 6px rgba(255, 200, 110, 0.9));
}
.step-num { margin-right: 8px; font-size: 13px; letter-spacing: 0.12em; color: rgba(240, 205, 138, 0.9); }
.step-copy { display: grid; gap: 3px; }
.step-copy strong { font-family: var(--serif); font-size: 21px; font-weight: 500; line-height: 1.15; color: #f6efe2; }
.step-copy > span { font-size: 14px; line-height: 1.45; color: rgba(232, 226, 214, 0.8); }

/* III. The spheres hang on an arc around the orbit: each row slides right as the circle bends. */
.spheres { position: relative; margin-top: 24px; }
.spheres-arc { position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; pointer-events: none; }
.spheres-arc path {
  fill: none;
  stroke: rgba(240, 205, 138, 0.38);
  stroke-width: 1;
  stroke-dasharray: 1200;
  stroke-dashoffset: 1200;
  transition: stroke-dashoffset 1.8s cubic-bezier(0.3, 0.6, 0.2, 1) 0.4s;
}
.stop.is-here .spheres-arc path { stroke-dashoffset: 0; }
.spheres ul { position: relative; margin: 0; padding: 0; list-style: none; }
.sphere {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  height: 70px;
  margin-left: var(--shift);
  cursor: default;
}
.sphere-star { display: grid; place-items: center; flex: none; width: 28px; height: 28px; }
.sphere-star svg {
  width: 14px;
  height: 14px;
  fill: #ffe4ad;
  filter: drop-shadow(0 0 4px rgba(255, 200, 110, 0.7));
  transition: transform 0.4s ease, filter 0.4s ease;
}
.sphere.is-lit .sphere-star svg { transform: scale(1.5) rotate(45deg); filter: drop-shadow(0 0 8px rgba(255, 200, 110, 1)); }
.sphere-copy { display: grid; gap: 2px; padding-top: 2px; }
.sphere-title { display: flex; align-items: baseline; gap: 10px; }
.sphere-title strong {
  font-family: var(--serif);
  font-size: 23px;
  font-weight: 500;
  line-height: 1.1;
  color: #f6efe2;
  transition: color 0.3s ease;
}
.sphere.is-lit .sphere-title strong { color: #ffe2a8; }
.sphere-house { font-size: 10.5px; letter-spacing: 0.22em; text-transform: uppercase; color: rgba(240, 205, 138, 0.8); }
.sphere-text { font-size: 15.5px; line-height: 1.45; color: rgba(236, 230, 218, 0.84); }

/* Compatibility: a separate, paid reading, set apart by an ornamental rule. */
.compat { margin-top: 8px; }
.compat-rule { display: flex; align-items: center; gap: 10px; margin-bottom: 18px; }
.compat-rule span { flex: 1; height: 1px; background: linear-gradient(90deg, transparent, rgba(240, 205, 138, 0.5)); }
.compat-rule span:last-child { background: linear-gradient(90deg, rgba(240, 205, 138, 0.5), transparent); }
.compat-rule svg { width: 10px; height: 10px; fill: #ffe4ad; filter: drop-shadow(0 0 4px rgba(255, 200, 110, 0.8)); }
.compat-row { display: flex; align-items: center; gap: 22px; }
.compat-orbits { flex: none; width: 120px; height: 84px; overflow: visible; }
.compat-orbits circle { fill: none; stroke: rgba(240, 205, 138, 0.55); stroke-width: 1; }
.compat-orbits .compat-lens { fill: rgba(255, 210, 126, 0.14); }
.compat-orbits .compat-sun { fill: #ffd27e; stroke: none; filter: drop-shadow(0 0 4px #ffb84d); }
.compat-orbits .compat-moon { fill: #cfdcf5; stroke: none; filter: drop-shadow(0 0 3px #9fb8e8); }
.compat-spark { fill: #ffe7b8; filter: drop-shadow(0 0 5px rgba(255, 200, 110, 0.9)); }
.compat-copy { display: grid; gap: 4px; }
.compat-title { margin: 0; font-family: var(--serif); font-size: 26px; line-height: 1.1; color: #f6efe2; }
.compat-text { margin: 0; font-size: 15.5px; line-height: 1.5; color: rgba(236, 230, 218, 0.84); }
.compat-foot { display: flex; align-items: center; flex-wrap: wrap; gap: 8px 18px; margin-top: 10px; }
.compat-price { font-family: var(--serif); font-size: 19px; color: #f0cd8a; white-space: nowrap; }

/* Secondary action: glass pill with a gold hairline. */
.line-cta {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 10px 20px;
  border-radius: 999px;
  border: 1px solid rgba(240, 205, 138, 0.45);
  background: rgba(20, 18, 22, 0.45);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  color: #f3dcae;
  font-size: 14.5px;
  text-decoration: none;
  transition: border-color 0.3s ease, background 0.3s ease, color 0.3s ease;
}
.line-cta span { transition: transform 0.3s ease; }
.line-cta:hover { border-color: rgba(255, 220, 160, 0.8); background: rgba(255, 210, 126, 0.08); color: #ffe7b8; }
.line-cta:hover span { transform: translateX(3px); }

/* IV. Two columns under the signs: copy and tariffs, then the two previews you can touch. */
.body-forecasts {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 372px;
  align-items: end;
  gap: 40px;
  width: min(880px, 100%);
}
.forecasts-copy .stop-lead { margin-bottom: 26px; }

/* Tariffs as columns of an old table: hairlines between them, a gold frame for the subscription. */
.plans { display: grid; grid-template-columns: repeat(3, 1fr); }
.plan { position: relative; padding: 16px 16px 14px; }
.plan + .plan { border-left: 1px solid rgba(240, 205, 138, 0.2); }
.plan.is-star {
  border: 1px solid rgba(240, 205, 138, 0.55);
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(255, 210, 126, 0.07), transparent 70%);
  box-shadow: 0 0 30px rgba(255, 200, 110, 0.08);
}
.plan.is-star + .plan, .plan + .plan.is-star { border-left-color: transparent; }
.plan-badge {
  position: absolute;
  top: -9px;
  left: 14px;
  padding: 0 8px;
  border-radius: 999px;
  background: #0b0c12;
  font-size: 10px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  line-height: 18px;
  color: #f0cd8a;
}
.plan p { margin: 0; }
.plan-title { font-size: 11px; letter-spacing: 0.2em; text-transform: uppercase; color: rgba(232, 220, 198, 0.8); }
.plan-price { display: grid; margin: 8px 0 10px !important; font-family: var(--serif); font-size: 30px; line-height: 1; color: #f6efe2; }
.plan.is-star .plan-price { color: #ffe2a8; }
.plan-price span { margin-top: 5px; font-family: var(--sans); font-size: 12.5px; letter-spacing: 0.04em; color: rgba(232, 220, 198, 0.72); }
.plan-text { font-size: 14px; line-height: 1.45; color: rgba(236, 230, 218, 0.82); }

.previews { display: grid; gap: 14px; }
.sky-card {
  padding: 16px 18px 18px;
  border-radius: 18px;
  border: 1px solid rgba(240, 210, 150, 0.2);
  background: linear-gradient(160deg, rgba(26, 23, 26, 0.55), rgba(8, 10, 18, 0.66));
  box-shadow: 0 24px 70px rgba(0, 0, 0, 0.36), inset 0 1px 0 rgba(255, 240, 210, 0.07);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}
.card-top { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
.card-kicker { font-size: 11px; letter-spacing: 0.24em; text-transform: uppercase; color: rgba(232, 220, 198, 0.74); }

.span-toggle {
  position: relative;
  display: grid;
  grid-template-columns: 1fr 1fr;
  padding: 3px;
  border-radius: 999px;
  border: 1px solid rgba(240, 210, 150, 0.22);
  background: rgba(255, 240, 210, 0.03);
}
.span-toggle button {
  position: relative;
  padding: 5px 14px;
  border: 0;
  background: none;
  font: inherit;
  font-size: 12.5px;
  color: rgba(226, 220, 210, 0.7);
  cursor: pointer;
  transition: color 0.3s ease;
}
.span-toggle button[aria-pressed='true'] { color: #2b1d0b; }
.span-toggle button:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 2px; border-radius: 999px; }
.span-thumb {
  position: absolute;
  top: 3px;
  bottom: 3px;
  left: 3px;
  width: calc(50% - 3px);
  border-radius: 999px;
  background: linear-gradient(180deg, #f4dba6, #dcb36c);
  transition: transform 0.45s cubic-bezier(0.3, 0.7, 0.2, 1);
}
.span-thumb.is-week { transform: translateX(100%); }

.forecast p { margin: 0; }
.forecast-title { font-family: var(--serif); font-size: 24px; line-height: 1.15; color: #f6efe2; }
.forecast-sky { margin-top: 4px !important; font-size: 13.5px; color: #f0cd8a; }
.forecast-text { margin-top: 10px !important; font-size: 15.5px; line-height: 1.5; color: rgba(238, 231, 219, 0.9); }
.forecast-lines {
  margin: 10px 0 0;
  padding: 10px 0 0;
  list-style: none;
  border-top: 1px solid rgba(240, 205, 138, 0.12);
  font-size: 13.5px;
  line-height: 1.55;
  color: rgba(232, 224, 210, 0.74);
}
.forecast-lines li::first-letter { text-transform: uppercase; }
.swap-enter-active, .swap-leave-active { transition: opacity 0.3s ease, transform 0.3s ease; }
.swap-enter-from { opacity: 0; transform: translateY(6px); }
.swap-leave-to { opacity: 0; transform: translateY(-6px); }

.soon {
  padding: 2px 9px;
  border-radius: 999px;
  border: 1px solid rgba(240, 205, 138, 0.4);
  font-size: 10.5px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #f0cd8a;
}
.bubble { max-width: 88%; margin: 0 0 8px; padding: 9px 13px; font-size: 14.5px; line-height: 1.45; }
.from-you {
  margin-left: auto;
  border-radius: 14px 14px 4px 14px;
  background: rgba(255, 240, 210, 0.08);
  color: #f2ebdf;
}
.from-astra {
  border-radius: 14px 14px 14px 4px;
  border: 1px solid rgba(240, 205, 138, 0.22);
  background: rgba(255, 210, 126, 0.06);
  color: rgba(240, 232, 218, 0.88);
}
.chat-input {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
  padding: 6px 6px 6px 14px;
  border-radius: 999px;
  border: 1px solid rgba(240, 210, 150, 0.16);
  font-size: 13px;
  color: rgba(226, 220, 210, 0.4);
}
.chat-send {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: rgba(240, 205, 138, 0.18);
  color: rgba(255, 226, 168, 0.6);
}

/* V. An accordion without panels: hairlines between rows, a small glyph on the left. */
.body-about { width: min(560px, 100%); }
.faq { margin-top: 18px; border-top: 1px solid rgba(240, 210, 150, 0.14); }
.faq-item { border-bottom: 1px solid rgba(240, 210, 150, 0.14); }
.faq-q {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 14px;
  padding: 14px 0;
  border: 0;
  background: none;
  color: #f2ebdf;
  font: inherit;
  font-size: 17px;
  line-height: 1.35;
  text-align: left;
  cursor: pointer;
  transition: color 0.3s ease;
}
.faq-q:hover, .faq-item.is-open .faq-q { color: #ffe2a8; }
.faq-q:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 2px; border-radius: 6px; }
.faq-glyph {
  flex: none;
  width: 18px;
  font-family: 'Segoe UI Symbol', 'Noto Sans Symbols', sans-serif;
  font-variant-emoji: text;
  font-size: 16px;
  text-align: center;
  color: rgba(240, 205, 138, 0.55);
  transition: color 0.3s ease, text-shadow 0.3s ease;
}
.faq-item.is-open .faq-glyph { color: #ffe2a8; text-shadow: 0 0 10px rgba(255, 210, 130, 0.7); }
.faq-text { flex: 1; }
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
.faq-a {
  display: grid;
  grid-template-rows: 0fr;
  opacity: 0;
  transition: grid-template-rows 0.4s ease, opacity 0.4s ease;
}
.faq-item.is-open .faq-a { grid-template-rows: 1fr; opacity: 1; }
.faq-a p {
  overflow: hidden;
  min-height: 0;
  margin: 0;
  padding-left: 32px;
  font-size: 15.5px;
  line-height: 1.55;
  color: rgba(236, 230, 218, 0.84);
}
.faq-item.is-open .faq-a p { padding-bottom: 14px; }

/* Principles stand in for reviews: three short lines, star-led. */
.principles {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 18px;
  margin: 22px 0 0;
  padding: 0;
  list-style: none;
}
.principles li { display: flex; gap: 8px; font-size: 13.5px; line-height: 1.45; color: rgba(236, 228, 212, 0.84); }
.principles svg { flex: none; width: 10px; height: 10px; margin-top: 4px; fill: #f0cd8a; }

.voices { display: flex; flex-wrap: wrap; gap: 18px; margin: 18px 0 0; padding: 0; list-style: none; }
.voice { position: relative; outline: none; }
.voice-star {
  display: block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #fff4dc;
  box-shadow: 0 0 10px 3px rgba(255, 220, 160, 0.6);
}
.voice-quote {
  position: absolute;
  bottom: 18px;
  left: -12px;
  width: 260px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(240, 210, 150, 0.2);
  background: rgba(8, 10, 18, 0.85);
  font-size: 13px;
  line-height: 1.45;
  color: #f2ebdf;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.3s ease;
}
.voice-quote cite { display: block; margin-top: 6px; font-style: normal; font-size: 12px; color: #f0cd8a; }
.voice:hover .voice-quote, .voice:focus-visible .voice-quote { opacity: 1; }

/* The finale mirrors the hero: copy above the planet, which is back at home. */
/* Same line as the hero copy: just inside the top of the orbit (see layout() in sky.js). */
.stop-start {
  align-items: flex-start;
  justify-content: center;
  padding-top: calc(max(13.7vh, 92px) + min(100vh / 8.89, 100vw / 15));
}
.start-copy { width: min(560px, calc(100% - 32px)); text-align: center; }
.start-copy p { margin: 16px auto 24px; max-width: 470px; font-size: 17px; line-height: 1.55; color: rgba(238, 231, 219, 0.88); }

@media (max-width: 760px) {
  /* The pair of signs takes the top of the screen and the planet waits in the corner. */
  .stop { align-items: flex-end; padding: 34svh 0 120px; }
  .stop-grid { justify-content: stretch !important; }
  .stop-body::before { inset: -50px -40px; }
  .stop-lead { margin-bottom: 22px; font-size: 16px; }
  .step-copy strong { font-size: 19px; }
  .faq-q { font-size: 16px; }
  /* Too narrow for the arc: the spheres line up in a plain column. */
  .spheres-arc { display: none; }
  .sphere { height: auto; min-height: 0; margin: 0 0 14px; gap: 10px; }
  .sphere-star { width: 18px; height: 24px; }
  .sphere-title strong { font-size: 21px; }
  .compat-row { gap: 14px; }
  .compat-orbits { width: 76px; height: 54px; }
  .compat-foot { gap: 10px 14px; }
  .line-cta { padding: 9px 16px; font-size: 13.5px; white-space: nowrap; }
  .body-forecasts { grid-template-columns: 1fr; gap: 26px; }
  .principles { grid-template-columns: 1fr; gap: 8px; }
  .plans { grid-template-columns: 1fr; gap: 6px; }
  .plan + .plan { border-left: 0; border-top: 1px solid rgba(240, 205, 138, 0.2); }
  .plan.is-star + .plan, .plan + .plan.is-star { border-top-color: transparent; }
  .plan.is-star { margin-top: 8px; }
  /* The phone home is calm: no planet comes back, so the finale reads under its Pisces and Aries. */
  .stop-start { align-items: flex-start; padding-top: max(34svh, 270px); }
}

/* Narrow phones: the three steps stand one under another, the thread runs down. */
@media (max-width: 560px) {
  .steps { grid-template-columns: minmax(0, 1fr); gap: 14px; }
  .steps::before { top: 10px; bottom: 10px; left: 9.5px; right: auto; width: 1px; height: auto; transform: scaleY(0); transform-origin: top; background: linear-gradient(180deg, rgba(240, 205, 138, 0.7), rgba(240, 205, 138, 0.2)); }
  .steps li { grid-template-columns: 20px minmax(0, 1fr); gap: 14px; align-items: start; }
}

@media (prefers-reduced-motion: reduce) {
  .stop :deep([data-reveal]) { opacity: 1; transform: none; transition: none; }
  .steps::before, .step-star svg, .spheres-arc path { transition: none; }
}
</style>
