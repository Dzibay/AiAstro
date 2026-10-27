<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import LiveText from './LiveText.vue'
import { useChart } from '../../composables/useChart.js'
import { usePrices } from '../../utils/prices.js'

/**
 * The portrait as a walk around the wheel: one chapter at a time in the panel — the thought
 * of it, the astrology under it, a few plain sentences and how to use it — while the wheel lights
 * the planets, signs and houses the chapter speaks of (the `lens` of useChart) and dims the rest.
 * Without «Небосвод» the first chapter is open and the others are named behind the haze.
 */
const props = defineProps({
  /** GET /me/chart/portrait: { reading: { essence, parts, outline? }, total, locked }. */
  portrait: { type: Object, required: true },
})

const { lens } = useChart()
const { sky: skyPrice } = usePrices()

const chapters = computed(() => props.portrait.reading.parts)
const outline = computed(() => (props.portrait.locked ? props.portrait.reading.outline || [] : []))
/** The chapters, then one more screen when some of them are behind the haze. */
const screens = computed(() => chapters.value.length + (outline.value.length ? 1 : 0))
const total = computed(() => Math.max(props.portrait.total || 0, chapters.value.length))

const at = ref(kept.essence === props.portrait.reading.essence ? Math.min(kept.at, screens.value - 1) : 0)
const forward = ref(true)
const chapter = computed(() => chapters.value[at.value] || null)
const isLast = computed(() => at.value >= screens.value - 1)

function go(index) {
  if (index < 0 || index >= screens.value || index === at.value) return
  forward.value = index > at.value
  at.value = index
  kept.essence = props.portrait.reading.essence
  kept.at = index
}
const next = () => go(isLast.value ? 0 : at.value + 1)
const prev = () => go(at.value - 1)

function onKey(event) {
  if (event.target.closest('input, textarea')) return
  if (event.key === 'ArrowRight') next()
  else if (event.key === 'ArrowLeft') prev()
  else return
  event.preventDefault()
}

/* ---- The wheel follows the chapter while the walk is in view ---- */

const root = ref(null)
const head = ref(null)
const seen = ref(false)
let observer = null
let mine = null

function light() {
  const focus = seen.value ? chapter.value?.focus : null
  const empty = !focus || !['points', 'signs', 'houses'].some((key) => focus[key]?.length)
  if (empty) {
    if (mine && lens.value === mine) lens.value = null
    mine = null
    return
  }
  mine = focus
  lens.value = focus
}
watch([seen, chapter], light)

onMounted(() => {
  observer = new IntersectionObserver(([entry]) => {
    seen.value = entry.isIntersecting && entry.intersectionRatio >= 0.3
  }, { threshold: [0, 0.3, 0.6] })
  observer.observe(root.value)
})
onBeforeUnmount(() => {
  observer?.disconnect()
  if (mine && lens.value === mine) lens.value = null
})

