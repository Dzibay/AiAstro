<script setup>
import { FEATURES } from './features.js'
import { usePrices } from '../../utils/prices.js'

/** «Бесплатно» against «Небосвод», feature by feature: what is open now and what the sky adds. */
defineProps({
  /** The column the person already has: the free one, or «Небосвод» once it burns. */
  lit: { type: Boolean, default: false },
})

const { sky, synastry, synastrySky } = usePrices()
</script>

<template>
  <table class="sky-compare">
    <caption class="visually-hidden">Что открыто бесплатно и что добавляет «Небосвод»</caption>
    <thead>
      <tr>
        <th scope="col"><span class="visually-hidden">Что</span></th>
        <th scope="col" :class="{ 'is-mine': !lit }">Бесплатно</th>
        <th scope="col" class="col-sky" :class="{ 'is-mine': lit }">
          <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg>
          Небосвод
        </th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="feature in FEATURES" :key="feature.id">
        <th scope="row">{{ feature.name }}</th>
        <td :class="{ 'is-same': feature.always }">{{ feature.free }}</td>
        <td class="col-sky">{{ feature.sky }}</td>
      </tr>
    </tbody>
    <tfoot>
      <tr>
        <th scope="row">Цена</th>
        <td>0 ₽ навсегда</td>
        <td class="col-sky">{{ sky }} в месяц</td>
      </tr>
      <tr class="pair-price">
        <th scope="row">Разбор пары</th>
        <td>{{ synastry }}</td>
        <td class="col-sky">{{ synastrySky }}</td>
      </tr>
    </tfoot>
  </table>
</template>

<style scoped>
.sky-compare { width: 100%; border-collapse: collapse; font-family: var(--book); font-size: 13.5px; line-height: 1.4; }
.sky-compare th, .sky-compare td { padding: 8px 6px; text-align: left; vertical-align: top; border-bottom: 1px solid rgba(240, 210, 150, 0.1); }
.sky-compare th:first-child { padding-left: 0; }
.sky-compare td:last-child, .sky-compare th:last-child { padding-right: 0; }

thead th { font-family: var(--caps); font-weight: 600; font-size: 14.5px; letter-spacing: 0.08em; color: rgba(226, 220, 210, 0.6); }
thead th.col-sky { color: #f0cd8a; }
thead th svg { width: 9px; height: 9px; margin-right: 3px; fill: #f0cd8a; filter: drop-shadow(0 0 4px rgba(255, 200, 110, 0.8)); }
thead th.is-mine::after { content: ' · у вас'; font-family: var(--serif); font-style: italic; font-weight: 400; font-size: 13px; letter-spacing: 0; text-transform: none; }

tbody th, tfoot th { font-weight: 400; color: #efe7d8; }
td { color: rgba(226, 220, 210, 0.6); }
td.col-sky { color: #f3dcae; background: linear-gradient(90deg, rgba(240, 205, 138, 0.05), transparent); }
td.is-same { color: #f3dcae; }

tfoot th, tfoot td { border-bottom: 0; font-family: var(--serif); font-style: italic; font-size: 15px; }
tfoot tr:first-child th, tfoot tr:first-child td { padding-top: 12px; }
.pair-price th, .pair-price td { padding-top: 0; font-size: 14px; }

.visually-hidden { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
</style>
