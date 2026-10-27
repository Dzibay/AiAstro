<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import PanelHead from '../../components/cabinet/PanelHead.vue'
import ReadingText from '../../components/cabinet/ReadingText.vue'
import PortraitWalk from '../../components/cabinet/PortraitWalk.vue'
import SkyNudge from '../../components/sky/SkyNudge.vue'
import { markStep, stepDone } from '../../utils/newcomer.js'
import { gameSupported, startGame } from '../../components/game/state.js'
import { queue } from '../../utils/track.js'
import { useChart } from '../../composables/useChart.js'
import { errorText } from '../../api/http.js'
import { formatDate } from '../../utils/format.js'
import { ASPECTS, ELEMENTS, MODES, POINTS, ROMAN, SIGN_BY_ID, chartItems, degrees } from '../../components/cabinet/astro.js'

/**
 * The chart's panel beside the wheel. Without a choice: the big three, the elements and the
 * crosses, and every planet as a link, so the whole chart is there without a mouse. With one
 * (/cabinet/chart/venus, from the wheel or the list): its reading and its aspects.
 */

const props = defineProps({
  user: { type: Object, required: true },
})

const route = useRoute()
const { chart, status, message, hot, load, reading, portrait: loadPortrait, forgetReadings } = useChart()

onMounted(load)

// The chart seen for the first time: the funnel's step, and the overview may ask what comes next (NextAsk).
watch(() => status.value === 'ready', (ready) => {
  if (!ready || stepDone(props.user.id, 'chart')) return
  markStep(props.user.id, 'chart')
  queue('act', 'chart:seen')
}, { immediate: true })

const item = computed(() => (typeof route.params.item === 'string' ? route.params.item : ''))
const items = computed(() => (chart.value ? chartItems(chart.value) : []))
const byId = computed(() => Object.fromEntries(items.value.map((point) => [point.id, point])))
const current = computed(() => byId.value[item.value] || null)

/* ---- The portrait: the chart read as a whole ---- */

const portrait = ref(null)
const portraitError = ref('')
async function fetchPortrait() {
  portraitError.value = ''
  try {
    portrait.value = await loadPortrait()
  } catch (error) {
    portraitError.value = errorText(error)
  }
}
watch(() => status.value === 'ready' && !item.value, (open) => {
  if (open && !portrait.value) fetchPortrait()
}, { immediate: true })

// «Небосвод» lit or gone out: the texts come again, whole or veiled.
watch(() => props.user.sky, async () => {
  forgetReadings()
  portrait.value = null
  if (status.value === 'ready' && !item.value) fetchPortrait()
  const id = item.value
  if (!id || !current.value) return
  try {
    const result = await reading(id)
    if (item.value === id) text.value = { id, ...result }
  } catch {
    // The old text stays; the next choice asks again.
  }
})

const birthLine = computed(() => {
  const birth = props.user.birth
  if (!birth) return ''
  return [formatDate(birth.date), birth.time, birth.place].filter(Boolean).join(' · ')
})

const linkTo = (id) => ({ name: 'cabinet-chart', params: { item: id } })

/** The natal sky game (NatalGame) once more, or for the first time if it was declined. */
const canPlay = gameSupported()
function replay() {
  queue('act', 'game:replay')
  startGame()
}

/** «в Весах, 18°24′» */
const where = (point) => `${SIGN_BY_ID[point.sign].in}, ${degrees(point.deg)}`

const bigThree = computed(() => ['sun', 'moon', 'asc'].map((id) => ({ id, point: byId.value[id] || null, ...POINTS[id] })))

const planets = computed(() => (chart.value ? chart.value.points : []))

/** A row of stars for each: lit as many as the planets, the rest dim, five at least. */
function bars(list, counts) {
  const slots = Math.max(5, ...Object.values(counts))
  return list.map((entry) => ({ ...entry, count: counts[entry.id], slots }))
}
const elements = computed(() => (chart.value ? bars(ELEMENTS, chart.value.balance.elements) : []))
const modes = computed(() => (chart.value ? bars(MODES, chart.value.balance.modes) : []))

/* ---- One point ---- */

const text = ref(null)
const textError = ref('')

const title = computed(() => {
  if (text.value?.id === item.value) return text.value.title
  const point = current.value
  if (!point) return ''
  const house = point.house ? `, в ${ROMAN[point.house - 1]} доме` : ''
  return `${POINTS[point.id].name} ${SIGN_BY_ID[point.sign].in}${house}`
})

