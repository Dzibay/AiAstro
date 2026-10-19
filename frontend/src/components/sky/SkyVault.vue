<script setup>
import { computed, onUnmounted, ref } from 'vue'
import { FEATURES } from './features.js'

/**
 * «Небосвод» as a vault of six stars over the horizon, one per thing it opens. Without the
 * subscription only the chart's star burns and the rest are ash; with it the whole arch lights,
 * star after star, and the lines between them are drawn. A star under the pointer (or the
 * keyboard) says what it gives; «Примерить» lights the arch for a moment before buying.
 */

const props = defineProps({
  lit: { type: Boolean, default: false },
  /** Offer «Примерить» while the vault is dim. */
  tryable: { type: Boolean, default: true },
})

const W = 340
const H = 168
// A low dome: wide and flat, the way the sky looks over a horizon.
const stars = FEATURES.map((feature, index) => {
  const t = index / (FEATURES.length - 1)
  const angle = Math.PI * (0.9 - 0.8 * t)
  const wobble = [6, -4, 3, -6, 4, -3][index]
  return {
    ...feature,
    x: W / 2 + Math.cos(angle) * 140,
    y: H - 22 - Math.sin(angle) * 112 + wobble,
    size: [1.25, 0.9, 1, 1.15, 0.95, 1.1][index],
  }
})
const edges = stars.slice(1).map((star, index) => ({ from: stars[index], to: star, key: star.id }))

// The dust between the stars: fixed, so the vault looks the same on every visit.
let seed = 7
const random = () => {
  seed = (seed * 16807) % 2147483647
  return seed / 2147483647
}
const dust = Array.from({ length: 46 }, () => ({ x: random() * W, y: random() * (H - 30), r: 0.4 + random() * 0.8, o: 0.15 + random() * 0.4 }))

const trying = ref(false)
const shown = computed(() => props.lit || trying.value)
const focus = ref('')
const current = computed(() => stars.find((star) => star.id === focus.value) || null)
const isOn = (star) => star.always || shown.value

let timer = 0
function tryOn() {
  trying.value = !trying.value
  clearTimeout(timer)
  // A glimpse, not a free subscription: the arch goes out again by itself.
  if (trying.value) timer = setTimeout(() => { trying.value = false }, 6000)
}
onUnmounted(() => clearTimeout(timer))

const caption = computed(() => {
  if (props.lit) return 'Небосвод горит: все шесть звёзд ваши.'
  if (trying.value) return 'Так загорится ваш Небосвод.'
  return 'Пока горит одна звезда — ваша карта. Остальные зажжёт «Небосвод».'
})
</script>

<template>
  <figure class="sky-vault" :class="{ 'is-lit': shown }">
    <svg :viewBox="`0 0 ${W} ${H}`" class="vault" aria-hidden="true" @pointerleave="focus = ''">
      <defs>
        <radialGradient id="vault-glow">
          <stop offset="0" stop-color="#ffe4a8" stop-opacity="0.9" />
          <stop offset="1" stop-color="#ffe4a8" stop-opacity="0" />
        </radialGradient>
        <linearGradient id="vault-horizon" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="#f0cd8a" stop-opacity="0" />
          <stop offset="1" stop-color="#f0cd8a" stop-opacity="0.16" />
        </linearGradient>
      </defs>
      <rect class="horizon-haze" x="0" :y="H - 60" :width="W" height="60" fill="url(#vault-horizon)" />
      <line class="horizon" x1="10" :y1="H - 8" :x2="W - 10" :y2="H - 8" />
      <circle v-for="(speck, index) in dust" :key="index" class="dust" :cx="speck.x" :cy="speck.y" :r="speck.r" :style="{ opacity: shown ? speck.o * 1.6 : speck.o }" />
      <line
        v-for="(edge, index) in edges"
        :key="edge.key"
        class="edge"
        :class="{ 'is-on': shown }"
        :x1="edge.from.x" :y1="edge.from.y" :x2="edge.to.x" :y2="edge.to.y"
        :style="{ transitionDelay: shown ? `${index * 140 + 120}ms` : '0ms' }"
      />
      <g
        v-for="(star, index) in stars"
        :key="star.id"
        class="star"
        :class="{ 'is-on': isOn(star), 'is-focus': focus === star.id }"
        :transform="`translate(${star.x} ${star.y})`"
        :style="{ transitionDelay: shown && !star.always ? `${index * 140}ms` : '0ms' }"
        @pointerenter="focus = star.id"
      >
        <circle class="hit" r="20" />
        <circle class="glow" :r="18 * star.size" fill="url(#vault-glow)" />
        <path :transform="`scale(${0.62 * star.size}) translate(-10 -10)`" d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" />
      </g>
    </svg>

    <!-- The same stars for the keyboard and for screen readers. -->
    <ul class="names">
      <li v-for="star in stars" :key="star.id">
        <button
          type="button"
          class="name"
          :class="{ 'is-on': isOn(star), 'is-focus': focus === star.id }"
          @focus="focus = star.id"
          @blur="focus = ''"
          @pointerenter="focus = star.id"
          @pointerleave="focus = ''"
        >
          {{ star.name }}<span class="visually-hidden">: {{ isOn(star) ? 'открыто' : `бесплатно — ${star.free}` }}</span>
        </button>
      </li>
    </ul>

    <figcaption class="caption" aria-live="polite">
      <template v-if="current">
        <span class="caption-name">{{ current.name }}</span>
        <span v-if="current.always">бесплатно и навсегда</span>
        <span v-else-if="lit">в «Небосводе» — {{ current.sky }}</span>
        <span v-else>сейчас — {{ current.free }}, в «Небосводе» — {{ current.sky }}</span>
      </template>
      <span v-else>{{ caption }}</span>
    </figcaption>

    <button v-if="tryable && !lit" type="button" class="try" :aria-pressed="trying" @click="tryOn">
      {{ trying ? 'Погасить' : 'Примерить Небосвод' }}
    </button>
  </figure>
