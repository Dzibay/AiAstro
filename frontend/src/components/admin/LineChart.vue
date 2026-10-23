<script setup>
/**
 * One share week by week: a 2px line with its points, a hairline grid, the last finished value
 * labelled, the rest in the crosshair tooltip (pointer or arrow keys) and in the table. The weeks
 * still being counted are dashed with hollow points: their people have not had their week yet.
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  /** [{ key, label (under the axis), title (tooltip head), value (0–1 or null), part, whole, done }] */
  points: { type: Array, required: true },
  color: { type: String, required: true },
  /** What the share is, for the tooltip and the table head. */
  name: { type: String, required: true },
  /** Who the share is of, for the tooltip: «из 310 посетителей». */
  of: { type: String, default: '' },
  height: { type: Number, default: 170 },
})

const box = ref(null)
const width = ref(360)
const active = ref(-1)
const table = ref(false)
let observer = null

onMounted(() => {
  width.value = box.value.clientWidth || 360
  observer = new ResizeObserver(([entry]) => {
    width.value = Math.max(220, Math.round(entry.contentRect.width))
  })
  observer.observe(box.value)
})
onBeforeUnmount(() => observer?.disconnect())

const PAD = { top: 18, right: 40, bottom: 24, left: 38 }
const SURFACE = '#141a18'

const percent = (rate) => {
  if (rate == null) return '—'
  const value = rate * 100
  return `${value.toLocaleString('ru-RU', { maximumFractionDigits: value < 10 && value > 0 ? 1 : 0 })}%`
}

/** A round top in per cent: 1, 2 or 5 times a power of ten, in about four steps. */
function niceStep(max) {
  if (max <= 0) return 5
  const raw = max / 4
  const power = 10 ** Math.floor(Math.log10(raw))
  return [1, 2, 5, 10].map((m) => m * power).find((s) => s >= raw)
}

const geo = computed(() => {
  const n = props.points.length
  const plotW = width.value - PAD.left - PAD.right
  const plotH = props.height - PAD.top - PAD.bottom
  const top = Math.max(...props.points.map((p) => (p.value == null ? 0 : p.value * 100)), 0)
  const step = niceStep(top)
  const max = Math.min(100, Math.max(step * Math.ceil(top / step), step))
  const ticks = []
  for (let v = 0; v <= max + step / 2; v += step) ticks.push(v)
  const x = (i) => PAD.left + (n > 1 ? (plotW * i) / (n - 1) : plotW / 2)
  const y = (v) => PAD.top + plotH - (v / max) * plotH
  const dots = props.points.map((p, i) => ({ ...p, i, cx: x(i), cy: p.value == null ? null : y(p.value * 100) }))
  // The line in pieces: solid between finished weeks, dashed from the last finished one on; a week
  // nobody came in breaks it.
  const solid = []
  const dashed = []
  for (let i = 1; i < n; i += 1) {
    const a = dots[i - 1]
    const b = dots[i]
    if (a.cy == null || b.cy == null) continue
    ;(a.done && b.done ? solid : dashed).push(`M${a.cx},${a.cy}L${b.cx},${b.cy}`)
  }
  const every = Math.max(1, Math.ceil(n / Math.max(1, Math.floor(plotW / 54))))
  const last = [...dots].reverse().find((d) => d.done && d.cy != null)
  return { plotH, ticks, y, dots, solid: solid.join(''), dashed: dashed.join(''), every, last, slot: plotW / Math.max(n - 1, 1), base: PAD.top + plotH }
})

const tip = computed(() => {
  const d = geo.value.dots[active.value]
  if (!d) return null
  const left = Math.min(Math.max(d.cx, 96), width.value - 96)
  return { ...d, left, top: d.cy == null ? geo.value.base - 8 : d.cy }
})

function onKey(event) {
  const n = props.points.length
  if (!n) return
  if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
    event.preventDefault()
    const from = active.value < 0 ? n - 1 : active.value
    active.value = Math.min(n - 1, Math.max(0, from + (event.key === 'ArrowRight' ? 1 : -1)))
  } else if (event.key === 'Escape') {
    active.value = -1
  }
}
</script>

