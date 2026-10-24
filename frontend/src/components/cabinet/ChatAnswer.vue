<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

/**
 * An answer of the ИИ-астролог ({ kind: 'talk', parts, key, follow }): conversational paragraphs,
 * then «Ключ — …» in gold, then what to ask next as chips. The answer arrives whole, already
 * checked; a new one is printed out letter by letter (a click shows it at once), an old one stands
 * as it is. Screen readers get the whole text at once, not the letters.
 */
const props = defineProps({
  reading: { type: Object, required: true },
  /** A new answer: printed out. */
  typing: { type: Boolean, default: false },
  /** The last answer of the conversation: its questions to ask next are offered. */
  followable: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['ask', 'typed', 'grow'])

// Quick enough to read along: 80 letters a second, and no answer prints longer than three seconds.
const SPEED = 80
const LONGEST = 3000

const key = computed(() => {
  const text = (props.reading.key || '').trim()
  if (!text) return ''
  return text[1] && text[1] === text[1].toLowerCase() ? `Ключ — ${text[0].toLowerCase()}${text.slice(1)}` : `Ключ — ${text}`
})
const lines = computed(() => [
  ...props.reading.parts.map((part) => ({ text: part.text, key: false })),
  ...(key.value ? [{ text: key.value, key: true }] : []),
])
const total = computed(() => lines.value.reduce((sum, line) => sum + line.text.length, 0))
const whole = computed(() => lines.value.map((line) => line.text).join('\n\n'))

const reduced = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
// Printed answers keep their whole text apart for screen readers: the log announces it once.
const animated = props.typing && !reduced
const shown = ref(animated ? 0 : Infinity)
const done = computed(() => shown.value >= total.value)
let frame = 0
let safety = 0

/** The lines as far as printed: the whole ones, the one being printed, nothing after. */
const visible = computed(() => {
  if (done.value) return lines.value
  let left = shown.value
  const out = []
  for (const line of lines.value) {
    if (left <= 0) break
    out.push({ ...line, text: line.text.slice(0, left), typing: left < line.text.length })
    left -= line.text.length
  }
  return out
})

function finish() {
  if (done.value) return
  cancelAnimationFrame(frame)
  clearTimeout(safety)
  shown.value = Infinity
  emit('grow')
  emit('typed')
}

onMounted(() => {
  if (done.value) return
  const speed = Math.max(SPEED, (total.value * 1000) / LONGEST)
  const start = performance.now()
  const step = (now) => {
    shown.value = Math.floor(((now - start) / 1000) * speed)
    emit('grow')
    if (done.value) {
      clearTimeout(safety)
      emit('typed')
    } else frame = requestAnimationFrame(step)
  }
  frame = requestAnimationFrame(step)
  // A tab out of sight draws no frames: the answer is shown whole anyway, not left blank till return.
  safety = setTimeout(finish, LONGEST + 1000)
})
onBeforeUnmount(() => {
  cancelAnimationFrame(frame)
  clearTimeout(safety)
})
</script>

<template>
  <div class="chat-answer" :class="{ 'is-typing': !done }" @click="finish">
    <span v-if="animated" class="visually-hidden">{{ whole }}</span>
    <div :aria-hidden="animated || undefined">
      <p v-for="(line, index) in visible" :key="index" :class="{ 'is-key': line.key }">{{ line.text }}<i v-if="line.typing" class="caret" aria-hidden="true" /></p>
    </div>
    <Transition name="follow">
      <ul v-if="done && followable && reading.follow?.length" class="follow" aria-label="Можно спросить дальше">
        <li v-for="text in reading.follow" :key="text">
          <button type="button" class="follow-chip" :disabled="disabled" @click.stop="$emit('ask', text)">{{ text }}</button>
        </li>
      </ul>
    </Transition>
  </div>
</template>

<style scoped>
.chat-answer { display: grid; gap: 12px; }
.chat-answer.is-typing { cursor: pointer; }
.chat-answer p { margin: 0; white-space: pre-line; overflow-wrap: anywhere; }
.chat-answer p + p { margin-top: 10px; }
/* The key: the one line to carry away, in the gold of the stars. */
.chat-answer .is-key { color: #f0cd8a; }
.caret {
  display: inline-block;
  width: 6px;
  height: 6px;
  margin-left: 3px;
  border-radius: 50%;
  background: #f0cd8a;
  box-shadow: 0 0 8px rgba(255, 200, 110, 0.8);
  vertical-align: middle;
}

.follow { display: flex; flex-wrap: wrap; gap: 6px; margin: 0; padding: 0; list-style: none; font-family: var(--book); font-style: normal; }
.follow-chip {
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid rgba(240, 210, 150, 0.22);
  background: rgba(255, 240, 210, 0.05);
  color: rgba(239, 231, 216, 0.9);
  font: inherit;
  font-size: 13px;
  line-height: 1.35;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.25s ease, color 0.25s ease;
}
.follow-chip:hover:not(:disabled) { border-color: rgba(240, 205, 138, 0.5); color: #f0cd8a; }
.follow-chip:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 2px; }
.follow-chip:disabled { opacity: 0.5; cursor: default; }
.follow-enter-active { transition: opacity 0.4s ease, transform 0.4s ease; }
.follow-enter-from { opacity: 0; transform: translateY(4px); }

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}

@media (max-width: 760px) {
  .follow-chip { min-height: 36px; }
}
</style>
