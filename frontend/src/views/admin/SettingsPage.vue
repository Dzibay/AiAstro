<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { adminApi } from '../../api/admin.js'
import { errorText } from '../../api/http.js'
import { useToast } from '../../composables/useToast.js'
import { failed } from './shared.js'

/** The settings under their headings, in the order of FIELDS on the server. */
const GROUPS = [
  { id: 'site', title: 'Сайт', note: 'Название, подзаголовок и почта поддержки.' },
  { id: 'prices', title: 'Цены', note: 'Целые рубли. Пока цена пуста, сайт пишет «от … ₽», а этот тариф не продаётся.' },
  { id: 'mail', title: 'Почта', note: 'SMTP почтового сервиса (Яндекс 360, Mail.ru для бизнеса, Unisender Go и подобные). С неё уходят ссылки для нового пароля, напоминание за три дня до конца «Небосвода» и весть об ответе партнёра.' },
  { id: 'pay', title: 'ЮKassa', note: 'shopId и секретный ключ — в личном кабинете ЮKassa, «Интеграция → Ключи API». Ключ test_… — для проверки без настоящих денег. Коды чека — из справочника ЮKassa (54-ФЗ).' },
]

const { push } = useToast()
const items = ref([])
const notifyUrl = ref('')
const returnUrl = ref('')
const error = ref('')
const saving = ref('')

onMounted(async () => {
  try {
    const [data, pays] = await Promise.all([adminApi.settings(), adminApi.payments({})])
    items.value = data.items
    notifyUrl.value = pays.notify_url
    returnUrl.value = pays.return_url || ''
  } catch (caught) {
    error.value = failed(caught)
  }
})

const groups = computed(() => GROUPS.map((group) => ({ ...group, items: items.value.filter((item) => item.group === group.id) })))
const value = (key) => items.value.find((item) => item.key === key)?.value || ''
const mailOn = computed(() => Boolean(value('smtp_host') && (value('mail_from') || value('smtp_user')).includes('@')))
const payOn = computed(() => Boolean(value('yookassa_shop_id') && items.value.find((item) => item.key === 'yookassa_secret_key')?.filled))

async function save(item, next = item.value) {
  error.value = ''
  saving.value = item.key
  try {
    const saved = await adminApi.saveSetting({ key: item.key, value: next })
    Object.assign(item, saved)
    push(item.secret && !next ? (item.key === 'smtp_password' ? 'Пароль стёрт' : 'Ключ стёрт') : `Сохранено: ${item.label}`)
  } catch (caught) {
    error.value = failed(caught)
  } finally {
    saving.value = ''
  }
}

const testMail = reactive({ email: '', busy: false, result: '', ok: false })
async function sendTestMail() {
  testMail.busy = true
  testMail.result = ''
  try {
    const answer = await adminApi.testMail(testMail.email.trim())
    testMail.ok = answer.ok
    testMail.result = answer.ok ? 'Письмо ушло — проверьте ящик (и папку «Спам»).' : `Сервер не принял письмо: ${answer.error}`
  } catch (caught) {
    testMail.ok = false
    testMail.result = errorText(caught)
  } finally {
    testMail.busy = false
  }
}

async function copyText(text, ok = 'Адрес скопирован') {
  try {
    await navigator.clipboard.writeText(text)
    push(ok)
  } catch {
    push('Не получилось скопировать — выделите адрес вручную')
  }
}
</script>

