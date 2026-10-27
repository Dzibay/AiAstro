<script setup>
import { computed, onMounted, ref } from 'vue'
import { useSky } from '../../composables/useSky.js'
import { useChart } from '../../composables/useChart.js'
import { clamp } from '../hero/sky.js'
import { talkWheelSpot, wheelSpot } from './layout.js'
import { ASPECTS, POINTS, SIGN_LIST, spread } from './astro.js'

/**
 * The natal wheel, engraved on the sky in thin gold lines with nothing behind it: the ring of
 * signs, the ring of houses, the planets at their degrees and the aspects inside. It draws itself
 * stroke by stroke as the sign engraving does at the login: rings, then planets, then aspects.
 * The Ascendant lies on the left, as on a paper chart; without the time, 0° Aries does.
 *
 * With a forecast the natal wheel steps inward and the sky of the day walks around it in cool
 * silver: the key transits are drawn as lines from the moving planet to the natal point it touches.
 *
 * Beside the ИИ-астролог's conversation it stands aside, quiet: a planet named in an answer
 * (LiveText) lights on it under the pointer.
 *
 * A chapter of the portrait (PortraitWalk) lights what it speaks of at once: its planets, the
 * aspects between them, its signs and houses as soft gold bands; the rest of the wheel dims.
 */

const props = defineProps({
  chart: { type: Object, required: true },
  /** The point whose reading is open in the panel. */
  selected: { type: String, default: '' },
  /** A forecast (GET /me/forecast): its `sky` circles the chart, its `transits` reach in. */
  forecast: { type: Object, default: null },
  /** Drawn under the last picture of the natal sky game (NatalGame): the planets come at once, where its bodies fade. */
  landing: { type: Boolean, default: false },
  /** Beside the conversation (talkWheelSpot): quiet until a planet named in an answer lights. */
  aside: { type: Boolean, default: false },
})
const emit = defineEmits(['select'])
// Read once: the drawing-in is decided when the wheel appears, a later change must not replay it.
const landed = props.landing

const { geo } = useSky()
const { hot, lens } = useChart()

const spot = computed(() => (props.aside && talkWheelSpot(geo.value)) || wheelSpot(geo.value))
const reduce = ref(false)
onMounted(() => {
  reduce.value = window.matchMedia('(prefers-reduced-motion: reduce)').matches
})

const RAD = Math.PI / 180
const fixed = (n) => n.toFixed(1)

/** Radii in px: the outer edge, the signs' inner edge, the houses' inner edge, the planets, the aspects. */
/** The natal wheel's own radius: the whole spot, or less of it when the day's sky circles it. */
const inner = computed(() => (props.forecast ? spot.value.r * 0.8 : spot.value.r))
const radii = computed(() => {
  const r = inner.value
  const houses = Boolean(props.chart.houses)
  return {
    outer: r,
    signs: r * 0.85,
    houses: r * 0.76,
    planets: houses ? r * 0.635 : r * 0.68,
    aspects: r * 0.5,
    transits: spot.value.r * 0.95,
  }
})
const sizes = computed(() => {
  const r = inner.value
  return {
    sign: clamp(r * 0.07, 10, 22),
    planet: clamp(r * 0.085, 12, 24),
    house: clamp(r * 0.042, 8, 12),
    axis: clamp(r * 0.045, 9, 13),
    transit: clamp(spot.value.r * 0.068, 11, 20),
  }
})
const pad = computed(() => Math.max(
  inner.value + sizes.value.axis * 2.6,
  props.forecast ? radii.value.transits + sizes.value.transit : 0,
))

const base = computed(() => (props.chart.angles ? props.chart.angles.asc.lon : 0))
function at(lon, radius) {
  const angle = (180 + lon - base.value) * RAD
  return [radius * Math.cos(angle), -radius * Math.sin(angle)]
}
function line(lon, from, to) {
  const [x1, y1] = at(lon, from)
  const [x2, y2] = at(lon, to)
  return `M${fixed(x1)} ${fixed(y1)}L${fixed(x2)} ${fixed(y2)}`
}

