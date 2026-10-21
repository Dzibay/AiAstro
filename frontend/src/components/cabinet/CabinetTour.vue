<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSky } from '../../composables/useSky.js'
import { SIGNS } from '../../utils/skyToday.js'
import { markTourSeen, stopTour, tour } from '../../utils/tour.js'
import { track } from '../../utils/track.js'
import { cabinetLayout, panelLeft } from './layout.js'

/**
 * The cabinet introduces itself: first a short scene on the sky, then spotlight steps over the
 * real things — the star, the five sections, the panel, the «?». The sky dims, a soft window stays
 * open around the thing being told about, and a card beside it says what it is and what is free.
 *
 * `intro` walks the overview (an invited partner starts with the pair just joined); `sky` follows
 * the purchase of «Небосвод»: the sections flare gold one by one, then the steps go into each
 * section and show what has opened there. On a phone the card sits at the top or the bottom,
 * whichever leaves the window clear, and a swipe on it turns the steps.
 */

const props = defineProps({
  user: { type: Object, required: true },
})

const route = useRoute()
const router = useRouter()
const { geo, mark } = useSky()

const SIGN_BY_ID = Object.fromEntries(SIGNS.map((sign) => [sign.id, sign]))
const narrow = computed(() => geo.value.narrow)
const lit = computed(() => Boolean(props.user.sky))

const OVERVIEW = { name: 'cabinet' }

const intro = computed(() => {
  const sign = SIGN_BY_ID[mark.sun]
  const steps = [
    {
      id: 'star',
      target: 'star',
      route: OVERVIEW,
      title: 'Ваша звезда',
      text: sign
        ? `Вокруг неё вычерчен ваш знак — ${sign.name}. Нажмите на звезду — откроются данные рождения; из любого раздела она вернёт сюда, к обзору.`
        : 'Как только появится дата рождения, вокруг неё зажжётся ваш знак. Нажмите на звезду — откроются данные рождения.',
      free: true,
    },
    {
      id: 'chart',
      target: 'point:chart',
      route: OVERVIEW,
      title: 'Карта',
      text: 'Планеты, дома и аспекты с толкованием каждой точки — ваши навсегда. Портрет карты целиком зажигает «Небосвод».',
      free: true,
      paid: true,
    },
    {
      id: 'forecast',
      target: 'point:forecast',
      route: OVERVIEW,
      title: 'Прогноз',
      text: 'Как небо дня и недели касается вашей карты. Первые строки и семь дней календаря — бесплатно, полные тексты и месяц вперёд — в «Небосводе».',
      free: true,
      paid: true,
    },
    {
      id: 'pair',
      target: 'point:pair',
      route: OVERVIEW,
      title: 'Пара',
      text: 'Добавьте близкого человека или пригласите его ссылкой — и увидите вашу совместимость по сферам жизни. Полный разбор открывается покупкой, сразу для обоих.',
      free: true,
    },
    {
      id: 'chat',
      target: 'point:chat',
      route: OVERVIEW,
      title: 'Астролог',
      text: 'Спросите о работе, любви или решении — астролог отвечает по вашей карте. Два вопроса в подарок, с «Небосводом» — без счёта.',
      free: true,
      paid: true,
    },
    {
      id: 'sky',
      target: 'point:sky',
      route: OVERVIEW,
      title: 'Небосвод',
      text: 'Подписка, которая зажигает всё целиком. Здесь видно, что уже горит, что зажжётся и на какой срок.',
      paid: true,
    },
    {
      id: 'panel',
      target: 'panel',
      route: OVERVIEW,
      title: 'Панель',
      text: narrow.value
        ? 'Здесь открывается выбранный раздел. Потяните панель за ручку вверх — она раскроется, а свайп вбок перелистнёт к соседнему разделу.'
        : 'Здесь открывается выбранный раздел. На обзоре — путь новичка и то, что вам уже открыто.',
    },
    {
      id: 'help',
      target: 'help',
      route: OVERVIEW,
      title: 'Если забудете',
      text: 'Нажмите «?» у вашей звезды — и знакомство начнётся заново; оно есть и в профиле. А в каждом разделе — свой «?» в углу панели: он покажет, как устроен раздел.',
    },
  ]
  if (!tour.pair) return steps
  return [
    {
      id: 'joined',
      target: 'panel',
      route: null,
      title: 'Ваша пара уже здесь',
      text: 'Вы приняли приглашение — и ваши карты встретились. Совместимость двоих открыта в разделе «Пара». Дальше — коротко обо всём кабинете.',
      free: true,
    },
    ...steps,
  ]
})

