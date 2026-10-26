<script setup>
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { useChart } from '../../composables/useChart.js'
import { useSky } from '../../composables/useSky.js'
import { useSiteConfig, fallbackConfig } from '../../composables/useSiteConfig.js'
import { chartItems, SIGN_BY_ID } from '../cabinet/astro.js'
import { formatDate } from '../../utils/format.js'
import {
  canSharePictures, cssFont, downloadPicture, finishPicture, paintStar, PICTURE, sharePicture, startPicture, SYMBOLS,
} from '../../utils/sharePicture.js'

/**
 * «Звёздный паспорт»: the person in one card — the name, the Sun, the Moon and the Ascendant,
 * the leading element and the birth data. It can be saved as a picture or shared: the picture
 * is drawn on a canvas in the browser, nothing goes to the server.
 */

const props = defineProps({
  user: { type: Object, required: true },
})

const { chart, load } = useChart()
const { mark } = useSky()
const { config } = useSiteConfig()
watch(() => props.user.birth?.date, (date) => {
  if (date) load()
}, { immediate: true })

const ELEMENT_OF = ['fire', 'earth', 'air', 'water']
const ELEMENTS = {
  fire: { name: 'Огонь', line: 'порыв, смелость, свет для других' },
  earth: { name: 'Земля', line: 'опора, терпение, дело в руках' },
  air: { name: 'Воздух', line: 'мысль, слово, лёгкость связей' },
  water: { name: 'Вода', line: 'чувство, глубина, память сердца' },
}
const SIGN_IDS = Object.keys(SIGN_BY_ID)

const byId = computed(() => (chart.value ? Object.fromEntries(chartItems(chart.value).map((point) => [point.id, point])) : {}))
const three = computed(() => [
  { id: 'sun', glyph: '☉︎', name: 'Солнце', sign: byId.value.sun?.sign || mark.sun },
  { id: 'moon', glyph: '☽︎', name: 'Луна', sign: byId.value.moon?.sign || mark.moon },
  { id: 'asc', glyph: 'Asc', name: 'Асцендент', sign: byId.value.asc?.sign || '' },
].map((entry) => ({ ...entry, info: SIGN_BY_ID[entry.sign] || null })))

const element = computed(() => {
  const counts = chart.value?.balance?.elements
  const sun = SIGN_IDS.indexOf(byId.value.sun?.sign || mark.sun)
  const sunElement = sun >= 0 ? ELEMENT_OF[sun % 4] : null
  if (counts) {
    const top = Math.max(...Object.values(counts))
    const tied = Object.keys(counts).filter((id) => counts[id] === top)
    // Two elements sharing the lead: the Sun's own one speaks for the person.
    const id = tied.includes(sunElement) ? sunElement : tied[0]
    if (top > 0) return { id, ...ELEMENTS[id] }
  }
  return sunElement ? { id: sunElement, ...ELEMENTS[sunElement] } : null
})

const birthLine = computed(() => {
  const birth = props.user.birth
  if (!birth) return ''
  return [formatDate(birth.date), birth.time, birth.place].filter(Boolean).join(' · ')
})

/* ---- The picture ---- */

/** The picture's big line: the name, or «Моё небо» for a cabinet that has not given one. */
const signature = computed(() => props.user.name || 'Моё небо')

const busy = ref(false)
const canShare = canSharePictures

