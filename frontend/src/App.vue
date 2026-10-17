<script setup>
import { onMounted, ref } from 'vue'
import { RouterView } from 'vue-router'
import { useToast } from './composables/useToast.js'
import { acceptConsent, hasConsent } from './utils/consent.js'

const { items } = useToast()
const showConsent = ref(false)

onMounted(() => {
  showConsent.value = !hasConsent()
})

function accept() {
  acceptConsent()
  showConsent.value = false
}
</script>

<template>
  <RouterView />
  <div class="toasts" aria-live="polite">
    <p v-for="item in items" :key="item.id" class="toast">{{ item.text }}</p>
  </div>
  <div v-if="showConsent" class="banner" role="dialog" aria-label="Сообщение о данных в браузере">
    <p>
      В браузере сохраняются согласие с этим сообщением и токен входа. Рекламных cookie нет.
      <RouterLink to="/legal/privacy">Подробнее</RouterLink>
    </p>
    <button type="button" class="button" @click="accept">Понятно</button>
  </div>
</template>