const SKY_STEPS = [
  {
    id: 'sky-chart',
    target: 'panel',
    route: { name: 'cabinet-chart' },
    title: 'Карта: портрет целиком',
    text: 'Восход, темперамент, акценты, путь роста — и смысл каждого аспекта вашей карты.',
  },
  {
    id: 'sky-forecast',
    target: 'panel',
    route: { name: 'cabinet-forecast' },
    title: 'Прогноз: полные тексты',
    text: 'Каждое утро — полный прогноз дня, на неделю — семь дней одним текстом, в календаре — тридцать дней вперёд.',
  },
  {
    id: 'sky-chat',
    target: 'panel',
    route: { name: 'cabinet-chat' },
    title: 'Астролог без счёта',
    text: 'Спрашивайте сколько хочется — о работе, любви и решениях. Вопросы больше не считаются.',
  },
  {
    id: 'sky-pair',
    target: 'panel',
    route: { name: 'cabinet-pair' },
    title: 'Пара: её день',
    text: 'У каждой открытой пары — её день по сегодняшнему небу, а полный разбор пары — дешевле.',
  },
  {
    id: 'sky-term',
    target: 'panel',
    route: { name: 'cabinet-sky' },
    title: 'Срок «Небосвода»',
    text: 'Здесь видно, до какого дня горит ваш «Небосвод», и здесь же его можно продлить.',
  },
]

/*
 * A section's own tour, from the «?» in the panel's corner. The targets are what the open section
 * shows: `css` inside the panel, `stage` the picture behind it (the wheel, the pair's stars, the
 * dome). A step whose target the section does not show right now (an empty list, a locked reading)
 * is left out, so the walk always matches the screen.
 */