async function draw() {
  const { W, H } = PICTURE
  const { canvas, ctx } = await startPicture(signature.value)
  const caps = cssFont('--caps')
  const serif = cssFont('--serif')
  const book = cssFont('--book')
  const star = (x, y, r, color) => paintStar(ctx, x, y, r, color)

  ctx.fillStyle = 'rgba(240, 205, 138, 0.85)'
  ctx.font = `600 40px ${caps}`
  ctx.fillText('звёздный паспорт', W / 2, 190)
  star(W / 2, 270, 34, '#fff3d6')

  ctx.fillStyle = '#f6efe2'
  ctx.font = `italic 500 104px ${serif}`
  ctx.fillText(signature.value, W / 2, 430, W - 220)
  if (birthLine.value) {
    ctx.fillStyle = 'rgba(226, 220, 210, 0.7)'
    ctx.font = `34px ${book}`
    ctx.fillText(birthLine.value, W / 2, 500, W - 220)
  }

  const columns = three.value
  columns.forEach((entry, index) => {
    const x = W / 2 + (index - 1) * 300
    ctx.fillStyle = '#f0cd8a'
    ctx.font = entry.id === 'asc' ? `600 50px ${caps}` : `64px ${SYMBOLS}`
    ctx.fillText(entry.id === 'asc' ? 'Asc' : entry.glyph, x, 680)
    ctx.fillStyle = 'rgba(226, 220, 210, 0.66)'
    ctx.font = `600 34px ${caps}`
    ctx.fillText(entry.name.toLowerCase(), x, 740)
    ctx.fillStyle = '#f6efe2'
    ctx.font = `italic 56px ${serif}`
    ctx.fillText(entry.info ? entry.info.name : '—', x, 810, 280)
  })

  ctx.strokeStyle = 'rgba(240, 205, 138, 0.3)'
  ctx.beginPath()
  ctx.moveTo(W / 2 - 220, 900)
  ctx.lineTo(W / 2 + 220, 900)
  ctx.stroke()

  if (element.value) {
    ctx.fillStyle = 'rgba(226, 220, 210, 0.66)'
    ctx.font = `600 34px ${caps}`
    ctx.fillText('ведущая стихия', W / 2, 980)
    ctx.fillStyle = '#f0cd8a'
    ctx.font = `italic 600 84px ${serif}`
    ctx.fillText(element.value.name, W / 2, 1075)
    ctx.fillStyle = 'rgba(239, 231, 216, 0.82)'
    ctx.font = `italic 40px ${serif}`
    ctx.fillText(element.value.line, W / 2, 1135, W - 220)
  }

  ctx.fillStyle = 'rgba(240, 205, 138, 0.7)'
  ctx.font = `600 32px ${caps}`
  ctx.fillText((config.value?.site_name || fallbackConfig.site_name).toLowerCase(), W / 2, H - 120)

  return finishPicture(canvas)
}

const fileName = () => `zvezdnyj-pasport.png`

async function save() {
  if (busy.value) return
  busy.value = true
  try {
    const blob = await draw()
    if (blob) downloadPicture(blob, fileName())
  } finally {
    busy.value = false
  }
}

