<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'
import PanelHead from '../../components/cabinet/PanelHead.vue'
import GuardField from '../../components/cabinet/GuardField.vue'
import { webApi } from '../../api/web.js'
import { errorText } from '../../api/http.js'
import { supportOf, useSiteConfig } from '../../composables/useSiteConfig.js'
import { formatDate } from '../../utils/format.js'
import { startTour } from '../../utils/tour.js'

/**
 * The profile: the name, the email, the password, «Небосвод» and, at the very end, the way to
 * delete the cabinet. Each part saves on its own; the email, a new password and the deletion ask
 * for the password or a code from a letter (GuardField), so a forgotten open tab cannot change
 * them. An account that came in by the letter has no password: its first one asks nothing.
 */

const props = defineProps({
  user: { type: Object, required: true },
})
const emit = defineEmits(['updated', 'logout'])

const { config, load } = useSiteConfig()
onMounted(load)
const support = computed(() => supportOf(config.value))

/** One small form: its fields, whether it is sending, its error and its «сохранено». */
function form(fields) {
  return reactive({ ...fields, busy: false, error: '', done: '' })
}
async function send(target, action, doneText) {
  if (target.busy) return
  target.busy = true
  target.error = ''
  target.done = ''
  try {
    const answer = await action()
    target.done = typeof doneText === 'function' ? doneText(answer) : doneText
  } catch (error) {
    target.error = errorText(error)
  } finally {
    target.busy = false
  }
}

const name = form({ value: props.user.name || '' })
const nameChanged = computed(() => name.value.trim() && name.value.trim() !== props.user.name)
function saveName() {
  const first = !props.user.name
  send(name, async () => {
    const next = await webApi.setName(name.value.trim())
    name.value = next.name
    emit('updated', next)
  }, first ? 'Приятно познакомиться' : 'Имя сохранено')
}

/** The six digits as the API takes them: «123 456» and «123456» alike. */
const digits = (code) => code.replace(/\D/g, '')
/** Whichever proof is filled in: the password or a whole code. */
const proven = (target, key = 'password') => Boolean(target[key] || digits(target.code).length === 6)

const email = form({ open: false, value: '', password: '', code: '' })
/** The new address takes the old one's place once the link in the letter to it is opened. */
function saveEmail() {
  send(email, async () => {
    const answer = await webApi.setEmail({ email: email.value.trim(), password: email.password, code: digits(email.code) })
    Object.assign(email, { open: false, value: '', password: '', code: '' })
    emit('updated', answer.user)
    return answer.pending
  }, (pending) => `Письмо ушло на ${pending}: откройте ссылку в нём — и входите с новой почтой. До тех пор вход — с прежней.`)
}

const password = form({ open: false, current: '', code: '', value: '' })
/** The first password asks nothing more: the person came in by the letter. */
const firstPassword = computed(() => !props.user.has_password)
function savePassword() {
  const first = firstPassword.value
  send(password, async () => {
    const answer = await webApi.setPassword({ current: password.current, code: digits(password.code), password: password.value })
    Object.assign(password, { open: false, current: '', code: '', value: '' })
    if (answer?.user) emit('updated', answer.user)
  }, first ? 'Пароль задан — теперь можно входить и по письму, и с ним' : 'Пароль изменён')
}

/** The letters about «Небосвод» and the partners; the password link comes regardless. */
const letters = form({})
function toggleLetters() {
  const on = !props.user.mail_notes
  send(letters, async () => {
    emit('updated', await webApi.setMailNotes(on))
  }, on ? 'Письма снова будут приходить' : 'Больше не напишем')
}

const removal = form({ open: false, password: '', code: '' })
function removeAccount() {
  send(removal, async () => {
    await webApi.deleteAccount({ password: removal.password, code: digits(removal.code) })
    emit('logout')
  }, '')
}

const untilFormat = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })
const skyLine = computed(() => (props.user.sky
  ? `горит до ${untilFormat.format(new Date(props.user.sky_until))}`
  : 'не зажжён'))
const showPassword = ref(false)
</script>

