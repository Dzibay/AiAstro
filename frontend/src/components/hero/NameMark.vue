<script setup>
import { computed } from 'vue'
import { useSky } from '../../composables/useSky.js'
import { SIGNS } from '../../utils/skyToday.js'
import { PROJECTED, ZODIAC_BY_ID } from './zodiac.js'
import { ZODIAC_ART } from './zodiacArt.js'
import { clamp } from './sky.js'
import { starRadius } from './journey.js'

/**
 * The person's own mark on the login sky (see useSky().mark): a star that lights up with their
 * name and the engraving of their Sun sign around it. Placed in the free sky beside the card.
 */

const props = defineProps({
  geo: { type: Object, required: true },
  /** 'login' places the star by the name; 'cabinet' brings it close, left of the panel, and leaves the words to the panel. */
  pose: { type: String, default: 'login' },
})
const { mark } = useSky()

const SIGN_BY_ID = Object.fromEntries(SIGNS.map((sign) => [sign.id, sign]))

/** FNV-1a: the same name always finds the same point of the sky. */
function hash(text) {
  let h = 0x811c9dc5
  for (const char of text) {
    h ^= char.codePointAt(0)
    h = Math.imul(h, 0x01000193)
  }
  return h >>> 0
}

const name = computed(() => mark.name.trim())
const shown = computed(() => Boolean(name.value || mark.sun))

/**
 * Where the star stands and how large its sign is drawn. While the name is typed the star
 * keeps the place of the first letter; once the name is set (mark.place) it glides to its own.
 * In the cabinet the camera comes close: the same drawing, moved and scaled by `k`, so the
 * pose change reads as a flight onto the star.
 */
const spot = computed(() => {
  const { W, H, narrow } = props.geo
  const key = (mark.place || name.value.slice(0, 1)).toLocaleLowerCase('ru')
  const h = hash(key)
  const a = (h & 0xffff) / 0xffff
  const b = (h >>> 16) / 0xffff
  let span
  let x0
  let x1
  let y0
  let y1
  if (narrow) {
    // Phones: the strip of sky above the sheet.
    span = Math.min(W * 0.44, 170)
    x0 = W * 0.1 + span / 2
    x1 = W * 0.72 - span / 2
    y0 = 70 + span / 2
    y1 = Math.max(y0, H * 0.34 - 40 - span / 2)
  } else {
    // Between the orbit's left half and the card, which hugs the right edge.
    span = clamp(H * 0.4, 220, 330)
    const cardLeft = W - clamp(W * 0.08, 20, 150) - 392
    x0 = W * 0.3 + span / 2
    x1 = Math.max(x0, cardLeft - 40 - span / 2)
    y0 = 96 + span / 2
    y1 = Math.max(y0, H * 0.62 - span / 2)
  }
  if (props.pose === 'cabinet') {
    if (narrow) {
      const k = 1.3
      return { x: W * 0.5, y: 76 + (span * k) / 2, span, k }
    }
    const k = clamp((H * 0.52) / span, 1.15, 1.6)
    const panelLeft = W - clamp(W * 0.08, 20, 150) - 420
    return { x: clamp(W * 0.3, (span * k) / 2 + 24, panelLeft - (span * k) / 2 - 40), y: clamp(H * 0.4, 90 + (span * k) / 2, H), span, k }
  }
  return { x: x0 + (x1 - x0) * a, y: y0 + (y1 - y0) * b, span, k: 1 }
})

/** The star grows with every letter, up to a bright one. */
const radius = computed(() => 1.8 + Math.min([...name.value].length, 14) * 0.3)

const sun = computed(() => SIGN_BY_ID[mark.sun] || null)
const moon = computed(() => SIGN_BY_ID[mark.moon] || null)

