<script setup>
import { RouterLink } from 'vue-router'
import ReadingText from './ReadingText.vue'
import { usePrices } from '../../utils/prices.js'

/**
 * A reading that «Небосвод» opens: whole with it, and without it the first lines dissolve into the
 * haze above a note and the way to the subscription. The server sends only those first lines.
 */
defineProps({
  reading: { type: Object, required: true },
  locked: { type: Boolean, default: false },
  /** What else is behind the haze, in a line. */
  note: { type: String, default: '' },
})

const { sky: skyPrice } = usePrices()
</script>

<template>
  <div class="locked-reading">
    <div class="text" :class="{ 'is-locked': locked }">
      <ReadingText :reading="reading" />
    </div>
    <div v-if="locked" class="unlock">
      <p v-if="note" class="unlock-note">{{ note }}</p>
      <RouterLink class="unlock-cta" :to="{ name: 'cabinet-sky' }">
        <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg>
        Зажечь Небосвод — {{ skyPrice }}
      </RouterLink>
    </div>
  </div>
</template>

<style scoped>
.locked-reading { display: grid; gap: 18px; }
.text { display: grid; gap: 12px; }
/* Without «Небосвод» the first lines dissolve into the haze. */
.text.is-locked {
  max-height: 14em;
  overflow: hidden;
  -webkit-mask-image: linear-gradient(180deg, #000 35%, transparent);
  mask-image: linear-gradient(180deg, #000 35%, transparent);
  user-select: none;
}
.unlock { display: grid; gap: 12px; justify-items: start; margin-top: -8px; }
.unlock-note { margin: 0; font-size: 13.5px; line-height: 1.5; color: rgba(233, 194, 124, 0.8); }
.unlock-cta {
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
.unlock-cta svg { width: 10px; height: 10px; fill: #5a3d12; }
.unlock-cta:hover { box-shadow: 0 10px 34px rgba(230, 170, 80, 0.38); transform: translateY(-1px); }
.unlock-cta:focus-visible { outline: 2px solid #ffe2a8; outline-offset: 3px; }

@media (max-width: 760px) {
  .unlock-cta { min-height: 44px; }
}
@media (prefers-reduced-motion: reduce) {
  .unlock-cta { transition: none; }
}
</style>
