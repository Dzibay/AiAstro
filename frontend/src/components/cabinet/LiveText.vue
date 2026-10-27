<script setup>
import { computed, onBeforeUnmount } from 'vue'
import { RouterLink } from 'vue-router'
import { useChart } from '../../composables/useChart.js'
import { hideTip, nextOwner, showTip, tip, tokenize } from './glossary.js'

/**
 * A line of a reading that knows its astrology (glossary.js): a planet named in it is a link to its
 * reading and lights on the wheel under the pointer, a term explains itself in a small hint, and
 * with `dates` the dates are set in gold. Everything else is the text as it was written.
 */
const props = defineProps({
  text: { type: String, default: '' },
  /** The dates as gold marks: in the astrologer's answers, where they are what one looks for. */
  dates: { type: Boolean, default: false },
  /** In a copy screen readers skip (ChatAnswer keeps a printed answer's words apart for them): out of the Tab order too. */
  untabbable: { type: Boolean, default: false },
})

const uid = nextOwner()
const tipId = `glossary-tip-${uid}`

const tokens = computed(() => tokenize(props.text, { dates: props.dates }))
const { hot } = useChart()

let lit = ''
function enter(event, token) {
  if (token.id) {
    lit = token.id
    hot.value = token.id
  }
  if (token.tip) showTip(uid, event.currentTarget, token.tip)
}
function leave(token) {
  if (token.id && hot.value === token.id) hot.value = ''
  lit = ''
  hideTip(uid)
}
/** A tap on a term opens its hint and a second one closes it; a pointer only hovers. */
function toggle(event, token) {
  if (tip.owner === uid && tip.head === token.tip.head) hideTip(uid)
  else showTip(uid, event.currentTarget, token.tip)
}

onBeforeUnmount(() => {
  if (lit && hot.value === lit) hot.value = ''
  hideTip(uid)
})
</script>

<template>
  <span class="live-text">
    <template v-for="(token, index) in tokens" :key="index">
      <template v-if="token.kind === 'text'">{{ token.text }}</template>
      <RouterLink
        v-else-if="token.kind === 'point'"
        class="live-point"
        :to="{ name: 'cabinet-chart', params: { item: token.id } }"
        :tabindex="untabbable ? -1 : undefined"
        :aria-describedby="tip.owner === uid ? tipId : undefined"
        @pointerenter="enter($event, token)"
        @pointerleave="leave(token)"
        @focus="enter($event, token)"
        @blur="leave(token)"
      >{{ token.text }}</RouterLink>
      <span v-else-if="token.kind === 'date'" class="live-date">{{ token.text }}</span>
      <span
        v-else
        class="live-term"
        :tabindex="untabbable ? -1 : 0"
        :aria-describedby="tip.owner === uid ? tipId : undefined"
        @pointerenter="$event.pointerType === 'mouse' && enter($event, token)"
        @pointerleave="$event.pointerType === 'mouse' && leave(token)"
        @click="toggle($event, token)"
        @focus="enter($event, token)"
        @blur="leave(token)"
      >{{ token.text }}</span>
    </template>
    <Teleport to="body">
      <span
        v-if="tip.owner === uid"
        :id="tipId"
        class="glossary-tip"
        :class="{ 'is-below': tip.below }"
        role="tooltip"
        :style="{ left: `${tip.x}px`, top: `${tip.y}px` }"
      >
        <b>{{ tip.head }}</b> — {{ tip.text }}
        <span v-if="tip.more" class="tip-more">{{ tip.more }}</span>
      </span>
    </Teleport>
  </span>
</template>

<style scoped>
.live-point {
  color: inherit;
  text-decoration: underline;
  text-decoration-color: rgba(240, 205, 138, 0.5);
  text-decoration-thickness: 1px;
  text-underline-offset: 3px;
  cursor: pointer;
  transition: color 0.2s ease, text-decoration-color 0.2s ease;
}
.live-point:hover, .live-point:focus-visible { color: #f6dca4; text-decoration-color: #f0cd8a; outline: none; }
.live-term {
  text-decoration: underline dotted;
  text-decoration-color: rgba(240, 205, 138, 0.55);
  text-decoration-thickness: 1px;
  text-underline-offset: 3px;
  cursor: help;
}
.live-term:hover, .live-term:focus-visible { text-decoration-color: #f0cd8a; outline: none; }
.live-date {
  padding: 0 0.28em;
  border-radius: 6px;
  background: rgba(240, 205, 138, 0.13);
  color: #f6dca4;
  white-space: nowrap;
  box-decoration-break: clone;
}

.glossary-tip {
  position: fixed;
  z-index: 95;
  display: block;
  width: max-content;
  max-width: min(300px, calc(100vw - 24px));
  padding: 10px 13px;
  border-radius: 12px;
  border: 1px solid rgba(240, 210, 150, 0.3);
  background: rgba(13, 17, 38, 0.96);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.45);
  font-family: var(--book);
  font-style: normal;
  font-size: 13.5px;
  font-weight: 400;
  line-height: 1.5;
  text-align: left;
  text-indent: 0;
  letter-spacing: normal;
  color: #efe7d8;
  pointer-events: none;
  transform: translate(-50%, -100%);
  animation: tip-in 0.18s ease;
}
.glossary-tip.is-below { transform: translate(-50%, 0); }
.glossary-tip b { font-weight: 600; color: #f6dca4; }
.tip-more { display: block; margin-top: 4px; color: rgba(239, 231, 216, 0.75); }
@keyframes tip-in { from { opacity: 0; } }
@media (prefers-reduced-motion: reduce) {
  .glossary-tip { animation: none; }
}
</style>