/** The sign drawn around the star, in the star's own coordinates. */
const sign = computed(() => {
  const id = mark.sun
  const figure = ZODIAC_BY_ID[id]
  if (!figure) return null
  const span = spot.value.span
  const map = ([x, y]) => `${((x / 1000 - 0.5) * span).toFixed(1)} ${((y / 1000 - 0.5) * span).toFixed(1)}`
  const stars = PROJECTED[id].map((p, index) => ({
    x: p.x * span,
    y: p.y * span,
    r: starRadius(figure.stars[index].mag) * 0.8,
  }))
  return {
    id,
    art: (ZODIAC_ART[id] || []).map((stroke, index) => ({ index, kind: stroke.kind, d: `M${stroke.pts.map(map).join('L')}` })),
    lines: figure.edges.map(([i, j]) => ({ key: `${i}-${j}`, a: stars[i], b: stars[j] })),
    stars,
  }
})

// U+FE0E keeps the sign a glyph instead of a coloured emoji on Windows.
const glyph = computed(() => (sun.value ? `${sun.value.glyph}\uFE0E` : ''))

const caption = computed(() => {
  if (!sun.value) return ''
  return moon.value ? `Солнце ${sun.value.in} · Луна ${moon.value.in}` : `Солнце ${sun.value.in}`
})
</script>

<template>
  <svg v-if="shown" class="name-mark" :class="`is-${pose}`" :viewBox="`0 0 ${geo.W} ${geo.H}`" aria-hidden="true">
    <defs>
      <radialGradient id="mark-halo">
        <stop offset="0" stop-color="#fff1cf" stop-opacity="0.9" />
        <stop offset="0.25" stop-color="#ffd58a" stop-opacity="0.35" />
        <stop offset="1" stop-color="#ffc56e" stop-opacity="0" />
      </radialGradient>
      <filter id="mark-glow" x="-10%" y="-10%" width="120%" height="120%">
        <feGaussianBlur stdDeviation="2.2" result="b" />
        <feColorMatrix in="b" type="matrix" values="1 0 0 0 0  0 0.8 0 0 0  0 0 0.45 0 0  0 0 0 0.9 0" result="g" />
        <feMerge><feMergeNode in="g" /><feMergeNode in="SourceGraphic" /></feMerge>
      </filter>
    </defs>

    <g class="mark" :style="{ transform: `translate(${spot.x.toFixed(1)}px, ${spot.y.toFixed(1)}px) scale(${spot.k.toFixed(3)})` }">
      <Transition name="sign">
        <g v-if="sign" :key="sign.id" class="sign">
          <g class="sign-art" filter="url(#mark-glow)">
            <path
              v-for="stroke in sign.art"
              :key="stroke.index"
              :class="`art-${stroke.kind}`"
              :d="stroke.d"
              pathLength="1"
              :style="{ '--i': stroke.index / Math.max(1, sign.art.length - 1) }"
            />
          </g>
          <g class="sign-lines">
            <line v-for="line in sign.lines" :key="line.key" :x1="line.a.x" :y1="line.a.y" :x2="line.b.x" :y2="line.b.y" />
          </g>
          <circle v-for="(star, index) in sign.stars" :key="index" class="sign-star" :cx="star.x" :cy="star.y" :r="star.r" />
          <text v-if="pose !== 'cabinet'" class="sign-caption" x="0" :y="spot.span / 2 + 30" text-anchor="middle">
            <tspan class="sign-glyph">{{ glyph }}</tspan>
            <tspan dx="8">{{ caption }}</tspan>
          </text>
        </g>
      </Transition>

      <g v-if="name" class="star">
        <circle class="star-halo" :r="radius * 7" fill="url(#mark-halo)" />
        <path class="star-spike" :d="`M0 ${-radius * 6}Q${radius * 0.5} ${-radius * 0.5} ${radius * 6} 0Q${radius * 0.5} ${radius * 0.5} 0 ${radius * 6}Q${-radius * 0.5} ${radius * 0.5} ${-radius * 6} 0Q${-radius * 0.5} ${-radius * 0.5} 0 ${-radius * 6}Z`" />
        <circle class="star-core" :r="radius" />
        <circle v-if="mark.flash" :key="mark.flash" class="star-flash" :r="radius * 3" />
        <text class="star-name" :x="radius * 3 + 10" y="5">{{ name }}</text>
      </g>
    </g>
  </svg>