const ticks = computed(() => {
  const { signs } = radii.value
  const { r } = spot.value
  let d = ''
  for (let lon = 0; lon < 360; lon += 5) {
    if (lon % 30) d += line(lon, signs, signs + r * (lon % 10 ? 0.018 : 0.034))
  }
  return d
})
const dividers = computed(() => SIGN_LIST.map((_, index) => line(index * 30, radii.value.signs, radii.value.outer)).join(''))

const signs = computed(() => SIGN_LIST.map((sign, index) => {
  const [x, y] = at(index * 30 + 15, (radii.value.outer + radii.value.signs) / 2)
  return { id: sign.id, glyph: sign.glyph, x, y }
}))

/** The cusps (the Ascendant's and the MC's drawn out past the rim) and the house numbers between them. */
const houses = computed(() => {
  const cusps = props.chart.houses
  if (!cusps) return null
  const { aspects, signs: inner, houses: ring, outer } = radii.value
  const lines = cusps.map((cusp, index) => {
    const axis = index === 0 || index === 9
    return { key: index, axis, d: line(cusp.lon, aspects, axis ? outer + sizes.value.axis * 0.6 : inner) }
  })
  const numbers = cusps.map((cusp, index) => {
    const next = cusps[(index + 1) % 12].lon
    const mid = cusp.lon + (((next - cusp.lon) % 360) + 360) % 360 / 2
    const [x, y] = at(mid, (inner + ring) / 2)
    return { key: index, label: index + 1, x, y }
  })
  return { lines, numbers }
})
const axes = computed(() => {
  if (!props.chart.angles) return []
  const reach = radii.value.outer + sizes.value.axis * 1.7
  return ['asc', 'mc'].map((id) => {
    const [x, y] = at(props.chart.angles[id].lon, reach)
    return { id, label: POINTS[id].glyph, x, y }
  })
})

const planets = computed(() => {
  const { planets: ring, aspects } = radii.value
  const gap = ((sizes.value.planet * 1.15) / ring) / RAD
  const shown = spread(props.chart.points, gap)
  return props.chart.points.map((point, index) => {
    const [x, y] = at(shown[point.id], ring)
    const [dx, dy] = at(point.lon, aspects)
    return { id: point.id, glyph: POINTS[point.id].glyph, approx: point.approx, retro: point.retro && point.id !== 'node', x, y, dx, dy, index }
  })
})

/** Every point an aspect can end at, by id: the planets' dots and the two angles on the inner circle. */
const ends = computed(() => {
  const map = Object.fromEntries(planets.value.map((p) => [p.id, [p.dx, p.dy]]))
  if (props.chart.angles) {
    for (const id of ['asc', 'mc']) map[id] = at(props.chart.angles[id].lon, radii.value.aspects)
  }
  return map
})

const focus = computed(() => hot.value || props.selected)

/** The portrait's chapter, while nothing is under the pointer or chosen and no forecast circles the chart. */
const glow = computed(() => {
  const value = lens.value
  if (!value || focus.value || props.forecast) return null
  const points = new Set(value.points || [])
  const signs = new Set(value.signs || [])
  const houses = new Set(value.houses || [])
  return points.size || signs.size || houses.size ? { points, signs, houses } : null
})
/** Lit by the pointer, the choice or the chapter. */
const isOn = (id) => focus.value === id || Boolean(glow.value?.points.has(id))

/** A band of the wheel between two degrees and two radii (degrees grow anticlockwise on screen). */
function sector(from, to, r1, r2) {
  const span = (((to - from) % 360) + 360) % 360
  const large = span > 180 ? 1 : 0
  const [ax, ay] = at(from, r2)
  const [bx, by] = at(to, r2)
  const [cx, cy] = at(to, r1)
  const [dx, dy] = at(from, r1)
  return `M${fixed(ax)} ${fixed(ay)}A${fixed(r2)} ${fixed(r2)} 0 ${large} 0 ${fixed(bx)} ${fixed(by)}`
    + `L${fixed(cx)} ${fixed(cy)}A${fixed(r1)} ${fixed(r1)} 0 ${large} 1 ${fixed(dx)} ${fixed(dy)}Z`
}
/** The chapter's signs in the belt of signs, its houses in the ring of their numbers. */
const bands = computed(() => {
  const { outer, signs: belt, houses: ring } = radii.value
  const list = SIGN_LIST.map((sign, index) => ({
    key: `s-${sign.id}`,
    d: sector(index * 30, index * 30 + 30, belt, outer),
    lit: Boolean(glow.value?.signs.has(sign.id)),
  }))
  const cusps = props.chart.houses
  if (cusps) {
    cusps.forEach((cusp, index) => list.push({
      key: `h-${index + 1}`,
      d: sector(cusp.lon, cusps[(index + 1) % 12].lon, ring, belt),
      lit: Boolean(glow.value?.houses.has(index + 1)),
    }))
  }
  return list
})

