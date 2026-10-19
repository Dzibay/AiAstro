<script setup>
import { computed, onMounted, ref } from 'vue'
import { useSky } from '../../composables/useSky.js'
import { birthSigns } from '../../utils/skyToday.js'
import { clamp } from '../hero/sky.js'
import { signFigure } from '../hero/signFigure.js'
import { ASPECTS, POINTS, SIGN_BY_ID } from './astro.js'
import { cabinetLayout, wheelSpot } from './layout.js'

/**
 * The pair on the sky: the partner's star in the free middle of it, and a thread from the
 * person's own star (NameMark, in the corner) to it. The thread leaves the person's star level
 * and bows over the fan of sections, so it never runs through them.
 *
 * One star while a pair is open or typed in; the whole list of pairs, in an arc, otherwise.
 * A star still waiting for its invitation is a hollow ring on a dotted thread.
 *
 * In the list every star can be pressed to open its pair (`select`), and the pointer over it
 * lights its row in the panel (`hover`). The one open pair wears the engraving of its Sun sign,
 * as the person's own star does.
 */

const props = defineProps({
  /** [{ id, name, date, time, lit, hot, flash }]: `lit` once the birth data are known. */
  stars: { type: Array, default: () => [] },
  /** The tone of the open pair (GET /me/partners/{id}/synastry): the colour of its thread. */
  tone: { type: String, default: '' },
  /** The aspect under the pointer in the panel: its glyphs hang on the thread. */
  aspect: { type: Object, default: null },
  /** Where the person's star is: the cabinet's own (default) or another page's. */
  from: { type: Object, default: null },
  /** The room for the partners' stars, { x, y, r }: the wheel's spot by default. */
  area: { type: Object, default: null },
})

const emit = defineEmits(['select', 'hover'])

const { geo } = useSky()
const reduce = ref(false)
const born = performance.now()
onMounted(() => {
  reduce.value = window.matchMedia('(prefers-reduced-motion: reduce)').matches
})

const fixed = (n) => n.toFixed(1)
const origin = computed(() => props.from || cabinetLayout(geo.value, 'pair').star)
const room = computed(() => props.area || wheelSpot(geo.value))

/**
 * The first stars wait for the person's star to land in the corner (NameMark's flight, 1.4 s);
 * a star typed in later starts at once.
 */
const delays = new Map()
function delayOf(id) {
  if (!delays.has(id)) delays.set(id, Math.max(0, 1.3 - (performance.now() - born) / 1000))
  return delays.get(id)
}

const COLOURS = { easy: '#f0cd8a', tense: '#e08a76', mixed: '#eab48a', calm: '#e6e0f4' }

/** The partner's sign as large as the person's own in a section, but never wider than the free sky. */
const signSpan = computed(() => {
  const { star } = cabinetLayout(geo.value, 'pair')
  return Math.min(star.span * star.k, room.value.r * 1.7)
})

const drawn = computed(() => {
  const { x: cx, y: cy, r } = room.value
  const from = origin.value
  const n = props.stars.length
  const narrow = geo.value.narrow
  return props.stars.map((star, index) => {
    let x = cx
    let y = cy
    if (n > 1) {
      // A gentle arc bowing away from the person's star, top to bottom.
      const t = n === 1 ? 0.5 : index / (n - 1)
      const spread = Math.min(r * 1.5, (narrow ? 34 : 70) * (n - 1))
      y = cy - spread / 2 + spread * t
      x = cx + (narrow ? r * 0.5 : r * 0.35) * Math.sin(Math.PI * t) - (narrow ? r * 0.2 : r * 0.1)
    }
    // Leaves level, above the fan of sections, and comes down onto the star.
    const control = [from.x + (x - from.x) * 0.62, Math.min(from.y, y) - clamp(Math.abs(y - from.y) * 0.25, 20, 70)]
    const mid = [0.25 * from.x + 0.5 * control[0] + 0.25 * x, 0.25 * from.y + 0.5 * control[1] + 0.25 * y]
    const radius = star.lit ? 1.8 + Math.min([...star.name].length, 12) * 0.28 : 3.2
    const signs = star.date ? birthSigns(star.date, star.time) : null
    const sun = signs ? SIGN_BY_ID[signs.sun] : null
    const single = n === 1
    return {
      figure: single && star.lit && signs ? signFigure(signs.sun, signSpan.value) : null,
      ...star,
      x,
      y,
      radius,
      d: `M${fixed(from.x)} ${fixed(from.y)}Q${fixed(control[0])} ${fixed(control[1])} ${fixed(x)} ${fixed(y)}`,
      mid,
      colour: single && props.tone ? COLOURS[props.tone] : '#f3dcae',
      sun: sun ? `${sun.glyph} ${sun.in}` : '',
      delay: delayOf(star.id),
      // In the list only the hovered pair speaks its sign; one pair always does.
      caption: single || star.hot,
      // Long names on a phone would leave the strip: they go under the star.
      below: narrow || x + radius * 3 + 10 + [...star.name].length * 11 > geo.value.W - 12,
    }
  })
})

