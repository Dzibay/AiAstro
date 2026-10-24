<script setup>
import { onMounted, ref, watch } from 'vue'
import Field from '../components/ui/Field.vue'
import { adminApi } from '../api/admin.js'
import { errorText } from '../api/http.js'
import { clearSession, writeSession } from '../composables/useSession.js'
import { useHead } from '../utils/useHead.js'
import { authed } from './admin/shared.js'
import './admin/admin.css'

useHead({ title: 'Админка', noindex: true })

/** The menu: a column on a wide screen, a row of tabs on a phone. */
const PAGES = [
  { to: { name: 'admin' }, label: 'Сводка', icon: 'M4 19V11M10 19V5M16 19v-6M22 19H2' },
  { to: { name: 'admin-analytics' }, label: 'Аналитика', icon: 'M3 4h18l-7 8.5V19l-4 2v-8.5Z' },
  { to: { name: 'admin-links' }, label: 'Ссылки', icon: 'M10 14a4.5 4.5 0 0 0 6.4 0l3.2-3.2a4.5 4.5 0 0 0-6.4-6.4L11.6 6M14 10a4.5 4.5 0 0 0-6.4 0l-3.2 3.2a4.5 4.5 0 0 0 6.4 6.4l1.6-1.6' },
  { to: { name: 'admin-users' }, label: 'Пользователи', icon: 'M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM2 21a7 7 0 0 1 14 0M17 3.5a4 4 0 0 1 0 7.5M22 21a7 7 0 0 0-4-6.3' },
  { to: { name: 'admin-payments' }, label: 'Платежи', icon: 'M2 6h20v12H2zM2 10h20M6 15h4' },
  { to: { name: 'admin-pairs' }, label: 'Пары', icon: 'M8.5 15a5.5 5.5 0 1 0 0-11 5.5 5.5 0 0 0 0 11ZM15.5 20a5.5 5.5 0 1 0 0-11 5.5 5.5 0 0 0 0 11Z' },
  { to: { name: 'admin-ai' }, label: 'ИИ-астролог', icon: 'M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8ZM18.5 15l.9 2.1 2.1.9-2.1.9-.9 2.1-.9-2.1-2.1-.9 2.1-.9Z' },
  { to: { name: 'admin-settings' }, label: 'Настройки', icon: 'M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0M16 4v4M10 10v4M18 16v4' },
]

const password = ref('')
const message = ref('')
const pending = ref(false)
const checked = ref(false)
let leaving = false

onMounted(async () => {
  if (!authed.value) {
    checked.value = true
    return
  }
  try {
    await adminApi.me()
  } catch (error) {
    authed.value = false
    message.value = errorText(error)
  } finally {
    checked.value = true
  }
})

// A session that ran out on some page: the password form, with a word why.
watch(authed, (on) => {
  if (!on && checked.value && !leaving) message.value = 'Сессия истекла, войдите снова'
  leaving = false
})

async function login() {
  message.value = ''
  pending.value = true
  try {
    const result = await adminApi.login({ password: password.value })
    writeSession('admin', result.token)
    password.value = ''
    message.value = ''
    authed.value = true
  } catch (error) {
    message.value = errorText(error)
  } finally {
    pending.value = false
  }
}

function logout() {
  clearSession('admin')
  leaving = true
  message.value = ''
  authed.value = false
}
</script>

<template>
  <!-- No site header or footer: the operator's pages keep the whole screen for the figures. -->
  <main class="site adm-site">
    <section class="section adm-section">
      <div v-if="!authed" class="wrap narrow">
        <h1>Админка</h1>
        <form class="form" @submit.prevent="login">
          <Field v-model="password" label="Пароль оператора" type="password" autocomplete="current-password" />
          <p v-if="message" class="error">{{ message }}</p>
          <button class="button" type="submit" :disabled="pending">Войти</button>
        </form>
      </div>

      <div v-else-if="checked" class="adm">
        <aside class="adm-side">
          <p class="adm-title">Админка</p>
          <RouterLink to="/" class="adm-site-link">← На сайт</RouterLink>
          <nav class="adm-nav" aria-label="Разделы админки">
            <RouterLink v-for="page in PAGES" :key="page.label" :to="page.to" class="adm-nav-link" :exact-active-class="page.to.name === 'admin' ? 'is-on' : ''" :active-class="page.to.name === 'admin' ? '' : 'is-on'">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path :d="page.icon" /></svg>
              <span>{{ page.label }}</span>
            </RouterLink>
          </nav>
          <button type="button" class="text-button adm-logout" @click="logout">Выйти</button>
        </aside>
        <div class="adm-main">
          <RouterView />
        </div>
      </div>
    </section>
  </main>
</template>