<template>
  <div class="profile-panel">
    <PanelHead lead="Имя, почта, пароль и «Небосвод» — всё о вас в одном месте.">
      Ваш <em>профиль</em>
    </PanelHead>

    <section class="block" aria-labelledby="name-title">
      <h3 id="name-title" class="block-title">Имя</h3>
      <form class="line" novalidate @submit.prevent="saveName">
        <label class="field">
          <span class="visually-hidden">Имя</span>
          <input v-model="name.value" type="text" maxlength="80" autocomplete="given-name" placeholder="Как к вам обращаться" />
        </label>
        <button type="submit" class="soft" :disabled="!nameChanged || name.busy">Сохранить</button>
      </form>
      <p class="hint">Так к вам обращаются в кабинете и в разборах.</p>
      <p v-if="name.error" class="error" role="alert">{{ name.error }}</p>
      <p v-else-if="name.done" class="done" role="status">✦ {{ name.done }}</p>
    </section>

    <section class="block" aria-labelledby="email-title">
      <h3 id="email-title" class="block-title">Почта</h3>
      <div class="row">
        <span class="value">{{ user.email }}</span>
        <button v-if="!email.open" type="button" class="link" @click="email.open = true; email.done = ''">Изменить</button>
      </div>
      <form v-if="email.open" class="stack" novalidate @submit.prevent="saveEmail">
        <label class="field">
          <span class="field-label">Новая почта</span>
          <input v-model="email.value" type="email" autocomplete="email" required />
        </label>
        <GuardField v-model:password="email.password" v-model:code="email.code" :has-password="user.has_password" />
        <div class="actions">
          <button type="submit" class="soft" :disabled="!email.value || !proven(email) || email.busy">Сменить почту</button>
          <button type="button" class="link" @click="Object.assign(email, { open: false, password: '', code: '', error: '' })">Отмена</button>
        </div>
      </form>
      <p v-if="email.error" class="error" role="alert">{{ email.error }}</p>
      <p v-else-if="email.done" class="done" role="status">✦ {{ email.done }}</p>
    </section>

    <section class="block" aria-labelledby="password-title">
      <h3 id="password-title" class="block-title">Пароль</h3>
      <div v-if="!password.open" class="row">
        <span v-if="firstPassword" class="value">Не задан — вход по письму</span>
        <span v-else class="value is-quiet">••••••••</span>
        <button type="button" class="link" @click="password.open = true; password.done = ''">{{ firstPassword ? 'Задать' : 'Сменить' }}</button>
      </div>
      <form v-else class="stack" novalidate @submit.prevent="savePassword">
        <GuardField
          v-if="!firstPassword"
          v-model:password="password.current"
          v-model:code="password.code"
          has-password
          label="Текущий пароль"
        />
        <label class="field">
          <span class="field-label">{{ firstPassword ? 'Пароль — от 8 символов' : 'Новый — от 8 символов' }}</span>
          <input v-model="password.value" :type="showPassword ? 'text' : 'password'" autocomplete="new-password" minlength="8" required />
        </label>
        <label class="check">
          <input v-model="showPassword" type="checkbox" />
          <span>Показать пароль</span>
        </label>
        <div class="actions">
          <button
            type="submit"
            class="soft"
            :disabled="(!firstPassword && !proven(password, 'current')) || password.value.length < 8 || password.busy"
          >
            {{ firstPassword ? 'Задать пароль' : 'Сменить пароль' }}
          </button>
          <button type="button" class="link" @click="Object.assign(password, { open: false, current: '', code: '', value: '', error: '' })">Отмена</button>
        </div>
      </form>
      <p v-if="firstPassword && !password.done" class="hint">По желанию: с паролем можно входить сразу, без письма.</p>
      <p v-if="password.error" class="error" role="alert">{{ password.error }}</p>
      <p v-else-if="password.done" class="done" role="status">✦ {{ password.done }}</p>
    </section>

    <section class="block" aria-labelledby="sky-title">
      <h3 id="sky-title" class="block-title">Небосвод</h3>
      <div class="row">
        <span class="value" :class="{ 'is-gold': user.sky }">{{ skyLine }}</span>
        <RouterLink class="link" v-seen="'sky:profile'" data-track="sky:profile" :to="{ name: 'cabinet-sky' }">{{ user.sky ? 'Продлить' : 'Зажечь' }}</RouterLink>
      </div>
      <p class="hint">
        {{ user.sky
          ? `Автопродления нет: когда срок выйдет, Небосвод просто погаснет, а карта останется с вами.${user.mail_notes ? ' За три дня до конца придёт письмо.' : ''}`
          : 'Натальная карта бесплатна навсегда. Небосвод добавляет полные прогнозы, календарь и ИИ-астролога на каждый день.' }}
      </p>
    </section>

    <section class="block" aria-labelledby="letters-title">
      <h3 id="letters-title" class="block-title">Письма</h3>
      <div class="row">
        <span class="value">{{ user.mail_notes ? 'Приходят' : 'Отключены' }}</span>
        <button type="button" class="link" :disabled="letters.busy" @click="toggleLetters">
          {{ user.mail_notes ? 'Отключить' : 'Включить' }}
        </button>
      </div>
      <p class="hint">
        Напоминания о конце «Небосвода» и о незавершённой оплате, вести о партнёре и паре. Подтверждение почты,
        ссылка для нового пароля и письмо об оплате приходят всегда.
      </p>
      <p v-if="letters.error" class="error" role="alert">{{ letters.error }}</p>
      <p v-else-if="letters.done" class="done" role="status">✦ {{ letters.done }}</p>
    </section>

    <section class="block" aria-labelledby="tour-title">
      <h3 id="tour-title" class="block-title">Знакомство</h3>
      <div class="row">
        <span class="value">Как устроен кабинет</span>
        <button type="button" class="link" @click="startTour('intro')">Пройти заново</button>
      </div>
      <div v-if="user.sky" class="row">
        <span class="value">Что открыл «Небосвод»</span>
        <button type="button" class="link" @click="startTour('sky')">Показать снова</button>
      </div>
      <p class="hint">Звезда, пять разделов и что из них бесплатно — по шагам. То же открывает «?» у вашей звезды, а «?» в углу панели раздела рассказывает о нём самом.</p>
    </section>

    <section v-if="support" class="block" aria-labelledby="support-title">
      <h3 id="support-title" class="block-title">Поддержка</h3>
      <div class="row">
        <span class="value">{{ support.kind === 'telegram' ? 'Telegram' : 'Почта' }}</span>
        <a class="link" :href="support.href" target="_blank" rel="noopener">{{ support.label }}</a>
      </div>
      <p class="hint">Если оплата прошла, а разбор не открылся, или нужно исправить данные рождения — напишите, разберёмся.</p>
    </section>

    <p class="since">С нами с {{ formatDate(user.created_at) }}</p>

    <section class="danger" aria-labelledby="delete-title">
      <h3 id="delete-title" class="visually-hidden">Удаление кабинета</h3>
      <button v-if="!removal.open" type="button" class="link is-danger" @click="removal.open = true">Удалить кабинет</button>
      <form v-else class="stack" novalidate @submit.prevent="removeAccount">
        <p class="warning">
          Кабинет исчезнет вместе с картой, парами и разговорами с ИИ-астрологом. Вернуть их будет нельзя.
        </p>
        <GuardField v-model:password="removal.password" v-model:code="removal.code" :has-password="user.has_password" />
        <div class="actions">
          <button type="submit" class="danger-button" :disabled="!proven(removal) || removal.busy">Удалить навсегда</button>
          <button type="button" class="link" @click="Object.assign(removal, { open: false, password: '', code: '', error: '' })">Оставить</button>
        </div>
        <p v-if="removal.error" class="error" role="alert">{{ removal.error }}</p>
      </form>
    </section>
  </div>