/* ---- The day's sky around the chart ---- */

const transitKey = (transit) => `${transit.a}-${transit.b}-${transit.type}`

const transitPlanets = computed(() => {
  if (!props.forecast) return []
  const ring = radii.value.transits
  const gap = ((sizes.value.transit * 1.1) / ring) / RAD
  const shown = spread(props.forecast.sky, gap)
  return props.forecast.sky.map((point, index) => {
    const [x, y] = at(shown[point.id], ring)
    const [tx, ty] = at(point.lon, radii.value.outer)
    const [ox, oy] = at(point.lon, radii.value.outer + spot.value.r * 0.035)
    return { id: point.id, key: `tr-${point.id}`, glyph: POINTS[point.id].glyph, retro: point.retro, x, y, tick: `M${fixed(tx)} ${fixed(ty)}L${fixed(ox)} ${fixed(oy)}`, index }
  })
})

/** Does the focus (a chip, a transiting planet or a natal point) take part in this transit? */
function touches(transit, id) {
  return id === transitKey(transit) || id === `tr-${transit.a}` || id === transit.b
}

const transitLines = computed(() => {
  if (!props.forecast) return []
  const sky = Object.fromEntries(props.forecast.sky.map((point) => [point.id, point]))
  return props.forecast.transits
    .filter((transit) => sky[transit.a] && ends.value[transit.b])
    .map((transit, index) => {
      const [x1, y1] = at(sky[transit.a].lon, radii.value.aspects)
      const [x2, y2] = ends.value[transit.b]
      const lit = Boolean(focus.value) && touches(transit, focus.value)
      return {
        key: transitKey(transit),
        tone: ASPECTS[transit.type].tone,
        d: `M${fixed(x1)} ${fixed(y1)}L${fixed(x2)} ${fixed(y2)}`,
        from: [x1, y1],
        lit,
        dim: Boolean(focus.value) && !lit,
        index,
      }
    })
})

/** In the forecast the partners of a point are the transits that touch it. */
const transitPartners = computed(() => {
  const set = new Set()
  if (!props.forecast || !focus.value) return set
  for (const transit of props.forecast.transits) {
    if (touches(transit, focus.value)) {
      set.add(transit.b)
      set.add(`tr-${transit.a}`)
    }
  }
  return set
})

const aspects = computed(() => (props.forecast ? [] : props.chart.aspects)
  .filter((aspect) => ends.value[aspect.a] && ends.value[aspect.b])
  .map((aspect, index) => {
    const [x1, y1] = ends.value[aspect.a]
    const [x2, y2] = ends.value[aspect.b]
    let lit = focus.value && (aspect.a === focus.value || aspect.b === focus.value)
    if (glow.value) {
      // One point of the chapter: its aspects; several: the aspects between them.
      const { points } = glow.value
      lit = points.size === 1 ? points.has(aspect.a) || points.has(aspect.b) : points.has(aspect.a) && points.has(aspect.b)
    }
    return {
      key: `${aspect.a}-${aspect.b}`,
      tone: ASPECTS[aspect.type].tone,
      d: `M${fixed(x1)} ${fixed(y1)}L${fixed(x2)} ${fixed(y2)}`,
      // A conjunction is a dot just inside the circle between the two.
      dot: [((x1 + x2) / 2) * 0.9, ((y1 + y2) / 2) * 0.9],
      lit,
      dim: Boolean(focus.value || glow.value) && !lit,
      // The tighter the orb, the stronger the line.
      strength: clamp(1 - aspect.orb / 9, 0.35, 1),
      index,
    }
  }))