const IN = '.cabinet-panel '
const SECTION_TOURS = {
  chart: {
    name: 'Карта',
    steps: [
      {
        id: 'wheel',
        stage: '.natal-wheel',
        title: 'Колесо карты',
        text: 'Небо в минуту вашего рождения: двенадцать знаков по кругу, дома и планеты. Наведите на планету — она загорится и в списке.',
        free: true,
      },
      {
        id: 'three',
        css: `${IN}.three`,
        title: 'Большая тройка',
        text: 'Солнце, Луна и Асцендент: кто вы, что чувствуете, какой вас видят. Нажмите — откроется толкование.',
        free: true,
      },
      {
        id: 'portrait',
        css: `${IN}[aria-labelledby="portrait-title"]`,
        title: 'Портрет',
        text: 'Карта, сложенная в одно целое. Первая глава — ядро карты — открыта всем, остальные главы зажигает «Небосвод».',
        free: true,
        paid: true,
      },
      {
        id: 'balance',
        css: `${IN}.balance`,
        title: 'Стихии и кресты',
        text: 'Сколько в вас огня, земли, воздуха и воды — и как вы действуете: начинаете, держите или меняетесь.',
        free: true,
      },
      {
        id: 'planets',
        css: `${IN}[aria-labelledby="planets-title"]`,
        title: 'Планеты',
        text: 'Каждая строка — точка карты. Внутри — её толкование и аспекты; смысл каждого аспекта целиком — в «Небосводе».',
        free: true,
        paid: true,
      },
    ],
  },
  forecast: {
    name: 'Прогноз',
    steps: [
      {
        id: 'mode',
        css: `${IN}.mode-toggle`,
        title: 'День, неделя, месяц',
        text: 'Переключайте, на какой срок смотреть: прогноз дня, семь дней недели или звёздный календарь на месяц.',
      },
      {
        id: 'text',
        css: [`${IN}.forecast-panel > .text`, `${IN}.star-calendar`],
        title: 'Прогноз',
        text: 'Как небо касается вашей карты. Первые строки — бесплатно; полные тексты и тридцать дней календаря — в «Небосводе».',
        free: true,
        paid: true,
      },
      {
        id: 'spheres',
        css: `${IN}[aria-labelledby="spheres-title"]`,
        title: 'Сферы',
        text: 'Где сегодня легче, а где стоит действовать бережнее: близкие, дела, разговоры, силы.',
        free: true,
      },
      {
        id: 'week',
        css: `${IN}[aria-labelledby="week-title"]`,
        title: 'Неделя',
        text: 'Семь дней одной строкой: по цвету видно, какой день легче, а какой бережнее, — и лучшие дни для каждой сферы.',
        free: true,
      },
      {
        id: 'transits',
        css: `${IN}[aria-labelledby="transits-title"]`,
        title: 'Транзиты',
        text: 'Какие планеты неба сейчас касаются точек вашей карты и до какого дня. На колесе они видны поверх карты.',
        free: true,
      },
      {
        id: 'sky-now',
        css: `${IN}[aria-labelledby="sky-title"]`,
        title: 'Небо дня',
        text: 'Фаза Луны, события неба и ретроградные планеты — то, что сейчас происходит для всех.',
        free: true,
      },
    ],
  },
  pair: {
    name: 'Пара',
    steps: [
      {
        id: 'stars',
        stage: '.pair-sky',
        title: 'Звёзды пар',
        text: 'Ваша звезда и звёзды близких: нить между вами горит тем ярче, чем больше созвучия.',
        free: true,
      },
      {
        id: 'list',
        css: `${IN}.pairs`,
        title: 'Ваши пары',
        text: 'Все пары списком, у каждой — её состояние. Нажмите на пару — откроется ваша совместимость; полный разбор открывается покупкой, у общей пары — сразу для обоих.',
        free: true,
      },
      {
        id: 'ways',
        css: `${IN}.ways`,
        title: 'Как добавить пару',
        text: 'Введите данные партнёра сами — или отправьте приглашение: партнёр укажет их без регистрации, а заведёт кабинет — пара станет общей.',
        free: true,
      },
      {
        id: 'spheres',
        css: `${IN}[aria-labelledby="spheres-title"]`,
        title: 'Сферы пары',
        text: 'Совместимость по сферам жизни: где вы звучите в унисон, а где учитесь друг у друга.',
        free: true,
      },
      {
        id: 'aspects',
        css: `${IN}[aria-labelledby="aspects-title"]`,
        title: 'Аспекты между картами',
        text: 'Как планеты одного касаются планет другого. Наведите на аспект — нить загорится на небе.',
        free: true,
      },
      {
        id: 'reading',
        css: [`${IN}.unlock`, `${IN}[aria-labelledby="reading-title"]`],
        title: 'Разбор пары',
        text: 'Полный разбор открывается один раз и остаётся с парой навсегда; у общей пары — сразу для обоих. С «Небосводом» он дешевле.',
        paid: true,
      },
      {
        id: 'pair-day',
        css: `${IN}[aria-labelledby="pair-day-title"]`,
        title: 'День пары',
        text: 'Как сегодняшнее небо касается вас двоих — с «Небосводом» для каждой открытой пары.',
        paid: true,
      },
      {
        id: 'foot',
        css: `${IN}.pair-foot`,
        title: 'Управление парой',
        text: 'Вернуться ко всем парам, исправить данные партнёра, пока разбор не открыт, или удалить пару.',
      },
    ],
  },
  chat: {
    name: 'Астролог',
    steps: [
      {
        id: 'starters',
        css: [`${IN}.starters`, `${IN}.chat-panel .panel-head`],
        title: 'С чего начать',
        text: 'Не знаете, о чём спросить? Нажмите на готовый вопрос — астролог ответит по вашей карте.',
        free: true,
      },
      {
        id: 'thread',
        css: `${IN}.thread`,
        title: 'Разговор',
        text: 'Ваши вопросы и ответы остаются здесь — к ним можно вернуться в любой день.',
        free: true,
      },
      {
        id: 'composer',
        css: [`${IN}.composer`, `${IN}.unlock`],
        title: 'Ваш вопрос',
        text: 'Спросите о работе, любви или решении простыми словами. Два вопроса в подарок, с «Небосводом» — без счёта.',
        free: true,
        paid: true,
      },
    ],
  },
  sky: {
    name: 'Небосвод',
    steps: [
      {
        id: 'dome',
        stage: '.sky-dome',
        title: 'Купол неба',
        text: 'Каждое созвездие на куполе — то, что зажигает «Небосвод». Наведите на созвездие — загорится его строка в списке.',
      },
      {
        id: 'features',
        css: `${IN}[aria-labelledby="sky-features"]`,
        title: 'Что зажигает',
        text: 'Всё, что открывает подписка, по разделам. Нажмите на строку — она раскроется и расскажет подробнее.',
        paid: true,
      },
      {
        id: 'compare',
        css: `${IN}[aria-labelledby="sky-compare"]`,
        title: 'Без подписки и с ней',
        text: 'Что остаётся бесплатным навсегда и что «Небосвод» добавляет к нему.',
        free: true,
        paid: true,
      },
      {
        id: 'plans',
        css: `${IN}[aria-labelledby="sky-plans"]`,
        title: 'Срок',
        text: 'Выберите, на сколько зажечь небо: чем дольше срок, тем дешевле месяц. Без автопродления: одно списание за срок.',
      },
      {
        id: 'pay',
        css: `${IN}.pay`,
        title: 'Оплата',
        text: 'Оплата проходит через ЮKassa. Если «Небосвод» уже горит, новый срок прибавится к текущему.',
      },
      {
        id: 'replay',
        css: `${IN}.sky-replay`,
        title: 'Что открылось',
        text: 'Эта кнопка снова проведёт по всему, что зажёг ваш «Небосвод», — раздел за разделом.',
      },
    ],
  },
}

/** The ids of the open section's steps it can show now; null until they are looked for. */
const available = ref(null)
const sectionTour = computed(() => SECTION_TOURS[route.meta.section] || null)

const firstMatch = (css) => [].concat(css).map((selector) => document.querySelector(selector)).find((element) => {
  if (!element) return false
  const r = element.getBoundingClientRect()
  return r.width > 0 && r.height > 0
}) || null

const targetOf = (item) => (item.stage ? firstMatch(item.stage) : item.css ? firstMatch(item.css) : null)

const sectionSteps = computed(() => {
  const all = sectionTour.value?.steps || []
  return available.value ? all.filter((item) => available.value.includes(item.id)) : []
})

