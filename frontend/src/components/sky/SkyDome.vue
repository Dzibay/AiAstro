<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useSky } from '../../composables/useSky.js'
import { useSkyOffer } from '../../composables/useSkyOffer.js'
import { wheelSpot } from '../cabinet/layout.js'
import { FEATURES } from './features.js'

/**
 * «Небосвод» on the sky: a round star map in the free middle of it, where the natal wheel stands
 * in the chart. Each feature of the subscription is a constellation on it; the person's own chart
 * burns in the middle from the start, the others are faint until the subscription lights them.
 *
 * A constellation under the pointer (here or in the panel's list) comes forward with its name;
 * the try-on lights them all for a while, and after a payment they catch fire one by one.
 */

const props = defineProps({
  /** The subscription runs: every constellation burns. */
  lit: { type: Boolean, default: false },
})

const { geo } = useSky()
const offer = useSkyOffer()
const reduce = ref(false)
onMounted(() => {
  reduce.value = window.matchMedia('(prefers-reduced-motion: reduce)').matches
})

const fixed = (n) => n.toFixed(1)
const rad = (deg) => (deg * Math.PI) / 180
const spot = computed(() => wheelSpot(geo.value))
const narrow = computed(() => geo.value.narrow)

const SPARK = (s) => `M0 ${-s}Q${s * 0.16} ${-s * 0.16} ${s} 0Q${s * 0.16} ${s * 0.16} 0 ${s}Q${-s * 0.16} ${s * 0.16} ${-s} 0Q${-s * 0.16} ${-s * 0.16} 0 ${-s}Z`

/** The rim: a tick every 5°, a longer one every 30°. */
const ticks = computed(() => {
  const r = spot.value.r
  return Array.from({ length: 72 }, (_, index) => {
    const a = rad(index * 5)
    const long = index % 6 === 0
    const r0 = r - (long ? 9 : 5)
    return { x1: fixed(r0 * Math.sin(a)), y1: fixed(-r0 * Math.cos(a)), x2: fixed(r * Math.sin(a)), y2: fixed(-r * Math.cos(a)), long }
  })
})
const meridians = computed(() => {
  const r = spot.value.r - 10
  return [0, 30, 60, 90, 120, 150].map((deg) => {
    const a = rad(deg)
    return { x1: fixed(-r * Math.sin(a)), y1: fixed(r * Math.cos(a)), x2: fixed(r * Math.sin(a)), y2: fixed(-r * Math.cos(a)) }
  })
})
/** The words around the rim, on a circle just inside it (desktop only, there is no room on a phone). */
const ringPath = computed(() => {
  const r = spot.value.r - 20
  return `M0 ${r}A${r} ${r} 0 1 1 0 ${-r}A${r} ${r} 0 1 1 0 ${r}`
})

const drawn = computed(() => {
  const { r } = spot.value
  const scale = r * (narrow.value ? 0.14 : 0.12)
  // Lit in the order they go round the dome, the person's own chart first.
  const order = [...FEATURES].sort((a, b) => (a.always ? -1 : b.always ? 1 : a.at[0] - b.at[0]))
  return FEATURES.map((feature) => {
    const [deg, share] = feature.at
    const x = share * r * Math.sin(rad(deg))
    const y = -share * r * Math.cos(rad(deg))
    const stars = feature.stars.map(([sx, sy, size]) => ({ x: sx * scale, y: sy * scale, size: size * (narrow.value ? 2.3 : 3) }))
    return {
      id: feature.id,
      name: feature.name,
      x,
      y,
      scale,
      stars,
      lines: feature.edges.map(([a, b]) => ({ a: stars[a], b: stars[b] })),
      on: feature.always || props.lit || offer.preview,
      always: Boolean(feature.always),
      step: order.indexOf(feature),
    }
  })
})

/** The moment of lighting after a payment: a new key restarts the stagger of flashes. */
const burst = ref(0)
watch(() => offer.celebrate, (value) => {
  if (value) burst.value = value
})

function enter(id) {
  offer.focus = id
}
function leave(id) {
  if (offer.focus === id) offer.focus = ''
}
/** Fingers have no hover: a tap names the constellation, a second tap lets it go. */
function tap(id) {
  offer.focus = offer.focus === id ? '' : id
}

const aria = computed(() => {
  const lit = drawn.value.filter((item) => item.on).map((item) => item.name)
  const dark = drawn.value.filter((item) => !item.on).map((item) => item.name)
  return dark.length ? `Небосвод: горит ${lit.join(', ')}; ждут подписки: ${dark.join(', ')}` : `Небосвод горит целиком: ${lit.join(', ')}`
})
</script>