// A new chapter keeps its top in view, so the reader starts it from its first line.
watch(at, async () => {
  await nextTick()
  head.value?.scrollIntoView({ block: 'nearest', behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' })
})

/** «глава», «главы», «глав». */
function plural(count, one, few, many) {
  const tens = count % 100
  const units = count % 10
  if (tens >= 11 && tens <= 14) return many
  if (units === 1) return one
  if (units >= 2 && units <= 4) return few
  return many
}

const counter = computed(() => (chapter.value
  ? `Глава ${at.value + 1} из ${total.value}`
  : `Ещё ${outline.value.length} ${plural(outline.value.length, 'глава', 'главы', 'глав')}`))
</script>

<script>
// The chapter reached is kept for the visit: a planet opened from the text and «Вся карта» bring the reader back to it.
const kept = { essence: '', at: 0 }
</script>

<template>
  <div ref="root" class="portrait-walk" @keydown="onKey">
    <p v-if="portrait.reading.essence" class="essence">«{{ portrait.reading.essence.replace(/[.…]+$/, '') }}»</p>

    <div ref="head" class="walk-head">
      <div class="progress" role="group" aria-label="Главы портрета">
        <button
          v-for="(part, index) in chapters"
          :key="index"
          type="button"
          class="segment"
          :class="{ 'is-done': index < at, 'is-now': index === at }"
          :aria-label="`Глава ${index + 1}: ${part.title || part.label}`"
          :aria-current="index === at ? 'step' : undefined"
          @click="go(index)"
        />
        <button
          v-for="(title, index) in outline"
          :key="`o${index}`"
          type="button"
          class="segment is-locked"
          :class="{ 'is-now': !chapter }"
          :aria-label="`${title} — закрыто`"
          @click="go(chapters.length)"
        />
      </div>
      <p class="counter" aria-live="polite">
        {{ counter }}<template v-if="chapter"> · {{ chapter.label }}</template>
      </p>
    </div>

    <Transition :name="forward ? 'turn-next' : 'turn-back'" mode="out-in">
      <article v-if="chapter" :key="at" class="chapter">
        <p v-if="chapter.term" class="kicker"><LiveText :text="chapter.term" /></p>
        <h4 class="title">{{ chapter.title || chapter.label }}</h4>
        <p class="text"><LiveText :text="chapter.text" /></p>
        <div v-if="chapter.todo" class="todo">
          <span class="todo-label"><span aria-hidden="true">✦ </span>Как этим пользоваться</span>
          <p><LiveText :text="chapter.todo" /></p>
        </div>
      </article>

      <article v-else key="locked" class="chapter is-locked">
        <p class="kicker">За туманом</p>
        <h4 class="title">Ещё {{ outline.length }} {{ plural(outline.length, 'глава', 'главы', 'глав') }} вашего портрета</h4>
        <ol class="outline" :start="chapters.length + 1">
          <li v-for="(title, index) in outline" :key="index">
            <svg viewBox="0 0 12 14" aria-hidden="true"><rect x="1.5" y="6" width="9" height="7" rx="1.6" /><path d="M3.6 6V4.3a2.4 2.4 0 0 1 4.8 0V6" /></svg>
            {{ title }}
          </li>
        </ol>
        <p class="locked-note">Каждая глава зажжёт на колесе свои планеты и объяснит, как ими пользоваться.</p>
        <RouterLink class="unlock-cta" v-seen="'sky:portrait'" data-track="sky:portrait" :to="{ name: 'cabinet-sky' }">
          <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg>
          Зажечь Небосвод — {{ skyPrice }}
        </RouterLink>
      </article>
    </Transition>

    <nav class="walk-nav" aria-label="Листать главы">
      <button type="button" class="back" :disabled="at === 0" @click="prev">
        <span aria-hidden="true">←</span> Назад
      </button>
      <button v-if="!(isLast && !chapter)" type="button" class="next" @click="next">
        <template v-if="isLast">С начала <span aria-hidden="true">↺</span></template>
        <template v-else-if="at + 1 >= chapters.length">Что дальше <span aria-hidden="true">→</span></template>
        <template v-else>Далее <span aria-hidden="true">→</span></template>
      </button>
    </nav>
  </div>
</template>

<style scoped>
.portrait-walk { display: grid; gap: 14px; }
.essence {
  margin: 0 0 4px;
  font-family: var(--serif);
  font-style: italic;
  font-size: 21px;
  line-height: 1.35;
  text-align: center;
  color: #f6efe2;
}

.walk-head { display: grid; gap: 8px; scroll-margin-top: 16px; }
.progress { display: flex; gap: 4px; }
.segment {
  flex: 1;
  height: 14px;
  padding: 0;
  border: 0;
  background: none;
  cursor: pointer;
  position: relative;
}
/* The visible bar is thin; the button around it is tall enough to hit. */
.segment::before {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  top: 5px;
  height: 3px;
  border-radius: 2px;
  background: rgba(240, 220, 180, 0.16);
  transition: background 0.35s ease, box-shadow 0.35s ease;
}
.segment.is-done::before { background: rgba(240, 205, 138, 0.6); }
.segment.is-now::before { background: #f0cd8a; box-shadow: 0 0 8px rgba(255, 205, 120, 0.6); }
.segment.is-locked::before { background: none; border-top: 1px dashed rgba(240, 220, 180, 0.3); height: 0; top: 6px; }
.segment.is-locked.is-now::before { border-top-color: rgba(240, 205, 138, 0.8); box-shadow: none; }
.segment:hover:not(.is-now)::before { background: rgba(240, 205, 138, 0.4); }
.segment.is-locked:hover::before { background: none; border-top-color: rgba(240, 205, 138, 0.6); }
.segment:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 1px; border-radius: 3px; }
.counter { margin: 0; font-family: var(--caps); font-weight: 600; font-size: 13.5px; letter-spacing: 0.08em; color: rgba(240, 205, 138, 0.75); }

.chapter { display: grid; gap: 12px; align-content: start; }
.kicker {
  margin: 0;
  font-family: var(--caps);
  font-weight: 600;
  font-size: 14.5px;
  line-height: 1.4;
  letter-spacing: 0.05em;
  color: rgba(240, 205, 138, 0.88);
}
.title {
  margin: 0;
  font-family: var(--serif);
  font-weight: 500;
  font-size: 27px;
  line-height: 1.15;
  color: #f8f1e4;
  text-wrap: balance;
}
.text {
  margin: 0;
  font-family: var(--book);
  font-size: 15.5px;
  line-height: 1.72;
  hyphens: auto;
  color: #efe7d8;
}
.todo {
  display: grid;
  gap: 6px;
  margin-top: 2px;
  padding: 13px 15px;
  border-radius: 16px;
  border: 1px solid rgba(240, 205, 138, 0.4);
  background: linear-gradient(180deg, rgba(240, 205, 138, 0.1), rgba(240, 205, 138, 0.03));
}
.todo-label { font-family: var(--caps); font-weight: 600; font-size: 14px; letter-spacing: 0.08em; color: #f0cd8a; }
.todo p { margin: 0; font-family: var(--serif); font-style: italic; font-size: 17.5px; line-height: 1.45; color: #f8ead0; }

.outline { display: flex; flex-wrap: wrap; gap: 6px; margin: 0; padding: 0; list-style: none; }
.outline li {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 6px 11px;
  border-radius: 999px;
  border: 1px dashed rgba(240, 210, 150, 0.22);
  font-family: var(--book);
  font-size: 13.5px;
  line-height: 1.3;
  color: rgba(226, 220, 210, 0.75);
}
.outline svg { flex: none; width: 11px; height: 13px; fill: none; stroke: rgba(240, 205, 138, 0.7); stroke-width: 1.4; }
.locked-note { margin: 0; font-size: 13.5px; line-height: 1.55; color: rgba(233, 194, 124, 0.85); }
.unlock-cta {
  justify-self: start;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 11px 20px;
  border-radius: 999px;
  background: linear-gradient(180deg, #f4dba6, #dcb36c);
  color: #2b1d0b;
  font-size: 14.5px;
  font-weight: 600;
  text-decoration: none;
  box-shadow: 0 8px 26px rgba(230, 170, 80, 0.22);
  transition: box-shadow 0.25s ease, transform 0.25s ease;
}
.unlock-cta svg { width: 12px; height: 12px; fill: #2b1d0b; }
.unlock-cta:hover { box-shadow: 0 10px 34px rgba(230, 170, 80, 0.38); transform: translateY(-1px); }
.unlock-cta:focus-visible { outline: 2px solid #ffe2a8; outline-offset: 3px; }

.walk-nav { display: flex; justify-content: space-between; gap: 10px; margin-top: 2px; }
.back, .next {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 40px;
  padding: 0 18px;
  border-radius: 999px;
  font: inherit;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease, opacity 0.25s ease;
}
.back { border: 1px solid rgba(240, 220, 180, 0.2); background: rgba(255, 245, 225, 0.04); color: #efe7d8; }
.back:hover:not(:disabled) { border-color: rgba(240, 205, 138, 0.5); background: rgba(255, 245, 225, 0.09); }
.back:disabled { opacity: 0.3; cursor: default; }
.next { border: 1px solid rgba(240, 205, 138, 0.55); background: rgba(240, 205, 138, 0.12); color: #f6dca4; font-weight: 600; }
.next:hover { background: rgba(240, 205, 138, 0.2); border-color: rgba(240, 205, 138, 0.85); }
.back:focus-visible, .next:focus-visible { outline: 2px solid #ffe2a8; outline-offset: 3px; }

/* The chapters turn in the direction of reading. */
.turn-next-enter-active, .turn-next-leave-active, .turn-back-enter-active, .turn-back-leave-active {
  transition: opacity 0.2s ease, transform 0.26s cubic-bezier(0.25, 0.8, 0.25, 1);
}
.turn-next-enter-from, .turn-back-leave-to { opacity: 0; transform: translateX(22px); }
.turn-next-leave-to, .turn-back-enter-from { opacity: 0; transform: translateX(-22px); }

@media (max-width: 760px) {
  .essence { font-size: 19px; }
  .title { font-size: 24px; }
  .back, .next { flex: 1; justify-content: center; min-height: 44px; }
}
@media (prefers-reduced-motion: reduce) {
  .segment::before, .back, .next, .unlock-cta { transition: none; }
  .turn-next-enter-active, .turn-next-leave-active, .turn-back-enter-active, .turn-back-leave-active { transition: opacity 0.15s ease; }
  .turn-next-enter-from, .turn-back-leave-to, .turn-next-leave-to, .turn-back-enter-from { transform: none; }
}
</style>