const steps = computed(() => (tour.kind === 'sky' ? SKY_STEPS : tour.kind === 'section' ? sectionSteps.value : intro.value))
const step = computed(() => steps.value[tour.step] || null)
const last = computed(() => tour.step >= steps.value.length - 1)

const scene = computed(() => {
  const sign = SIGN_BY_ID[mark.sun]
  if (tour.kind === 'sky') {
    return {
      kicker: 'Небосвод',
      title: 'Небосвод зажжён',
      lead: 'Всё, что ждало подписки, теперь горит. Покажем, что открылось, — пять коротких шагов.',
      go: 'Показать',
    }
  }
  return {
    kicker: 'Знакомство',
    title: tour.pair ? 'Ваша пара на небе' : 'Ваша звезда зажглась',
    lead: tour.pair
      ? 'Приглашение принято — ваши звёзды встретились. Покажем пару и то, как устроен кабинет: несколько коротких шагов.'
      : `${props.user.name}, ${sign ? `небо нарисовало ваш знак — ${sign.name}` : 'ваша звезда уже на небе'}. Покажем, как оно устроено: восемь коротких шагов.`,
    go: 'Показать',
  }
})

/* ---- Where the window opens ---- */

/** The window around the step's target, in viewport px: { x, y, w, h, round }. */
const hole = ref(null)
const card = ref(null)
const cardHeight = ref(220)
const star = ref({ x: 0, y: 0 })

function rectOf(selector, pad) {
  const element = document.querySelector(selector)
  if (!element) return null
  const r = element.getBoundingClientRect()
  if (!r.width && !r.height) return null
  return { x: r.left - pad, y: r.top - pad, w: r.width + pad * 2, h: r.height + pad * 2, round: false }
}

function measureStar() {
  const element = document.querySelector('.cabinet-sky .home-star')
  if (!element) return null
  const r = element.getBoundingClientRect()
  return { x: r.left + r.width / 2, y: r.top + r.height / 2 }
}

function measure() {
  const centre = measureStar()
  if (centre) star.value = centre
  const target = step.value && (tour.kind === 'section' ? 'section' : step.value.target)
  if (tour.scene || !target) {
    hole.value = null
    return
  }
  let next = null
  if (target === 'star' && centre) {
    // The whole engraving, not only the star: the sign is what this step is about.
    const layout = cabinetLayout(geo.value, route.meta.section || '')
    const r = Math.max(46, (layout.star.span * layout.star.k) / 2 * 0.82)
    next = { x: centre.x - r, y: centre.y - r, w: r * 2, h: r * 2, round: true }
  } else if (target === 'help') {
    next = rectOf('.cabinet-sky .tour-help', 10)
    if (next) next.round = true
  } else if (target === 'panel') {
    next = rectOf('.cabinet-panel', 6)
  } else if (target.startsWith('point:')) {
    next = rectOf(`.cabinet-sky .point[data-section="${target.slice(6)}"]`, 8)
  } else if (target === 'section') {
    next = sectionRect(step.value)
  }
  hole.value = next
  if (card.value) cardHeight.value = card.value.offsetHeight
}

/** A section's target: the picture behind the panel whole, a part of the panel cut to what of it is seen. */
function sectionRect(item) {
  const element = targetOf(item)
  if (!element) return rectOf('.cabinet-panel', 6)
  const r = element.getBoundingClientRect()
  const pad = item.stage ? 0 : 8
  let box = { top: r.top - pad, bottom: r.bottom + pad, left: r.left - pad, right: r.right + pad }
  if (item.stage) {
    // The picture may run past the screen: the window stays on it.
    box = { top: Math.max(box.top, 70), bottom: Math.min(box.bottom, window.innerHeight - 10), left: Math.max(box.left, 10), right: Math.min(box.right, window.innerWidth - 10) }
    // …and on the sky the panel leaves free: beside it on a desktop, above the sheet on a phone.
    const panel = document.querySelector('.cabinet-panel')?.getBoundingClientRect()
    if (panel && narrow.value) box.bottom = Math.min(box.bottom, panel.top - 8)
    else if (panel) box.right = Math.min(box.right, panel.left - 16)
  } else {
    const view = document.querySelector('.cabinet-panel .panel-scroll')?.getBoundingClientRect()
    if (view) box = { ...box, top: Math.max(box.top, view.top - 4), bottom: Math.min(box.bottom, view.bottom + 4) }
  }
  if (box.bottom - box.top < 24) return rectOf('.cabinet-panel', 6)
  return { x: box.left, y: box.top, w: box.right - box.left, h: box.bottom - box.top, round: false }
}

/** Brings a part of the panel into the middle of its scroll, smoothly, before the window opens on it. */
function scrollToTarget(item) {
  if (!item?.css) return
  const element = targetOf(item)
  const scroller = element?.closest('.panel-scroll')
  if (!scroller) return
  const r = element.getBoundingClientRect()
  const view = scroller.getBoundingClientRect()
  const top = r.height > view.height * 0.8 ? r.top - view.top - 16 : r.top - view.top - (view.height - r.height) / 2
  scroller.scrollTo({ top: scroller.scrollTop + top, behavior: reduceMotion() ? 'auto' : 'smooth' })
}
const reduceMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches

