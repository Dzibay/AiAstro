<script setup>
/**
 * One series of columns over time: thin columns from one baseline, a hairline grid,
 * the highest column labelled, the rest in the tooltip (pointer or arrow keys) and in the table.
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  /** [{ key, label (under the axis), title (tooltip head), value }] */
  points: { type: Array, required: true },
  color: { type: String, required: true },
  /** What the series is, for the tooltip row and the table head. */
  name: { type: String, required: true },
  format: { type: Function, default: (value) => String(value) },
  axisFormat: { type: Function, default: (value) => String(value) },
  height: { type: Number, default: 220 },
})

const box = ref(null)
const width = ref(640)
const active = ref(-1)
const table = ref(false)
let observer = null

onMounted(() => {
  width.value = box.value.clientWidth || 640
  observer = new ResizeObserver(([entry]) => {
    width.value = Math.max(240, Math.round(entry.contentRect.width))
  })
  observer.observe(box.value)
})
onBeforeUnmount(() => observer?.disconnect())

const PAD = { top: 24, right: 6, bottom: 28, left: 46 }

/** A round top for the axis: 1, 2 or 5 times a power of ten, in four steps. */
function niceStep(max) {
  if (max <= 0) return 1
  const raw = max / 4
  const power = 10 ** Math.floor(Math.log10(raw))
  const step = [1, 2, 5, 10].map((m) => m * power).find((s) => s >= raw)
  return Math.max(step, 1)
}

const geo = computed(() => {
  const n = props.points.length
  const plotW = width.value - PAD.left - PAD.right
  const plotH = props.height - PAD.top - PAD.bottom
  const top = Math.max(...props.points.map((p) => p.value), 0)
  const step = niceStep(top)
  const max = Math.max(step * Math.ceil(top / step), step)
  const ticks = []
  for (let v = 0; v <= max + step / 2; v += step) ticks.push(v)
  const slot = plotW / Math.max(n, 1)
  const bar = Math.max(2, Math.min(24, slot * 0.68))
  const y = (v) => PAD.top + plotH - (v / max) * plotH
  const bars = props.points.map((p, i) => {
    const cx = PAD.left + slot * i + slot / 2
    const h = (p.value / max) * plotH
    return { ...p, i, cx, x: cx - bar / 2, h, y: y(p.value) }
  })
  // As many labels under the axis as fit, every k-th one, from the first.
  const every = Math.max(1, Math.ceil(n / Math.max(1, Math.floor(plotW / 62))))
  let peak = -1
  bars.forEach((b) => {
    if (b.value > 0 && (peak < 0 || b.value > bars[peak].value)) peak = b.i
  })
  return { plotW, plotH, ticks, y, slot, bar, bars, every, peak, base: PAD.top + plotH }
})

/** A column with a 4px round top and a square foot. */
function column(b) {
  const w = geo.value.bar
  const h = Math.max(b.h, 0)
  if (h <= 0) return ''
  const r = Math.min(4, w / 2, h)
  const x = b.x
  const yTop = geo.value.base - h
  return `M${x},${geo.value.base}V${yTop + r}Q${x},${yTop} ${x + r},${yTop}H${x + w - r}Q${x + w},${yTop} ${x + w},${yTop + r}V${geo.value.base}Z`
}

