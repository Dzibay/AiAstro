<script setup>
import { computed, nextTick, onUnmounted, ref, watch } from 'vue'

/**
 * A reading as screens, one thought each, read like stories: { essence, parts, outline? }.
 *
 * In the panel stays the cover — the essence and the names of the screens; the reader opens over
 * the page with a progress line, a step back and «далее», swipes and the arrow keys, and on every
 * screen that has one, «Что делать». A part is { label, text, title?, term?, score?, tone?, todo?,
 * items?, kind? }: kind "years" is the pair's timeline (its locked form shows one period and
 * counts the `hidden` rest), kind "plan" — numbered steps. A locked reading names the screens
 * behind the haze (`outline`), and its last screen is the way to open them (slot `locked`).
 */

const props = defineProps({
  reading: { type: Object, required: true },
  locked: { type: Boolean, default: false },
  /** The reader's name for assistive technology: «Прогноз дня», «Разбор пары». */
  name: { type: String, required: true },
  /** The heading of the locked reader's last screen. */
  lockedTitle: { type: String, default: 'Дальше — в полной версии' },
})
const emit = defineEmits(['open'])

const plural = (count, one, few, many) => {
  const teen = count % 100 >= 11 && count % 100 <= 14
  if (count % 10 === 1 && !teen) return one
  return count % 10 >= 2 && count % 10 <= 4 && !teen ? few : many
}

const screens = computed(() => props.reading.parts.map((part) => ({
  ...part,
  heading: part.title || part.label,
  // The astrology of the screen, or its section when the heading says something else. It follows the heading.
  kicker: part.term || (part.title && part.title !== part.label ? part.label : ''),
  items: (part.items || []).filter((item) => item.text),
  // One short thought and nothing else on the screen (the advice of the day): it is set as a quote.
  short: !part.kind && !part.todo && !(part.items || []).some((item) => item.text) && (part.text || '').length < 180,
})))
const outline = computed(() => (props.locked ? props.reading.outline || [] : []))
const total = computed(() => screens.value.length + (outline.value.length ? 1 : 0))

const words = computed(() => screens.value.reduce((sum, screen) => {
  const parts = [screen.text, screen.todo, ...screen.items.flatMap((item) => [item.title, item.text, item.todo])]
  return sum + parts.filter(Boolean).join(' ').split(/\s+/).length
}, 0))
const minutes = computed(() => Math.max(1, Math.round(words.value / 170)))

/* ---- The reader ---- */

const at = ref(-1)
const isOpen = computed(() => at.value >= 0)
const last = ref(0)
const forward = ref(true)
const dialog = ref(null)
const body = ref(null)
const nextButton = ref(null)
let opener = null

const screen = computed(() => (at.value < screens.value.length ? screens.value[at.value] : null))
const isLast = computed(() => at.value === total.value - 1)

function open(index = 0) {
  opener = document.activeElement
  forward.value = true
  at.value = Math.min(index, total.value - 1)
  emit('open', at.value)
}
function close() {
  if (!isOpen.value) return
  // Read to the end: the next time starts from the beginning; left midway, it goes on from there.
  last.value = isLast.value ? 0 : at.value
  at.value = -1
}
function go(index) {
  if (index < 0 || index >= total.value) return
  forward.value = index > at.value
  at.value = index
}
const next = () => (isLast.value ? close() : go(at.value + 1))
const prev = () => go(at.value - 1)

watch(isOpen, async (value) => {
  document.documentElement.classList.toggle('stories-open', value)
  if (value) {
    await nextTick()
    nextButton.value?.focus({ preventScroll: true })
  } else if (opener && document.contains(opener)) {
    opener.focus({ preventScroll: true })
  }
})
watch(at, () => {
  if (body.value) body.value.scrollTop = 0
})
// A reading changed under an open reader (another pair, «Небосвод» opened): it closes.
watch(() => props.reading, () => {
  at.value = -1
  last.value = 0
})
onUnmounted(() => document.documentElement.classList.remove('stories-open'))