/** «18°24′ Весов · XII дом · попятный» */
const position = computed(() => {
  const point = current.value
  if (!point) return ''
  const parts = [`${degrees(point.deg)} ${SIGN_BY_ID[point.sign].of}`]
  if (point.house) parts.push(`${ROMAN[point.house - 1]} дом`)
  if (point.retro && point.id !== 'node') parts.push('попятный')
  return parts.join(' · ')
})

const aspects = computed(() => {
  if (!chart.value || !current.value) return []
  return chart.value.aspects
    .filter((aspect) => aspect.a === item.value || aspect.b === item.value)
    .map((aspect) => {
      const other = aspect.a === item.value ? aspect.b : aspect.a
      const meaning = text.value?.id === item.value
        ? text.value.aspects?.find((entry) => entry.a === aspect.a && entry.b === aspect.b && entry.type === aspect.type)
        : null
      return {
        key: `${aspect.a}-${aspect.b}`,
        other,
        ...ASPECTS[aspect.type],
        with: POINTS[other].with,
        orb: degrees(aspect.orb),
        text: meaning?.text || '',
      }
    })
})
const aspectsLocked = computed(() => Boolean(text.value?.id === item.value && text.value.locked))

const panel = ref(null)
let asked = ''
watch([item, () => status.value], async ([id], previous) => {
  if (!id || !current.value || asked === id) return
  asked = id
  textError.value = ''
  try {
    const result = await reading(id)
    if (item.value === id) text.value = { id, ...result }
    if (id === 'sun') markStep(props.user.id, 'sun')
  } catch (error) {
    if (item.value === id) textError.value = errorText(error)
  } finally {
    asked = ''
  }
  // A choice made from the list or the wheel: the keyboard goes on from the new heading.
  if (previous && item.value === id) {
    await nextTick()
    panel.value?.querySelector('.panel-title')?.focus({ preventScroll: true })
  }
}, { immediate: true })

function setHot(id) {
  hot.value = id
}

/**
 * The hint under a reading, once it is read: the planets of love lead to the pair, the rest to
 * the sky of today over the same chart.
 */
const LOVE = {
  venus: 'Венера говорит о том, как вы любите. Как она звучит рядом с картой близкого человека, покажет совместимость — по пяти сферам жизни.',
  mars: 'Марс — ваша искра и ваш напор. Где он зажигает другого человека, а где спорит с ним, видно в совместимости двух карт.',
  moon: 'Луна — то, что нужно вам, чтобы чувствовать себя дома. С кем этот дом складывается легче, подскажет совместимость.',
}
const nudge = computed(() => {
  if (!text.value || text.value.id !== item.value) return null
  if (LOVE[item.value]) {
    return { tone: 'sky', text: LOVE[item.value], action: 'Сложить две карты', to: { name: 'cabinet-pair' } }
  }
  return {
    tone: 'gold',
    text: props.user.sky
      ? 'Карта — то, с чем вы родились. Как небо касается её сегодня и в ближайший месяц, читайте в прогнозе.'
      : 'Карта — то, с чем вы родились. Каждый день небо касается её по-новому: транзиты дня открыты всем, а полный прогноз и звёздный календарь горят в «Небосводе».',
    action: 'Прогноз дня',
    to: { name: 'cabinet-forecast' },
  }
})
</script>

