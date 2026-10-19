<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import SiteFrame from '../components/SiteFrame.vue'
import Field from '../components/ui/Field.vue'
import { adminApi } from '../api/admin.js'
import { errorText } from '../api/http.js'
import { clearSession, readSession, writeSession } from '../composables/useSession.js'
import { useToast } from '../composables/useToast.js'
import { useHead } from '../utils/useHead.js'

const SKY_DAYS = 30

const { push } = useToast()
const authed = ref(Boolean(readSession('admin')))
const password = ref('')
const items = ref([])
const message = ref('')
const pending = ref(false)
const query = ref('')
const users = ref([])
const usersMessage = ref('')
const busy = ref(null)
let searchTimer = 0

useHead({ title: 'Админка', noindex: true })

const untilFormat = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })

function skyStatus(user) {
  return user.sky ? `Небосвод до ${untilFormat.format(new Date(user.sky_until))}` : 'без подписки'
}

async function loadSettings() {
  const data = await adminApi.settings()
  items.value = data.items
}

async function loadUsers() {
  usersMessage.value = ''
  const asked = query.value
  try {
    const data = await adminApi.users(asked)
    // An older answer must not overwrite the list of a newer query.
    if (asked === query.value) users.value = data.items
  } catch (error) {
    usersMessage.value = errorText(error)
  }
}

watch(query, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(loadUsers, 300)
})
onBeforeUnmount(() => clearTimeout(searchTimer))

onMounted(async () => {
  if (!authed.value) return
  try {
    await adminApi.me()
    await Promise.all([loadSettings(), loadUsers()])
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
    await Promise.all([loadSettings(), loadUsers()])
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

async function setSky(user, days) {
  usersMessage.value = ''
  busy.value = user.id
  try {
    const saved = await adminApi.setSky(user.id, days)
    Object.assign(user, saved)
    push(days ? `Небосвод открыт: ${user.email}` : `Небосвод снят: ${user.email}`)
  } catch (error) {
    usersMessage.value = errorText(error)
  } finally {
    busy.value = null
  }
}

/** The pairs of one person, opened on demand: until payment, a pair's reading is opened here. */
const pairs = ref({})
async function togglePairs(user) {
  if (pairs.value[user.id]) {
    const { [user.id]: _, ...rest } = pairs.value
    pairs.value = rest
    return
  }
  usersMessage.value = ''
  try {
    const data = await adminApi.partners(user.id)
    pairs.value = { ...pairs.value, [user.id]: data.items }
  } catch (error) {
    usersMessage.value = errorText(error)
  }
}
async function setBought(user, partner, bought) {
  usersMessage.value = ''
  busy.value = user.id
  try {
    const saved = await adminApi.setBought(user.id, partner.id, bought)
    Object.assign(partner, saved)
    push(bought ? `Разбор пары открыт: ${user.email} и ${partner.name}` : `Разбор пары закрыт: ${user.email} и ${partner.name}`)
  } catch (error) {
    usersMessage.value = errorText(error)
  } finally {
    busy.value = null
  }
}

function logout() {
  clearSession('admin')
  authed.value = false
  items.value = []
  users.value = []
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

          <h2 class="admin-heading">Пользователи</h2>
          <p class="meta">Пока оплаты нет, «Небосвод» открывается здесь: на {{ SKY_DAYS }} дней, от конца текущего срока. Разбор пары — в списке пар человека.</p>
          <div class="form">
            <Field v-model="query" label="Поиск по почте или имени" type="search" autocomplete="off" />
          </div>
          <p v-if="usersMessage" class="error">{{ usersMessage }}</p>
          <ul v-if="users.length" class="users">
            <li v-for="user in users" :key="user.id" class="user-row">
              <div class="user-who">
                <strong>{{ user.email }}</strong>
                <span class="meta">
                  {{ user.name }}<template v-if="user.blocked"> · заблокирован</template> · {{ skyStatus(user) }}
                </span>
              </div>
              <div class="user-actions">
                <button class="button button-small" type="button" :disabled="busy === user.id" @click="setSky(user, SKY_DAYS)">
                  Небосвод на {{ SKY_DAYS }} дней
                </button>
                <button
                  v-if="user.sky"
                  class="text-button"
                  type="button"
                  :disabled="busy === user.id"
                  @click="setSky(user, 0)"
                >
                  Снять
                </button>
                <button class="text-button" type="button" :aria-expanded="Boolean(pairs[user.id])" @click="togglePairs(user)">
                  {{ pairs[user.id] ? 'Скрыть пары' : 'Пары' }}
                </button>
              </div>
              <template v-if="pairs[user.id]">
                <ul v-if="pairs[user.id].length" class="pairs">
                  <li v-for="partner in pairs[user.id]" :key="partner.id" class="pair-row">
                    <span>
                      {{ partner.name }}
                      <span class="meta"> · {{ partner.birth ? 'данные есть' : 'ждём ответа' }}<template v-if="partner.bought"> · разбор оплачен</template></span>
                    </span>
                    <button
                      class="text-button"
                      type="button"
                      :disabled="busy === user.id || !partner.birth"
                      @click="setBought(user, partner, !partner.bought)"
                    >
                      {{ partner.bought ? 'Закрыть разбор' : 'Отметить оплату' }}
                    </button>
                  </li>
                </ul>
                <p v-else class="meta">Пар пока нет.</p>
              </template>
            </li>
          </ul>
          <p v-else-if="!usersMessage" class="meta">Никого не нашлось.</p>

          <button type="button" class="text-button logout" @click="logout">Выйти</button>
        </template>
      </div>
    </section>
  </SiteFrame>
</template>

<style scoped>
.admin-heading { margin: 40px 0 6px; font-size: 32px; }

.users {
  list-style: none;
  margin: 0;
  padding: 0;
  border-top: 1px solid var(--line);
}

.user-row {
  display: grid;
  gap: 10px;
  padding: 14px 0;
  border-bottom: 1px solid var(--line);
}

.user-who { display: grid; gap: 2px; min-width: 0; }
.user-who strong { overflow-wrap: anywhere; font-weight: 600; }

.user-actions { display: flex; flex-wrap: wrap; gap: 16px; align-items: center; }
.pairs { display: grid; gap: 6px; margin: 0; padding: 0 0 0 14px; list-style: none; border-left: 1px solid var(--line); }
.pair-row { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 6px 16px; }
.button-small { padding: 8px 16px; font-size: 15px; }

.logout { margin-top: 28px; }
</style>
