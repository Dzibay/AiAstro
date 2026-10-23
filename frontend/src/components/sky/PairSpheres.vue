<script setup>
import { computed } from 'vue'

/**
 * The pair by sphere of life: five rows of stars, as in «Стихии и кресты» of the chart. The
 * scores are open to everyone; what stands behind each of them is the full reading.
 */

const props = defineProps({
  /** [{ id, score: 1..5 }] from the synastry (backend app/astro/synastry.py SPHERES). */
  spheres: { type: Array, required: true },
})

const NAMES = {
  feelings: { name: 'Чувства', hint: 'Луна и Венера: как вы любите и как принимаете любовь' },
  passion: { name: 'Притяжение', hint: 'Марс, Венера, Плутон: искра и желание' },
  talk: { name: 'Разговоры', hint: 'Меркурий и Солнце: как вы слышите друг друга' },
  home: { name: 'Быт и опора', hint: 'Луна и Сатурн: дом, привычки, надёжность' },
  path: { name: 'Общий путь', hint: 'Солнце, Юпитер, Сатурн: куда вы идёте вместе' },
}
const WORDS = ['', 'точка роста', 'в развитии', 'ровно', 'легко', 'созвучно']

const rows = computed(() => props.spheres.filter((sphere) => NAMES[sphere.id]).map((sphere) => ({
  ...sphere,
  ...NAMES[sphere.id],
  word: WORDS[sphere.score],
})))
</script>

<template>
  <dl class="spheres">
    <div v-for="row in rows" :key="row.id" class="sphere" :title="row.hint">
      <dt>{{ row.name }}</dt>
      <dd>
        <span class="word">{{ row.word }}</span>
        <span class="visually-hidden">, {{ row.score }} из 5</span>
        <span class="stars" aria-hidden="true">{{ '✦'.repeat(row.score) }}<span class="star-off">{{ '✦'.repeat(5 - row.score) }}</span></span>
      </dd>
    </div>
  </dl>
</template>

<style scoped>
.spheres { display: grid; gap: 6px; margin: 0; }
.sphere { display: flex; justify-content: space-between; align-items: baseline; gap: 16px; font-family: var(--book); font-size: 14.5px; }
.sphere dt { color: #efe7d8; }
.sphere dd { display: inline-flex; align-items: baseline; gap: 10px; margin: 0; }
.word { font-family: var(--serif); font-style: italic; font-size: 15px; color: rgba(226, 220, 210, 0.55); }
.stars { letter-spacing: 0.18em; color: #f0cd8a; white-space: nowrap; }
.star-off { color: rgba(240, 205, 138, 0.2); }
.visually-hidden { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
</style>
