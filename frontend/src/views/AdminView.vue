<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
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

/** The settings under their headings, in the order of FIELDS on the server. */
const GROUPS = [
  { id: 'site', title: 'Сайт', note: 'Название, подзаголовок и почта поддержки.' },
  { id: 'prices', title: 'Цены', note: 'Целые рубли. Пока цена пуста, сайт пишет «от … ₽», а этот тариф не продаётся.' },
  { id: 'mail', title: 'Почта', note: 'SMTP почтового сервиса (Яндекс 360, Mail.ru для бизнеса, Unisender Go и подобные). С неё уходят ссылки для нового пароля, напоминание за три дня до конца «Небосвода» и весть об ответе партнёра.' },
  { id: 'pay', title: 'ЮKassa', note: 'shopId и секретный ключ — в личном кабинете ЮKassa, «Интеграция → Ключи API». Ключ test_… — для проверки без настоящих денег. Коды чека — из справочника ЮKassa (54-ФЗ).' },
]
const groups = computed(() => GROUPS.map((group) => ({ ...group, items: items.value.filter((item) => item.group === group.id) })))
const payOn = computed(() => {
  const shop = items.value.find((item) => item.key === 'yookassa_shop_id')
  const secret = items.value.find((item) => item.key === 'yookassa_secret_key')
  return Boolean(shop?.value && secret?.filled)
})

const value = (key) => items.value.find((item) => item.key === key)?.value || ''
const mailOn = computed(() => Boolean(value('smtp_host') && (value('mail_from') || value('smtp_user')).includes('@')))
const testMail = reactive({ email: '', busy: false, result: '', ok: false })
async function sendTestMail() {
  testMail.busy = true
  testMail.result = ''
  try {
    const answer = await adminApi.testMail(testMail.email.trim())
    testMail.ok = answer.ok
    testMail.result = answer.ok ? 'Письмо ушло — проверьте ящик (и папку «Спам»).' : `Сервер не принял письмо: ${answer.error}`
  } catch (error) {
    testMail.ok = false
    testMail.result = errorText(error)
  } finally {
    testMail.busy = false
  }
}

async function loadSettings() {
  const data = await adminApi.settings()
  items.value = data.items
}

/* ---- Payments ---- */

const payments = ref([])
const notifyUrl = ref('')
const STATUS = { new: 'создан', pending: 'ждёт оплаты', succeeded: 'оплачен', canceled: 'отменён', failed: 'не создан' }
const paidFormat = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
async function loadPayments() {
  const data = await adminApi.payments()
  payments.value = data.items
  notifyUrl.value = data.notify_url
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
    await Promise.all([loadSettings(), loadUsers(), loadPayments()])
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
    await Promise.all([loadSettings(), loadUsers(), loadPayments()])
  } catch (error) {
    message.value = errorText(error)
  } finally {
    pending.value = false
  }
}