</template>

<style scoped>
.name-mark {
  position: absolute;
  z-index: 2;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: visible;
  pointer-events: none;
  animation: mark-in 1s ease 0.6s both;
}

.mark { transition: transform 1.1s cubic-bezier(0.3, 0.7, 0.2, 1); }
/* The flight between poses: as long as the sky's own (SkyStage FLIGHT_MS) and on the same curve. */
.name-mark.is-cabinet .mark { transition: transform 1.4s cubic-bezier(0.65, 0, 0.35, 1); }

.star-halo { animation: star-breathe 4s ease-in-out infinite; transform-origin: 0 0; }
.star-spike { fill: rgba(255, 236, 196, 0.55); animation: star-breathe 4s ease-in-out infinite; transform-origin: 0 0; }
.star-core { fill: #fff8e6; filter: drop-shadow(0 0 4px #ffd58a); transition: r 0.35s ease; }
.star-flash {
  fill: none;
  stroke: #ffe2a8;
  stroke-width: 1.2;
  transform-origin: 0 0;
  animation: star-flash 1.2s cubic-bezier(0.2, 0.7, 0.2, 1) forwards;
}
.star-name {
  font-family: var(--serif);
  font-style: italic;
  font-size: 20px;
  fill: #f3dcae;
  paint-order: stroke;
  stroke: rgba(4, 6, 12, 0.55);
  stroke-width: 4px;
  animation: name-in 0.6s ease both;
}

.sign-art path {
  fill: none;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-dasharray: 1;
  stroke-dashoffset: 1;
  animation: art-draw 1.8s cubic-bezier(0.4, 0.1, 0.2, 1) calc(var(--i) * 0.9s) forwards;
}
.art-outline { stroke: #f0cf8e; stroke-width: 1.15; opacity: 0.8; }
.art-detail { stroke: #e6c17e; stroke-width: 0.8; opacity: 0.55; }
.art-hatch { stroke: #d8b274; stroke-width: 0.6; opacity: 0.35; }
.sign-lines line { stroke: #e3cfa6; stroke-width: 0.8; stroke-linecap: round; opacity: 0.35; }
.sign-star { fill: #fff3da; filter: drop-shadow(0 0 3px rgba(255, 214, 140, 0.9)); }
.sign-caption {
  font-family: var(--serif);
  font-style: italic;
  font-size: 18px;
  fill: rgba(242, 228, 200, 0.9);
  paint-order: stroke;
  stroke: rgba(4, 6, 12, 0.6);
  stroke-width: 4px;
  animation: name-in 0.8s ease 0.9s both;
}
.sign-glyph { font-family: 'Segoe UI Symbol', 'Noto Sans Symbols', sans-serif; font-style: normal; fill: #ffd998; }

.sign-enter-active { transition: opacity 0.6s ease; }
.sign-leave-active { transition: opacity 0.4s ease; }
.sign-enter-from, .sign-leave-to { opacity: 0; }

@keyframes mark-in { from { opacity: 0; } }
@keyframes name-in { from { opacity: 0; } }
@keyframes art-draw { to { stroke-dashoffset: 0; } }
@keyframes star-breathe { 50% { transform: scale(0.86); opacity: 0.8; } }
@keyframes star-flash {
  from { transform: scale(0.4); opacity: 1; }
  to { transform: scale(4); opacity: 0; }
}

@media (max-width: 760px) {
  .star-name { font-size: 17px; }
  .sign-caption { font-size: 15px; }
}

@media (prefers-reduced-motion: reduce) {
  .name-mark, .star-halo, .star-spike, .star-flash, .star-name, .sign-caption { animation: none; }
  .star-flash { display: none; }
  .sign-art path { animation: none; stroke-dashoffset: 0; }
  .mark { transition: none; }
}
</style>