<template>
  <div ref="box" class="lc">
    <template v-if="!table">
      <svg
        class="lc-svg"
        :width="width"
        :height="height"
        :viewBox="`0 0 ${width} ${height}`"
        role="img"
        tabindex="0"
        :aria-label="`${name}: по неделям, стрелки — значения`"
        @keydown="onKey"
        @focus="active = active < 0 ? points.length - 1 : active"
        @blur="active = -1"
        @pointerleave="active = -1"
      >
        <g class="lc-grid">
          <template v-for="tick in geo.ticks" :key="tick">
            <line :x1="38" :x2="width - 40" :y1="geo.y(tick)" :y2="geo.y(tick)" :class="{ 'is-base': tick === 0 }" />
            <text :x="30" :y="geo.y(tick)" dy="0.32em" text-anchor="end">{{ tick }}%</text>
          </template>
        </g>
        <line v-if="tip" class="lc-cross" :x1="tip.cx" :x2="tip.cx" :y1="18" :y2="geo.base" />
        <path :d="geo.solid" :stroke="color" class="lc-line" />
        <path :d="geo.dashed" :stroke="color" class="lc-line is-open" />
        <template v-for="d in geo.dots" :key="d.key">
          <circle
            v-if="d.cy != null"
            :cx="d.cx"
            :cy="d.cy"
            :r="active === d.i ? 5.5 : 4"
            :fill="d.done ? color : SURFACE"
            :stroke="d.done ? SURFACE : color"
            :stroke-width="2"
          />
        </template>
        <text v-if="geo.last && active < 0" class="lc-end" :x="geo.last.cx + 9" :y="geo.last.cy" dy="0.32em">{{ percent(geo.last.value) }}</text>
        <g class="lc-x">
          <template v-for="d in geo.dots" :key="`x-${d.key}`">
            <text v-if="(geo.dots.length - 1 - d.i) % geo.every === 0" :x="d.cx" :y="height - 6" text-anchor="middle">{{ d.label }}</text>
          </template>
        </g>
        <!-- Hit areas: a whole slot around each week, not only the point. -->
        <rect
          v-for="d in geo.dots"
          :key="`hit-${d.key}`"
          :x="d.cx - geo.slot / 2"
          :y="0"
          :width="geo.slot"
          :height="geo.base"
          fill="transparent"
          @pointerenter="active = d.i"
          @pointermove="active = d.i"
        />
      </svg>
      <div v-if="tip" class="lc-tip" :style="{ left: `${tip.left}px`, top: `${tip.top}px` }" aria-live="polite">
        <span class="lc-tip-head">{{ tip.title }}</span>
        <span class="lc-tip-row"><i :style="{ background: color }" /><strong>{{ percent(tip.value) }}</strong>{{ tip.whole ? ` · ${tip.part} из ${tip.whole}${of ? ` ${of}` : ''}` : ' · никого' }}</span>
        <span v-if="!tip.done" class="lc-tip-note">неделя ещё досчитывается</span>
      </div>
    </template>
    <div v-else class="lc-table">
      <table>
        <thead><tr><th>Неделя</th><th class="num">{{ name }}</th><th class="num">Из скольких</th></tr></thead>
        <tbody>
          <tr v-for="p in points" :key="p.key">
            <td>{{ p.title }}<span v-if="!p.done" class="lc-open"> · досчитывается</span></td>
            <td class="num">{{ percent(p.value) }}</td>
            <td class="num">{{ p.part }} из {{ p.whole }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <button type="button" class="text-button lc-toggle" :aria-pressed="table" @click="table = !table">
      {{ table ? 'Показать график' : 'Таблицей' }}
    </button>
  </div>
</template>

<style scoped>
.lc { position: relative; min-width: 0; }
.lc-svg { display: block; overflow: visible; outline: none; touch-action: pan-y; }
.lc-svg:focus-visible { outline: 2px solid rgba(224, 193, 122, 0.45); outline-offset: 4px; border-radius: 8px; }
.lc-grid line { stroke: rgba(244, 239, 230, 0.08); stroke-width: 1; shape-rendering: crispEdges; }
.lc-grid line.is-base { stroke: rgba(244, 239, 230, 0.2); }
.lc-grid text, .lc-x text { fill: rgba(244, 239, 230, 0.5); font-size: 11px; font-variant-numeric: tabular-nums; }
.lc-line { fill: none; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
.lc-line.is-open { stroke-dasharray: 4 4; }
.lc-end { fill: var(--ink); font-size: 12px; font-weight: 600; font-variant-numeric: tabular-nums; }
.lc-cross { stroke: rgba(244, 239, 230, 0.25); stroke-width: 1; pointer-events: none; }
.lc-tip {
  position: absolute;
  z-index: 2;
  display: grid;
  gap: 2px;
  min-width: 150px;
  padding: 8px 12px;
  translate: -50% calc(-100% - 12px);
  border: 1px solid rgba(244, 239, 230, 0.14);
  border-radius: 12px;
  background: #18211d;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
  font-size: 13px;
  pointer-events: none;
  white-space: nowrap;
}
.lc-tip-head { color: var(--muted); }
.lc-tip-row { display: flex; align-items: center; gap: 6px; color: var(--muted); }
.lc-tip-row i { width: 12px; height: 3px; border-radius: 2px; margin-right: 2px; }
.lc-tip-row strong { color: var(--ink); font-size: 15px; }
.lc-tip-note { color: var(--soft); font-size: 12px; }
.lc-toggle { margin-top: 4px; font-size: 13px; }
.lc-toggle:hover { color: var(--ink); }
.lc-table { max-height: 220px; overflow: auto; }
.lc-table table { width: 100%; border-collapse: collapse; font-size: 13px; }
.lc-table th { position: sticky; top: 0; background: #151d1a; color: var(--muted); font-weight: 500; text-align: left; padding: 6px 8px; }
.lc-table td { padding: 5px 8px; border-top: 1px solid rgba(244, 239, 230, 0.07); }
.lc-table .num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
.lc-open { color: var(--soft); }
</style>