</template>

<style scoped>
.sky-vault { position: relative; display: grid; gap: 10px; margin: 0; }
.vault { display: block; width: 100%; height: auto; overflow: visible; }

.horizon { stroke: rgba(240, 205, 138, 0.3); stroke-width: 1; }
.horizon-haze { transition: opacity 1.2s ease; opacity: 0.4; }
.is-lit .horizon-haze { opacity: 1; }
.dust { fill: #efe7d8; transition: opacity 1.2s ease; }

.edge {
  stroke: rgba(240, 205, 138, 0.12);
  stroke-width: 0.8;
  stroke-dasharray: 3 4;
  transition: stroke 0.8s ease;
}
.edge.is-on { stroke: rgba(240, 205, 138, 0.55); stroke-dasharray: none; }

.star .hit { fill: transparent; }
.star path { fill: rgba(226, 220, 210, 0.28); transition: fill 0.7s ease; transition-delay: inherit; }
.star .glow { opacity: 0; transform: scale(0.4); transition: opacity 0.9s ease, transform 0.9s cubic-bezier(0.3, 0.7, 0.2, 1); transition-delay: inherit; }
.star.is-on path { fill: #fff3d6; }
.star.is-on .glow { opacity: 0.85; transform: scale(1); }
.star.is-focus .glow { opacity: 1; transform: scale(1.35); }
.star.is-focus:not(.is-on) path { fill: rgba(240, 205, 138, 0.6); }

.names { display: flex; flex-wrap: wrap; justify-content: center; gap: 2px 12px; margin: -4px 0 0; padding: 0; list-style: none; }
.name {
  padding: 2px 0;
  border: 0;
  background: none;
  font-family: var(--caps);
  font-size: 13.5px;
  letter-spacing: 0.06em;
  color: rgba(226, 220, 210, 0.42);
  cursor: default;
  transition: color 0.5s ease;
}
.name.is-on { color: rgba(240, 205, 138, 0.85); }
.name.is-focus { color: #f6efe2; }
.name:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 2px; border-radius: 4px; }

.caption {
  display: grid;
  gap: 2px;
  min-height: 2.8em;
  text-align: center;
  font-family: var(--serif);
  font-style: italic;
  font-size: 16px;
  line-height: 1.35;
  color: rgba(242, 228, 200, 0.8);
}
.caption-name { font-family: var(--caps); font-style: normal; font-size: 15px; letter-spacing: 0.08em; color: #f0cd8a; }

.try {
  justify-self: center;
  padding: 6px 14px;
  border-radius: 999px;
  border: 1px solid rgba(240, 210, 150, 0.26);
  background: rgba(255, 240, 210, 0.04);
  font: inherit;
  font-size: 12.5px;
  letter-spacing: 0.04em;
  color: #f3dcae;
  cursor: pointer;
  transition: border-color 0.25s ease, background 0.25s ease;
}
.try:hover { border-color: rgba(240, 205, 138, 0.6); background: rgba(255, 240, 210, 0.08); }
.try:focus-visible { outline: 2px solid #f0cd8a; outline-offset: 3px; }

.visually-hidden { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }

@media (max-width: 760px) {
  .try { min-height: 44px; }
  .name { padding-block: 6px; }
}
@media (prefers-reduced-motion: reduce) {
  .star path, .star .glow, .edge, .dust, .horizon-haze { transition: none; }
}
</style>