/** What the open section shows now: waits for its data (a «…» line) to settle, a few seconds at most. */
async function prepareSection() {
  available.value = null
  const deadline = performance.now() + 4000
  await nextTick()
  // A «…» line, or the panel of the section left still fading out.
  while (performance.now() < deadline && document.querySelector('.cabinet-panel .loading, .cabinet-panel .next-leave-active, .cabinet-panel .next-enter-active')) {
    await new Promise((resolve) => setTimeout(resolve, 150))
  }
  // The panel may still be sliding in with its parts (a section just opened): what it shows
  // is taken once it has held still for half a second.
  const look = () => (sectionTour.value?.steps || []).filter((item) => targetOf(item)).map((item) => item.id)
  let found = look()
  for (let still = 0; still < 3 && performance.now() < deadline + 1500; ) {
    await new Promise((resolve) => setTimeout(resolve, 170))
    if (tour.kind !== 'section') return
    const now = look()
    still = now.join() === found.join() ? still + 1 : 0
    found = now
  }
  if (tour.kind !== 'section') return
  if (!found.length) {
    stopTour()
    return
  }
  available.value = found
  // Shown is seen: the section's walk does not come by itself again, its «?» still brings it back.
  markTourSeen(props.user.id, `section-${route.meta.section}`)
  told(name(), 'start')
  show(0)
}

/* The points fly and the panel slides after a change: the window follows them for a while. */
let raf = 0
let followUntil = 0
function follow(ms = 1800) {
  followUntil = performance.now() + ms
  if (raf) return
  const loop = (now) => {
    measure()
    raf = now < followUntil ? requestAnimationFrame(loop) : 0
  }
  raf = requestAnimationFrame(loop)
}

const holeStyle = computed(() => {
  const h = hole.value
  if (!h) return null
  return {
    left: `${h.x}px`,
    top: `${h.y}px`,
    width: `${h.w}px`,
    height: `${h.h}px`,
    borderRadius: h.round ? '50%' : '24px',
  }
})

const CARD_W = 340
const GAP = 22

const cardPlace = computed(() => {
  const W = window.innerWidth
  const V = window.innerHeight
  const h = hole.value
  if (narrow.value) {
    // A phone: the card at the top or the bottom, away from the window.
    const low = h && h.y + h.h / 2 > V * 0.5
    return { side: low ? 'top' : 'bottom', style: null }
  }
  if (!h) return { side: 'free', style: { left: `${Math.max(20, panelLeft(W) / 2 - CARD_W / 2)}px`, bottom: '8vh' } }
  const height = cardHeight.value
  const top = Math.min(Math.max(h.y + h.h / 2 - height / 2, 84), V - height - 20)
  if (h.x + h.w + GAP + CARD_W < W - 16) return { side: 'right', style: { left: `${h.x + h.w + GAP}px`, top: `${top}px` } }
  if (h.x - GAP - CARD_W > 16) return { side: 'left', style: { left: `${h.x - GAP - CARD_W}px`, top: `${top}px` } }
  const below = h.y + h.h + GAP + height < V - 16
  return {
    side: below ? 'below' : 'above',
    style: {
      left: `${Math.min(Math.max(h.x + h.w / 2 - CARD_W / 2, 16), W - CARD_W - 16)}px`,
      top: below ? `${h.y + h.h + GAP}px` : `${Math.max(16, h.y - GAP - height)}px`,
    },
  }
})

/** The scene's card: under the sky's free part, clear of the star. */
const sceneStyle = computed(() => {
  if (narrow.value) return null
  return { left: `${Math.max(20, panelLeft(window.innerWidth) / 2 - 190)}px` }
})

/* ---- Steps ---- */

const primary = ref(null)

async function show(index) {
  const next = steps.value[index]
  if (!next) return
  tour.step = index
  if (next.route && route.name !== next.route.name) await router.push(next.route).catch(() => {})
  await nextTick()
  scrollToTarget(tour.kind === 'section' ? next : null)
  measure()
  follow(tour.kind === 'section' ? 1000 : 1800)
  primary.value?.focus({ preventScroll: true })
}

/* ---- What the figures learn: a tour shown, walked to its end, or left at some step ---- */

const name = () => (tour.kind === 'section' ? `section-${route.meta.section || ''}` : tour.kind)
const told = (tourName, how, value) => track('tour', `${tourName}:${how}`, value === undefined ? {} : { value })

