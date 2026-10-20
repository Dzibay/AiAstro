<script setup>
import { computed } from 'vue'
import { ZODIAC_BY_ID } from '../hero/zodiac.js'
import { signFigure } from '../hero/signFigure.js'

/**
 * On phones the sky does not travel: the signs of a stop are simply drawn above its copy and
 * scroll with the page. Decoration only, so nothing here catches a tap.
 */
const props = defineProps({
  /** Two sign ids, east to west: the first goes on the left. */
  signs: { type: Array, required: true },
})

/** Small figures grow a little more than large ones, so a pair looks even. */
const spanOf = (id) => 56 + ZODIAC_BY_ID[id].size * 0.22

const drawn = computed(() => props.signs.map((id) => {
  const span = spanOf(id)
  const figure = signFigure(id, span)
  const xs = figure.stars.map((star) => star.x)
  const ys = figure.stars.map((star) => star.y)
  const pad = 14
  const box = {
    x: Math.min(-span * 0.5, ...xs) - pad,
    y: Math.min(-span * 0.5, ...ys) - pad,
  }
  box.w = Math.max(span * 0.5, ...xs) + pad - box.x
  box.h = Math.max(span * 0.5, ...ys) + pad - box.y
  return { ...figure, name: ZODIAC_BY_ID[id].name, box }
}))
</script>

<template>
  <div class="page-signs" aria-hidden="true">
    <figure v-for="(sign, order) in drawn" :key="sign.id" class="page-sign" :class="`is-${order ? 'right' : 'left'}`">
      <svg :viewBox="`${sign.box.x} ${sign.box.y} ${sign.box.w} ${sign.box.h}`" :width="sign.box.w" :height="sign.box.h">
        <g class="sign-art">
          <path v-for="stroke in sign.art" :key="stroke.index" :class="`art-${stroke.kind}`" :d="stroke.d" />
        </g>
        <line v-for="line in sign.lines" :key="line.key" class="sign-line" :x1="line.a.x" :y1="line.a.y" :x2="line.b.x" :y2="line.b.y" />
        <g v-for="(star, index) in sign.stars" :key="index" class="sign-star" :class="{ 'is-bright': star.r > 2 }" :style="{ '--d': `${(index * 0.9) % 5}s` }">
          <circle class="sign-halo" :cx="star.x" :cy="star.y" :r="star.r * 4.5" />
          <circle class="sign-core" :cx="star.x" :cy="star.y" :r="star.r" />
        </g>
      </svg>
      <figcaption>{{ sign.name }}</figcaption>
    </figure>
  </div>
</template>

<style scoped>
.page-signs { display: none; }

@media (max-width: 759.98px) {
  /* The strip above the copy, below the header: the stop's padding keeps it free. */
  .page-signs {
    position: absolute;
    top: 78px;
    left: 0;
    right: 0;
    height: calc(34svh - 90px);
    min-height: 170px;
    display: block;
    pointer-events: none;
  }
}

.page-sign {
  position: absolute;
  margin: 0;
  display: grid;
  justify-items: center;
  gap: 2px;
}
.page-sign.is-left { left: 5%; top: 0; }
.page-sign.is-right { right: 5%; top: 18%; }
.page-sign svg { width: auto; height: auto; max-width: 40vw; max-height: max(110px, calc(34svh - 120px)); overflow: visible; }

.sign-art path { fill: none; stroke-linecap: round; stroke-linejoin: round; }
.sign-art .art-outline { stroke: #f0cf8e; stroke-width: 1; opacity: 0.26; }
.sign-art .art-detail { stroke: #e6c17e; stroke-width: 0.7; opacity: 0.16; }
.sign-art .art-hatch { stroke: #d8b274; stroke-width: 0.5; opacity: 0.1; }
.sign-line { stroke: #e3cfa6; stroke-width: 0.8; stroke-linecap: round; opacity: 0.32; }
.sign-halo { fill: rgba(255, 217, 160, 0.13); }
.sign-core { fill: #fff6e2; }
/* Only the brightest stars breathe, on opacity alone: cheap enough for any phone. */
.sign-star.is-bright .sign-halo { animation: sign-twinkle 4.6s ease-in-out var(--d) infinite; }
@keyframes sign-twinkle { 50% { opacity: 0.35; } }

figcaption {
  font-size: 9px;
  letter-spacing: 0.34em;
  text-transform: uppercase;
  color: rgba(217, 204, 180, 0.6);
}

@media (prefers-reduced-motion: reduce) {
  .sign-star.is-bright .sign-halo { animation: none; }
}
</style>