const label = computed(() => {
  if (!props.aspect || drawn.value.length !== 1) return null
  const [x, y] = drawn.value[0].mid
  return {
    x,
    y: y - 12,
    text: `${POINTS[props.aspect.a].glyph}  ${ASPECTS[props.aspect.type].glyph}  ${POINTS[props.aspect.b].glyph}`,
    tone: ASPECTS[props.aspect.type].tone,
  }
})

const pickable = computed(() => drawn.value.length > 1)
function pick(star) {
  emit('hover', null)
  emit('select', star.id)
}

const aria = computed(() => {
  const names = props.stars.filter((star) => star.name).map((star) => star.name)
  return names.length ? `Ваша звезда и ${names.length === 1 ? 'звезда' : 'звёзды'}: ${names.join(', ')}` : ''
})
</script>

<template>
  <svg
    v-if="drawn.length"
    class="pair-sky"
    :class="{ 'motion-off': reduce }"
    :width="geo.W"
    :height="geo.H"
    :viewBox="`0 0 ${geo.W} ${geo.H}`"
    role="img"
    :aria-label="aria"
  >
    <defs>
      <filter id="pair-sign-glow" x="-10%" y="-10%" width="120%" height="120%">
        <feGaussianBlur stdDeviation="2.2" result="b" />
        <feColorMatrix in="b" type="matrix" values="1 0 0 0 0  0 0.78 0 0 0  0 0 0.6 0 0  0 0 0 0.9 0" result="g" />
        <feMerge><feMergeNode in="g" /><feMergeNode in="SourceGraphic" /></feMerge>
      </filter>
      <radialGradient id="pair-halo">
        <stop offset="0" stop-color="#fff4ee" stop-opacity="0.9" />
        <stop offset="0.25" stop-color="#ffc9b8" stop-opacity="0.32" />
        <stop offset="1" stop-color="#ffb4a0" stop-opacity="0" />
      </radialGradient>
    </defs>

    <g
      v-for="star in drawn"
      :key="star.id"
      class="pair"
      :class="{ 'is-lit': star.lit, 'is-hot': star.hot, 'is-quiet': drawn.length > 1 && !star.hot }"
      :style="{ '--d0': `${star.delay}s`, '--c': star.colour }"
    >
      <path class="thread-glow" :d="star.d" pathLength="1" />
      <path class="thread" :d="star.d" pathLength="1" />

      <g class="partner" :style="{ transform: `translate(${fixed(star.x)}px, ${fixed(star.y)}px)` }">
        <g v-if="star.figure" :key="star.figure.id" class="sign">
          <g class="sign-art" filter="url(#pair-sign-glow)">
            <path
              v-for="stroke in star.figure.art"
              :key="stroke.index"
              :class="`art-${stroke.kind}`"
              :d="stroke.d"
              pathLength="1"
              :style="{ '--i': stroke.index / Math.max(1, star.figure.art.length - 1) }"
            />
          </g>
          <g class="sign-lines">
            <line v-for="line in star.figure.lines" :key="line.key" :x1="line.a.x" :y1="line.a.y" :x2="line.b.x" :y2="line.b.y" />
          </g>
          <circle v-for="(dot, index) in star.figure.stars" :key="index" class="sign-star" :cx="dot.x" :cy="dot.y" :r="dot.r" />
        </g>
        <template v-if="star.lit">
          <circle class="partner-halo" :r="star.radius * 7" fill="url(#pair-halo)" />
          <path
            class="partner-spike"
            :d="`M0 ${-star.radius * 5}Q${star.radius * 0.45} ${-star.radius * 0.45} ${star.radius * 5} 0Q${star.radius * 0.45} ${star.radius * 0.45} 0 ${star.radius * 5}Q${-star.radius * 0.45} ${star.radius * 0.45} ${-star.radius * 5} 0Q${-star.radius * 0.45} ${-star.radius * 0.45} 0 ${-star.radius * 5}Z`"
          />
          <circle class="partner-core" :r="star.radius" />
        </template>
        <circle v-else class="partner-wait" :r="star.radius" />
        <circle v-if="star.flash" class="partner-flash" :r="star.radius * 3" />

        <text
          v-if="star.name"
          class="partner-name"
          :x="star.below ? 0 : star.radius * 3 + 10"
          :y="star.below ? star.radius * 3 + 20 : 5"
          :text-anchor="star.below ? 'middle' : 'start'"
        >{{ star.name }}</text>
        <text
          v-if="star.caption && (star.sun || !star.lit)"
          class="partner-sign"
          :x="star.below ? 0 : star.radius * 3 + 10"
          :y="star.below ? star.radius * 3 + 40 : 26"
          :text-anchor="star.below ? 'middle' : 'start'"
        >{{ star.lit ? star.sun : 'звезда ещё не зажглась' }}</text>

        <g
          v-if="pickable"
          class="partner-hit"
          role="button"
          tabindex="-1"
          :aria-label="`Открыть пару: ${star.name}`"
          @click="pick(star)"
          @pointerenter="emit('hover', star.id)"
          @pointerleave="emit('hover', null)"
        >
          <circle r="26" />
          <rect
            :x="star.below ? -[...star.name].length * 5.5 - 8 : star.radius * 3 + 4"
            :y="star.below ? star.radius * 3 + 2 : -16"
            :width="[...star.name].length * 11 + 16"
            height="28"
          />
        </g>
      </g>
    </g>

    <Transition name="label">
      <text v-if="label" :key="label.text" class="aspect-label" :class="`tone-${label.tone}`" :x="label.x" :y="label.y" text-anchor="middle">
        {{ label.text }}
      </text>
    </Transition>
  </svg>