</template>

<style scoped>
.profile-panel { display: grid; gap: 18px; }

.line { display: grid; grid-template-columns: 1fr auto; gap: 10px; align-items: center; }
.stack { display: grid; gap: 12px; }
.row { display: flex; justify-content: space-between; align-items: baseline; gap: 16px; }
.value { font-family: var(--book); font-size: 15px; color: #efe7d8; overflow-wrap: anywhere; }
.value.is-quiet { letter-spacing: 0.2em; color: rgba(226, 220, 210, 0.5); }
.value.is-gold { font-family: var(--serif); font-style: italic; font-size: 17px; color: #f3dcae; }
.actions { display: flex; flex-wrap: wrap; align-items: center; gap: 10px 16px; }

.field { display: grid; gap: 7px; min-width: 0; }
.field-label { line-height: 16px; font-size: 10.5px; letter-spacing: 0.24em; text-transform: uppercase; color: rgba(226, 214, 192, 0.66); }
.field input {
  width: 100%;
  min-width: 0;
  height: 44px;
  padding: 0 14px;
  border-radius: 12px;
  border: 1px solid rgba(240, 210, 150, 0.18);
  background: rgba(255, 240, 210, 0.04);
  color: #f6efe2;
  font: inherit;
  font-size: 15px;
  color-scheme: dark;
  outline: none;
  transition: border-color 0.25s ease, background 0.25s ease, box-shadow 0.25s ease;
}
.field input:hover { border-color: rgba(240, 210, 150, 0.32); }
.field input:focus { border-color: rgba(240, 205, 138, 0.7); background: rgba(255, 240, 210, 0.06); box-shadow: 0 0 0 3px rgba(240, 205, 138, 0.12); }

.check { display: inline-flex; align-items: center; gap: 8px; font-size: 12.5px; color: rgba(226, 220, 210, 0.7); cursor: pointer; }
.check input { width: auto; margin: 0; padding: 0; accent-color: #dcb36c; }

.soft {
  padding: 0 18px;
  height: 44px;
  border-radius: 999px;
  border: 1px solid rgba(240, 205, 138, 0.5);
  background: rgba(240, 205, 138, 0.08);
  font: inherit;
  font-size: 14px;
  color: #f3dcae;
  cursor: pointer;
  transition: background 0.25s ease, border-color 0.25s ease, opacity 0.25s ease;
}
.soft:hover:not(:disabled) { background: rgba(240, 205, 138, 0.14); border-color: rgba(240, 205, 138, 0.8); }
.soft:disabled { opacity: 0.4; cursor: default; }
.soft:focus-visible { outline: 2px solid #ffe2a8; outline-offset: 3px; }

.link {
  padding: 4px 0;
  border: 0;
  background: none;
  font: inherit;
  font-size: 13.5px;
  color: #f0cd8a;
  text-decoration: underline;
  text-decoration-color: rgba(240, 205, 138, 0.35);
  text-underline-offset: 3px;
  cursor: pointer;
  white-space: nowrap;
}
.link:hover { text-decoration-color: currentColor; }
.link:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 2px; border-radius: 4px; }
.link.is-danger { color: rgba(226, 160, 140, 0.8); text-decoration-color: rgba(226, 160, 140, 0.3); }

.hint { margin: 0; font-size: 13px; line-height: 1.5; color: rgba(226, 220, 210, 0.6); }
.error { margin: 0; font-size: 13.5px; color: #f2a48c; }
.done { margin: 0; font-family: var(--serif); font-style: italic; font-size: 15.5px; color: #f0cd8a; }
.since { margin: 0; text-align: center; font-family: var(--serif); font-style: italic; font-size: 15px; color: rgba(226, 220, 210, 0.5); }

.danger { display: grid; justify-items: center; padding-top: 14px; border-top: 1px solid rgba(240, 210, 150, 0.12); }
.danger .stack { justify-items: stretch; width: 100%; }
.warning { margin: 0; font-family: var(--book); font-size: 14px; line-height: 1.55; color: #f0c2b2; }
.danger-button {
  padding: 0 18px;
  height: 44px;
  border-radius: 999px;
  border: 1px solid rgba(226, 140, 120, 0.6);
  background: rgba(226, 140, 120, 0.12);
  font: inherit;
  font-size: 14px;
  color: #f4c8b8;
  cursor: pointer;
}
.danger-button:hover:not(:disabled) { background: rgba(226, 140, 120, 0.2); }
.danger-button:disabled { opacity: 0.4; cursor: default; }
.danger-button:focus-visible { outline: 2px solid #f4c8b8; outline-offset: 3px; }

.visually-hidden { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }

@media (max-width: 760px) {
  .link { min-height: 44px; }
}
</style>
