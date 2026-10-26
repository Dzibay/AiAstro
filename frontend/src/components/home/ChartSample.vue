<script setup>
import { ref } from 'vue'
import { ASPECTS, POINTS, SIGN_BY_ID, SIGN_LIST } from '../cabinet/astro.js'

/**
 * A sample of the free chart on the home page: a small wheel engraved in gold and the reading of
 * the planet picked on it. The words are the product's own (backend app/astro/natal_signs.py), so
 * the visitor reads what the cabinet will say about their own sky.
 */

// A made-up sky, plausible enough together: Mercury and Venus keep near the Sun.
const ASC = 155
const SKY = [
  { id: 'sun', lon: 142 },
  { id: 'moon', lon: 352 },
  { id: 'mercury', lon: 158 },
  { id: 'venus', lon: 182 },
  { id: 'mars', lon: 22 },
  { id: 'jupiter', lon: 215 },
  { id: 'pluto', lon: 240 },
  { id: 'uranus', lon: 293 },
  { id: 'saturn', lon: 336 },
]

/** The planets you can read here: { essence, text } as the cabinet shows them. */
const READINGS = {
  sun: {
    essence: 'Вы рождены светить: щедрое сердце и право быть собой',
    text: 'Солнце во Льве — в собственном знаке, и жизненная сила звучит здесь в полный голос: тепло, творчески, '
      + 'с достоинством. Вы раскрываетесь, когда можете создавать, вдохновлять и видеть, что ваш свет кому-то нужен. '
      + 'Ваш рост — в свете, которому не нужно разрешение: творите прежде всего для радости.',
  },
  moon: {
    essence: 'Чувства тонки и безбрежны: вы чувствуете мир как себя',
    text: 'Луна в Рыбах дарит глубокое сострадание и интуицию: вы чувствуете настроение других, как своё. '
      + 'Вас успокаивают музыка, вода, тишина, творчество и возможность побыть наедине с собой. '
      + 'Ваш рост — в бережных границах и времени уединения: так ваша чуткость наполняется.',
  },
  venus: {
    essence: 'Любовь гармоничная и изящная: вы созданы для союза',
    text: 'Венера в Весах — в собственном знаке: любовь здесь учтива, романтична и стремится к равному партнёрству. '
      + 'У вас тонкий вкус, вы умеете создавать красоту и атмосферу, в которой людям хорошо вместе. '
      + 'Ваш рост — в гармонии, которая включает и ваши желания.',
  },
  mars: {
    essence: 'Энергия прямая и неудержимая: вы идёте напролом',
    text: 'Марс в Овне — в собственном знаке: энергия здесь чистая, быстрая, смелая. Вы инициативны, легко берётесь '
      + 'за смелые задачи, умеете постоять за себя и других. Ваш рост — в выдержке: направляйте огонь в дела, '
      + 'где нужна скорость, и он приведёт к цели.',
  },
}
const READABLE = Object.keys(READINGS)

const R = { outer: 104, signs: 88, houses: 79, planets: 65, aspects: 52 }
const RAD = Math.PI / 180
const fixed = (n) => n.toFixed(1)
// The Ascendant lies on the left, as on a paper chart and in the cabinet's wheel.
function at(lon, radius) {
  const angle = (180 + lon - ASC) * RAD
  return [radius * Math.cos(angle), -radius * Math.sin(angle)]
}
function segment(lon, from, to) {
  const [x1, y1] = at(lon, from)
  const [x2, y2] = at(lon, to)
  return `M${fixed(x1)} ${fixed(y1)}L${fixed(x2)} ${fixed(y2)}`
}

const signTicks = SIGN_LIST.map((_, index) => segment(index * 30, R.signs, R.outer)).join('')
const signGlyphs = SIGN_LIST.map((sign, index) => {
  const [x, y] = at(index * 30 + 15, (R.signs + R.outer) / 2)
  return { id: sign.id, glyph: sign.glyph, x: fixed(x), y: fixed(y) }
})
// Equal houses from the Ascendant: enough for a picture. The four angles are drawn bolder.
const houseLines = Array.from({ length: 12 }, (_, index) => index)
  .filter((index) => index % 3)
  .map((index) => segment(ASC + index * 30, R.aspects, R.houses))
  .join('')
const angleLines = [0, 90, 180, 270].map((turn) => segment(ASC + turn, R.aspects, R.outer)).join('')

const planets = SKY.map((point) => {
  const [x, y] = at(point.lon, R.planets)
  const [dx, dy] = at(point.lon, R.houses + 4)
  return {
    ...point,
    glyph: POINTS[point.id].glyph,
    x: fixed(x),
    y: fixed(y),
    dx: fixed(dx),
    dy: fixed(dy),
    readable: READABLE.includes(point.id),
  }
})

