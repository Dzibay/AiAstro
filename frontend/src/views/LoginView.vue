<script setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SiteFrame from '../components/SiteFrame.vue'
import Field from '../components/ui/Field.vue'
import { webApi } from '../api/web.js'
import { errorText } from '../api/http.js'
import { writeSession } from '../composables/useSession.js'
import { useHead } from '../utils/useHead.js'

const route = useRoute()
const router = useRouter()
const mode = ref('login')
const email = ref('')
const password = ref('')
const name = ref('')
const message = ref('')
const pending = ref(false)

watch(mode, (value) => {
  useHead({ title: value === 'register' ? 'Регистрация' : 'Вход', noindex: true })
}, { immediate: true })

async function submit() {
  message.value = ''
  pending.value = true
  try {
    const body = { email: email.value, password: password.value }
    const result =
      mode.value === 'register'
        ? await webApi.register({ ...body, name: name.value })
        : await webApi.login(body)
    writeSession('web', result.token)
    const next = typeof route.query.next === 'string' ? route.query.next : '/cabinet'
    const target = next.startsWith('/') && !next.startsWith('//') && !next.startsWith('/login')
      ? next
      : '/cabinet'
    router.push(target)
  } catch (error) {
    message.value = errorText(error)
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <SiteFrame>
    <section class="section">
      <div class="wrap narrow">
        <h1>{{ mode === 'register' ? 'Новый кабинет' : 'Вход' }}</h1>
        <p class="lede">Почта и пароль. Разбор карты на этом шаге не считается.</p>
        <form class="form" @submit.prevent="submit">
          <Field
            v-if="mode === 'register'"
            v-model="name"
            label="Имя"
            autocomplete="name"
          />
          <Field v-model="email" label="Почта" type="email" autocomplete="email" />
          <Field
            v-model="password"
            label="Пароль"
            type="password"
            :autocomplete="mode === 'register' ? 'new-password' : 'current-password'"
          />
          <p v-if="message" class="error">{{ message }}</p>
          <button class="button" type="submit" :disabled="pending">
            {{ mode === 'register' ? 'Создать кабинет' : 'Войти' }}
          </button>
        </form>
        <button
          type="button"
          class="text-button"
          @click="mode = mode === 'login' ? 'register' : 'login'"
        >
          {{ mode === 'login' ? 'Нет кабинета — зарегистрироваться' : 'Уже есть кабинет — войти' }}
        </button>
      </div>
    </section>
  </SiteFrame>
</template>