<template>
  <svg
    class="sky-dome"
    :class="{ 'is-lit': lit || offer.preview, 'has-focus': offer.focus, 'motion-off': reduce, 'is-narrow': narrow }"
    :width="geo.W"
    :height="geo.H"
    :viewBox="`0 0 ${geo.W} ${geo.H}`"
    role="img"
    :aria-label="aria"
  >
    <defs>
      <radialGradient id="dome-vault">
        <stop offset="0" stop-color="#1b2140" stop-opacity="0.55" />
        <stop offset="0.7" stop-color="#0d1124" stop-opacity="0.42" />
        <stop offset="1" stop-color="#070910" stop-opacity="0.2" />
      </radialGradient>
      <radialGradient id="dome-glow">
        <stop offset="0" stop-color="#ffe7b4" stop-opacity="0.55" />
        <stop offset="0.4" stop-color="#f0cd8a" stop-opacity="0.16" />
        <stop offset="1" stop-color="#f0cd8a" stop-opacity="0" />
      </radialGradient>
      <path id="dome-ring" :d="ringPath" />
    </defs>

    <g :transform="`translate(${fixed(spot.x)} ${fixed(spot.y)})`">
      <!-- The vault itself: a dark disc with its grid, the rim and the words around it. -->
      <g class="vault">
        <circle class="vault-disc" :r="spot.r" fill="url(#dome-vault)" />
        <circle class="vault-aura" :r="spot.r * 1.04" />
        <circle class="vault-rim" :r="spot.r" />
        <circle class="vault-rim inner" :r="spot.r - 10" />
        <line v-for="(tick, index) in ticks" :key="`t${index}`" class="vault-tick" :class="{ long: tick.long }" v-bind="tick" />
        <line v-for="(line, index) in meridians" :key="`m${index}`" class="vault-grid" v-bind="line" />
        <circle class="vault-grid" :r="spot.r * 0.36" />
        <circle class="vault-grid" :r="spot.r * 0.7" />
        <text v-if="!narrow" class="vault-words">
          <textPath href="#dome-ring" startOffset="0">
            НЕБОСВОД ✦ ДЕНЬ ✦ НЕДЕЛЯ ✦ МЕСЯЦ ✦ РАЗГОВОР ✦ ПАРА ✦ НЕБОСВОД ✦ ДЕНЬ ✦ НЕДЕЛЯ ✦ МЕСЯЦ ✦ РАЗГОВОР ✦ ПАРА ✦
          </textPath>
        </text>
      </g>

      <g :key="burst" :class="{ 'is-burst': burst }">
        <g
          v-for="item in drawn"
          :key="item.id"
          class="figure"
          :class="{ 'is-on': item.on, 'is-hot': offer.focus === item.id, 'is-own': item.always }"
          :style="{ '--i': item.step, transform: `translate(${fixed(item.x)}px, ${fixed(item.y)}px)` }"
        >
          <circle class="figure-glow" :r="item.scale * 2.1" fill="url(#dome-glow)" />
          <line
            v-for="(line, index) in item.lines"
            :key="`l${index}`"
            class="figure-line"
            :x1="fixed(line.a.x)"
            :y1="fixed(line.a.y)"
            :x2="fixed(line.b.x)"
            :y2="fixed(line.b.y)"
          />
          <path
            v-for="(star, index) in item.stars"
            :key="`s${index}`"
            class="figure-star"
            :d="SPARK(star.size)"
            :transform="`translate(${fixed(star.x)} ${fixed(star.y)})`"
          />
          <circle class="figure-flash" :r="item.scale * 1.4" />
          <text
            class="figure-name"
            :y="fixed(item.scale * 1.15 + (narrow ? 11 : 16))"
            text-anchor="middle"
          >{{ item.name }}</text>
          <circle
            class="figure-hit"
            :r="item.scale * 1.55"
            @pointerenter="enter(item.id)"
            @pointerleave="leave(item.id)"
            @click="tap(item.id)"
          />
        </g>
      </g>
    </g>
  </svg>
</template>

<style scoped>
/* On the sky, in its coordinates (as the natal wheel), under the sections and the panel. */
.sky-dome {
  position: fixed;
  z-index: 1;
  top: 0;
  left: 0;
  overflow: visible;
  pointer-events: none;
}