async function save(item, value = item.value) {
  message.value = ''
  try {
    const saved = await adminApi.saveSetting({ key: item.key, value })
    Object.assign(item, saved)
    push(item.secret && !value ? 'Ключ стёрт' : 'Сохранено')
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
  payments.value = []
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
          <p v-if="message" class="error">{{ message }}</p>
          <template v-for="group in groups" :key="group.id">
            <h2 class="admin-heading">{{ group.title }}</h2>
            <p class="meta">{{ group.note }}</p>
            <p v-if="group.id === 'mail'" class="pay-state" :class="{ 'is-on': mailOn }">
              {{ mailOn ? 'Почта включена: письма уходят.' : 'Почта выключена: заполните сервер и адрес отправителя. Восстановить пароль пока нельзя.' }}
            </p>
            <p v-if="group.id === 'pay'" class="pay-state" :class="{ 'is-on': payOn }">
              {{ payOn ? 'Оплата включена: кнопки оплаты на сайте работают.' : 'Оплата выключена: заполните shopId и секретный ключ.' }}
            </p>
            <form v-for="item in group.items" :key="item.key" class="form setting" @submit.prevent="save(item)">
              <Field
                v-model="item.value"
                :label="item.label"
                :type="item.secret ? 'password' : 'text'"
                :placeholder="item.secret && item.filled ? `${item.key === 'smtp_password' ? 'Пароль сохранён' : 'Ключ сохранён'} — введите новый, чтобы заменить` : ''"
                autocomplete="off"
              />
              <div class="setting-actions">
                <button class="button" type="submit" :disabled="item.secret && !item.value">Сохранить</button>
                <button v-if="item.secret && item.filled" class="text-button" type="button" @click="save(item, '')">{{ item.key === 'smtp_password' ? 'Стереть пароль' : 'Стереть ключ' }}</button>
              </div>
            </form>
            <form v-if="group.id === 'mail' && mailOn" class="form setting" @submit.prevent="sendTestMail">
              <Field v-model="testMail.email" label="Пробное письмо на адрес" type="email" autocomplete="off" />
              <div class="setting-actions">
                <button class="button" type="submit" :disabled="!testMail.email.includes('@') || testMail.busy">
                  {{ testMail.busy ? 'Отправляем…' : 'Отправить' }}
                </button>
              </div>
              <p v-if="testMail.result" class="meta" :class="testMail.ok ? 'mail-ok' : 'error'">{{ testMail.result }}</p>
            </form>
            <div v-if="group.id === 'pay' && notifyUrl" class="notify">
              <p class="meta">
                В личном кабинете ЮKassa, «Интеграция → HTTP-уведомления», укажите этот адрес и события
                <code>payment.succeeded</code> и <code>payment.canceled</code>:
              </p>
              <code class="notify-url">{{ notifyUrl }}</code>
            </div>
          </template>

          <h2 class="admin-heading">Платежи</h2>
          <p class="meta">Последние пятьдесят. Возврат делается в личном кабинете ЮKassa; подписку после него можно снять ниже.</p>
          <ul v-if="payments.length" class="payments">
            <li v-for="payment in payments" :key="payment.id" class="payment-row" :class="`is-${payment.status}`">
              <span class="payment-when">{{ paidFormat.format(new Date(payment.paid_at || payment.created_at)) }}</span>
              <span class="payment-what">
                {{ payment.title }}
                <span class="meta"> · {{ payment.email }}</span>
              </span>
              <span class="payment-sum">{{ payment.amount.toLocaleString('ru-RU') }} ₽</span>
              <span class="payment-status">{{ STATUS[payment.status] || payment.status }}</span>
            </li>
          </ul>
          <p v-else class="meta">Платежей пока не было.</p>

          <h2 class="admin-heading">Пользователи</h2>
          <p class="meta">Оплаченное через ЮKassa открывается само. Здесь — вручную: «Небосвод» на {{ SKY_DAYS }} дней от конца текущего срока (подарок, возврат), разбор пары — в списке пар человека.</p>
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

.setting-actions { display: flex; flex-wrap: wrap; align-items: center; gap: 16px; }
.pay-state { margin: 4px 0 14px; font-weight: 600; color: #f2a48c; }
.pay-state.is-on { color: #9fd3a8; }
.mail-ok { color: #9fd3a8; }
.notify { display: grid; gap: 6px; margin-top: 4px; }
.notify-url { overflow-wrap: anywhere; padding: 10px 12px; border-radius: 10px; border: 1px solid var(--line); background: rgba(255, 240, 210, 0.04); font-size: 14px; user-select: all; }

.payments { list-style: none; margin: 0; padding: 0; border-top: 1px solid var(--line); }
.payment-row { display: grid; grid-template-columns: 7.5em 1fr auto auto; align-items: baseline; gap: 4px 16px; padding: 10px 0; border-bottom: 1px solid var(--line); font-size: 15px; }
.payment-what { min-width: 0; overflow-wrap: anywhere; }
.payment-when, .payment-status { font-size: 13px; opacity: 0.7; }
.payment-sum { font-variant-numeric: tabular-nums; font-weight: 600; }
.is-succeeded .payment-status { color: #9fd3a8; opacity: 1; }
.is-canceled .payment-status, .is-failed .payment-status { color: #f2a48c; opacity: 1; }
@media (max-width: 640px) {
  .payment-row { grid-template-columns: 1fr auto auto; }
  .payment-what { grid-column: 1 / -1; grid-row: 1; }
}
</style>