const ANGLES = [['sextile', 60], ['square', 90], ['trine', 120], ['opposition', 180]]
const ORB = 7
const aspects = []
SKY.forEach((one, index) => {
  SKY.slice(index + 1).forEach((other) => {
    let gap = Math.abs(one.lon - other.lon) % 360
    if (gap > 180) gap = 360 - gap
    const hit = ANGLES.find(([, angle]) => Math.abs(gap - angle) <= ORB)
    if (!hit) return
    const [x1, y1] = at(one.lon, R.aspects)
    const [x2, y2] = at(other.lon, R.aspects)
    aspects.push({
      key: `${one.id}-${other.id}`,
      ids: [one.id, other.id],
      tone: ASPECTS[hit[0]].tone,
      d: `M${fixed(x1)} ${fixed(y1)}L${fixed(x2)} ${fixed(y2)}`,
    })
  })
})

const signOf = (id) => SIGN_LIST[Math.floor(SKY.find((point) => point.id === id).lon / 30)].id
const title = (id) => `${POINTS[id].name} ${SIGN_BY_ID[signOf(id)].in}`

const picked = ref('sun')
function pick(id) {
  picked.value = id
}
</script>

<template>
  <div class="chart-sample">
    <div class="sample-top">
      <span class="sample-kicker">Пример карты</span>
      <div class="sample-chips" role="group" aria-label="Планета для разбора">
        <button
          v-for="id in READABLE"
          :key="id"
          type="button"
          :aria-pressed="picked === id"
          :data-track="`how:sample-${id}`"
          @click="pick(id)"
        >
          <span class="chip-glyph" aria-hidden="true">{{ POINTS[id].glyph }}</span>
          {{ POINTS[id].name }}
        </button>
      </div>
    </div>

    <div class="sample-body">
      <svg class="wheel" viewBox="-112 -112 224 224" role="img" aria-label="Натальная карта: знаки, дома, планеты и аспекты">
        <circle class="ring" r="104" pathLength="1" />
        <circle class="ring" r="88" pathLength="1" />
        <circle class="ring is-thin" r="79" pathLength="1" />
        <circle class="ring is-thin" r="52" pathLength="1" />
        <path class="ticks" :d="signTicks" />
        <text v-for="sign in signGlyphs" :key="sign.id" class="sign-glyph" :x="sign.x" :y="sign.y">{{ sign.glyph }}</text>
        <path class="houses" :d="houseLines" />
        <path class="angles" :d="angleLines" />
        <path
          v-for="aspect in aspects"
          :key="aspect.key"
          class="aspect"
          :class="[`is-${aspect.tone}`, { 'is-on': aspect.ids.includes(picked) }]"
          :d="aspect.d"
        />
        <g
          v-for="planet in planets"
          :key="planet.id"
          class="planet"
          :class="{ 'is-readable': planet.readable, 'is-picked': planet.id === picked }"
          @click="planet.readable && pick(planet.id)"
        >
          <circle class="planet-dot" :cx="planet.dx" :cy="planet.dy" r="1.5" />
          <circle class="planet-halo" :cx="planet.x" :cy="planet.y" r="9" />
          <text :x="planet.x" :y="planet.y">{{ planet.glyph }}</text>
        </g>
      </svg>

      <!-- Every reading stands in one cell, so the card keeps the height of the longest. -->
      <div class="sample-texts" aria-live="polite">
        <div
          v-for="id in READABLE"
          :key="id"
          class="sample-text"
          :class="{ 'is-picked': picked === id }"
          :aria-hidden="picked !== id"
        >
          <p class="sample-place">{{ title(id) }}</p>
          <p class="sample-essence">{{ READINGS[id].essence }}</p>
          <p class="sample-reading">{{ READINGS[id].text }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chart-sample {
  padding: 16px 20px 20px;
  border-radius: 20px;
  border: 1px solid rgba(240, 210, 150, 0.22);
  background: linear-gradient(160deg, rgba(26, 23, 26, 0.58), rgba(8, 10, 18, 0.7));
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.38), inset 0 1px 0 rgba(255, 240, 210, 0.07);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

.sample-top {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px 14px;
  margin-bottom: 16px;
}
.sample-kicker { font-size: 11px; letter-spacing: 0.24em; text-transform: uppercase; color: rgba(226, 214, 192, 0.72); }
.sample-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.sample-chips button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 13px 6px 11px;
  border-radius: 999px;
  border: 1px solid rgba(240, 210, 150, 0.26);
  background: rgba(255, 240, 210, 0.04);
  font: inherit;
  font-size: 13.5px;
  line-height: 1;
  color: rgba(240, 234, 222, 0.86);
  cursor: pointer;
  transition: background 0.25s ease, color 0.25s ease, border-color 0.25s ease;
}
.sample-chips button:hover { border-color: rgba(240, 205, 138, 0.6); }
.sample-chips button[aria-pressed='true'] {
  border-color: transparent;
  background: linear-gradient(180deg, #f4dba6, #dcb36c);
  color: #2b1d0b;
}
.sample-chips button:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 2px; }
.chip-glyph { font-family: 'Segoe UI Symbol', 'Noto Sans Symbols', sans-serif; font-size: 13px; }

