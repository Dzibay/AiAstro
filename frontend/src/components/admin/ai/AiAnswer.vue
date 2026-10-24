<script setup>
import { computed } from 'vue'

/**
 * An answer of the ИИ-астролог as the person sees it in the chat: the paragraphs, the «Ключ —»
 * line, the follow-up questions as chips. A text from the journal comes whole, the key inside.
 */
const props = defineProps({
  answer: { type: String, default: '' },
  keyLine: { type: String, default: '' },
  follow: { type: Array, default: () => [] },
})

const paragraphs = computed(() => props.answer.split(/\n\s*\n/).map((text) => text.trim()).filter(Boolean))
const key = computed(() => {
  const text = props.keyLine.trim()
  if (!text) return ''
  return text[1] && text[1] === text[1].toLowerCase() ? text[0].toLowerCase() + text.slice(1) : text
})
</script>

<template>
  <div class="ai-answer">
    <p v-for="(paragraph, index) in paragraphs" :key="index" :class="{ 'is-key': paragraph.startsWith('Ключ —') }">{{ paragraph }}</p>
    <p v-if="!paragraphs.length" class="adm-dim">Пустой ответ</p>
    <p v-if="key" class="is-key">Ключ — {{ key }}</p>
    <ul v-if="follow.length" class="ai-answer-follow" aria-label="Можно спросить дальше">
      <li v-for="text in follow" :key="text">{{ text }}</li>
    </ul>
  </div>
</template>

<style scoped>
.ai-answer {
  display: grid;
  gap: 8px;
  padding-left: 14px;
  border-left: 1px solid rgba(240, 205, 138, 0.35);
  font-family: var(--serif);
  font-style: italic;
  font-size: 16.5px;
  line-height: 1.45;
  color: rgba(242, 232, 214, 0.92);
}
.ai-answer p { margin: 0; white-space: pre-line; overflow-wrap: anywhere; }
.ai-answer .is-key { color: #f0cd8a; }
.ai-answer .adm-dim { font-style: normal; font-family: var(--sans); font-size: 14px; }
.ai-answer-follow { display: flex; flex-wrap: wrap; gap: 6px; margin: 4px 0 0; padding: 0; list-style: none; font-family: var(--sans); font-style: normal; }
.ai-answer-follow li {
  padding: 4px 11px;
  border: 1px solid rgba(240, 210, 150, 0.18);
  border-radius: 999px;
  background: rgba(255, 240, 210, 0.04);
  color: rgba(239, 231, 216, 0.85);
  font-size: 12.5px;
}
</style>
