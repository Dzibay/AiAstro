<script setup>
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { useChart } from '../../composables/useChart.js'
import { useSky } from '../../composables/useSky.js'
import { useSiteConfig, fallbackConfig } from '../../composables/useSiteConfig.js'
import { chartItems, SIGN_BY_ID } from '../cabinet/astro.js'
import { formatDate } from '../../utils/format.js'

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
  if (counts) {
    const best = Object.entries(counts).sort((a, b) => b[1] - a[1])[0]
    if (best && best[1] > 0) return { id: best[0], ...ELEMENTS[best[0]] }
  }
  const sun = SIGN_IDS.indexOf(mark.sun)
  return sun >= 0 ? { id: ELEMENT_OF[sun % 4], ...ELEMENTS[ELEMENT_OF[sun % 4]] } : null
})

const birthLine = computed(() => {
  const birth = props.user.birth
  if (!birth) return ''
  return [formatDate(birth.date), birth.time, birth.place].filter(Boolean).join(' · ')
})

/* ---- The picture ---- */

const busy = ref(false)
const canShare = typeof navigator !== 'undefined' && typeof navigator.share === 'function'

const cssFont = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim() || 'Georgia, serif'

async function draw() {
  await document.fonts?.ready
  const W = 1080
  const H = 1350
  const canvas = document.createElement('canvas')
  canvas.width = W
  canvas.height = H
  const ctx = canvas.getContext('2d')
  const caps = cssFont('--caps')
  const serif = cssFont('--serif')
  const book = cssFont('--book')

  const sky = ctx.createRadialGradient(W / 2, H * 0.32, 60, W / 2, H * 0.45, H * 0.85)
  sky.addColorStop(0, '#2a2140')
  sky.addColorStop(0.55, '#120f22')
  sky.addColorStop(1, '#06050c')
  ctx.fillStyle = sky
  ctx.fillRect(0, 0, W, H)

  let seed = [...props.user.name].reduce((sum, char) => sum + char.charCodeAt(0), 11)
  const random = () => {
    seed = (seed * 16807) % 2147483647
    return seed / 2147483647
  }
  for (let index = 0; index < 260; index += 1) {
    ctx.globalAlpha = 0.2 + random() * 0.7
    ctx.fillStyle = random() > 0.85 ? '#ffe4a8' : '#efe7d8'
    ctx.beginPath()
    ctx.arc(random() * W, random() * H, 0.6 + random() * 1.8, 0, Math.PI * 2)
    ctx.fill()
  }
  ctx.globalAlpha = 1

  // The folio's frame: a double gold rule.
  ctx.strokeStyle = 'rgba(240, 205, 138, 0.55)'
  ctx.lineWidth = 2
  ctx.strokeRect(60, 60, W - 120, H - 120)
  ctx.strokeStyle = 'rgba(240, 205, 138, 0.25)'
  ctx.strokeRect(76, 76, W - 152, H - 152)

  const star = (x, y, r, color) => {
    ctx.save()
    ctx.translate(x - r, y - r)
    ctx.scale(r / 10, r / 10)
    ctx.fillStyle = color
    ctx.shadowColor = 'rgba(255, 205, 120, 0.9)'
    ctx.shadowBlur = 24
    ctx.fill(new Path2D('M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z'))
    ctx.restore()
  }

  ctx.textAlign = 'center'
  ctx.textBaseline = 'alphabetic'
  ctx.fillStyle = 'rgba(240, 205, 138, 0.85)'
  ctx.font = `600 40px ${caps}`
  ctx.fillText('звёздный паспорт', W / 2, 190)
  star(W / 2, 270, 34, '#fff3d6')

  ctx.fillStyle = '#f6efe2'
  ctx.font = `italic 500 104px ${serif}`
  ctx.fillText(props.user.name, W / 2, 430, W - 220)
  if (birthLine.value) {
    ctx.fillStyle = 'rgba(226, 220, 210, 0.7)'
    ctx.font = `34px ${book}`
    ctx.fillText(birthLine.value, W / 2, 500, W - 220)
  }

  const columns = three.value
  columns.forEach((entry, index) => {
    const x = W / 2 + (index - 1) * 300
    ctx.fillStyle = '#f0cd8a'
    ctx.font = entry.id === 'asc' ? `600 50px ${caps}` : `64px 'Segoe UI Symbol', 'Noto Sans Symbols', sans-serif`
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

  return new Promise((resolve) => canvas.toBlob(resolve, 'image/png'))
}

const fileName = () => `zvezdnyj-pasport.png`

async function save() {
  if (busy.value) return
  busy.value = true
  try {
    const blob = await draw()
    if (!blob) return
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = fileName()
    link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  } finally {
    busy.value = false
  }
}

async function share() {
  if (busy.value) return
  busy.value = true
  try {
    const blob = await draw()
    if (!blob) return
    const file = new File([blob], fileName(), { type: 'image/png' })
    const data = { files: [file], title: 'Звёздный паспорт' }
    if (navigator.canShare?.(data)) await navigator.share(data)
    else await navigator.share({ title: 'Звёздный паспорт', text: `${props.user.name}: ${three.value.filter((entry) => entry.info).map((entry) => `${entry.name} ${entry.info.in}`).join(', ')}` })
  } catch {
    // The person closed the share sheet: nothing to say.
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