function onKey(event) {
  if (event.key === 'Escape') {
    event.preventDefault()
    close()
  } else if (event.key === 'ArrowRight') {
    event.preventDefault()
    if (!isLast.value) next()
  } else if (event.key === 'ArrowLeft') {
    event.preventDefault()
    prev()
  } else if (event.key === 'Tab') {
    // The focus stays inside the reader.
    const focusable = [...dialog.value.querySelectorAll('button:not([disabled]), a[href], [tabindex="0"]')]
    if (!focusable.length) return
    const first = focusable[0]
    const end = focusable[focusable.length - 1]
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault()
      end.focus()
    } else if (!event.shiftKey && document.activeElement === end) {
      event.preventDefault()
      first.focus()
    }
  }
}

/* A swipe sideways turns the screen; an upright one scrolls it. */
let touch = null
function onDown(event) {
  if (event.pointerType === 'mouse') return
  touch = { x: event.clientX, y: event.clientY, time: event.timeStamp }
}
function onUp(event) {
  if (!touch) return
  const dx = event.clientX - touch.x
  const dy = event.clientY - touch.y
  const quick = event.timeStamp - touch.time < 700
  touch = null
  if (!quick || Math.abs(dx) < 48 || Math.abs(dx) < Math.abs(dy) * 1.4) return
  if (dx < 0) {
    if (!isLast.value) next()
  } else {
    prev()
  }
}

// The page may open the reader at a screen of its own: the pair's timeline opens its «Пять лет».
defineExpose({ open })

const readLabel = computed(() => {
  if (props.locked) return 'Читать начало'
  if (last.value > 0) return `Продолжить с экрана ${last.value + 1}`
  return 'Читать'
})
</script>

