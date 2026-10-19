<script setup>
import { RouterLink } from 'vue-router'

/**
 * A hint at the right moment: one line in the margin of the page and a way to follow it. Quiet,
 * an outline and a small star, so it reads as a note of the folio, not as an advert.
 */
defineProps({
  to: { type: [Object, String], required: true },
  action: { type: String, required: true },
  /** «Небосвод» hints are gold; the others (the pair, the astrologer) are the pale blue of the sky. */
  tone: { type: String, default: 'gold' },
})
</script>

<template>
  <aside class="sky-nudge" :class="`tone-${tone}`">
    <svg class="nudge-star" viewBox="0 0 20 20" aria-hidden="true"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg>
    <p class="nudge-text"><slot /></p>
    <RouterLink class="nudge-link" :to="to">{{ action }}<span aria-hidden="true"> →</span></RouterLink>
  </aside>
</template>

<style scoped>
.sky-nudge {
  display: grid;
  grid-template-columns: auto 1fr;
  column-gap: 12px;
  row-gap: 6px;
  align-items: start;
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid rgba(240, 205, 138, 0.22);
  background: linear-gradient(120deg, rgba(240, 205, 138, 0.07), rgba(240, 205, 138, 0.01));
}
.tone-sky { border-color: rgba(170, 200, 245, 0.22); background: linear-gradient(120deg, rgba(170, 200, 245, 0.07), rgba(170, 200, 245, 0.01)); }
.nudge-star { grid-row: span 2; width: 12px; height: 12px; margin-top: 5px; fill: #f0cd8a; filter: drop-shadow(0 0 6px rgba(255, 200, 110, 0.8)); }
.tone-sky .nudge-star { fill: #d6e2f4; filter: drop-shadow(0 0 6px rgba(180, 210, 255, 0.8)); }
.nudge-text { margin: 0; font-family: var(--book); font-size: 14px; line-height: 1.55; color: #efe7d8; }
.nudge-link {
  justify-self: start;
  font-size: 13px;
  letter-spacing: 0.02em;
  color: #f0cd8a;
  text-decoration: underline;
  text-decoration-color: rgba(240, 205, 138, 0.35);
  text-underline-offset: 3px;
  transition: text-decoration-color 0.25s ease;
}
.tone-sky .nudge-link { color: #d6e2f4; text-decoration-color: rgba(214, 226, 244, 0.35); }
.nudge-link:hover { text-decoration-color: currentColor; }
.nudge-link:focus-visible { outline: 1px solid currentColor; outline-offset: 2px; border-radius: 4px; }

@media (max-width: 760px) {
  .nudge-link { padding-block: 10px; margin-block: -8px; }
}
</style>