function begin() {
  tour.scene = false
  show(0)
}
function forward() {
  if (last.value) finish(true)
  else show(tour.step + 1)
}
function back() {
  if (tour.step > 0) show(tour.step - 1)
}
function finish(done = false) {
  const kind = tour.kind
  // A skip tells the step it was left at: 0 is the scene, 1 the first step.
  if (kind) told(name(), done === true ? 'done' : 'skip', done === true ? steps.value.length : tour.scene ? 0 : tour.step + 1)
  if (kind !== 'section') markTourSeen(props.user.id, kind)
  // The intro has already told a lit sky what it holds: the «Небосвод» tour would repeat it.
  if (kind === 'intro' && props.user.sky) markTourSeen(props.user.id, 'sky')
  stopTour()
}

function onKey(event) {
  if (!tour.kind) return
  if (event.key === 'Escape') {
    event.preventDefault()
    finish()
  } else if (!tour.scene && event.key === 'ArrowRight') {
    forward()
  } else if (!tour.scene && event.key === 'ArrowLeft') {
    back()
  }
}

/** A sideways swipe on the card turns the steps on a phone. */
let touch = null
function onTouchStart(event) {
  touch = event.touches.length === 1 ? { x: event.touches[0].clientX, y: event.touches[0].clientY } : null
}
function onTouchEnd(event) {
  if (!touch) return
  const dx = event.changedTouches[0].clientX - touch.x
  const dy = event.changedTouches[0].clientY - touch.y
  touch = null
  if (Math.abs(dx) < 50 || Math.abs(dx) < Math.abs(dy) * 1.5) return
  if (dx < 0) forward()
  else back()
}

/* ---- «Небосвод» catches fire: the sections flare one by one ---- */

const FLARE_ORDER = ['chart', 'forecast', 'pair', 'chat', 'sky']
let flareTimers = []
function flare() {
  flareTimers.forEach(clearTimeout)
  flareTimers = FLARE_ORDER.map((id, index) => setTimeout(() => {
    if (tour.kind === 'sky') tour.flare = [...tour.flare, id]
  }, 500 + index * 450))
}

const sceneButton = ref(null)
watch(() => [tour.kind, tour.scene], async ([kind, isScene]) => {
  if (!kind) return
  if (kind === 'section' && tour.step < 0) {
    prepareSection()
    return
  }
  if (isScene) {
    told(kind, 'start')
    if (kind === 'sky') flare()
    await nextTick()
    measure()
    sceneButton.value?.focus({ preventScroll: true })
  }
}, { immediate: true })

function onResize() {
  if (tour.kind) follow(300)
}

onMounted(() => {
  window.addEventListener('keydown', onKey)
  window.addEventListener('resize', onResize)
})
onUnmounted(() => {
  window.removeEventListener('keydown', onKey)
  window.removeEventListener('resize', onResize)
  cancelAnimationFrame(raf)
  flareTimers.forEach(clearTimeout)
})

const label = computed(() => {
  if (tour.kind === 'sky') return 'Что открыл «Небосвод»'
  if (tour.kind === 'section') return `Как устроен раздел «${sectionTour.value?.name || ''}»`
  return 'Знакомство с кабинетом'
})

/* Leaving the section mid-walk ends its tour: its steps belong to the section left behind. */
watch(() => route.meta.section, (now, before) => {
  if (tour.kind !== 'section') return
  if (available.value) told(`section-${before || ''}`, 'skip', tour.step + 1)
  stopTour()
})

const free = computed(() => step.value?.free)
const paid = computed(() => step.value?.paid)
</script>

<template>
  <Teleport to="body">
    <Transition name="tour">
      <div
        v-if="tour.kind"
        class="tour"
        :class="[`is-${tour.kind}`, { 'is-scene': tour.scene, 'is-narrow': narrow }]"
        role="dialog"
        aria-modal="true"
        :aria-label="label"
      >
        <!-- The dim: a plain veil for the scene, a window cut by a wide shadow for the steps. -->
        <div v-if="tour.scene || !holeStyle" class="veil" />
        <div v-else class="hole" :style="holeStyle" />
        <div class="catch" @click.self="tour.scene ? null : forward()" />

        <template v-if="tour.scene">
          <div class="flare" :style="{ left: `${star.x}px`, top: `${star.y}px` }" aria-hidden="true">
            <span class="ring" />
            <span class="ring" />
            <span class="ring" />
          </div>
          <section class="card scene-card" :style="sceneStyle" @touchstart.passive="onTouchStart" @touchend="onTouchEnd">
            <p class="kicker">{{ scene.kicker }}</p>
            <h2 class="title">{{ scene.title }}</h2>
            <p class="text">{{ scene.lead }}</p>
            <div class="actions">
              <button type="button" class="skip" @click="finish()">Позже</button>
              <button ref="sceneButton" type="button" class="go" @click="begin">{{ scene.go }}</button>
            </div>
          </section>
        </template>

        <section
          v-else-if="step"
          ref="card"
          :key="step.id"
          class="card step-card"
          :class="`at-${cardPlace.side}`"
          :style="cardPlace.style"
          aria-live="polite"
          @touchstart.passive="onTouchStart"
          @touchend="onTouchEnd"
        >
          <div class="step-top">
            <p class="kicker"><template v-if="tour.kind === 'section'">{{ sectionTour?.name }} · </template>{{ tour.step + 1 }} из {{ steps.length }}</p>
            <button type="button" class="skip" @click="finish()">Пропустить</button>
          </div>
          <h2 class="title">{{ step.title }}</h2>
          <p class="text">{{ step.text }}</p>
          <p v-if="free || paid" class="marks">
            <span v-if="free" class="mark-free">бесплатно</span>
            <span v-if="paid" class="mark-sky" :class="{ 'is-lit': lit }">
              <svg viewBox="0 0 16 12" aria-hidden="true"><path d="M1.5 10.5L1 3l4 3.2L8 1l3 5.2L15 3l-.5 7.5z" /></svg>
              {{ lit ? 'открыто с «Небосводом»' : 'полностью — в «Небосводе»' }}
            </span>
          </p>
          <div class="actions">
            <span class="dots" aria-hidden="true">
              <span v-for="(item, index) in steps" :key="item.id" class="dot" :class="{ 'is-on': index === tour.step }" />
            </span>
            <button v-if="tour.step > 0" type="button" class="back" @click="back">Назад</button>
            <button ref="primary" type="button" class="go" @click="forward">{{ last ? 'Готово' : 'Далее' }}</button>
          </div>
          <p v-if="narrow" class="swipe" aria-hidden="true">свайп — к соседнему шагу</p>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.tour { position: fixed; inset: 0; z-index: 50; }

