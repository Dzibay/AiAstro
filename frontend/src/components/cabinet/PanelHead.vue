<script setup>
/** The heading of a cabinet panel: a serif title with an italic accent, and a line under it. */
defineProps({
  lead: { type: String, default: '' },
  /** The overview greets as the page's h1; the sections are its parts. */
  level: { type: Number, default: 2 },
})
</script>

<template>
  <header class="panel-head">
    <component :is="`h${level}`" class="panel-title" tabindex="-1"><slot /></component>
    <p v-if="lead || $slots.lead" class="panel-lead"><slot name="lead">{{ lead }}</slot></p>
  </header>
</template>

<style scoped>
.panel-head { display: grid; gap: 8px; }
.panel-title {
  margin: 0;
  font-family: var(--serif);
  font-weight: 500;
  font-size: 32px;
  line-height: 1.08;
  color: #f6efe2;
  outline: none;
}
.panel-title :deep(em) { font-style: italic; color: #f0cd8a; }
.panel-lead { margin: 0; font-family: var(--serif); font-style: italic; font-size: 17px; line-height: 1.4; color: rgba(242, 228, 200, 0.82); }

@media (max-width: 760px) {
  .panel-title { font-size: 28px; }
}
</style>
