<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import PanelHead from '../../components/cabinet/PanelHead.vue'

/** The panel of a section that is not open yet: what it will be, and no more. */

defineProps({
  user: { type: Object, default: null },
})

const route = useRoute()

const COPY = {
  chart: {
    title: ['Натальная', 'карта'],
    lead: 'Небо минуты вашего рождения: где стояли Солнце, Луна и планеты, какие дома они заняли и как говорят друг с другом.',
  },
  forecast: {
    title: ['Прогноз', 'дня и недели'],
    lead: 'Сегодняшнее небо поверх вашего: какие планеты касаются вашей карты и что это значит для ближайших дней.',
  },
  pair: {
    title: ['Совместимость', 'двоих'],
    lead: 'Две карты рядом: где вы звучите в унисон и чему учитесь друг у друга.',
  },
  chat: {
    title: ['Разговор', 'с астрологом'],
    lead: 'Спросите о своей карте простыми словами — ответ придёт с опорой на ваше небо.',
  },
}

const copy = computed(() => COPY[route.meta.section] || COPY.chart)
</script>

<template>
  <div class="soon">
    <PanelHead :lead="copy.lead">{{ copy.title[0] }} <em>{{ copy.title[1] }}</em></PanelHead>
    <p class="soon-note">
      <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg>
      Раздел откроется совсем скоро.
    </p>
  </div>
</template>

<style scoped>
.soon { display: grid; gap: 18px; }
.soon-note {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0;
  padding-top: 14px;
  border-top: 1px solid rgba(240, 210, 150, 0.12);
  font-size: 14px;
  color: rgba(226, 220, 210, 0.7);
}
.soon-note svg { flex: none; width: 10px; height: 10px; fill: #f0cd8a; filter: drop-shadow(0 0 5px rgba(255, 200, 110, 0.8)); }
</style>
