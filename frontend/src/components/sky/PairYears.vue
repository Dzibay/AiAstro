<script setup>
import { computed } from 'vue'

/**
 * The pair's next five years at a glance: each period on a thread, its dates and its name, in its
 * tone. The words of each period are in the reading's «Пять лет» screen, which the button opens.
 * Before the reading is bought the nearest period is seen and the rest are only their place.
 */

const props = defineProps({
  /** The reading's part of kind "years": { items: [{ name, title, tone }], hidden? }. */
  part: { type: Object, required: true },
  locked: { type: Boolean, default: false },
})
const emit = defineEmits(['open'])

const hidden = computed(() => props.part.hidden || 0)
const word = computed(() => {
  const count = hidden.value
  const teen = count % 100 >= 11 && count % 100 <= 14
  if (count % 10 === 1 && !teen) return 'период'
  return count % 10 >= 2 && count % 10 <= 4 && !teen ? 'периода' : 'периодов'
})
const TONE = { easy: 'лёгкий период', tense: 'период роста', calm: 'ровный период' }
</script>

<template>
  <section class="block pair-years" aria-labelledby="years-title">
    <h3 id="years-title" class="block-title">Ваши ближайшие пять лет</h3>
    <ol class="thread">
      <li v-for="(item, index) in part.items" :key="index" class="period" :class="item.tone && `tone-${item.tone}`">
        <span class="when">{{ item.name }}<span class="sr-only"> — {{ TONE[item.tone] || '' }}</span></span>
        <span class="what">{{ item.title }}</span>
      </li>
      <li v-for="index in hidden" :key="`h${index}`" class="period is-hidden" aria-hidden="true">
        <span class="when">░░░░ ░░░░</span>
        <span class="what">░░░░░░░ ░░░░░</span>
      </li>
    </ol>
    <p v-if="locked && hidden" class="note">
      Виден ближайший период. Ещё {{ hidden }} {{ word }} — с датами, смыслом и советом, что делать, — откроются с разбором.
    </p>
    <button type="button" class="more" @click="emit('open')">
      {{ locked ? 'Прочитать о ближайшем периоде' : 'Читать о каждом периоде' }} <span aria-hidden="true">→</span>
    </button>
  </section>
</template>

<style scoped>
.thread { position: relative; display: grid; gap: 12px; margin: 0; padding: 0 0 0 22px; list-style: none; }
.thread::before {
  content: '';
  position: absolute;
  top: 7px;
  bottom: 7px;
  left: 4px;
  width: 1px;
  background: linear-gradient(180deg, rgba(240, 205, 138, 0.5), rgba(240, 205, 138, 0.08));
}
.period { position: relative; display: grid; gap: 1px; }
.period::before {
  content: '';
  position: absolute;
  top: 5px;
  left: -22px;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #c9d2e6;
}
.period.tone-easy::before { background: #f0cd8a; box-shadow: 0 0 9px rgba(255, 205, 120, 0.7); }
.period.tone-tense::before { background: #d98b7a; box-shadow: 0 0 9px rgba(230, 130, 110, 0.6); }
.when { font-family: var(--caps); font-weight: 600; font-size: 14px; letter-spacing: 0.06em; color: rgba(240, 205, 138, 0.8); }
.period.tone-tense .when { color: #e8a594; }
.what { font-family: var(--serif); font-size: 18px; line-height: 1.3; color: #f6efe2; }
.period.is-hidden { filter: blur(4px); opacity: 0.5; user-select: none; }
.note { margin: 0; font-family: var(--book); font-style: italic; font-size: 13.5px; line-height: 1.5; color: rgba(233, 194, 124, 0.8); }
.more {
  justify-self: start;
  padding: 0;
  border: 0;
  background: none;
  font: inherit;
  font-size: 13.5px;
  color: #f0cd8a;
  text-decoration: underline;
  text-decoration-color: rgba(240, 205, 138, 0.35);
  text-underline-offset: 3px;
  cursor: pointer;
}
.more:hover { text-decoration-color: currentColor; }
.more:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 3px; border-radius: 4px; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }

@media (max-width: 760px) {
  .more { min-height: 44px; }
}
</style>