.vault { animation: vault-in 1.2s cubic-bezier(0.3, 0.7, 0.2, 1) 0.5s both; transform-origin: 0 0; }
.vault-aura { fill: none; stroke: rgba(240, 205, 138, 0.1); stroke-width: 14; filter: blur(8px); transition: stroke 0.8s ease; }
.is-lit .vault-aura { stroke: rgba(240, 205, 138, 0.22); }
.vault-rim { fill: none; stroke: rgba(240, 210, 150, 0.42); stroke-width: 1; }
.vault-rim.inner { stroke: rgba(240, 210, 150, 0.16); }
.vault-tick { stroke: rgba(240, 210, 150, 0.28); stroke-width: 0.8; }
.vault-tick.long { stroke: rgba(240, 210, 150, 0.55); }
.vault-grid { fill: none; stroke: rgba(214, 226, 244, 0.08); stroke-width: 0.8; stroke-dasharray: 2 5; }
.vault-words { font-family: var(--caps); font-weight: 600; font-size: 10.5px; letter-spacing: 0.32em; fill: rgba(240, 205, 138, 0.42); }

/* A figure waits faint and dotted; lit, it burns gold. Lighting goes round the dome in turn. */
.figure { transition: opacity 0.4s ease; animation: figure-in 0.9s ease calc(0.9s + var(--i) * 0.08s) both; }
.figure-line {
  stroke: rgba(214, 226, 244, 0.2);
  stroke-width: 0.9;
  stroke-dasharray: 1.5 3.5;
  stroke-linecap: round;
  transition: stroke 0.6s ease calc(var(--i) * 0.12s), stroke-width 0.4s ease;
}
.figure-star {
  fill: rgba(214, 222, 238, 0.4);
  transition: fill 0.6s ease calc(var(--i) * 0.12s), filter 0.6s ease calc(var(--i) * 0.12s);
}
.figure-glow { opacity: 0; transition: opacity 0.6s ease calc(var(--i) * 0.12s); }
.figure-name {
  font-family: var(--caps);
  font-weight: 600;
  font-size: 12.5px;
  letter-spacing: 0.08em;
  fill: rgba(226, 220, 210, 0.45);
  paint-order: stroke;
  stroke: rgba(4, 6, 12, 0.85);
  stroke-width: 3px;
  transition: fill 0.4s ease, opacity 0.4s ease;
}
.figure-flash { fill: none; stroke: #ffe7b4; stroke-width: 1.2; opacity: 0; }
.figure-hit { fill: transparent; pointer-events: auto; cursor: pointer; }

.figure.is-on .figure-line { stroke: rgba(240, 205, 138, 0.6); stroke-dasharray: none; }
.figure.is-on .figure-star { fill: #fff1d4; filter: drop-shadow(0 0 3px rgba(255, 214, 140, 0.9)); }
.figure.is-on .figure-glow { opacity: 0.5; }
.figure.is-on .figure-name { fill: rgba(240, 205, 138, 0.8); }

/* The one under the pointer comes forward; the rest step back a little. */
.has-focus .figure:not(.is-hot) { opacity: 0.55; }
.figure.is-hot .figure-line { stroke-width: 1.4; stroke: rgba(240, 205, 138, 0.85); }
.figure.is-hot .figure-star { fill: #fff6e2; filter: drop-shadow(0 0 5px rgba(255, 214, 140, 1)); }
.figure.is-hot .figure-glow { opacity: 1; }
.figure.is-hot .figure-name { fill: #f6efe2; }
.figure.is-hot:not(.is-on) .figure-star { fill: rgba(240, 232, 214, 0.75); filter: none; }

/* On a phone the names would crowd: only the chosen one speaks. */
.is-narrow .figure-name { font-size: 11px; opacity: 0; }
.is-narrow .figure.is-hot .figure-name { opacity: 1; }

/* After a payment: each constellation flashes in turn. */
.is-burst .figure-flash { animation: flash 1.1s ease-out calc(0.3s + var(--i) * 0.35s) both; }
.is-burst .figure-star { animation: ignite 1.1s ease-out calc(0.3s + var(--i) * 0.35s) both; }

@keyframes vault-in { from { opacity: 0; transform: scale(0.92) rotate(-8deg); } }
@keyframes figure-in { from { opacity: 0; } }
@keyframes flash { 0% { opacity: 0.9; transform: scale(0.3); } 100% { opacity: 0; transform: scale(2.4); } }
@keyframes ignite { 0% { fill: rgba(214, 222, 238, 0.4); } 35% { fill: #ffffff; filter: drop-shadow(0 0 10px #ffe2a8); } }

.motion-off .vault, .motion-off .figure { animation: none; }
.motion-off .is-burst .figure-flash, .motion-off .is-burst .figure-star { animation: none; }
.motion-off .figure-line, .motion-off .figure-star, .motion-off .figure-glow { transition: none; }
</style>
