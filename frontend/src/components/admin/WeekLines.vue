<script setup>
/** Three shares of the way week by week, side by side: each its own scale, so a small share still shows its turns. */
import { computed } from 'vue'
import LineChart from './LineChart.vue'
import { WEEK_LINES, weekPoints } from '../../views/admin/way.js'

const props = defineProps({
  /** pulse.py weeks().items */
  items: { type: Array, required: true },
})

const lines = computed(() => WEEK_LINES.map((line) => ({ ...line, points: weekPoints(props.items, line) })))
</script>

<template>
  <div class="wl">
    <figure v-for="line in lines" :key="line.key" class="wl-one">
      <figcaption>
        <strong><i :style="{ background: line.color }" />{{ line.name }}</strong>
        <span>{{ line.hint }}</span>
      </figcaption>
      <LineChart :points="line.points" :color="line.color" :name="line.name" :of="line.of" />
    </figure>
  </div>
</template>

<style scoped>
.wl { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 18px 22px; }
.wl-one { display: grid; gap: 8px; min-width: 0; margin: 0; }
.wl-one figcaption { display: grid; gap: 1px; }
.wl-one strong { display: inline-flex; align-items: center; gap: 8px; font-size: 15px; font-weight: 600; }
.wl-one strong i { width: 14px; height: 3px; border-radius: 2px; }
.wl-one span { color: var(--soft); font-size: 12px; }
@media (max-width: 1100px) {
  .wl { grid-template-columns: minmax(0, 1fr); }
}
</style>
