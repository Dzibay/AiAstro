<script setup>
import { onMounted, ref } from 'vue'
import SiteFrame from '../components/SiteFrame.vue'
import Field from '../components/ui/Field.vue'
import { adminApi } from '../api/admin.js'
import { errorText } from '../api/http.js'
import { clearSession, readSession, writeSession } from '../composables/useSession.js'
import { useToast } from '../composables/useToast.js'
import { useHead } from '../utils/useHead.js'

const { push } = useToast()
const authed = ref(Boolean(readSession('admin')))
const password = ref('')
const items = ref([])
const message = ref('')
const pending = ref(false)

useHead({ title: 'Админка', noindex: true })

async function loadSettings() {
  const data = await adminApi.settings()
  items.value = data.items
}

onMounted(async () => {
  if (!authed.value) return
  try {
    await adminApi.me()
    await loadSettings()
  } catch (error) {
    authed.value = false
    message.value = errorText(error)
  }
})

async function login() {
  message.value = ''
  pending.value = true
  try {
    const result = await adminApi.login({ password: password.value })
    writeSession('admin', result.token)
    authed.value = true
    password.value = ''
    await loadSettings()
  } catch (error) {
    message.value = errorText(error)
  } finally {
    pending.value = false
  }
}

async function save(item) {
  message.value = ''
  try {
    const saved = await adminApi.saveSetting({ key: item.key, value: item.value })
    item.value = saved.value
    push('Сохранено')
  } catch (error) {
    message.value = errorText(error)
  }
}

function logout() {
  clearSession('admin')
  authed.value = false
  items.value = []
}
</script>

<template>
  <SiteFrame>
    <section class="section">
      <div class="wrap narrow">
        <h1>Админка</h1>
        <form v-if="!authed" class="form" @submit.prevent="login">
          <Field v-model="password" label="Пароль оператора" type="password" autocomplete="current-password" />
          <p v-if="message" class="error">{{ message }}</p>
          <button class="button" type="submit" :disabled="pending">Войти</button>
        </form>
        <template v-else>
          <p class="lede">Название, подзаголовок и почта поддержки. Секреты здесь не меняются.</p>
          <p v-if="message" class="error">{{ message }}</p>
          <form v-for="item in items" :key="item.key" class="form setting" @submit.prevent="save(item)">
            <Field v-model="item.value" :label="item.label" autocomplete="off" />
            <button class="button" type="submit">Сохранить</button>
          </form>
          <button type="button" class="text-button" @click="logout">Выйти</button>
        </template>
      </div>
    </section>
  </SiteFrame>
</template>
