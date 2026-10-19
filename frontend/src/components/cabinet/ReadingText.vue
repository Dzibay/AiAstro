<script setup>
/**
 * A reading as the server writes it: { essence, parts: [{ label, text }] }. The essence is the
 * heart of it, an italic serif line under a gold bar; the parts are short theses, each under a
 * small gold label. A part without a label (an old answer in the chat) is a plain paragraph.
 */
defineProps({
  reading: { type: Object, required: true },
  /** In the chat the answer sits among messages: a smaller essence, closer parts. */
  compact: { type: Boolean, default: false },
})
</script>

<template>
  <div class="reading-text" :class="{ 'is-compact': compact }">
    <p v-if="reading.essence" class="essence">{{ reading.essence }}</p>
    <dl v-if="reading.parts.length" class="parts">
      <div v-for="(part, index) in reading.parts" :key="index" class="part">
        <dt v-if="part.label" class="label">{{ part.label }}</dt>
        <dd class="body">{{ part.text }}</dd>
      </div>
    </dl>
  </div>
</template>

<style scoped>
.reading-text { display: grid; gap: 18px; }
.essence {
  margin: 0;
  padding: 2px 0 2px 16px;
  border-left: 2px solid transparent;
  border-image: linear-gradient(180deg, #f4dba6, rgba(220, 179, 108, 0.35)) 1;
  font-family: var(--serif);
  font-style: italic;
  font-size: 20px;
  line-height: 1.35;
  color: #f6efe2;
}
.parts { display: grid; gap: 14px; margin: 0; }
.part { display: grid; gap: 5px; }
.label {
  font-size: 10px;
  letter-spacing: 0.2em;
  line-height: 1.5;
  text-transform: uppercase;
  color: rgba(233, 194, 124, 0.85);
}
.body { margin: 0; font-size: 15px; line-height: 1.6; color: #efe7d8; }

.is-compact { gap: 12px; }
.is-compact .essence { padding-left: 14px; font-size: 18px; }
.is-compact .parts { gap: 10px; }
.is-compact .part { gap: 3px; }
.is-compact .body { font-size: 14.5px; line-height: 1.55; color: rgba(239, 231, 216, 0.92); }

@media (max-width: 760px) {
  .essence { font-size: 19px; }
  .is-compact .essence { font-size: 17px; }
}
</style>