/** Points that share an aspect with the focused one glow a little too. */
const partners = computed(() => {
  if (props.forecast) return transitPartners.value
  const set = new Set()
  if (!focus.value) return set
  for (const aspect of props.chart.aspects) {
    if (aspect.a === focus.value) set.add(aspect.b)
    if (aspect.b === focus.value) set.add(aspect.a)
  }
  return set
})

const frame = computed(() => {
  const S = pad.value
  return {
    style: { left: `${fixed(spot.value.x - S)}px`, top: `${fixed(spot.value.y - S)}px`, width: `${fixed(S * 2)}px`, height: `${fixed(S * 2)}px` },
    viewBox: `${fixed(-S)} ${fixed(-S)} ${fixed(S * 2)} ${fixed(S * 2)}`,
  }
})

function setHot(id) {
  hot.value = id
}

function choose(id) {
  emit('select', id)
}
</script>

<template>
  <div class="natal-wheel" :class="{ 'is-landed': landed, 'motion-off': reduce, 'has-focus': Boolean(focus || glow), 'with-transits': Boolean(forecast), 'is-aside': aside }" :style="frame.style">
    <svg :viewBox="frame.viewBox" role="img" :aria-label="forecast ? 'Транзиты над натальной картой. Ключевые транзиты — в панели.' : 'Колесо натальной карты. Те же планеты списком — в панели.'">
      <g class="rings">
        <circle class="ring" :r="radii.outer" pathLength="1" />
        <circle class="ring" :r="radii.signs" pathLength="1" style="--i: 1" />
        <circle v-if="houses" class="ring ring-faint" :r="radii.houses" pathLength="1" style="--i: 2" />
        <circle class="ring ring-faint" :r="radii.aspects" pathLength="1" style="--i: 3" />
      </g>
      <g class="bands" aria-hidden="true">
        <path v-for="band in bands" :key="band.key" class="band" :class="{ 'is-lit': band.lit }" :d="band.d" />
      </g>
      <path class="ticks" :d="ticks" />
      <path class="dividers" :d="dividers" />
      <text
        v-for="(sign, index) in signs"
        :key="sign.id"
        class="sign-glyph"
        :class="{ 'is-lit': glow?.signs.has(sign.id) }"
        :x="sign.x"
        :y="sign.y"
        :font-size="sizes.sign"
        :style="{ '--i': index }"
      >{{ sign.glyph }}</text>

      <g v-if="houses" class="houses">
        <path
          v-for="cusp in houses.lines"
          :key="cusp.key"
          class="cusp"
          :class="{ 'is-axis': cusp.axis, 'is-lit': cusp.axis && isOn(cusp.key === 0 ? 'asc' : 'mc') }"
          :d="cusp.d"
        />
        <text
          v-for="number in houses.numbers"
          :key="number.key"
          class="house-number"
          :class="{ 'is-lit': glow?.houses.has(number.label) }"
          :x="number.x"
          :y="number.y"
          :font-size="sizes.house"
        >{{ number.label }}</text>
      </g>
      <text
        v-for="axis in axes"
        :key="axis.id"
        class="axis-label"
        :class="{ 'is-on': isOn(axis.id) }"
        :x="axis.x"
        :y="axis.y"
        :font-size="sizes.axis"
        @click="choose(axis.id)"
        @pointerenter="setHot(axis.id)"
        @pointerleave="setHot('')"
      >{{ axis.label }}</text>

      <g class="aspects">
        <template v-for="aspect in aspects" :key="aspect.key">
          <circle
            v-if="aspect.tone === 'joint'"
            class="aspect-dot"
            :class="{ 'is-lit': aspect.lit, 'is-dim': aspect.dim }"
            :cx="aspect.dot[0]"
            :cy="aspect.dot[1]"
            :r="Math.max(1.6, spot.r * 0.009)"
            :style="{ '--i': aspect.index, '--s': aspect.strength }"
          />
          <path
            v-else
            class="aspect"
            :class="[`tone-${aspect.tone}`, { 'is-lit': aspect.lit, 'is-dim': aspect.dim }]"
            :d="aspect.d"
            pathLength="1"
            :style="{ '--i': aspect.index, '--s': aspect.strength }"
          />
        </template>
        <g v-for="line in transitLines" :key="line.key" class="transit-line" :class="[`tone-${line.tone}`, { 'is-lit': line.lit, 'is-dim': line.dim }]" :style="{ '--i': line.index }">
          <path :d="line.d" pathLength="1" />
          <circle :cx="line.from[0]" :cy="line.from[1]" :r="Math.max(1.6, spot.r * 0.009)" />
        </g>
      </g>

      <g v-if="forecast" class="transit-ring">
        <circle class="ring ring-transit" :r="radii.transits + sizes.transit * 0.75" pathLength="1" />
        <g
          v-for="planet in transitPlanets"
          :key="planet.key"
          class="transit"
          :class="{ 'is-on': focus === planet.key, 'is-partner': partners.has(planet.key) }"
          :style="{ '--i': planet.index }"
          @pointerenter="setHot(planet.key)"
          @pointerleave="setHot('')"
        >
          <path class="transit-tick" :d="planet.tick" />
          <circle class="planet-hit" :cx="planet.x" :cy="planet.y" :r="sizes.transit * 0.85" />
          <text class="transit-glyph" :x="planet.x" :y="planet.y" :font-size="sizes.transit">{{ planet.glyph }}</text>
          <text
            v-if="planet.retro"
            class="planet-mark transit-mark"
            :x="planet.x + sizes.transit * 0.62"
            :y="planet.y + sizes.transit * 0.5"
            :font-size="sizes.transit * 0.5"
          >R</text>
        </g>
      </g>

      <g
        v-for="planet in planets"
        :key="planet.id"
        class="planet"
        :class="{ 'is-on': isOn(planet.id), 'is-partner': partners.has(planet.id), 'is-selected': selected === planet.id }"
        :style="{ '--i': planet.index }"
        @click="choose(planet.id)"
        @pointerenter="setHot(planet.id)"
        @pointerleave="setHot('')"
      >
        <circle class="planet-dot" :cx="planet.dx" :cy="planet.dy" :r="Math.max(1.4, spot.r * 0.008)" />
        <circle class="planet-hit" :cx="planet.x" :cy="planet.y" :r="sizes.planet * 0.85" />
        <text class="planet-glyph" :x="planet.x" :y="planet.y" :font-size="sizes.planet">{{ planet.glyph }}</text>
        <text
          v-if="planet.approx || planet.retro"
          class="planet-mark"
          :x="planet.x + sizes.planet * 0.62"
          :y="planet.y + sizes.planet * 0.5"
          :font-size="sizes.planet * 0.5"
        >{{ planet.approx ? '≈' : 'R' }}</text>
      </g>
    </svg>
  </div>
