<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import SiteFrame from '../components/SiteFrame.vue'
import SkyVault from '../components/sky/SkyVault.vue'
import SkyCompare from '../components/sky/SkyCompare.vue'
import { webApi } from '../api/web.js'
import { readSession } from '../composables/useSession.js'
import { usePrices } from '../utils/prices.js'
import { useHead } from '../utils/useHead.js'

/**
 * What is being bought, before payment is connected: «Небосвод» as the vault it lights and the
 * comparison with the free cabinet, or the pair's reading with both of its prices. No forms.
 */

const PRODUCTS = {
  sky: {
    title: 'Небосвод',
    lead: 'Подписка, которая зажигает весь ваш небосвод: полные прогнозы, звёздный календарь на месяц, астролог без ограничений и разбор пары дешевле.',
  },
  synastry: {
    title: 'Разбор пары',
    lead: 'Две карты рядом, подробно: как вы любите, спорите и растёте рядом друг с другом.',
  },
}

const PAIR_PARTS = [
  { name: 'Чувства', text: 'как каждый любит и как принимает любовь' },
  { name: 'Притяжение', text: 'где искра и откуда берётся желание' },
  { name: 'Разговоры', text: 'как вы слышите друг друга и о чём спорите' },
  { name: 'Быт и опора', text: 'дом, привычки и надёжность' },
  { name: 'Общий путь', text: 'куда вы растёте вместе' },
]

const route = useRoute()
const router = useRouter()
const product = computed(() => PRODUCTS[route.params.product] || null)
const { sky: skyPrice, synastry: pairPrice, synastrySky: pairSkyPrice } = usePrices()

useHead({ title: 'Оплата', noindex: true })

/** Signed in: the person's «Небосвод» and the partner the reading is for, to say them by name. */
const user = ref(null)
const partnerName = ref('')
onMounted(async () => {
  if (!readSession('web')) return
  try {
    user.value = await webApi.me()
    const id = Number(route.query.partner)
    if (route.params.product === 'synastry' && id) {
      const { items } = await webApi.partners()
      partnerName.value = items.find((partner) => partner.id === id)?.name || ''
    }
  } catch {
    // Without the account the page still says what is being bought.
  }
})
const hasSky = computed(() => Boolean(user.value?.sky))

function back() {
  if (window.history.state?.back) router.back()
  else router.push({ name: 'cabinet' })
}
</script>

<template>
  <SiteFrame>
    <section class="section">
      <div class="wrap narrow">
        <p class="eyebrow">Оплата</p>
        <template v-if="route.params.product === 'sky'">
          <h1>{{ product.title }}</h1>
          <p class="lede">{{ product.lead }}</p>
          <div class="vault">
            <SkyVault :lit="hasSky" />
          </div>
          <p class="price">{{ skyPrice }} <span class="per">в месяц</span></p>
          <p v-if="hasSky" class="note">Ваш Небосвод уже горит — продление добавит месяц к сроку.</p>
          <SkyCompare class="compare" :lit="hasSky" />
          <p class="soon">Оплата появится совсем скоро. Мы бережно готовим её, чтобы всё прошло спокойно и надёжно.</p>
        </template>

        <template v-else-if="route.params.product === 'synastry'">
          <h1>{{ product.title }}<template v-if="partnerName">: <em>вы и {{ partnerName }}</em></template></h1>
          <p class="lede">{{ product.lead }}</p>
          <ul class="parts">
            <li v-for="part in PAIR_PARTS" :key="part.name">
              <span class="part-star" aria-hidden="true">✦</span>
              <span><span class="part-name">{{ part.name }}</span> — {{ part.text }}</span>
            </li>
          </ul>
          <dl class="prices">
            <div :class="{ 'is-mine': !hasSky }">
              <dt>Отдельно</dt>
              <dd>{{ pairPrice }}</dd>
            </div>
            <div class="with-sky" :class="{ 'is-mine': hasSky }">
              <dt>С Небосводом</dt>
              <dd>{{ pairSkyPrice }}</dd>
            </div>
          </dl>
          <p v-if="hasSky" class="note">У вас горит Небосвод — для вас действует цена со скидкой.</p>
          <p v-else class="note">
            С «Небосводом» разбор каждой пары дешевле.
            <RouterLink class="inline" :to="{ name: 'checkout', params: { product: 'sky' } }">Что ещё он зажигает</RouterLink>
          </p>
          <p class="soon">Оплата появится совсем скоро. Мы бережно готовим её, чтобы всё прошло спокойно и надёжно.</p>
        </template>

        <template v-else>
          <h1>Такого тарифа нет</h1>
          <p class="lede">Возможно, ссылка устарела.</p>
        </template>

        <div class="actions">
          <button class="button" type="button" @click="back">Вернуться</button>
          <RouterLink class="text-button" :to="{ name: 'cabinet' }">В кабинет</RouterLink>
        </div>
      </div>
    </section>
  </SiteFrame>
</template>

<style scoped>
h1 em { font-style: italic; color: #f0cd8a; }
.vault { max-width: 440px; margin: 8px auto 12px; }
.price { margin: 0 0 6px; font-family: var(--serif); font-size: 30px; text-align: center; color: #f6efe2; }
.per { font-style: italic; font-size: 18px; color: rgba(226, 220, 210, 0.6); }
.note { margin: 0 0 14px; text-align: center; font-family: var(--serif); font-style: italic; font-size: 17px; color: rgba(240, 205, 138, 0.85); }
.compare { margin: 10px 0 22px; }
.soon { margin: 18px 0 0; font-size: 14.5px; line-height: 1.6; color: rgba(226, 220, 210, 0.7); }

.parts { display: grid; gap: 8px; margin: 6px 0 22px; padding: 0; list-style: none; font-family: var(--book); font-size: 15px; line-height: 1.5; color: #efe7d8; }
.parts li { display: grid; grid-template-columns: 18px 1fr; }
.part-star { color: #f0cd8a; }
.part-name { font-family: var(--caps); font-weight: 600; font-size: 1.1em; letter-spacing: 0.04em; color: #f0cd8a; }

.prices { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 0 0 14px; }
.prices div { display: grid; gap: 4px; justify-items: center; padding: 14px 10px; border-radius: 16px; border: 1px solid rgba(240, 210, 150, 0.16); }
.prices .with-sky { border-color: rgba(240, 205, 138, 0.45); background: linear-gradient(180deg, rgba(240, 205, 138, 0.08), transparent); }
.prices .is-mine { box-shadow: 0 0 0 3px rgba(240, 205, 138, 0.12); }
.prices dt { font-family: var(--caps); font-weight: 600; font-size: 15px; letter-spacing: 0.08em; color: rgba(226, 220, 210, 0.66); }
.prices .with-sky dt { color: #f0cd8a; }
.prices dd { margin: 0; font-family: var(--serif); font-size: 26px; color: #f6efe2; }

.inline { color: #f0cd8a; text-decoration: underline; text-decoration-color: rgba(240, 205, 138, 0.35); text-underline-offset: 3px; }
.inline:hover { text-decoration-color: currentColor; }

.actions { display: flex; flex-wrap: wrap; align-items: center; gap: 22px; margin-top: 28px; }
.actions .text-button { text-decoration: none; }
</style>