<template>
  <header class="adm-head">
    <div>
      <h1>Настройки</h1>
      <p>Каждое поле сохраняется отдельно и сразу действует на сайте.</p>
    </div>
  </header>

  <p v-if="error" class="error">{{ error }}</p>

  <div class="st">
    <section v-for="group in groups" :key="group.id" class="adm-panel">
      <div class="adm-panel-head">
        <h2>{{ group.title }}</h2>
        <span v-if="group.id === 'mail'" class="adm-badge" :class="mailOn ? 'is-ok' : 'is-warn'">{{ mailOn ? 'включена' : 'выключена' }}</span>
        <span v-if="group.id === 'pay'" class="adm-badge" :class="payOn ? 'is-ok' : 'is-warn'">{{ payOn ? 'оплата включена' : 'оплата выключена' }}</span>
      </div>
      <p class="adm-note">{{ group.note }}</p>
      <p v-if="group.id === 'mail' && !mailOn" class="st-warn">Заполните сервер и адрес отправителя — пока письма не уходят и восстановить пароль нельзя.</p>
      <p v-if="group.id === 'pay' && !payOn" class="st-warn">Заполните shopId и секретный ключ — пока кнопки оплаты на сайте не работают.</p>

      <div class="st-fields" :class="{ 'is-prices': group.id === 'prices' }">
        <form v-for="item in group.items" :key="item.key" class="st-field" @submit.prevent="save(item)">
          <label class="adm-label" :for="`st-${item.key}`">{{ item.label }}</label>
          <div class="st-row">
            <input
              :id="`st-${item.key}`"
              v-model="item.value"
              class="adm-input"
              :type="item.secret ? 'password' : 'text'"
              :inputmode="group.id === 'prices' ? 'numeric' : undefined"
              :placeholder="item.secret && item.filled ? `${item.key === 'smtp_password' ? 'Пароль сохранён' : 'Ключ сохранён'} — введите новый, чтобы заменить` : ''"
              autocomplete="off"
            />
            <button class="adm-btn" type="submit" :disabled="(item.secret && !item.value) || saving === item.key">Сохранить</button>
          </div>
          <button v-if="item.secret && item.filled" class="text-button st-erase" type="button" :disabled="saving === item.key" @click="save(item, '')">
            {{ item.key === 'smtp_password' ? 'Стереть пароль' : 'Стереть ключ' }}
          </button>
        </form>
      </div>

      <form v-if="group.id === 'mail' && mailOn" class="st-field st-extra" @submit.prevent="sendTestMail">
        <label class="adm-label" for="st-test">Пробное письмо на адрес</label>
        <div class="st-row">
          <input id="st-test" v-model="testMail.email" class="adm-input" type="email" autocomplete="off" />
          <button class="adm-btn" type="submit" :disabled="!testMail.email.includes('@') || testMail.busy">{{ testMail.busy ? 'Отправляем…' : 'Отправить' }}</button>
        </div>
        <p v-if="testMail.result" class="st-result" :class="testMail.ok ? 'is-ok' : 'error'">{{ testMail.result }}</p>
      </form>

      <div v-if="group.id === 'pay' && (notifyUrl || returnUrl)" class="st-extra">
        <template v-if="returnUrl">
          <p class="adm-note">
            После оплаты мы просим ЮKassa вернуть человека сюда (<code>return_url</code>). Если в ссылке
            на странице ЮKassa всё равно главная — откройте настройки магазина в ЮKassa и в поле
            «Адрес сайта» поставьте этот же адрес (кнопка «Вернуться» иногда берёт его, а не
            <code>return_url</code> из платежа):
          </p>
          <div class="st-row">
            <code class="st-url">{{ returnUrl }}</code>
            <button type="button" class="adm-btn" @click="copyText(returnUrl)">Скопировать</button>
          </div>
        </template>
        <template v-if="notifyUrl">
          <p class="adm-note">
            В личном кабинете ЮKassa, «Интеграция → HTTP-уведомления», укажите этот адрес и события
            <code>payment.succeeded</code> и <code>payment.canceled</code>:
          </p>
          <div class="st-row">
            <code class="st-url">{{ notifyUrl }}</code>
            <button type="button" class="adm-btn" @click="copyText(notifyUrl)">Скопировать</button>
          </div>
        </template>
      </div>
    </section>
  </div>
</template>

<style scoped>
.st { display: grid; gap: 18px; }
.st-fields { display: grid; gap: 16px; }
.st-fields.is-prices { grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); }
.st-field { display: grid; gap: 6px; margin: 0; }
.st-row { display: flex; align-items: stretch; gap: 10px; }
.st-row .adm-input { flex: 1; min-width: 0; }
.st-row .adm-btn { flex: none; }
.st-erase { justify-self: start; font-size: 13px; }
.st-warn { margin: -6px 0 14px; color: #e6c27a; font-size: 14px; }
.st-extra { display: grid; gap: 6px; margin-top: 18px; padding-top: 16px; border-top: 1px solid var(--panel-line); }
.st-extra .adm-note { margin: 0; }
.st-result { margin: 0; font-size: 14px; }
.st-result.is-ok { color: var(--ok); }
.st-url { flex: 1; min-width: 0; padding: 9px 12px; border: 1px solid var(--line); border-radius: 10px; background: rgba(255, 240, 210, 0.04); font-size: 14px; overflow-wrap: anywhere; user-select: all; }
@media (max-width: 640px) {
  .st-row { flex-wrap: wrap; }
  .st-row .adm-btn { flex: 1; }
}
</style>