.veil { position: absolute; inset: 0; background: rgba(3, 4, 10, 0.66); transition: background 0.6s ease; }
.is-sky .veil { background: radial-gradient(70% 70% at 30% 45%, rgba(3, 4, 10, 0.12), rgba(3, 4, 10, 0.5)); }
/* The window: a soft gold rim, and the rest of the screen under its shadow. */
.hole {
  position: absolute;
  box-shadow: 0 0 0 200vmax rgba(3, 4, 10, 0.66), 0 0 0 1px rgba(255, 226, 168, 0.55), 0 0 34px 6px rgba(255, 200, 110, 0.22);
  transition: left 0.5s cubic-bezier(0.3, 0.7, 0.2, 1), top 0.5s cubic-bezier(0.3, 0.7, 0.2, 1), width 0.5s cubic-bezier(0.3, 0.7, 0.2, 1),
    height 0.5s cubic-bezier(0.3, 0.7, 0.2, 1), border-radius 0.5s ease;
  pointer-events: none;
}
.hole::after {
  content: '';
  position: absolute;
  inset: -1px;
  border-radius: inherit;
  border: 1px solid rgba(255, 226, 168, 0.5);
  animation: hole-breathe 2.6s ease-in-out infinite;
}
/* Clicks never reach the cabinet under the tour; a click on the dim goes on to the next step. */
.catch { position: absolute; inset: 0; }

/* The scene: rings of light spreading from the person's star. */
.flare { position: absolute; width: 0; height: 0; pointer-events: none; }
.flare::before {
  content: '';
  position: absolute;
  left: -110px;
  top: -110px;
  width: 220px;
  height: 220px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 236, 196, 0.75), rgba(255, 196, 110, 0.18) 38%, transparent 70%);
  animation: flare-in 1.6s cubic-bezier(0.2, 0.7, 0.2, 1) both;
}
.ring {
  position: absolute;
  left: -40px;
  top: -40px;
  width: 80px;
  height: 80px;
  border-radius: 50%;
  border: 1px solid rgba(255, 226, 168, 0.7);
  opacity: 0;
  animation: ring 3.2s cubic-bezier(0.2, 0.6, 0.3, 1) infinite;
}
.ring:nth-child(2) { animation-delay: 1.05s; }
.ring:nth-child(3) { animation-delay: 2.1s; }
.is-sky .flare { display: none; }