</template>

<style scoped>
/* On the sky, in its coordinates (as the natal wheel), under the sections and the panel. */
.pair-sky {
  position: fixed;
  z-index: 1;
  top: 0;
  left: 0;
  overflow: visible;
  pointer-events: none;
  animation: show-sky 0.6s ease both;
}

.thread, .thread-glow {
  fill: none;
  stroke: var(--c);
  stroke-linecap: round;
  stroke-dasharray: 1;
  stroke-dashoffset: 1;
  animation: draw 1.4s cubic-bezier(0.4, 0.1, 0.2, 1) var(--d0) forwards;
  transition: stroke 0.6s ease, opacity 0.4s ease;
}
.thread { stroke-width: 1.1; opacity: 0.8; }
.thread-glow { stroke-width: 5; opacity: 0.12; filter: blur(3px); }
/* Waiting for the partner: a dotted thread, drawn at once. */
.pair:not(.is-lit) .thread { stroke-dasharray: 0.004 0.012; stroke-dashoffset: 0; opacity: 0.5; animation: show 1s ease var(--d0) both; }
.pair:not(.is-lit) .thread-glow { display: none; }
.pair.is-quiet .thread { opacity: 0.32; }
.pair.is-quiet .thread-glow { opacity: 0.05; }
.pair.is-hot .thread { opacity: 1; stroke-width: 1.5; }
.pair.is-hot .thread-glow { opacity: 0.22; }