async function share() {
  if (busy.value) return
  busy.value = true
  try {
    const blob = await draw()
    const text = `${signature.value}: ${three.value.filter((entry) => entry.info).map((entry) => `${entry.name} ${entry.info.in}`).join(', ')}`
    if (blob) await sharePicture(blob, fileName(), 'Звёздный паспорт', text)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section class="passport" aria-labelledby="passport-title">
    <p id="passport-title" class="passport-kicker">
      <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg>
      Звёздный паспорт
    </p>
    <p v-if="birthLine" class="passport-birth">
      {{ birthLine }}
      <RouterLink class="edit" :to="{ name: 'cabinet-birth' }" aria-label="Изменить данные рождения">изменить</RouterLink>
    </p>

    <div class="three">
      <RouterLink
        v-for="entry in three"
        :key="entry.id"
        class="three-item"
        :class="{ 'is-off': !entry.info }"
        :to="entry.info ? { name: 'cabinet-chart', params: { item: entry.id } } : { name: 'cabinet-birth' }"
        :aria-label="entry.info ? `${entry.name} ${entry.info.in}` : `${entry.name}: нужно ${entry.id === 'asc' ? 'время и город' : 'дата'} рождения`"
      >
        <span class="three-glyph" aria-hidden="true">{{ entry.glyph }}</span>
        <span class="three-name" aria-hidden="true">{{ entry.name }}</span>
        <span class="three-sign" aria-hidden="true">{{ entry.info ? entry.info.name : 'нужно время' }}</span>
      </RouterLink>
    </div>

    <p v-if="element" class="element">
      Ведущая стихия — <em>{{ element.name }}</em>: {{ element.line }}.
    </p>

    <div v-if="user.birth" class="passport-actions">
      <button type="button" class="soft" :disabled="busy" @click="save">
        <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 2.5v8M4.5 7L8 10.5L11.5 7M3 13.5h10" /></svg>
        Сохранить картинкой
      </button>
      <button v-if="canShare" type="button" class="soft" :disabled="busy" @click="share">
        <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 10V2.5M5 5.5L8 2.5L11 5.5M3.5 8.5v5h9v-5" /></svg>
        Поделиться
      </button>
    </div>
  </section>
</template>

<style scoped>
/* A page within the page: a double gold rule, as in the picture it saves. */
.passport {
  position: relative;
  display: grid;
  gap: 12px;
  padding: 16px 16px 14px;
  border: 1px solid rgba(240, 205, 138, 0.32);
  border-radius: 4px;
  outline: 1px solid rgba(240, 205, 138, 0.12);
  outline-offset: -6px;
  background: radial-gradient(120% 90% at 50% 0%, rgba(240, 205, 138, 0.07), transparent 70%);
}
.passport-kicker {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-family: var(--caps);
  font-weight: 600;
  font-size: 15px;
  letter-spacing: 0.14em;
  color: rgba(240, 205, 138, 0.85);
}
.passport-kicker svg { width: 10px; height: 10px; fill: #f0cd8a; filter: drop-shadow(0 0 5px rgba(255, 200, 110, 0.8)); }
.passport-birth { margin: -6px 0 0; text-align: center; font-family: var(--book); font-size: 13.5px; color: rgba(226, 220, 210, 0.7); }

.three { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }
.three-item {
  display: grid;
  justify-items: center;
  gap: 2px;
  padding: 6px 2px;
  border-radius: 10px;
  color: #efe7d8;
  text-decoration: none;
  transition: background 0.25s ease;
}
.three-item:hover { background: rgba(240, 205, 138, 0.06); }
.three-item:hover .three-sign { color: #f0cd8a; }
.three-item:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 2px; }
.three-item.is-off { opacity: 0.5; }
.three-glyph { font-family: 'Segoe UI Symbol', 'Noto Sans Symbols', sans-serif; font-size: 18px; line-height: 1.2; color: #f0cd8a; }
.three-name { font-family: var(--caps); font-size: 13.5px; letter-spacing: 0.1em; color: rgba(226, 220, 210, 0.62); }
.three-sign { font-family: var(--serif); font-style: italic; font-size: 21px; line-height: 1.1; color: #f6efe2; transition: color 0.25s ease; }

.element { margin: 0; padding-top: 10px; border-top: 1px solid rgba(240, 210, 150, 0.12); text-align: center; font-family: var(--book); font-size: 14px; line-height: 1.5; color: rgba(239, 231, 216, 0.85); }
.element em { font-family: var(--serif); font-size: 18px; color: #f0cd8a; }

.passport-actions { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; }
.soft {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 7px 14px;
  border-radius: 999px;
  border: 1px solid rgba(240, 210, 150, 0.26);
  background: rgba(255, 240, 210, 0.04);
  font: inherit;
  font-size: 12.5px;
  color: #efe7d8;
  cursor: pointer;
  transition: border-color 0.25s ease, color 0.25s ease, background 0.25s ease;
}
.soft svg { width: 13px; height: 13px; fill: none; stroke: currentColor; stroke-width: 1.4; stroke-linecap: round; stroke-linejoin: round; }
.soft:hover:not(:disabled) { border-color: rgba(240, 205, 138, 0.6); background: rgba(255, 240, 210, 0.08); color: #f0cd8a; }
.soft:disabled { opacity: 0.6; cursor: progress; }
.soft:focus-visible { outline: 2px solid #f0cd8a; outline-offset: 3px; }

.edit {
  margin-left: 6px;
  font-size: 12.5px;
  color: #f0cd8a;
  text-decoration: underline;
  text-decoration-color: rgba(240, 205, 138, 0.35);
  text-underline-offset: 3px;
}
.edit:hover { text-decoration-color: currentColor; }
.edit:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 2px; border-radius: 4px; }

@media (max-width: 760px) {
  .soft { min-height: 44px; }
  .edit { padding-block: 12px; margin-block: -6px; }
}
</style>
