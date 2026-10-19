<script setup>
import { computed } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import SiteFrame from '../components/SiteFrame.vue'
import { useHead } from '../utils/useHead.js'

/** Until payment is connected: what is being bought and the way back. No real prices yet, no forms. */

const PRODUCTS = {
  sky: {
    title: 'Небосвод',
    lead: 'Полные прогнозы на день и неделю и разговор с астрологом.',
  },
  synastry: {
    title: 'Разбор пары',
    lead: 'Две карты рядом, подробно: как вы любите, спорите и растёте рядом друг с другом.',
  },
}

const route = useRoute()
const router = useRouter()
const product = computed(() => PRODUCTS[route.params.product] || null)

useHead({ title: 'Оплата', noindex: true })

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
        <template v-if="product">
          <h1>{{ product.title }}</h1>
          <p class="lede">{{ product.lead }}</p>
          <p class="price">от … ₽</p>
          <p>Оплата появится совсем скоро. Мы бережно готовим её, чтобы всё прошло спокойно и надёжно.</p>
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
.price { margin: 0 0 18px; font-family: var(--serif); font-size: 28px; }
.actions { display: flex; flex-wrap: wrap; align-items: center; gap: 22px; margin-top: 28px; }
.actions .text-button { text-decoration: none; }
</style>