.sample-body { display: grid; grid-template-columns: 200px minmax(0, 1fr); align-items: start; gap: 22px; }

/* The wheel draws itself when the sky arrives at the stop, as the cabinet's wheel does. */
.wheel { display: block; width: 100%; height: auto; overflow: visible; }
.ring { fill: none; stroke: rgba(240, 205, 138, 0.6); stroke-width: 0.8; stroke-dasharray: 1; stroke-dashoffset: 1; }
.ring.is-thin { stroke: rgba(240, 205, 138, 0.3); stroke-width: 0.6; }
.ring { transition: stroke-dashoffset 1.4s cubic-bezier(0.3, 0.6, 0.2, 1) 0.3s; }
.is-here .ring { stroke-dashoffset: 0; }
.ticks { stroke: rgba(240, 205, 138, 0.45); stroke-width: 0.6; }
.houses { stroke: rgba(240, 205, 138, 0.2); stroke-width: 0.5; }
.angles { stroke: rgba(240, 205, 138, 0.62); stroke-width: 0.9; }
.sign-glyph,
.planet text {
  font-family: 'Segoe UI Symbol', 'Noto Sans Symbols', sans-serif;
  text-anchor: middle;
  dominant-baseline: central;
}
.sign-glyph { font-size: 10px; fill: rgba(240, 205, 138, 0.85); }

.aspect { fill: none; stroke-width: 0.7; opacity: 0.4; transition: opacity 0.3s ease, stroke-width 0.3s ease; }
.aspect.is-easy { stroke: #e9c47e; }
.aspect.is-tense { stroke: #d39a8e; }
.aspect.is-on { opacity: 1; stroke-width: 1.1; }

.planet text { font-size: 12.5px; fill: rgba(239, 230, 214, 0.75); transition: fill 0.3s ease; }
.planet-dot { fill: rgba(240, 205, 138, 0.8); }
.planet-halo { fill: rgba(255, 210, 126, 0.12); stroke: rgba(255, 210, 126, 0.55); stroke-width: 0.6; opacity: 0; transition: opacity 0.3s ease; }
.planet.is-readable { cursor: pointer; }
.planet.is-readable text { fill: #f6efe2; }
.planet.is-readable:hover .planet-halo { opacity: 0.6; }
.planet.is-picked .planet-halo { opacity: 1; }
.planet.is-picked text { fill: #ffe2a8; }

.sample-texts { display: grid; }
.sample-text {
  grid-area: 1 / 1;
  opacity: 0;
  visibility: hidden;
  transform: translateY(6px);
  transition: opacity 0.3s ease, transform 0.3s ease, visibility 0s linear 0.3s;
}
.sample-text.is-picked {
  opacity: 1;
  visibility: visible;
  transform: none;
  transition: opacity 0.35s ease 0.08s, transform 0.35s ease 0.08s, visibility 0s;
}
.sample-text p { margin: 0; }
.sample-place { font-size: 11px; letter-spacing: 0.2em; text-transform: uppercase; color: #f0cd8a; }
.sample-essence { margin-top: 6px !important; font-family: var(--serif); font-size: 21px; line-height: 1.2; color: #f6efe2; }
.sample-reading { margin-top: 10px !important; font-size: 14.5px; line-height: 1.6; color: rgba(236, 228, 214, 0.86); }

@media (max-width: 560px) {
  .chart-sample { padding: 14px 16px 18px; }
  .sample-top { justify-content: center; }
  .sample-kicker { width: 100%; text-align: center; }
  /* All four planets in one row down to the narrowest phones. */
  .sample-chips { justify-content: center; gap: 5px; }
  .sample-chips button { gap: 5px; padding: 6px 10px 6px 9px; font-size: 13px; }
  .sample-body { grid-template-columns: minmax(0, 1fr); gap: 16px; }
  .wheel { width: min(210px, 68%); margin: 0 auto; }
  .sample-essence { font-size: 20px; }
}
@media (max-width: 380px) {
  .chart-sample { padding-left: 12px; padding-right: 12px; }
  .sample-chips { gap: 4px; }
  .sample-chips button { gap: 4px; padding: 6px 8px 6px 7px; }
}

@media (prefers-reduced-motion: reduce) {
  .ring, .sample-text, .sample-text.is-picked { transition: none; }
}
</style>