</template>

<style scoped>
/* On the sky, in its coordinates (the same frame as CabinetSky), under the sections and the panel. */
.natal-wheel {
  position: fixed;
  z-index: 1;
  pointer-events: none;
  --d0: 0.55s;
}
/* Beside the conversation the wheel stays in the background, and comes forward with a planet named. */
/* On the picture, not the wheel itself: the wheel's own opacity is CabinetView's fade in and out. */
.natal-wheel.is-aside svg { opacity: 0.5; transition: opacity 0.5s ease; }
.natal-wheel.is-aside.has-focus svg { opacity: 1; }
.natal-wheel svg { display: block; width: 100%; height: 100%; overflow: visible; }

.ring {
  fill: none;
  stroke: #e9cf98;
  stroke-width: 1;
  vector-effect: non-scaling-stroke;
  opacity: 0.55;
  stroke-dasharray: 1;
  stroke-dashoffset: 1;
  filter: drop-shadow(0 0 3px rgba(255, 205, 120, 0.35));
  animation: draw 1.3s cubic-bezier(0.45, 0.1, 0.25, 1) calc(var(--d0) + var(--i, 0) * 0.12s) forwards;
}
.ring-faint { opacity: 0.28; }

.ticks, .dividers, .cusp {
  fill: none;
  stroke: #e9cf98;
  stroke-width: 1;
  vector-effect: non-scaling-stroke;
  opacity: 0;
  animation: show 0.9s ease calc(var(--d0) + 0.7s) forwards;
  --o: 0.3;
}
.dividers { --o: 0.5; }
.cusp { --o: 0.22; }
.cusp.is-axis { --o: 0.6; stroke-width: 1.3; }