/* The card: the cabinet's glass, with a denser body, for it is read over a dimmed sky. */
.card {
  position: absolute;
  width: 340px;
  padding: 20px 22px 18px;
  border-radius: 20px;
  border: 1px solid rgba(240, 210, 150, 0.32);
  background:
    radial-gradient(120% 80% at 0% 0%, rgba(255, 196, 120, 0.14), transparent 60%),
    linear-gradient(160deg, rgba(26, 23, 26, 0.86), rgba(8, 10, 18, 0.92));
  box-shadow: 0 24px 70px rgba(0, 0, 0, 0.55), inset 0 1px 0 rgba(255, 240, 210, 0.1);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  color: #efe7d8;
  transition: left 0.5s cubic-bezier(0.3, 0.7, 0.2, 1), top 0.5s cubic-bezier(0.3, 0.7, 0.2, 1);
  animation: card-rise 0.45s cubic-bezier(0.3, 0.7, 0.2, 1) both;
}
.scene-card { bottom: 9vh; width: 380px; text-align: center; animation-delay: 0.7s; }
.scene-card .actions { justify-content: center; }
/* While the sections flare, the card keeps low, so the sky above it is seen catching fire. */
.is-sky .scene-card { bottom: 3vh; }
.kicker { margin: 0; font-size: 10px; letter-spacing: 0.26em; text-transform: uppercase; color: rgba(233, 194, 124, 0.8); }
.title { margin: 6px 0 8px; font-family: var(--serif); font-weight: 400; font-size: 26px; line-height: 1.1; color: #fff3da; }
.scene-card .title { font-size: 32px; font-style: italic; }
.text { margin: 0; font-family: var(--book); font-size: 15px; line-height: 1.5; color: rgba(239, 231, 216, 0.9); }

.step-top { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.marks { display: flex; flex-wrap: wrap; gap: 6px; margin: 12px 0 0; }
.marks > span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
  letter-spacing: 0.02em;
}
.mark-free { border: 1px solid rgba(214, 222, 238, 0.3); color: rgba(226, 232, 244, 0.85); }
.mark-sky { border: 1px solid rgba(240, 205, 138, 0.45); color: #f0cd8a; }
.mark-sky svg { width: 11px; height: 9px; fill: none; stroke: currentColor; stroke-width: 1.2; stroke-linejoin: round; }
.mark-sky.is-lit { background: rgba(240, 205, 138, 0.12); }
.mark-sky.is-lit svg { fill: currentColor; }

.actions { display: flex; align-items: center; gap: 10px; margin-top: 16px; }
.dots { display: flex; gap: 5px; margin-right: auto; }
.dot { width: 5px; height: 5px; border-radius: 50%; background: rgba(240, 205, 138, 0.22); transition: background 0.3s ease, transform 0.3s ease; }
.dot.is-on { background: #f0cd8a; transform: scale(1.4); box-shadow: 0 0 6px rgba(255, 205, 120, 0.8); }
.go, .back, .skip {
  font: inherit;
  cursor: pointer;
  transition: background 0.25s ease, border-color 0.25s ease, color 0.25s ease, box-shadow 0.25s ease;
}
.go {
  padding: 9px 20px;
  border-radius: 999px;
  border: 1px solid rgba(240, 205, 138, 0.7);
  background: linear-gradient(180deg, rgba(240, 205, 138, 0.28), rgba(240, 205, 138, 0.12));
  font-size: 14px;
  color: #fff1d4;
}
.go:hover { background: linear-gradient(180deg, rgba(240, 205, 138, 0.4), rgba(240, 205, 138, 0.18)); box-shadow: 0 6px 24px rgba(230, 170, 80, 0.25); }
.back {
  padding: 9px 14px;
  border-radius: 999px;
  border: 1px solid rgba(240, 210, 150, 0.22);
  background: none;
  font-size: 14px;
  color: rgba(239, 231, 216, 0.85);
}
.back:hover { border-color: rgba(240, 205, 138, 0.55); color: #f0cd8a; }
.skip { padding: 4px 2px; border: 0; background: none; font-size: 12.5px; color: rgba(226, 220, 210, 0.6); }
.skip:hover { color: #f0cd8a; }
.scene-card .skip { padding: 9px 14px; font-size: 14px; }
.go:focus-visible, .back:focus-visible, .skip:focus-visible { outline: 2px solid #ffe2a8; outline-offset: 3px; border-radius: 999px; }
.swipe { margin: 10px 0 0; text-align: center; font-size: 11px; letter-spacing: 0.06em; color: rgba(226, 220, 210, 0.45); }

/* Phones: the card across the screen, at the top or the bottom; the scene lighter, without the glow. */
.is-narrow .card { left: 12px !important; right: 12px; width: auto; }
.is-narrow .step-card.at-bottom { top: auto !important; bottom: calc(12px + env(safe-area-inset-bottom)); }
.is-narrow .step-card.at-top { top: 70px !important; bottom: auto; }
.is-narrow .scene-card { bottom: calc(16px + env(safe-area-inset-bottom)); }
.is-narrow .title { font-size: 22px; }
.is-narrow .scene-card .title { font-size: 26px; }
.is-narrow .go, .is-narrow .back { min-height: 44px; }
.is-narrow .skip { min-height: 44px; }
.is-narrow .ring:nth-child(3) { display: none; }

.tour-enter-active, .tour-leave-active { transition: opacity 0.5s ease; }
.tour-enter-from, .tour-leave-to { opacity: 0; }

@keyframes card-rise { from { opacity: 0; transform: translateY(10px); } }
@keyframes flare-in { from { opacity: 0; transform: scale(0.3); } 40% { opacity: 1; } }
@keyframes ring { 0% { opacity: 0.9; transform: scale(0.4); } 100% { opacity: 0; transform: scale(5); } }
@keyframes hole-breathe { 50% { opacity: 0.25; } }

@media (prefers-reduced-motion: reduce) {
  .hole, .card { transition: none; }
  .hole::after, .ring { animation: none; }
  .card { animation: card-fade 0.3s ease both; }
  .flare::before { animation: none; }
}
@keyframes card-fade { from { opacity: 0; } }
</style>
