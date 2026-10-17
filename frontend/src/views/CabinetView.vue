<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import SiteFrame from '../components/SiteFrame.vue'
import { webApi } from '../api/web.js'
import { ApiError, errorText } from '../api/http.js'
import { clearSession } from '../composables/useSession.js'
import { formatDate } from '../utils/format.js'
import { useHead } from '../utils/useHead.js'

const router = useRouter()
const user = ref(null)
const message = ref('')

useHead({ title: 'Кабинет', noindex: true })

onMounted(async () => {
  try {
    user.value = await webApi.me()
  } catch (error) {
    if (error instanceof ApiError && (error.status === 401 || error.code === 'blocked')) {
      clearSession('web')
      router.push({ name: 'login' })
      return
    }
    message.value = errorText(error)
  }
})

function logout() {
  clearSession('web')
  router.push('/')
}
</script>

<template>
  <SiteFrame>
    <section class="section">
      <div class="wrap narrow-copy">
        <h1>Кабинет</h1>
        <p v-if="message" class="error">{{ message }}</p>
        <template v-else-if="user">
          <p class="lede">{{ user.name }}</p>
          <p>{{ user.email }}</p>
          <p class="meta">С {{ formatDate(user.created_at) }}</p>
          <div class="card">
            <h2>Разборы</h2>
            <p>Готовых разборов нет. Расчёт натальной карты ещё не подключён.</p>
          </div>
          <button type="button" class="text-button" @click="logout">Выйти</button>
        </template>
        <p v-else>Открываем кабинет…</p>
      </div>
    </section>
  </SiteFrame>
</template>