.sign-glyph, .house-number, .axis-label, .planet-glyph, .planet-mark {
  text-anchor: middle;
  dominant-baseline: central;
  font-family: 'Segoe UI Symbol', 'Noto Sans Symbols', 'Noto Sans Symbols 2', sans-serif;
}
.sign-glyph {
  fill: #f0d6a2;
  opacity: 0;
  filter: drop-shadow(0 0 4px rgba(255, 200, 110, 0.4));
  animation: show 0.6s ease calc(var(--d0) + 0.8s + var(--i) * 0.05s) forwards;
  --o: 0.8;
  transition: fill 0.35s ease, filter 0.35s ease;
}
/* The chapter's signs and houses: the glyph brightens over a soft gold band (the fade-in owns the opacity). */
.sign-glyph.is-lit, .house-number.is-lit { fill: #fff6df; filter: drop-shadow(0 0 6px rgba(255, 210, 130, 0.95)); }
.band { fill: #f0cd8a; fill-opacity: 0; stroke: none; transition: fill-opacity 0.45s ease; }
.band.is-lit { fill-opacity: 0.13; }
.cusp.is-lit { stroke: #fff3d6; filter: drop-shadow(0 0 3px rgba(255, 210, 130, 0.8)); }
.house-number {
  font-family: var(--serif);
  font-style: italic;
  fill: #e9cf98;
  opacity: 0;
  animation: show 0.8s ease calc(var(--d0) + 1s) forwards;
  --o: 0.45;
  transition: fill 0.35s ease, filter 0.35s ease;
}
.axis-label {
  font-family: var(--serif);
  font-style: italic;
  fill: #f0d6a2;
  opacity: 0;
  pointer-events: auto;
  cursor: pointer;
  animation: show 0.8s ease calc(var(--d0) + 1s) forwards;
  --o: 0.75;
  transition: fill 0.25s ease;
}
.axis-label.is-on { fill: #fff3d6; filter: drop-shadow(0 0 5px rgba(255, 210, 130, 0.9)); }

.aspect {
  fill: none;
  stroke-width: 1;
  vector-effect: non-scaling-stroke;
  stroke-dasharray: 1;
  stroke-dashoffset: 1;
  opacity: calc(0.22 + var(--s) * 0.35);
  animation: draw 0.9s ease calc(var(--d0) + 1.8s + var(--i) * 0.04s) forwards;
  transition: opacity 0.3s ease, stroke-width 0.3s ease;
}
.tone-easy { stroke: #e7c27a; }
.tone-tense { stroke: #c8796a; }
.aspect-dot {
  fill: #f0d6a2;
  opacity: 0;
  animation: show 0.6s ease calc(var(--d0) + 1.8s + var(--i) * 0.04s) forwards;
  --o: calc(0.4 + var(--s) * 0.5);
  transition: opacity 0.3s ease;
}
.has-focus .aspect.is-dim { opacity: 0.06; }
.has-focus .aspect-dot.is-dim { opacity: 0.1; animation: none; }
.aspect.is-lit { opacity: 0.95; stroke-width: 1.4; filter: drop-shadow(0 0 3px rgba(255, 200, 120, 0.5)); }
.aspect-dot.is-lit { opacity: 1; animation: none; }

.planet {
  pointer-events: auto;
  cursor: pointer;
  opacity: 0;
  animation: show 0.6s ease calc(var(--d0) + 1.3s + var(--i) * 0.06s) forwards;
  --o: 1;
}
.planet-hit { fill: transparent; }
.planet-dot { fill: #f6e2b6; opacity: 0.8; }
.planet-glyph {
  fill: #f6e6c4;
  filter: drop-shadow(0 0 4px rgba(255, 205, 120, 0.45));
  transition: fill 0.25s ease, filter 0.25s ease;
}
.planet-mark { font-family: var(--serif); font-style: italic; fill: rgba(240, 214, 162, 0.75); }
.planet.is-partner .planet-glyph { fill: #ffe7b5; }
.planet.is-on .planet-glyph, .planet.is-selected .planet-glyph {
  fill: #fff6df;
  filter: drop-shadow(0 0 6px rgba(255, 210, 130, 0.95));
}
.has-focus .planet:not(.is-on):not(.is-partner):not(.is-selected) .planet-glyph { fill: rgba(246, 230, 196, 0.55); }

/* The day's sky: cool silver, so it never reads as part of the birth chart. */
.ring-transit { stroke: #c4d4ec; opacity: 0.22; stroke-dasharray: 0.004 0.008; stroke-dashoffset: 0; animation: show 1s ease calc(var(--d0) + 0.4s) both; --o: 0.22; }
.transit {
  pointer-events: auto;
  cursor: default;
  opacity: 0;
  animation: show 0.6s ease calc(var(--d0) + 1.5s + var(--i) * 0.06s) forwards;
  --o: 1;
}
.transit-tick { stroke: #c4d4ec; stroke-width: 1; vector-effect: non-scaling-stroke; opacity: 0.55; }
.transit-glyph {
  text-anchor: middle;
  dominant-baseline: central;
  font-family: 'Segoe UI Symbol', 'Noto Sans Symbols', 'Noto Sans Symbols 2', sans-serif;
  fill: #d6e2f4;
  filter: drop-shadow(0 0 4px rgba(170, 200, 255, 0.45));
  transition: fill 0.25s ease, filter 0.25s ease;
}
.transit-mark { fill: rgba(200, 216, 240, 0.75); }
.transit.is-on .transit-glyph, .transit.is-partner .transit-glyph { fill: #f4f8ff; filter: drop-shadow(0 0 7px rgba(180, 210, 255, 0.95)); }
.has-focus .transit:not(.is-on):not(.is-partner) .transit-glyph { fill: rgba(214, 226, 244, 0.5); }

/* The key transits glow from the start; the one under the pointer glows brighter. */
.transit-line path {
  fill: none;
  stroke-width: 1.3;
  vector-effect: non-scaling-stroke;
  stroke-dasharray: 1;
  stroke-dashoffset: 1;
  opacity: 0.75;
  filter: drop-shadow(0 0 4px rgba(255, 210, 140, 0.55));
  animation: draw 1s ease calc(var(--d0) + 2s + var(--i) * 0.15s) forwards;
  transition: opacity 0.3s ease, stroke-width 0.3s ease;
}
.transit-line.tone-easy path { stroke: #f0cd8a; }
.transit-line.tone-tense path { stroke: #e08a76; filter: drop-shadow(0 0 4px rgba(240, 130, 110, 0.55)); }
.transit-line.tone-joint path { stroke: #e6e0f4; filter: drop-shadow(0 0 4px rgba(200, 210, 255, 0.55)); }
.transit-line circle {
  fill: #d6e2f4;
  opacity: 0;
  animation: show 0.5s ease calc(var(--d0) + 2s + var(--i) * 0.15s) forwards;
  --o: 0.9;
}
.transit-line.is-lit path { opacity: 1; stroke-width: 1.8; }
.has-focus .transit-line.is-dim path { opacity: 0.18; }
.with-transits .planet:not(.is-partner):not(.is-on) .planet-glyph { fill: rgba(246, 230, 196, 0.8); }

@keyframes draw { to { stroke-dashoffset: 0; } }
@keyframes show { to { opacity: var(--o); } }

/* After the game: the rings draw at once beneath its fading picture, the planets take over its bodies. */
.is-landed { --d0: 0s; }
.is-landed .planet { animation: show 0.7s ease calc(0.2s + var(--i) * 0.03s) forwards; }

/* Without the flights: everything simply fades in at once. */
.motion-off .ring, .motion-off .aspect { stroke-dashoffset: 0; animation: none; }
.motion-off .ticks, .motion-off .dividers, .motion-off .cusp, .motion-off .sign-glyph,
.motion-off .transit-line path { stroke-dashoffset: 0; animation: none; }
.motion-off .house-number, .motion-off .axis-label, .motion-off .planet, .motion-off .aspect-dot,
.motion-off .transit, .motion-off .transit-line circle {
  animation: show 0.5s ease forwards;
}
</style>