const tip = computed(() => {
  const b = geo.value.bars[active.value]
  if (!b) return null
  const left = Math.min(Math.max(b.cx, 90), width.value - 90)
  return { ...b, left, top: Math.min(b.y, geo.value.base - 8) }
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
  <div ref="box" class="cc">
    <template v-if="!table">
      <svg
        class="cc-svg"
        :width="width"
        :height="height"
        :viewBox="`0 0 ${width} ${height}`"
        role="img"
        tabindex="0"
        :aria-label="`${name}: график по периодам, стрелки — значения`"
        @keydown="onKey"
        @focus="active = active < 0 ? points.length - 1 : active"
        @blur="active = -1"
        @pointerleave="active = -1"
      >
        <g class="cc-grid">
          <template v-for="tick in geo.ticks" :key="tick">
            <line :x1="46" :x2="width - 6" :y1="geo.y(tick)" :y2="geo.y(tick)" :class="{ 'is-base': tick === 0 }" />
            <text :x="38" :y="geo.y(tick)" dy="0.32em" text-anchor="end">{{ axisFormat(tick) }}</text>
          </template>
        </g>
        <g>
          <path
            v-for="b in geo.bars"
            :key="b.key"
            :d="column(b)"
            :fill="color"
            class="cc-bar"
            :class="{ 'is-dim': active >= 0 && active !== b.i }"
          />
        </g>
        <text
          v-if="geo.peak >= 0 && active < 0"
          class="cc-peak"
          :x="geo.bars[geo.peak].cx"
          :y="geo.bars[geo.peak].y - 7"
          text-anchor="middle"
        >{{ format(geo.bars[geo.peak].value) }}</text>
        <g class="cc-x">
          <template v-for="b in geo.bars" :key="b.key">
            <text v-if="b.i % geo.every === 0" :x="b.cx" :y="height - 8" text-anchor="middle">{{ b.label }}</text>
          </template>
        </g>
        <line v-if="tip" class="cc-cross" :x1="tip.cx" :x2="tip.cx" :y1="24" :y2="geo.base" />
        <!-- Hit areas: the whole column of the slot, not only the painted bar. -->
        <rect
          v-for="b in geo.bars"
          :key="`hit-${b.key}`"
          :x="b.cx - geo.slot / 2"
          :y="0"
          :width="geo.slot"
          :height="geo.base"
          fill="transparent"
          @pointerenter="active = b.i"
          @pointermove="active = b.i"
        />
      </svg>
      <div v-if="tip" class="cc-tip" :style="{ left: `${tip.left}px`, top: `${tip.top}px` }" aria-live="polite">
        <span class="cc-tip-head">{{ tip.title }}</span>
        <span class="cc-tip-row"><i :style="{ background: color }" /><strong>{{ format(tip.value) }}</strong> {{ name.toLowerCase() }}</span>
      </div>
    </template>
    <div v-else class="cc-table">
      <table>
        <thead><tr><th>Период</th><th class="num">{{ name }}</th></tr></thead>
        <tbody>
          <tr v-for="p in points" :key="p.key"><td>{{ p.title }}</td><td class="num">{{ format(p.value) }}</td></tr>
        </tbody>
      </table>
    </div>
    <button type="button" class="text-button cc-toggle" :aria-pressed="table" @click="table = !table">
      {{ table ? 'Показать график' : 'Таблицей' }}
    </button>
  </div>
</template>

<style scoped>
.cc { position: relative; min-width: 0; }
.cc-svg { display: block; overflow: visible; outline: none; touch-action: pan-y; }
.cc-svg:focus-visible { outline: 2px solid rgba(224, 193, 122, 0.45); outline-offset: 4px; border-radius: 8px; }
.cc-grid line { stroke: rgba(244, 239, 230, 0.08); stroke-width: 1; shape-rendering: crispEdges; }
.cc-grid line.is-base { stroke: rgba(244, 239, 230, 0.2); }
.cc-grid text, .cc-x text { fill: rgba(244, 239, 230, 0.5); font-size: 12px; font-variant-numeric: tabular-nums; }
.cc-bar { transition: opacity 0.15s ease; }
.cc-bar.is-dim { opacity: 0.45; }
.cc-peak { fill: var(--ink); font-size: 12px; font-weight: 600; }
.cc-cross { stroke: rgba(244, 239, 230, 0.25); stroke-width: 1; pointer-events: none; }
.cc-tip {
  position: absolute;
  z-index: 2;
  display: grid;
  gap: 2px;
  min-width: 140px;
  padding: 8px 12px;
  translate: -50% calc(-100% - 10px);
  border: 1px solid rgba(244, 239, 230, 0.14);
  border-radius: 12px;
  background: #18211d;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
  font-size: 13px;
  pointer-events: none;
  white-space: nowrap;
}
.cc-tip-head { color: var(--muted); }
.cc-tip-row { display: flex; align-items: center; gap: 8px; color: var(--muted); }
.cc-tip-row i { width: 12px; height: 3px; border-radius: 2px; }
.cc-tip-row strong { color: var(--ink); font-size: 15px; }
.cc-toggle { margin-top: 6px; font-size: 13px; }
.cc-toggle:hover { color: var(--ink); }
.cc-table { max-height: 240px; overflow: auto; }
.cc-table table { width: 100%; border-collapse: collapse; font-size: 14px; }
.cc-table th { position: sticky; top: 0; background: #151d1a; color: var(--muted); font-weight: 500; text-align: left; padding: 6px 8px; }
.cc-table td { padding: 5px 8px; border-top: 1px solid rgba(244, 239, 230, 0.07); }
.cc-table .num { text-align: right; font-variant-numeric: tabular-nums; }
</style>
