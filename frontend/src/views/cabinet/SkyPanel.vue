<script setup>
import { computed, onUnmounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import PanelHead from '../../components/cabinet/PanelHead.vue'
import { FEATURES } from '../../components/sky/features.js'
import { useSkyOffer } from '../../composables/useSkyOffer.js'
import { usePrices } from '../../utils/prices.js'
import { skyEnding, skyLine } from '../../utils/skyTerm.js'
import { usePayment } from '../../composables/usePayment.js'
import { startTour } from '../../utils/tour.js'

/**
 * «Небосвод»: what the subscription lights, for how long and the way to pay for it. The list of
 * features and the dome on the sky (SkyDome) answer each other: a row under the pointer lights
 * its constellation, a constellation under the pointer lights its row; a press opens a row,
 * smoothly, and the rest slides down with it.
 *
 * The person comes back to the cabinet after ЮKassa; the subscription opens on the notification.
 */

const props = defineProps({
  user: { type: Object, required: true },
})

const offer = useSkyOffer()
const { prices, pay: payOn } = usePrices()

const money = (n) => `${Number(n).toLocaleString('ru-RU')} ₽`

/* ---- The terms ---- */

const PLANS = [
  { id: 'sky1', key: 'sky', months: 1, name: '1 месяц', term: 'на месяц' },
  { id: 'sky3', key: 'sky_3', months: 3, name: '3 месяца', term: 'на 3 месяца' },
  { id: 'sky12', key: 'sky_12', months: 12, name: '12 месяцев', term: 'на год' },
]
const plan = ref('sky3')
const plans = computed(() => {
  const monthly = Number(prices.value.sky) || 0
  return PLANS.map((item) => {
    const price = Number(prices.value[item.key]) || 0
    const saving = monthly && price && item.months > 1 ? Math.round((1 - price / (monthly * item.months)) * 100) : 0
    return {
      ...item,
      price,
      label: price ? money(price) : 'от … ₽',
      perMonth: price && item.months > 1 ? `${money(Math.round(price / item.months))} в месяц` : price ? 'на 30 дней' : '',
      saving: saving > 0 ? saving : 0,
    }
  })
})
const best = computed(() => plans.value.reduce((top, item) => (item.saving > (top?.saving || 0) ? item : top), null)?.id || '')
const chosen = computed(() => plans.value.find((item) => item.id === plan.value))

const ending = computed(() => skyEnding(props.user))
const state = computed(() => (props.user.sky ? `Небосвод ${skyLine(props.user)}.` : ''))

/* ---- The features, in step with the dome ---- */

const open = computed(() => offer.opened)
function hover(id) {
  offer.focus = id
}
function unhover(id) {
  if (offer.focus === id && offer.opened !== id) offer.focus = ''
}
function toggle(id) {
  offer.opened = offer.opened === id ? '' : id
  offer.focus = offer.opened
}

/* ---- Paying, and the way back from ЮKassa ---- */

const { busy, message, start } = usePayment()
function pay() {
  if (chosen.value?.price && payOn.value) {
    start({ product: plan.value }, { sky: props.user.sky, skyUntil: props.user.sky_until })
  }
}

onUnmounted(() => {
  offer.focus = ''
  offer.opened = ''
  offer.preview = false
})
</script>

<template>
  <div class="sky-panel">
    <PanelHead>
      Подписка <em>«Небосвод»</em>
      <template #lead>
        <template v-if="user.sky">{{ state }}</template>
        <template v-else>Пока на вашем небе горит одна звезда — ваша карта. Зажгите остальные.</template>
      </template>
    </PanelHead>

    <!-- Once lit, the walk through what «Небосвод» opened can be taken again at any time. -->
    <button v-if="user.sky" type="button" class="sky-replay" @click="startTour('sky')">
      <svg viewBox="0 0 16 12" aria-hidden="true"><path d="M1.5 10.5L1 3l4 3.2L8 1l3 5.2L15 3l-.5 7.5z" /></svg>
      Показать, что открыл «Небосвод»
    </button>

    <section aria-labelledby="sky-features">
      <h3 id="sky-features" class="part-title">Что зажигается</h3>
      <ul class="features">
        <li
          v-for="feature in FEATURES"
          :key="feature.id"
          class="feature"
          :class="{ 'is-open': open === feature.id, 'is-hot': offer.focus === feature.id, 'is-on': feature.always || user.sky || offer.preview }"
          @pointerenter="hover(feature.id)"
          @pointerleave="unhover(feature.id)"
        >
          <button
            type="button"
            class="feature-head"
            :aria-expanded="open === feature.id ? 'true' : 'false'"
            :aria-controls="`feature-${feature.id}`"
            @click="toggle(feature.id)"
            @focus="hover(feature.id)"
          >
            <svg class="feature-star" viewBox="0 0 20 20" aria-hidden="true"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg>
            <span class="feature-name">{{ feature.name }}</span>
            <span class="feature-sky">{{ feature.always ? 'уже ваша' : feature.sky }}</span>
          </button>
          <div :id="`feature-${feature.id}`" class="feature-more" :aria-hidden="open === feature.id ? 'false' : 'true'">
            <div class="feature-more-in">
              <p>{{ feature.about }}</p>
              <p v-if="!feature.always" class="feature-free">Без подписки: {{ feature.free }}</p>
            </div>
          </div>
        </li>
      </ul>
      <button
        v-if="!user.sky"
        type="button"
        class="try"
        :aria-pressed="offer.preview ? 'true' : 'false'"
        @click="offer.preview = !offer.preview"
      >
        {{ offer.preview ? 'Погасить примерку' : 'Примерить зажжённое небо' }}
      </button>
    </section>

    <section aria-labelledby="sky-compare">
      <h3 id="sky-compare" class="part-title">Без подписки и с ней</h3>
      <table class="compare" :class="{ 'is-lit': user.sky }">
        <thead>
          <tr>
            <th scope="col"><span class="visually-hidden">Что</span></th>
            <th scope="col">Бесплатно</th>
            <th scope="col" class="compare-sky">
              <svg viewBox="0 0 16 12" aria-hidden="true"><path d="M1.5 10.5L1 3l4 3.2L8 1l3 5.2L15 3l-.5 7.5z" /></svg>
              С «Небосводом»
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="feature in FEATURES" :key="feature.id">
            <th scope="row">{{ feature.name }}</th>
            <td>{{ feature.free }}</td>
            <td class="compare-sky">{{ feature.sky }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section aria-labelledby="sky-plans">
      <h3 id="sky-plans" class="part-title">{{ user.sky ? 'Продлить' : 'Срок' }}</h3>
      <div class="plans" role="radiogroup" aria-labelledby="sky-plans">
        <label v-for="item in plans" :key="item.id" class="plan" :class="{ 'is-chosen': plan === item.id }">
          <input v-model="plan" class="visually-hidden" type="radio" name="plan" :value="item.id" />
          <span v-if="best === item.id" class="plan-badge">выгоднее всего</span>
          <span class="plan-name">{{ item.name }}</span>
          <span class="plan-price">{{ item.label }}</span>
          <span class="plan-note">{{ item.perMonth }}</span>
          <span v-if="item.saving" class="plan-saving">−{{ item.saving }}%</span>
        </label>
      </div>
    </section>

    <div class="pay">
      <button
        type="button"
        class="pay-cta"
        :class="{ 'is-quiet': user.sky && !ending }"
        :disabled="busy || !payOn || !chosen?.price"
        @click="pay"
      >
        <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg>
        <template v-if="busy">Открываем ЮKassa…</template>
        <template v-else-if="user.sky">Продлить {{ chosen.term }}<template v-if="chosen.price"> — {{ chosen.label }}</template></template>
        <template v-else>Зажечь Небосвод<template v-if="chosen.price"> — {{ chosen.label }}</template></template>
      </button>
      <p v-if="message" class="error" role="alert">{{ message }}</p>
      <p v-else-if="!payOn" class="pay-note">Оплата откроется совсем скоро.</p>
      <p v-else-if="!chosen?.price" class="pay-note">Цена этого срока ещё не назначена.</p>
    </div>

    <ul class="terms">
      <li>Без автопродления: одно списание за выбранный срок, дальше — только по вашему решению.</li>
      <li v-if="user.sky">Новый срок прибавится к текущему, ни один день не пропадёт.</li>
      <li>Оплата проходит на защищённой странице ЮKassa, чек придёт на {{ user.email }}.</li>
      <li>
        Условия — в
        <RouterLink class="inline" :to="{ name: 'legal', params: { page: 'offer' }, hash: '#sky' }">публичной оферте</RouterLink>.
      </li>
    </ul>
  </div>
</template>

<style scoped>
.sky-panel { display: grid; gap: 20px; }
.sky-panel > * { min-width: 0; }

.sky-replay {
  justify-self: center;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 999px;
  border: 1px solid rgba(240, 205, 138, 0.45);
  background: rgba(240, 205, 138, 0.08);
  font: inherit;
  font-size: 14px;
  color: #f3dcae;
  cursor: pointer;
  transition: background 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease;
}
.sky-replay svg { width: 13px; height: 10px; fill: currentColor; }
.sky-replay:hover { border-color: #f0cd8a; background: rgba(240, 205, 138, 0.16); box-shadow: 0 6px 22px rgba(230, 170, 80, 0.2); }
.sky-replay:focus-visible { outline: 2px solid #ffe2a8; outline-offset: 3px; }

.part-title { margin: 0 0 10px; font-family: var(--caps); font-weight: 600; font-size: 15px; letter-spacing: 0.12em; color: rgba(240, 205, 138, 0.85); }

/* The features: a quiet list; the open row shows what it gives and what stays free. */
.features { display: grid; gap: 2px; margin: 0; padding: 0; list-style: none; }
.feature { border-radius: 12px; transition: background 0.25s ease; }
.feature.is-hot { background: rgba(240, 205, 138, 0.035); }
.feature.is-open { background: rgba(240, 205, 138, 0.06); }
.feature-head {
  display: grid;
  grid-template-columns: 14px auto 1fr;
  align-items: baseline;
  gap: 10px;
  width: 100%;
  padding: 9px 10px;
  border: 0;
  border-radius: 12px;
  background: none;
  font: inherit;
  text-align: left;
  color: inherit;
  cursor: pointer;
}
.feature-head:focus-visible { outline: 1px solid #f0cd8a; outline-offset: -1px; }
.feature-star { width: 11px; height: 11px; align-self: center; fill: rgba(214, 222, 238, 0.4); transition: fill 0.5s ease, filter 0.5s ease; }
.feature.is-on .feature-star { fill: #f0cd8a; filter: drop-shadow(0 0 4px rgba(255, 205, 120, 0.85)); }
.feature-name { font-family: var(--serif); font-size: 18px; color: #f6efe2; }
.feature-sky { justify-self: end; text-align: right; font-size: 12.5px; line-height: 1.35; color: rgba(226, 220, 210, 0.6); }
.feature.is-on .feature-sky { color: rgba(240, 205, 138, 0.85); }
/* A row opens by height, not by a jump: the rest of the page slides down with it. */
.feature-more {
  display: grid;
  grid-template-rows: 0fr;
  visibility: hidden;
  transition: grid-template-rows 0.4s cubic-bezier(0.3, 0.7, 0.2, 1), visibility 0s linear 0.4s;
}
.feature.is-open .feature-more { grid-template-rows: 1fr; visibility: visible; transition-delay: 0s; }
.feature-more-in { min-height: 0; overflow: hidden; padding: 0 12px 0 34px; opacity: 0; transition: opacity 0.25s ease; }
.feature.is-open .feature-more-in { opacity: 1; transition: opacity 0.35s ease 0.12s; }
.feature-more p { margin: 0; font-family: var(--book); font-size: 14.5px; line-height: 1.55; color: rgba(239, 231, 216, 0.85); }
.feature-more .feature-free { margin-top: 6px; font-size: 12.5px; color: rgba(226, 220, 210, 0.55); }
.feature-more-in > :last-child { margin-bottom: 12px; }

.try {
  margin-top: 8px;
  padding: 6px 0;
  border: 0;
  background: none;
  font: inherit;
  font-family: var(--serif);
  font-style: italic;
  font-size: 16px;
  color: #f0cd8a;
  text-decoration: underline;
  text-decoration-color: rgba(240, 205, 138, 0.35);
  text-underline-offset: 3px;
  cursor: pointer;
}
.try:hover { text-decoration-color: currentColor; }
.try:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 2px; border-radius: 4px; }

/* The terms: three glass cards to choose from. */
.plans { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.plan {
  position: relative;
  display: grid;
  justify-items: center;
  gap: 2px;
  padding: 16px 6px 12px;
  border-radius: 16px;
  border: 1px solid rgba(240, 210, 150, 0.18);
  background: rgba(255, 240, 210, 0.03);
  text-align: center;
  cursor: pointer;
  transition: border-color 0.25s ease, background 0.25s ease, box-shadow 0.25s ease;
}
.plan:hover { border-color: rgba(240, 205, 138, 0.45); }
.plan.is-chosen { border-color: rgba(240, 205, 138, 0.85); background: radial-gradient(120% 100% at 50% 0%, rgba(240, 205, 138, 0.14), rgba(255, 240, 210, 0.03)); box-shadow: 0 8px 26px rgba(230, 170, 80, 0.14); }
.plan:has(input:focus-visible) { outline: 2px solid #ffe2a8; outline-offset: 2px; }
.plan-badge {
  position: absolute;
  top: -9px;
  padding: 2px 8px;
  border-radius: 999px;
  background: linear-gradient(180deg, #f4dba6, #dcb36c);
  color: #2b1d0b;
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.02em;
  white-space: nowrap;
}
.plan-name { font-family: var(--caps); font-weight: 600; font-size: 14px; letter-spacing: 0.06em; color: rgba(240, 205, 138, 0.9); }
.plan-price { font-family: var(--serif); font-size: 22px; line-height: 1.2; color: #f6efe2; }
.plan-note { min-height: 1.3em; font-size: 11.5px; color: rgba(226, 220, 210, 0.6); }
.plan-saving { font-size: 11.5px; font-weight: 600; color: #f0cd8a; }

.pay { display: grid; justify-items: center; gap: 8px; }
.pay-cta {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  width: 100%;
  min-height: 48px;
  padding: 12px 22px;
  border: 0;
  border-radius: 999px;
  background: linear-gradient(180deg, #f4dba6, #dcb36c);
  color: #2b1d0b;
  font: inherit;
  font-size: 15.5px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 8px 26px rgba(230, 170, 80, 0.22), inset 0 1px 0 rgba(255, 255, 255, 0.5);
  transition: box-shadow 0.25s ease, transform 0.25s ease, opacity 0.25s ease;
}
.pay-cta svg { width: 11px; height: 11px; fill: #5a3d12; }
.pay-cta:hover:not(:disabled) { box-shadow: 0 10px 34px rgba(230, 170, 80, 0.38); transform: translateY(-1px); }
.pay-cta:focus-visible { outline: 2px solid #ffe2a8; outline-offset: 3px; }
.pay-cta:disabled { opacity: 0.5; cursor: default; }
/* While the term runs far ahead, the renewal is an outline, not a call. */
.pay-cta.is-quiet { border: 1px solid rgba(240, 205, 138, 0.55); background: rgba(240, 205, 138, 0.07); color: #f3dcae; box-shadow: none; }
.pay-cta.is-quiet svg { fill: #f0cd8a; }
.pay-note { margin: 0; font-family: var(--serif); font-style: italic; font-size: 15px; color: rgba(226, 220, 210, 0.65); }
.error { margin: 0; font-size: 13.5px; color: #f2a48c; }

.terms { display: grid; gap: 4px; margin: 0; padding: 14px 0 0; border-top: 1px solid rgba(240, 210, 150, 0.12); list-style: none; }
.terms li { position: relative; padding-left: 16px; font-size: 12.5px; line-height: 1.5; color: rgba(226, 220, 210, 0.62); }
.terms li::before { content: '✦'; position: absolute; left: 0; top: 0.1em; font-size: 0.75em; color: rgba(240, 205, 138, 0.7); }
.inline { color: #f0cd8a; text-decoration: underline; text-decoration-color: rgba(240, 205, 138, 0.35); text-underline-offset: 3px; }
.inline:hover { text-decoration-color: currentColor; }

/* Free and lit side by side: one row per feature, the subscription's column in gold. */
.compare { width: 100%; border-collapse: collapse; font-size: 13px; line-height: 1.35; }
.compare th, .compare td { padding: 7px 6px; text-align: left; vertical-align: top; border-top: 1px solid rgba(240, 210, 150, 0.1); }
.compare thead th { border-top: 0; padding-top: 0; font-size: 11px; font-weight: 400; letter-spacing: 0.08em; text-transform: uppercase; color: rgba(226, 220, 210, 0.55); }
.compare tbody th { font-family: var(--serif); font-weight: 400; font-size: 15px; color: #f6efe2; }
.compare td { color: rgba(226, 220, 210, 0.7); }
.compare .compare-sky { color: rgba(240, 205, 138, 0.9); }
.compare thead .compare-sky { color: rgba(240, 205, 138, 0.85); white-space: nowrap; }
.compare-sky svg { width: 11px; height: 9px; margin-right: 3px; fill: none; stroke: currentColor; stroke-width: 1.2; stroke-linejoin: round; }
.compare.is-lit .compare-sky svg { fill: currentColor; }
.visually-hidden { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0; }

@media (max-width: 760px) {
  .feature-head { min-height: 44px; align-items: center; }
  .feature-name { font-size: 17px; }
  .plans { gap: 6px; }
  .plan-price { font-size: 19px; }
  .try { min-height: 44px; }
}
@media (prefers-reduced-motion: reduce) {
  .pay-cta, .feature-star, .feature-more, .feature-more-in { transition: none; }
}
</style>