.partner { transition: transform 0.9s cubic-bezier(0.3, 0.7, 0.2, 1); }
.partner > * { opacity: 0; animation: show 0.8s ease calc(var(--d0) + 1.1s) forwards; }
.partner-halo { --o: 1; transform-origin: 0 0; animation: show 0.8s ease calc(var(--d0) + 1.1s) forwards, breathe 4.6s ease-in-out calc(var(--d0) + 2s) infinite; }
.partner-spike { --o: 1; fill: rgba(255, 228, 220, 0.5); }
.partner-core { --o: 1; fill: #fff6f2; filter: drop-shadow(0 0 4px #ffb9a4); transition: r 0.35s ease; }
.partner-wait { --o: 0.7; fill: none; stroke: #f3dcae; stroke-width: 1; stroke-dasharray: 2 3; }
.partner-flash {
  --o: 1;
  fill: none;
  stroke: #ffd9cc;
  stroke-width: 1.2;
  transform-origin: 0 0;
  animation: flash 1.4s cubic-bezier(0.2, 0.7, 0.2, 1) forwards;
}
.partner-name {
  --o: 1;
  font-family: var(--serif);
  font-style: italic;
  font-size: 19px;
  fill: #f6dccf;
  paint-order: stroke;
  stroke: rgba(4, 6, 12, 0.55);
  stroke-width: 4px;
}
.pair.is-quiet .partner-name { --o: 0.7; }
.partner-sign {
  --o: 0.85;
  font-family: var(--serif);
  font-style: italic;
  font-size: 14px;
  fill: rgba(242, 228, 200, 0.9);
  paint-order: stroke;
  stroke: rgba(4, 6, 12, 0.6);
  stroke-width: 4px;
}

/* The open pair's sign: the same engraving as the person's own, a shade rosier. */
.partner > .sign { --o: 1; }
.sign-art path {
  fill: none;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-dasharray: 1;
  stroke-dashoffset: 1;
  animation: draw 1.8s cubic-bezier(0.4, 0.1, 0.2, 1) calc(var(--d0) + 1.3s + var(--i) * 0.9s) forwards;
}
.art-outline { stroke: #f2cdb4; stroke-width: 1.15; opacity: 0.8; }
.art-detail { stroke: #e8bfa6; stroke-width: 0.8; opacity: 0.55; }
.art-hatch { stroke: #d9ad96; stroke-width: 0.6; opacity: 0.35; }
.sign-lines line { stroke: #ecd2c4; stroke-width: 0.8; stroke-linecap: round; opacity: 0.35; }
.sign-star { fill: #fff1ea; filter: drop-shadow(0 0 3px rgba(255, 190, 160, 0.9)); }

/* A star in the list opens its pair: the circle around it and its name answer the pointer. */
.partner > .partner-hit { --o: 1; pointer-events: auto; cursor: pointer; }
.partner-hit circle, .partner-hit rect { fill: transparent; }

.aspect-label {
  font-family: 'Segoe UI Symbol', 'Noto Sans Symbols', 'Noto Sans Symbols 2', sans-serif;
  font-size: 17px;
  fill: #f0cd8a;
  paint-order: stroke;
  stroke: rgba(4, 6, 12, 0.6);
  stroke-width: 4px;
  filter: drop-shadow(0 0 5px rgba(255, 200, 120, 0.6));
}
.aspect-label.tone-tense { fill: #f0a08c; }
.aspect-label.tone-joint { fill: #ece6f6; }
.label-enter-active, .label-leave-active { transition: opacity 0.25s ease; }
.label-enter-from, .label-leave-to { opacity: 0; }

@keyframes draw { to { stroke-dashoffset: 0; } }
@keyframes show { to { opacity: var(--o, 1); } }
@keyframes show-sky { from { opacity: 0; } }
@keyframes breathe { 50% { transform: scale(0.86); opacity: 0.8; } }
@keyframes flash {
  from { transform: scale(0.4); opacity: 1; }
  to { transform: scale(4.5); opacity: 0; }
}

@media (max-width: 760px) {
  .partner-name { font-size: 16px; }
  .partner-sign { font-size: 12.5px; }
}

.motion-off, .motion-off .partner > *, .motion-off .thread, .motion-off .thread-glow { animation: none; }
.motion-off .partner > * { opacity: var(--o, 1); }
.motion-off .thread, .motion-off .thread-glow { stroke-dashoffset: 0; }
.motion-off .partner-flash { display: none; }
.motion-off .partner { transition: none; }
.motion-off .sign-art path { animation: none; stroke-dashoffset: 0; }
</style>