<template>
  <div class="reading-stories">
    <p v-if="reading.essence" class="essence">«{{ reading.essence.replace(/[.…]+$/, '') }}»</p>

    <ol class="contents" :aria-label="`Экраны: ${name}`">
      <li v-for="(item, index) in screens" :key="`s${index}`">
        <button type="button" class="chapter" :class="item.tone && `tone-${item.tone}`" @click="open(index)">
          <span class="chapter-number" aria-hidden="true">{{ index + 1 }}</span>{{ item.heading }}
        </button>
      </li>
      <li v-for="(title, index) in outline" :key="`o${index}`">
        <button type="button" class="chapter is-locked" :aria-label="`${title} — закрыто`" @click="open(screens.length)">
          <svg viewBox="0 0 12 14" aria-hidden="true"><rect x="1.5" y="6" width="9" height="7" rx="1.6" /><path d="M3.6 6V4.3a2.4 2.4 0 0 1 4.8 0V6" /></svg>{{ title }}
        </button>
      </li>
    </ol>

    <div class="cover-actions">
      <button type="button" class="read" @click="open(locked ? 0 : last)">
        {{ readLabel }} <span aria-hidden="true">→</span>
      </button>
      <span class="cover-meta">
        <template v-if="locked">{{ screens.length }} {{ plural(screens.length, 'экран открыт', 'экрана открыты', 'экранов открыто') }}<template v-if="outline.length"> · ещё {{ outline.length }} за туманом</template></template>
        <template v-else>{{ screens.length }} {{ plural(screens.length, 'экран', 'экрана', 'экранов') }} · {{ minutes }} мин</template>
      </span>
    </div>

    <Teleport to="body">
      <Transition name="stories">
        <div v-if="isOpen" ref="dialog" class="stories" role="dialog" aria-modal="true" :aria-label="name" @keydown="onKey">
          <div class="stories-backdrop" aria-hidden="true" @click="close" />
          <div class="stories-card" @pointerdown="onDown" @pointerup="onUp" @pointercancel="touch = null">
            <header class="stories-top">
              <div class="progress" aria-hidden="true">
                <span v-for="index in total" :key="index" class="segment" :class="{ 'is-done': index - 1 < at, 'is-now': index - 1 === at }" />
              </div>
              <div class="top-row">
                <span class="counter">{{ name }} · {{ at + 1 }} из {{ total }}</span>
                <button type="button" class="close" aria-label="Закрыть" @click="close">
                  <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3 3L13 13M13 3L3 13" /></svg>
                </button>
              </div>
            </header>

            <div ref="body" class="stories-body">
              <Transition :name="forward ? 'turn-next' : 'turn-back'" mode="out-in">
                <article v-if="screen" :key="at" class="screen" :class="[screen.tone && `tone-${screen.tone}`, { 'is-short': screen.short }]">
                  <span class="glow" aria-hidden="true" />
                  <h2 class="title">{{ screen.heading }}</h2>
                  <p v-if="screen.kicker" class="kicker">{{ screen.kicker }}</p>
                  <p v-if="screen.score" class="score" :aria-label="`${screen.score} из 5`">
                    <span v-for="index in 5" :key="index" class="score-dot" :class="{ 'is-on': index <= screen.score }" aria-hidden="true" />
                  </p>
                  <p v-if="screen.text" class="text">{{ screen.text }}</p>

                  <template v-if="screen.kind === 'years'">
                    <ol class="years">
                      <li v-for="(item, index) in screen.items" :key="index" class="year" :class="item.tone && `tone-${item.tone}`">
                        <span class="year-when">{{ item.name }}</span>
                        <strong class="year-title">{{ item.title }}</strong>
                        <p class="year-text">{{ item.text }}</p>
                        <p v-if="item.todo" class="year-todo"><span aria-hidden="true">✦ </span>{{ item.todo }}</p>
                      </li>
                      <!-- The periods behind the haze: their place on the thread, not their words. -->
                      <li v-for="index in screen.hidden || 0" :key="`h${index}`" class="year is-hidden" aria-hidden="true">
                        <span class="year-when">░░░░░ ░░░░</span>
                        <strong class="year-title">░░░░░░░ ░░░░░░</strong>
                        <p class="year-text">░░░░░ ░░░ ░░░░░░░░ ░░░░ ░░░░░░ ░░░░░░░░░░ ░░░░</p>
                      </li>
                    </ol>
                    <p v-if="screen.hidden" class="hidden-note">
                      Ещё {{ screen.hidden }} {{ plural(screen.hidden, 'период', 'периода', 'периодов') }} с датами и советами — в полном разборе.
                    </p>
                  </template>

                  <ol v-else-if="screen.kind === 'plan'" class="plan">
                    <li v-for="(item, index) in screen.items" :key="index" class="step">
                      <span class="step-number" aria-hidden="true">{{ index + 1 }}</span>
                      <span class="step-copy"><strong>{{ item.name }}</strong> {{ item.text }}</span>
                    </li>
                  </ol>

                  <ul v-else-if="screen.items.length" class="items">
                    <li v-for="(item, index) in screen.items" :key="index" class="item" :class="item.tone && `tone-${item.tone}`">
                      <span v-if="item.name" class="item-name">{{ item.name }}</span>
                      <span class="item-text">{{ item.text }}</span>
                    </li>
                  </ul>

                  <div v-if="screen.todo" class="todo">
                    <span class="todo-label"><span aria-hidden="true">✦ </span>Что делать</span>
                    <p>{{ screen.todo }}</p>
                  </div>
                </article>

                <article v-else :key="'locked'" class="screen is-locked-screen">
                  <span class="glow" aria-hidden="true" />
                  <h2 class="title">{{ lockedTitle }}</h2>
                  <p class="kicker">За туманом</p>
                  <ul class="outline">
                    <li v-for="(title, index) in outline" :key="index">
                      <svg viewBox="0 0 12 14" aria-hidden="true"><rect x="1.5" y="6" width="9" height="7" rx="1.6" /><path d="M3.6 6V4.3a2.4 2.4 0 0 1 4.8 0V6" /></svg>
                      {{ title }}
                    </li>
                  </ul>
                  <slot name="locked" :close="close" />
                </article>
              </Transition>
            </div>

            <footer class="stories-nav">
              <button type="button" class="back" :disabled="at === 0" @click="prev">
                <span aria-hidden="true">←</span> Назад
              </button>
              <button ref="nextButton" type="button" class="next" @click="next">
                <template v-if="isLast">Готово</template>
                <template v-else>Далее <span aria-hidden="true">→</span></template>
              </button>
            </footer>
            <p class="sr-only" aria-live="polite">Экран {{ at + 1 }} из {{ total }}: {{ screen ? screen.heading : lockedTitle }}</p>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.reading-stories { display: grid; gap: 16px; }