<template>
  <div ref="panel" class="chart-panel">
    <template v-if="status === 'empty'">
      <PanelHead lead="Чтобы нарисовать карту, небу нужна дата вашего рождения. Время и город сделают её точнее.">
        Натальная <em>карта</em>
      </PanelHead>
      <RouterLink class="add-birth" :to="{ name: 'cabinet-birth' }">
        <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg>
        Добавить дату рождения
      </RouterLink>
    </template>

    <p v-else-if="status === 'error'" class="error">{{ message }}</p>
    <p v-else-if="!chart" class="loading">Считаем ваше небо…</p>

    <!-- One point: its reading and its aspects. -->
    <template v-else-if="item">
      <RouterLink class="back" :to="{ name: 'cabinet-chart' }">
        <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M10 3L5 8L10 13" /></svg>
        Вся карта
      </RouterLink>

      <template v-if="current">
        <PanelHead :lead="position">
          <span class="title-glyph" aria-hidden="true">{{ POINTS[current.id].glyph }}</span>
          {{ title }}
        </PanelHead>

        <p v-if="textError" class="error">{{ textError }}</p>
        <ReadingText v-else-if="text && text.id === item" :reading="text.reading" />
        <p v-else class="loading">Читаем ваше небо…</p>

        <p v-if="current.approx" class="note">
          Время рождения неизвестно, поэтому место Луны приблизительно: за сутки она проходит около 13°.
          <RouterLink class="inline" :to="{ name: 'cabinet-birth' }">Уточнить время</RouterLink>
        </p>

        <section class="block" aria-labelledby="aspects-title">
          <h3 id="aspects-title" class="block-title">Аспекты</h3>
          <ul v-if="aspects.length" class="aspect-list">
            <li v-for="aspect in aspects" :key="aspect.key">
              <span class="aspect-glyph" :class="`tone-${aspect.tone}`" aria-hidden="true">{{ aspect.glyph }}</span>
              <span>
                {{ aspect.name }} с
                <RouterLink class="inline" :to="linkTo(aspect.other)" @pointerenter="setHot(aspect.other)" @pointerleave="setHot('')">{{ aspect.with }}</RouterLink>
              </span>
              <span class="orb">орбис {{ aspect.orb }}</span>
              <p v-if="aspect.text" class="aspect-text">{{ aspect.text }}</p>
            </li>
          </ul>
          <p v-else class="quiet-text">Мажорных аспектов нет: эта точка говорит сама за себя.</p>
          <p v-if="aspects.length && aspectsLocked" class="note">
            Что значит каждый из этих аспектов для вас, читайте в
            <RouterLink class="inline" v-seen="'sky:chart'" data-track="sky:chart" :to="{ name: 'cabinet-sky' }">«Небосводе»</RouterLink>.
          </p>
        </section>

        <SkyNudge v-if="nudge" :to="nudge.to" :action="nudge.action" :tone="nudge.tone">{{ nudge.text }}</SkyNudge>
      </template>
      <p v-else class="quiet-text">Такой точки в вашей карте нет.</p>
    </template>

    <!-- The whole chart. -->
    <template v-else>
      <PanelHead :lead="birthLine">Натальная <em>карта</em></PanelHead>

      <button v-if="canPlay" type="button" class="replay" @click="replay">
        <svg viewBox="-12 -12 24 24" aria-hidden="true">
          <circle class="replay-orbit" r="7" />
          <path class="replay-ray" d="M0 7V-11" />
          <circle class="replay-sun" r="2.2" />
          <circle class="replay-earth" cy="7" r="1.6" />
        </svg>
        Собрать своё небо
      </button>

      <p v-if="!chart.time_known" class="note">
        Время рождения неизвестно: домов и Асцендента нет, Луна стоит приблизительно.
        <RouterLink class="inline" :to="{ name: 'cabinet-birth' }">Уточнить время</RouterLink>
      </p>
      <p v-else-if="!chart.place_known" class="note">
        Город записан без координат, поэтому домов нет.
        <RouterLink class="inline" :to="{ name: 'cabinet-birth' }">Выбрать город из подсказок</RouterLink>
      </p>
      <p v-else-if="chart.house_system === 'porphyry'" class="note">
        За полярным кругом дома по Плацидусу не определены, они построены по Порфирию.
      </p>

      <section class="block" aria-labelledby="three-title">
        <h3 id="three-title" class="block-title">Большая тройка</h3>
        <div class="three">
          <template v-for="entry in bigThree" :key="entry.id">
            <RouterLink
              v-if="entry.point"
              class="three-item"
              :to="linkTo(entry.id)"
              @pointerenter="setHot(entry.id)"
              @pointerleave="setHot('')"
              @focus="setHot(entry.id)"
              @blur="setHot('')"
            >
              <span class="three-glyph" aria-hidden="true">{{ entry.glyph }}</span>
              <span class="three-name">{{ entry.name }}</span>
              <span class="three-sign">{{ SIGN_BY_ID[entry.point.sign].name }}<template v-if="entry.point.approx"> ≈</template></span>
            </RouterLink>
            <span v-else class="three-item is-off">
              <span class="three-glyph" aria-hidden="true">{{ entry.glyph }}</span>
              <span class="three-name">{{ entry.name }}</span>
              <span class="three-sign">нужно время</span>
            </span>
          </template>
        </div>
      </section>

      <section class="block" aria-labelledby="portrait-title">
        <h3 id="portrait-title" class="block-title">Портрет</h3>
        <p v-if="portraitError" class="error">{{ portraitError }}</p>
        <PortraitWalk v-else-if="portrait" :portrait="portrait" />
        <p v-else class="loading">Складываем карту в одно целое…</p>
      </section>

      <section class="block balance" aria-labelledby="balance-title">
        <h3 id="balance-title" class="block-title">Стихии и кресты</h3>
        <dl class="stars">
          <div v-for="group in [elements, modes]" :key="group[0].id" class="star-group">
            <div v-for="entry in group" :key="entry.id" class="star-row">
              <dt>{{ entry.name }}</dt>
              <dd>
                <span class="visually-hidden">{{ entry.count }}</span>
                <span aria-hidden="true">{{ '✦'.repeat(entry.count) }}<span class="star-off">{{ '✦'.repeat(entry.slots - entry.count) }}</span></span>
              </dd>
            </div>
          </div>
        </dl>
      </section>

      <section class="block" aria-labelledby="planets-title">
        <h3 id="planets-title" class="block-title">Планеты</h3>
        <ul class="planet-list">
          <li v-for="point in planets" :key="point.id">
            <RouterLink
              class="planet-row"
              :to="linkTo(point.id)"
              @pointerenter="setHot(point.id)"
              @pointerleave="setHot('')"
              @focus="setHot(point.id)"
              @blur="setHot('')"
            >
              <span class="row-glyph" aria-hidden="true">{{ POINTS[point.id].glyph }}</span>
              <span class="row-name">{{ POINTS[point.id].name }}</span>
              <span class="row-where">{{ where(point) }}<template v-if="point.approx"> ≈</template></span>
              <span class="row-house">{{ point.house ? ROMAN[point.house - 1] : '' }}</span>
              <span class="row-retro" :title="point.retro && point.id !== 'node' ? 'Попятное движение' : undefined">
                {{ point.retro && point.id !== 'node' ? 'R' : '' }}
              </span>
            </RouterLink>
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>

