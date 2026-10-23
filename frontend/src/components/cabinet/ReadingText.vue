<script setup>
/**
 * A reading as the server writes it: { essence, parts: [{ label, text, items?, todo? }] }, set as
 * a page of a folio. The essence is a centred italic line in guillemets; the parts are paragraphs,
 * each opening with its label run in small caps, the first one with a gold drop cap, followed by
 * its items as short lines and its «Что делать». A part without a label (an old answer in the
 * chat) is a plain paragraph. The forecasts and the pair are read as screens (ReadingStories).
 */
defineProps({
  reading: { type: Object, required: true },
  /** In the chat the answer sits among messages: no drop cap, a smaller essence, closer lines. */
  compact: { type: Boolean, default: false },
})

/** «Тема» → «Тема.», and a label that already ends in a stop keeps it. */
const runIn = (label) => (/[.!?…:]$/.test(label) ? label : `${label}.`)
</script>

<template>
  <div class="reading-text" :class="{ 'is-compact': compact }">
    <p v-if="reading.essence" class="essence">«{{ reading.essence.replace(/[.…]+$/, '') }}»</p>
    <div v-if="reading.parts.length" class="parts">
      <template v-for="(part, index) in reading.parts" :key="index">
        <p class="part">
          <template v-if="part.label"><span class="label">{{ runIn(part.label) }}</span>{{ ' ' }}</template>{{ part.text }}
        </p>
        <ul v-if="part.items?.length" class="items">
          <li v-for="(item, line) in part.items" :key="line"><b v-if="item.name">{{ item.name }}.</b> {{ item.text }}</li>
        </ul>
        <p v-if="part.todo" class="todo"><span class="todo-label">✦ Что делать:</span> {{ part.todo }}</p>
      </template>
    </div>
  </div>
</template>

<style scoped>
.reading-text { display: grid; gap: 16px; }
.essence {
  margin: 0;
  font-family: var(--serif);
  font-style: italic;
  font-size: 22px;
  line-height: 1.35;
  text-align: center;
  color: #f6efe2;
}
.parts { display: grid; }
.part {
  margin: 0;
  font-family: var(--book);
  font-size: 15px;
  line-height: 1.75;
  hyphens: auto;
  color: #efe7d8;
}
.part + .part { text-indent: 1.6em; }
.parts > .part:first-child::first-letter {
  float: left;
  margin: 5px 8px 0 0;
  font-family: var(--serif);
  font-weight: 600;
  font-style: normal;
  font-size: 56px;
  line-height: 0.8;
  color: #f0cd8a;
}
.label { font-family: var(--caps); font-weight: 600; font-size: 1.1em; letter-spacing: 0.06em; color: #f0cd8a; }
.items { display: grid; gap: 4px; margin: 6px 0 4px; padding-left: 1.2em; font-family: var(--book); font-size: 14.5px; line-height: 1.6; color: rgba(239, 231, 216, 0.9); }
.items b { font-weight: 600; color: #f3dcae; }
.todo { margin: 6px 0 10px; font-family: var(--serif); font-style: italic; font-size: 16px; line-height: 1.5; color: #f8ead0; }
.todo-label { font-family: var(--caps); font-style: normal; font-weight: 600; letter-spacing: 0.06em; color: #f0cd8a; }

.is-compact { gap: 10px; }
.is-compact .essence { font-size: 18px; }
.is-compact .part { font-size: 14.5px; line-height: 1.6; color: rgba(239, 231, 216, 0.92); }
.is-compact .parts > .part:first-child::first-letter { all: unset; }

@media (max-width: 760px) {
  .essence { font-size: 20px; }
  .is-compact .essence { font-size: 17px; }
}
</style>