.essence {
  margin: 0;
  font-family: var(--serif);
  font-style: italic;
  font-size: 22px;
  line-height: 1.35;
  text-align: center;
  color: #f6efe2;
}

/* ---- The cover: the screens as a table of contents ---- */
.contents { display: flex; flex-wrap: wrap; justify-content: center; gap: 6px; margin: 0; padding: 0; list-style: none; }
.chapter {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 6px 12px 6px 7px;
  border-radius: 999px;
  border: 1px solid rgba(240, 210, 150, 0.18);
  background: rgba(255, 240, 210, 0.03);
  font-family: var(--book);
  font-size: 13.5px;
  line-height: 1.2;
  color: #efe7d8;
  cursor: pointer;
  transition: border-color 0.25s ease, background 0.25s ease;
}
.chapter:hover { border-color: rgba(240, 205, 138, 0.55); background: rgba(240, 205, 138, 0.08); }
.chapter:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 2px; }
.chapter-number {
  display: inline-grid;
  place-items: center;
  min-width: 20px;
  height: 20px;
  border-radius: 999px;
  background: rgba(240, 205, 138, 0.12);
  font-family: var(--caps);
  font-weight: 600;
  font-size: 13px;
  color: #f0cd8a;
}
.chapter.tone-easy .chapter-number { box-shadow: inset 0 0 0 1px rgba(240, 205, 138, 0.55); }
.chapter.tone-tense .chapter-number { color: #e8a594; background: rgba(217, 139, 122, 0.14); }
.chapter.is-locked { padding-left: 11px; color: rgba(226, 220, 210, 0.45); border-style: dashed; }
.chapter.is-locked svg { width: 10px; height: 12px; fill: none; stroke: currentColor; stroke-width: 1.4; }

.cover-actions { display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: 10px 16px; }
.read {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 11px 22px;
  border: 0;
  border-radius: 999px;
  background: linear-gradient(180deg, #f4dba6, #dcb36c);
  color: #2b1d0b;
  font: inherit;
  font-size: 14.5px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 8px 26px rgba(230, 170, 80, 0.22);
  transition: box-shadow 0.25s ease, transform 0.25s ease;
}
.read:hover { box-shadow: 0 10px 34px rgba(230, 170, 80, 0.38); transform: translateY(-1px); }
.read:focus-visible { outline: 2px solid #ffe2a8; outline-offset: 3px; }
.cover-meta { font-family: var(--serif); font-style: italic; font-size: 15px; color: rgba(226, 220, 210, 0.6); }

/* ---- The reader ---- */
.stories {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: grid;
  place-items: center;
  padding: 24px;
}
.stories-backdrop { position: absolute; inset: 0; background: rgba(5, 7, 16, 0.82); }
.stories-card {
  position: relative;
  display: grid;
  grid-template-rows: auto 1fr auto;
  width: min(560px, 100%);
  height: min(700px, calc(100dvh - 48px));
  overflow: hidden;
  border-radius: 26px;
  border: 1px solid rgba(240, 210, 150, 0.2);
  background: linear-gradient(180deg, #151b35 0%, #0d1126 55%, #0a0d1d 100%);
  box-shadow: 0 30px 90px rgba(0, 0, 0, 0.55);
  touch-action: pan-y;
}

.stories-top { position: relative; z-index: 2; display: grid; gap: 10px; padding: 16px 18px 6px; }
.progress { display: flex; gap: 4px; }
.segment { flex: 1; height: 3px; border-radius: 2px; background: rgba(240, 220, 180, 0.16); transition: background 0.35s ease; }
.segment.is-done { background: rgba(240, 205, 138, 0.6); }
.segment.is-now { background: #f0cd8a; box-shadow: 0 0 8px rgba(255, 205, 120, 0.6); }
.top-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.counter { font-family: var(--caps); font-weight: 600; font-size: 14px; letter-spacing: 0.08em; color: rgba(240, 205, 138, 0.75); }
.close {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 1px solid rgba(240, 220, 180, 0.22);
  background: rgba(255, 245, 225, 0.06);
  -webkit-backdrop-filter: blur(10px);
  backdrop-filter: blur(10px);
  color: #efe7d8;
  cursor: pointer;
  transition: background 0.25s ease, border-color 0.25s ease;
}
.close svg { width: 13px; height: 13px; stroke: currentColor; stroke-width: 1.6; stroke-linecap: round; }
.close:hover { background: rgba(255, 245, 225, 0.12); border-color: rgba(240, 205, 138, 0.5); }
.close:focus-visible { outline: 2px solid #f0cd8a; outline-offset: 2px; }

.stories-body { position: relative; overflow-x: hidden; overflow-y: auto; overscroll-behavior: contain; padding: 6px 26px 22px; }
.screen { position: relative; display: grid; gap: 14px; align-content: start; }
.glow {
  position: absolute;
  top: -140px;
  left: 50%;
  width: 420px;
  height: 260px;
  transform: translateX(-50%);
  border-radius: 50%;
  background: radial-gradient(closest-side, rgba(180, 196, 240, 0.12), transparent);
  pointer-events: none;
}
.tone-easy > .glow { background: radial-gradient(closest-side, rgba(255, 205, 120, 0.16), transparent); }
.tone-tense > .glow { background: radial-gradient(closest-side, rgba(230, 130, 110, 0.15), transparent); }

.kicker {
  position: relative;
  margin: 0;
  font-family: var(--caps);
  font-weight: 600;
  font-size: 15px;
  line-height: 1.35;
  letter-spacing: 0.06em;
  color: rgba(240, 205, 138, 0.85);
}
.tone-tense > .kicker { color: #e8a594; }
.title {
  position: relative;
  margin: 0;
  font-family: var(--serif);
  font-weight: 500;
  font-size: 30px;
  line-height: 1.15;
  color: #f8f1e4;
  text-wrap: balance;
}
.score { display: flex; gap: 6px; margin: -2px 0 0; }
.score-dot { width: 9px; height: 9px; border-radius: 50%; border: 1px solid rgba(240, 205, 138, 0.45); }
.score-dot.is-on { background: #f0cd8a; border-color: #f0cd8a; box-shadow: 0 0 8px rgba(255, 205, 120, 0.55); }
.tone-tense .score-dot.is-on { background: #e0907c; border-color: #e0907c; box-shadow: 0 0 8px rgba(230, 130, 110, 0.5); }
.text {
  position: relative;
  margin: 0;
  font-family: var(--book);
  font-size: 16.5px;
  line-height: 1.7;
  hyphens: auto;
  color: #efe7d8;
}
.is-short .text {
  margin-top: 10px;
  padding-left: 18px;
  border-left: 2px solid rgba(240, 205, 138, 0.45);
  font-family: var(--serif);
  font-style: italic;
  font-size: 23px;
  line-height: 1.45;
  hyphens: manual;
  color: #f6efe2;
}

.items { display: grid; gap: 8px; margin: 0; padding: 0; list-style: none; }
.item {
  display: grid;
  gap: 3px;
  padding: 11px 14px;
  border-radius: 14px;
  border: 1px solid rgba(240, 210, 150, 0.12);
  background: rgba(255, 240, 210, 0.025);
}
.item-name {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: var(--caps);
  font-weight: 600;
  font-size: 15px;
  letter-spacing: 0.04em;
  color: #f0cd8a;
}
.item.tone-easy .item-name::before, .item.tone-tense .item-name::before, .item.tone-calm .item-name::before {
  content: '';
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: rgba(226, 220, 210, 0.4);
}
.item.tone-easy .item-name::before { background: #f0cd8a; box-shadow: 0 0 8px rgba(255, 205, 120, 0.7); }
.item.tone-tense .item-name { color: #e8a594; }
.item.tone-tense .item-name::before { background: #d98b7a; box-shadow: 0 0 8px rgba(230, 130, 110, 0.6); }
.item.tone-calm .item-name { color: #dfe6f2; }
.item-text { font-family: var(--book); font-size: 15px; line-height: 1.6; color: rgba(239, 231, 216, 0.92); }

/* The years: a thread down the left, a star at each period in its tone. */
.years { position: relative; display: grid; gap: 18px; margin: 4px 0 0; padding: 0 0 0 22px; list-style: none; }
.years::before {
  content: '';
  position: absolute;
  top: 6px;
  bottom: 6px;
  left: 4px;
  width: 1px;
  background: linear-gradient(180deg, rgba(240, 205, 138, 0.5), rgba(240, 205, 138, 0.08));
}
.year { position: relative; display: grid; gap: 4px; }
.year::before {
  content: '';
  position: absolute;
  top: 5px;
  left: -22px;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #c9d2e6;
  box-shadow: 0 0 0 3px #0d1126;
}
.year.tone-easy::before { background: #f0cd8a; box-shadow: 0 0 0 3px #0d1126, 0 0 10px rgba(255, 205, 120, 0.7); }
.year.tone-tense::before { background: #d98b7a; box-shadow: 0 0 0 3px #0d1126, 0 0 10px rgba(230, 130, 110, 0.6); }
.year-when { font-family: var(--caps); font-weight: 600; font-size: 14.5px; letter-spacing: 0.06em; color: rgba(240, 205, 138, 0.85); }
.year.tone-tense .year-when { color: #e8a594; }
.year-title { font-family: var(--serif); font-weight: 500; font-size: 20px; line-height: 1.25; color: #f6efe2; }
.year-text { margin: 0; font-family: var(--book); font-size: 15px; line-height: 1.6; color: rgba(239, 231, 216, 0.9); }
.year-todo { margin: 2px 0 0; font-family: var(--serif); font-style: italic; font-size: 16px; line-height: 1.45; color: #f3dcae; }
.year.is-hidden { filter: blur(5px); opacity: 0.55; user-select: none; }
.year.is-hidden .year-title, .year.is-hidden .year-text { letter-spacing: -0.05em; }
.hidden-note { margin: 0; font-family: var(--book); font-style: italic; font-size: 14px; color: rgba(233, 194, 124, 0.85); }

.plan { display: grid; gap: 10px; margin: 0; padding: 0; list-style: none; counter-reset: step; }
.step {
  display: grid;
  grid-template-columns: 30px 1fr;
  gap: 12px;
  align-items: start;
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid rgba(240, 210, 150, 0.14);
  background: rgba(255, 240, 210, 0.03);
}
.step-number {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  border: 1px solid rgba(240, 205, 138, 0.55);
  font-family: var(--serif);
  font-size: 17px;
  color: #f0cd8a;
}
.step-copy { font-family: var(--book); font-size: 15px; line-height: 1.6; color: rgba(239, 231, 216, 0.92); }
.step-copy strong { display: block; margin-bottom: 2px; font-family: var(--serif); font-weight: 500; font-size: 18px; color: #f6efe2; }

.todo {
  position: relative;
  display: grid;
  gap: 6px;
  margin-top: 4px;
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid rgba(240, 205, 138, 0.4);
  background: linear-gradient(180deg, rgba(240, 205, 138, 0.1), rgba(240, 205, 138, 0.03));
}
.todo-label { font-family: var(--caps); font-weight: 600; font-size: 15px; letter-spacing: 0.08em; color: #f0cd8a; }
.todo p { margin: 0; font-family: var(--serif); font-style: italic; font-size: 18px; line-height: 1.45; color: #f8ead0; }

/* The hidden chapters wrap as chips: a list of twelve rows would push the button out of view. */
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
  color: rgba(226, 220, 210, 0.7);
}
.outline svg { flex: none; width: 11px; height: 13px; fill: none; stroke: rgba(240, 205, 138, 0.7); stroke-width: 1.4; }

.stories-nav {
  position: relative;
  z-index: 2;
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 12px 18px calc(16px + env(safe-area-inset-bottom));
  border-top: 1px solid rgba(240, 210, 150, 0.1);
  background: rgba(10, 13, 29, 0.92);
}
.back, .next {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 44px;
  padding: 0 20px;
  border-radius: 999px;
  font: inherit;
  font-size: 14.5px;
  cursor: pointer;
  transition: background 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease, opacity 0.25s ease;
}
.back {
  border: 1px solid rgba(240, 220, 180, 0.2);
  background: rgba(255, 245, 225, 0.05);
  -webkit-backdrop-filter: blur(10px);
  backdrop-filter: blur(10px);
  color: #efe7d8;
}
.back:hover:not(:disabled) { border-color: rgba(240, 205, 138, 0.5); background: rgba(255, 245, 225, 0.1); }
.back:disabled { opacity: 0.35; cursor: default; }
.next {
  border: 0;
  background: linear-gradient(180deg, #f4dba6, #dcb36c);
  color: #2b1d0b;
  font-weight: 600;
  box-shadow: 0 8px 26px rgba(230, 170, 80, 0.22);
}
.next:hover { box-shadow: 0 10px 34px rgba(230, 170, 80, 0.38); }
.back:focus-visible, .next:focus-visible { outline: 2px solid #ffe2a8; outline-offset: 3px; }

.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }

/* ---- Motion: the reader rises, the screens turn in the direction of reading ---- */
.stories-enter-active, .stories-leave-active { transition: opacity 0.3s ease; }
.stories-enter-active .stories-card, .stories-leave-active .stories-card { transition: transform 0.4s cubic-bezier(0.2, 0.8, 0.2, 1); }
.stories-enter-from, .stories-leave-to { opacity: 0; }
.stories-enter-from .stories-card { transform: translateY(24px) scale(0.98); }
.stories-leave-to .stories-card { transform: translateY(12px); }

.turn-next-enter-active, .turn-next-leave-active, .turn-back-enter-active, .turn-back-leave-active {
  transition: opacity 0.22s ease, transform 0.28s cubic-bezier(0.25, 0.8, 0.25, 1);
}
.turn-next-enter-from, .turn-back-leave-to { opacity: 0; transform: translateX(28px); }
.turn-next-leave-to, .turn-back-enter-from { opacity: 0; transform: translateX(-28px); }

@media (max-width: 760px) {
  .essence { font-size: 20px; }
  .chapter, .read { min-height: 40px; }
  .stories { padding: 0; }
  .stories-card { width: 100%; height: 100dvh; border-radius: 0; border: 0; }
  .stories-top { padding-top: calc(12px + env(safe-area-inset-top)); }
  .stories-body { padding: 4px 20px 20px; }
  .title { font-size: 26px; }
  .text { font-size: 16px; }
  .is-short .text { font-size: 21px; }
  .back, .next { flex: 1; justify-content: center; }
}
/* Light devices: no blur behind the buttons. */
:global(html.lite) .close, :global(html.lite) .back { -webkit-backdrop-filter: none; backdrop-filter: none; }
@media (prefers-reduced-motion: reduce) {
  .chapter, .read, .segment, .close, .back, .next { transition: none; }
  .stories-enter-active .stories-card, .stories-leave-active .stories-card { transition: none; }
  .stories-enter-from .stories-card, .stories-leave-to .stories-card { transform: none; }
  .turn-next-enter-active, .turn-next-leave-active, .turn-back-enter-active, .turn-back-leave-active { transition: opacity 0.15s ease; }
  .turn-next-enter-from, .turn-back-leave-to, .turn-next-leave-to, .turn-back-enter-from { transform: none; }
}
</style>

<style>
/* The page under an open reader stays still. */
html.stories-open, html.stories-open body { overflow: hidden; }
</style>