<style scoped>
.chart-panel { display: grid; gap: 18px; }

.loading { margin: 0; font-family: var(--serif); font-style: italic; font-size: 17px; color: rgba(242, 228, 200, 0.75); }
.error { margin: 0; font-size: 14px; color: #f2a48c; }
.note { margin: 0; font-size: 13.5px; line-height: 1.6; color: rgba(233, 194, 124, 0.8); }
.quiet-text { margin: 0; font-size: 14.5px; line-height: 1.6; color: rgba(226, 220, 210, 0.62); }

.inline {
  color: #f0cd8a;
  text-decoration: underline;
  text-decoration-color: rgba(240, 205, 138, 0.35);
  text-underline-offset: 3px;
  transition: text-decoration-color 0.25s ease;
}
.inline:hover { text-decoration-color: currentColor; }
.inline:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 2px; border-radius: 4px; }

.title-glyph {
  margin-right: 4px;
  font-family: 'Segoe UI Symbol', 'Noto Sans Symbols', sans-serif;
  font-size: 0.8em;
  color: #f0cd8a;
}

.back {
  justify-self: start;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: -6px 0 -8px -4px;
  padding: 4px;
  font-size: 13px;
  color: rgba(242, 228, 200, 0.72);
  text-decoration: none;
  transition: color 0.25s ease;
}
.back svg { width: 12px; height: 12px; fill: none; stroke: currentColor; stroke-width: 1.5; stroke-linecap: round; stroke-linejoin: round; }
.back:hover { color: #f0cd8a; }
.back:focus-visible { outline: 1px solid #f0cd8a; border-radius: 6px; }

/* Sun, Moon, Ascendant: three centred entries, no frames, each a way into its reading. */
.three { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.three-item {
  display: grid;
  justify-items: center;
  gap: 3px;
  padding: 6px 4px;
  border-radius: 12px;
  color: #efe7d8;
  text-decoration: none;
  transition: background 0.25s ease;
}
a.three-item:hover { background: rgba(240, 205, 138, 0.06); }
a.three-item:hover .three-sign { color: #f0cd8a; }
a.three-item:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 2px; }
.three-item.is-off { opacity: 0.45; }
.three-glyph { font-family: 'Segoe UI Symbol', 'Noto Sans Symbols', sans-serif; font-size: 20px; line-height: 1.2; color: #f0cd8a; }
.three-name { font-family: var(--caps); font-size: 14px; letter-spacing: 0.1em; color: rgba(226, 220, 210, 0.66); }
.three-sign { font-family: var(--serif); font-style: italic; font-size: 22px; line-height: 1.1; color: #f6efe2; transition: color 0.25s ease; }

/* The elements and the crosses as rows of stars: lit for each planet, the rest dim. */
.stars { display: grid; gap: 12px; margin: 0; }
.star-group { display: grid; gap: 4px; }
.star-row { display: flex; justify-content: space-between; align-items: baseline; gap: 16px; font-family: var(--book); font-size: 14.5px; }
.star-row dt { color: #efe7d8; }
.star-row dd { margin: 0; letter-spacing: 0.18em; color: #f0cd8a; white-space: nowrap; }
.star-off { color: rgba(240, 205, 138, 0.2); }
.visually-hidden { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }

.planet-list, .aspect-list { display: grid; gap: 2px; margin: 0; padding: 0; list-style: none; }
.planet-row {
  display: grid;
  grid-template-columns: 22px 1fr auto 34px 12px;
  align-items: baseline;
  gap: 8px;
  padding: 6px 8px;
  margin: 0 -8px;
  border-radius: 10px;
  color: #efe7d8;
  text-decoration: none;
  font-family: var(--book);
  font-size: 15px;
  transition: background 0.2s ease;
}
.planet-row:hover { background: rgba(240, 205, 138, 0.07); }
.planet-row:focus-visible { outline: 1px solid #f0cd8a; outline-offset: -1px; }
.row-glyph { font-family: 'Segoe UI Symbol', 'Noto Sans Symbols', sans-serif; font-size: 16px; color: #f0cd8a; text-align: center; }
.row-where { font-family: var(--serif); font-style: italic; font-size: 17px; color: rgba(239, 231, 216, 0.75); font-variant-numeric: tabular-nums; white-space: nowrap; }
.row-house { font-family: var(--caps); font-size: 15px; color: rgba(233, 194, 124, 0.8); text-align: right; }
.row-retro { font-family: var(--serif); font-style: italic; font-size: 14px; color: rgba(233, 194, 124, 0.8); }

.aspect-list li { display: grid; grid-template-columns: 22px 1fr auto; align-items: baseline; gap: 8px; padding: 5px 0; font-family: var(--book); font-size: 15px; }
.aspect-text {
  grid-column: 2 / -1;
  margin: 2px 0 6px;
  font-family: var(--book);
  font-size: 14px;
  line-height: 1.65;
  color: rgba(239, 231, 216, 0.82);
}
.aspect-glyph { font-family: 'Segoe UI Symbol', 'Noto Sans Symbols', sans-serif; text-align: center; }
.tone-easy, .tone-joint { color: #f0cd8a; }
.tone-tense { color: #d98b7a; }
.orb { font-family: var(--serif); font-style: italic; font-size: 15px; color: rgba(226, 220, 210, 0.55); font-variant-numeric: tabular-nums; }

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

.replay {
  justify-self: start;
  display: inline-flex;
  align-items: center;
  gap: 9px;
  margin-top: -4px;
  padding: 7px 16px 7px 10px;
  border-radius: 999px;
  border: 1px solid rgba(240, 205, 138, 0.38);
  background: rgba(240, 205, 138, 0.05);
  font: inherit;
  font-size: 13.5px;
  color: #f3dcae;
  cursor: pointer;
  transition: background 0.25s ease, border-color 0.25s ease;
}
.replay svg { width: 22px; height: 22px; overflow: visible; }
.replay-orbit { fill: none; stroke: rgba(240, 205, 138, 0.45); stroke-width: 0.9; }
.replay-ray { stroke: #ffe2a8; stroke-width: 1; stroke-linecap: round; opacity: 0.8; }
.replay-sun { fill: #ffe7b0; filter: drop-shadow(0 0 3px rgba(255, 196, 110, 0.9)); }
.replay-earth { fill: #8fc2ff; }
.replay:hover { background: rgba(240, 205, 138, 0.12); border-color: rgba(240, 205, 138, 0.8); }
.replay:focus-visible { outline: 2px solid #ffe2a8; outline-offset: 3px; }

@media (max-width: 760px) {
  .planet-row { min-height: 44px; align-items: center; }
  .back, .replay { min-height: 44px; }
}
</style>
