<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SiteHeader from '../components/SiteHeader.vue'
import { webApi } from '../api/web.js'
import { ApiError, errorText } from '../api/http.js'
import { readSession, webToken, writeSession } from '../composables/useSession.js'
import { START_PLACES, forgetSignIn, keptLetter, savedBirth, startSignIn } from '../composables/useSignIn.js'
import { supportOf, useSiteConfig } from '../composables/useSiteConfig.js'
import { useSky } from '../composables/useSky.js'
import { useHead } from '../utils/useHead.js'
import { likelyMeant, mailbox } from '../utils/mailbox.js'
import { skyOn } from '../utils/skyToday.js'
import { queue, reachGoal } from '../utils/track.js'

/**
 * The way into the cabinet, on the same sky as the home page (router meta.sky: 'login'). One
 * address serves the sign-up and the sign-in alike: a letter with a link and six digits goes to
 * it, and the cabinet opens by either — the link on any device, the code right on this page. The
 * password is the second way, for those who have set one in the profile.
 *
 * The birth data, the name and the password are asked in the cabinet, after the first look at the
 * chart. An account from before the letters, signed in but not yet confirmed, gets the same
 * letter screen (`?mode=confirm`), its session watching for the link.
 */

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
/** The confirmation screen of a signed-in account asks the server this often whether the link has been opened. */
const WATCH_MS = 4000

const route = useRoute()
const router = useRouter()
const { config, load } = useSiteConfig()
const { markUser, clearMark } = useSky()

/** The letter's link brings `?reset=<token>`: the card asks for the new password straight away. */
const resetToken = typeof route.query.reset === 'string' ? route.query.reset : ''
/** The letter's link brings `?confirm=<token>`: the cabinet opens on arrival. */
const confirmToken = typeof route.query.confirm === 'string' ? route.query.confirm : ''
const QUERY_MODES = { register: 'email', password: 'password', sent: 'sent', confirm: 'confirm' }
/**
 * email (the address for the letter) | password | forgot (the email for the reset link) | reset
 * (the new password by the link) | sent (the letter is on its way) | confirm (the same, for an
 * account signed in before the letters) | confirming (the letter's link is being opened).
 */
const mode = ref(resetToken ? 'reset' : confirmToken ? 'confirming' : QUERY_MODES[route.query.mode] || 'email')
/** Came for the chart (the buttons «Получить карту», a landing's form): the page greets a newcomer. */
/** The birth data typed on the home page wait for the new cabinet: the chart is ready on arrival. */
const birthWaiting = Boolean(savedBirth())
const fresh = route.query.mode === 'register' || birthWaiting
/** Where the address was given, for the funnel: the page that sent here, else the login itself. */
const place = START_PLACES.includes(route.query.from) ? route.query.from : 'login'

const email = ref('')
const password = ref('')
const code = ref('')
const consent = ref(false)
/** The consent's tick: shown to a newcomer at once, to anyone else once the server asks for it. */
const askConsent = ref(fresh)
const showPassword = ref(false)
const message = ref('')
const pending = ref(false)
/** A quiet answer that is not an error: the letter is on its way. */
const note = ref('')
/** Set once the cabinet is entered: the card dissolves and the star stays for the cabinet. */
const leaving = ref(false)
/** Signing in has begun: the session's arrival is this page's own, not another tab's. */
let entering = false
const emailField = ref(null)
const codeField = ref(null)

/**
 * The letter screen: the address the letter went to, the seconds before another may leave, the
 * flight's number (a new letter flies off again), the address being corrected (a signed-in account).
 */
const letter = reactive({ email: '', wait: 0, flight: 0, editing: false, value: '' })

const forgot = computed(() => mode.value === 'forgot')
const resetting = computed(() => mode.value === 'reset')
const lettered = computed(() => ['sent', 'confirm', 'confirming'].includes(mode.value))
const waiting = computed(() => mode.value === 'sent' || mode.value === 'confirm')
const asksPassword = computed(() => mode.value === 'password' || resetting.value)

/** Where the cabinet opens: the page asked for, never another site or the login itself. */
const target = computed(() => {
  const next = typeof route.query.next === 'string' ? route.query.next : '/cabinet'
  return next.startsWith('/') && !next.startsWith('//') && !next.startsWith('/login') ? next : '/cabinet'
})

/** The person's mail service ({ label, url }) and a likely slip in the address. */
const box = computed(() => mailbox(letter.email))
const slip = computed(() => likelyMeant(letter.email))
const typedSlip = computed(() => (EMAIL.test(email.value.trim()) ? likelyMeant(email.value.trim()) : ''))
const waitText = computed(() => `${Math.floor(letter.wait / 60)}:${String(letter.wait % 60).padStart(2, '0')}`)
const digits = computed(() => code.value.replace(/\D/g, ''))

const sky = skyOn(new Date())
const today = `Сегодня Луна ${sky.moon.in}, ${sky.phase}`

const TITLES = {
  forgot: 'Новый пароль',
  reset: 'Новый пароль',
  sent: 'Письмо для входа',
  confirm: 'Письмо для входа',
  confirming: 'Открываем кабинет',
}
// Sync, so a note set right after the switch of the mode stays.
watch(mode, (value) => {
  message.value = ''
  note.value = ''
  letter.editing = false
  useHead({ title: TITLES[value] || 'Вход', noindex: true })
}, { immediate: true, flush: 'sync' })
// The header leads here as well, to the address.
watch(() => route.query.mode, (value) => {
  if ((!confirmToken && !resetToken) || value) mode.value = QUERY_MODES[value] || 'email'
})
watch(mode, (value) => {
  if (value === 'password') queue('act', 'login:password')
})

/** The API's codes in the voice of the page; the rest falls back to the common texts. */
function say(error) {
  if (error instanceof ApiError && error.status < 500) {
    if (error.code === 'unauthorized') return 'Не узнаём эту почту с этим паролем'
    const support = supportOf(config.value)
    if (error.code === 'blocked') return support ? `Кабинет закрыт. Напишите нам: ${support.label}` : 'Кабинет закрыт. Напишите в поддержку'
    if (error.code === 'mail_off') return support ? `Письма пока не отправляются. Напишите нам: ${support.label}` : 'Письма пока не отправляются — напишите в поддержку'
  }
  return errorText(error)
}

/** The card dissolves first, then the sky flies on to the cabinet with the person's star. */
async function fly(user, to) {
  leaving.value = true
  markUser(user)
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  await new Promise((resolve) => setTimeout(resolve, reduce ? 0 : 320))
  router.push(to)
}

/**
 * In, by any way — the link, the code, the password, a cabinet opened at once: the session, the
 * goals, the birth data typed on the home page if the cabinet has none yet, then the cabinet.
 */
async function signedInto(result, to, { first = false } = {}) {
  entering = true
  writeSession('web', result.token)
  let user = result.user
  if (first) {
    reachGoal('astra.registration@success')
    if (user?.birth) reachGoal('astra.birth@save')
  }
  const birth = savedBirth()
  if (birth && user && !user.birth && user.email_confirmed !== false) {
    try {
      user = await webApi.setBirth(birth)
      reachGoal('astra.birth@save')
    } catch {
      /* the cabinet asks for them again */
    }
  }
  forgetSignIn()
  entering = false
  if (user?.email_confirmed === false) openConfirm(user)
  else await fly(user, to)
}

// ---- The letter: the address first ----

let begun = false
/** The first character of the address for the letter: the funnel's step «Начали вводить почту», from this
 * page's place. The address typed for the password is a sign-in, not a start. */
function begin() {
  if (begun || mode.value !== 'email') return
  begun = true
  queue('act', `email:${place}`)
}

/** The same answer whether the address is known or new: the letter goes, the screen waits for it. */
async function sendLetter() {
  const address = email.value.trim()
  message.value = ''
  note.value = ''
  if (!EMAIL.test(address)) {
    message.value = 'Почта выглядит неполной'
    return
  }
  if (askConsent.value && !consent.value) {
    message.value = 'Отметьте согласие на обработку данных'
    return
  }
  pending.value = true
  queue('act', `start:${place}`)
  try {
    const answer = await startSignIn({ email: address, consent: consent.value, next: target.value, place })
    // The site's mail is not set up: a new cabinet opens at once.
    if (answer.token) await signedInto(answer, target.value, { first: true })
    else openSent(address, answer)
  } catch (error) {
    if (error instanceof ApiError && error.code === 'consent') {
      askConsent.value = true
      message.value = 'Похоже, вы у нас впервые: отметьте согласие — и письмо уйдёт'
    } else if (error instanceof ApiError && error.code === 'mail_off') {
      mode.value = 'password'
      note.value = 'Письма пока не отправляются — войдите с паролем'
    } else if (error instanceof ApiError && error.code === 'confirm_wait') {
      openSent(address, { sent: false, wait: 60 })
    } else {
      message.value = say(error)
    }
  } finally {
    pending.value = false
  }
}

let waitTimer = 0
function startWait(seconds) {
  clearInterval(waitTimer)
  letter.wait = seconds
  waitTimer = setInterval(() => {
    letter.wait = Math.max(0, letter.wait - 1)
    if (!letter.wait) clearInterval(waitTimer)
  }, 1000)
}

/** On a computer the code is typed at once; a phone keeps its keyboard down until the field is touched. */
function focusCode() {
  if (window.matchMedia('(pointer: fine)').matches) nextTick(() => codeField.value?.focus())
}

/** The screen of the flying letter; `sent` false — the previous letter is still fresh and no new one went. */
function openSent(address, { sent = true, wait = 60 } = {}) {
  letter.email = address
  letter.flight += 1
  code.value = ''
  mode.value = 'sent'
  // A reload keeps the screen: the address says what it is (the email itself stays in this tab).
  if (route.query.mode !== 'sent') router.replace({ query: { mode: 'sent', next: route.query.next, from: route.query.from } })
  startWait(wait)
  if (!sent) note.value = 'Письмо уже в пути — новое можно попросить через минуту'
  focusCode()
}

/** Another letter to the same address; its code replaces the previous one. */
async function resend() {
  if (letter.wait > 0 || pending.value) return
  if (mode.value === 'confirm') {
    await resendConfirm()
    return
  }
  message.value = ''
  note.value = ''
  pending.value = true
  try {
    const answer = await startSignIn({ email: letter.email, next: target.value, place })
    if (answer.token) {
      await signedInto(answer, target.value, { first: true })
      return
    }
    if (answer.sent) {
      letter.flight += 1
      code.value = ''
      note.value = 'Свежее письмо уже летит к вам — код в нём новый'
      queue('act', 'confirm:resend')
    } else {
      note.value = 'Письмо уже в пути'
    }
    startWait(answer.wait)
  } catch (error) {
    if (error instanceof ApiError && error.code === 'confirm_wait') startWait(60)
    else if (error instanceof ApiError && error.code === 'consent') {
      // The cabinet was deleted meanwhile: the address is new again.
      email.value = letter.email
      mode.value = 'email'
      askConsent.value = true
    } else message.value = say(error)
  } finally {
    pending.value = false
  }
}

/** A slip in the address: back to the address, as it was typed. */
function otherAddress(value = letter.email) {
  email.value = value
  mode.value = 'email'
  if (route.query.mode === 'sent') router.replace({ query: { next: route.query.next, from: route.query.from } })
  nextTick(() => emailField.value?.focus())
}

/** The six digits typed here: the same as the letter's link, for a letter opened on another device. */
async function submitCode() {
  if (pending.value) return
  message.value = ''
  note.value = ''
  if (digits.value.length !== 6) {
    message.value = 'В коде шесть цифр — он в письме под кнопкой'
    return
  }
  pending.value = true
  try {
    const result = await webApi.code({ email: letter.email, code: digits.value })
    if (result.first) reachGoal('astra.email@confirm')
    await signedInto(result, result.next || target.value, { first: result.first })
  } catch (error) {
    code.value = ''
    if (error instanceof ApiError && error.code === 'code') message.value = 'Код не подошёл — проверьте цифры в последнем письме'
    else if (error instanceof ApiError && error.code === 'code_old') message.value = 'Этот код больше не действует — попросите новое письмо'
    else message.value = say(error)
    focusCode()
  } finally {
    pending.value = false
  }
}

// Six digits typed or pasted («482 915» too): the cabinet opens without a press of the button.
watch(code, (value) => {
  const clean = value.replace(/\D/g, '').slice(0, 6)
  if (clean !== value) code.value = clean
  else if (clean.length === 6 && waiting.value && !letter.editing) submitCode()
})

// The link opened in another tab of this browser: this page follows it into the cabinet.
watch(webToken, async (token) => {
  if (!token || mode.value !== 'sent' || leaving.value || entering) return
  const me = await webApi.me().catch(() => null)
  if (me?.email_confirmed && mode.value === 'sent' && !leaving.value && !entering) {
    forgetSignIn()
    await fly(me, target.value)
  }
})

// ---- An account signed in before the letters: its confirmation ----

/** The letter screen for the account's own address; a fresh letter goes unless one has just gone. */
function openConfirm(user) {
  letter.email = user.email
  letter.flight += 1
  code.value = ''
  mode.value = 'confirm'
  nextTick(() => markUser(user))
  if (route.query.mode !== 'confirm') router.replace({ query: { mode: 'confirm', next: target.value === '/cabinet' ? undefined : target.value } })
  resendConfirm({ quiet: true })
}

async function resendConfirm({ quiet = false } = {}) {
  if (letter.wait > 0 || pending.value) return
  message.value = ''
  note.value = ''
  pending.value = true
  try {
    const answer = await webApi.confirmSend({ next: target.value })
    if (!answer.sent) {
      // Confirmed meanwhile, in another tab or on another device.
      await fly(answer.user, target.value)
      return
    }
    letter.email = answer.user.email
    if (!quiet) {
      letter.flight += 1
      code.value = ''
      note.value = 'Свежее письмо уже летит к вам — код в нём новый'
      queue('act', 'confirm:resend')
    }
    startWait(answer.pause || 60)
  } catch (error) {
    if (error instanceof ApiError && error.code === 'confirm_wait') startWait(60)
    else if (error instanceof ApiError && error.status === 401) mode.value = 'email'
    else if (!quiet) message.value = say(error)
  } finally {
    pending.value = false
  }
}

function editAddress(value = letter.email) {
  letter.value = value
  letter.editing = true
  message.value = ''
  note.value = ''
}

/** The letter to a corrected address: the account is not open yet, so no password is asked. */
async function changeAddress(value = letter.value) {
  const address = value.trim()
  message.value = ''
  note.value = ''
  if (!EMAIL.test(address)) {
    message.value = 'Почта выглядит неполной'
    return
  }
  if (address.toLowerCase() === letter.email.toLowerCase()) {
    letter.editing = false
    return
  }
  pending.value = true
  try {
    const answer = await webApi.confirmSend({ email: address, next: target.value })
    if (!answer.sent) {
      await fly(answer.user, target.value)
      return
    }
    letter.email = answer.user.email
    letter.editing = false
    letter.flight += 1
    code.value = ''
    note.value = 'Письмо летит на новый адрес'
    queue('act', 'confirm:change')
    startWait(answer.pause || 60)
  } catch (error) {
    message.value = error instanceof ApiError && error.code === 'exists'
      ? 'С этой почтой кабинет уже открыт — войдите с ней'
      : say(error)
  } finally {
    pending.value = false
  }
}

/** The page checks by itself whether the link has been opened, and leads on once it is. */
async function checkConfirmed() {
  if (mode.value !== 'confirm' || leaving.value || !readSession('web')) return
  try {
    const me = await webApi.me()
    if (me.email_confirmed && mode.value === 'confirm' && !leaving.value) await fly(me, target.value)
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) mode.value = 'email'
  }
}

let watchTimer = 0
watch(mode, (value) => {
  clearInterval(watchTimer)
  watchTimer = value === 'confirm' ? setInterval(() => {
    if (document.visibilityState === 'visible') checkConfirmed()
  }, WATCH_MS) : 0
}, { immediate: true })

/** Back from the mail in this tab: the confirmation is checked at once. */
function onVisible() {
  if (document.visibilityState === 'visible') checkConfirmed()
}

/** Opened by `?mode=confirm` (the cabinet sent here): the address is the account's own. */
async function resumeConfirm() {
  if (!readSession('web')) {
    mode.value = 'email'
    return
  }
  try {
    const me = await webApi.me()
    if (me.email_confirmed) await fly(me, target.value)
    else openConfirm(me)
  } catch (error) {
    mode.value = 'email'
    if (!(error instanceof ApiError && error.status === 401)) message.value = say(error)
  }
}

// ---- The letter's link ----

async function confirmByLink() {
  message.value = ''
  pending.value = true
  try {
    const result = await webApi.confirm(confirmToken)
    if (result.first) reachGoal('astra.email@confirm')
    await signedInto(result, result.next || '/cabinet', { first: result.first })
  } catch (error) {
    if (!(error instanceof ApiError) || error.status >= 500) {
      // The link is still whole: the button tries it again.
      message.value = say(error)
      return
    }
    router.replace({ name: 'login' })
    const known = readSession('web') ? await webApi.me().catch(() => null) : null
    if (known?.email_confirmed) {
      // Opened twice — the first time has signed this browser in already.
      await fly(known, '/cabinet')
      return
    }
    if (known) {
      openConfirm(known)
      note.value = 'Эта ссылка уже отслужила своё — свежая уже летит к вам'
      return
    }
    mode.value = 'email'
    if (error.code === 'confirm_link') note.value = 'Эта ссылка уже отслужила своё. Укажите почту — пришлём свежую'
    else message.value = say(error)
  } finally {
    pending.value = false
  }
}

// ---- The password: the second way ----

async function signInWithPassword() {
  const address = email.value.trim()
  message.value = ''
  note.value = ''
  if (!EMAIL.test(address)) {
    message.value = 'Почта выглядит неполной'
    return
  }
  if (!password.value) {
    message.value = 'Введите пароль — или войдите по письму'
    return
  }
  pending.value = true
  let noPassword = false
  try {
    const result = await webApi.login({ email: address, password: password.value })
    await signedInto(result, target.value)
  } catch (error) {
    if (error instanceof ApiError && error.code === 'no_password') noPassword = true
    else message.value = say(error)
  } finally {
    pending.value = false
  }
  if (noPassword) {
    // The cabinet has never had a password: the letter goes instead, one press saved.
    mode.value = 'email'
    await sendLetter()
    if (mode.value === 'sent') note.value = 'У этого кабинета нет пароля — письмо для входа уже летит к вам'
  }
}

/** The same answer whether the mail is known or not: the form does not tell whose it is. */
async function sendResetLink() {
  message.value = ''
  note.value = ''
  if (!EMAIL.test(email.value.trim())) {
    message.value = 'Почта выглядит неполной'
    return
  }
  pending.value = true
  try {
    await webApi.forgotPassword(email.value.trim())
    note.value = 'Если у кабинета с этой почтой есть пароль, письмо со ссылкой уже летит к вам. Ссылка открыта час.'
  } catch (error) {
    message.value = say(error)
  } finally {
    pending.value = false
  }
}

async function savePassword() {
  if (password.value.length < 8) {
    message.value = 'Пароль — не короче 8 символов'
    return
  }
  message.value = ''
  pending.value = true
  try {
    const result = await webApi.resetPassword({ token: resetToken, password: password.value })
    await signedInto(result, target.value)
  } catch (error) {
    message.value = say(error)
  } finally {
    pending.value = false
  }
}

function submit() {
  if (mode.value === 'confirming') confirmByLink()
  else if (waiting.value) {
    if (letter.editing) changeAddress()
    else submitCode()
  } else if (forgot.value) sendResetLink()
  else if (resetting.value) savePassword()
  else if (mode.value === 'password') signInWithPassword()
  else sendLetter()
}

const cta = computed(() => {
  if (pending.value) return 'Минуту…'
  if (mode.value === 'confirming') return 'Открыть кабинет'
  if (waiting.value) return letter.editing ? 'Отправить на этот адрес' : 'Войти по коду'
  if (forgot.value) return 'Прислать ссылку'
  if (resetting.value) return 'Сохранить и войти'
  if (mode.value === 'password') return 'Войти'
  return fresh ? 'Получить карту бесплатно' : 'Получить письмо для входа'
})
/** While no digit is typed, the gold button leads to the person's mail, where the letter waits. */
const toMailbox = computed(() => waiting.value && !letter.editing && box.value && !digits.value)

const kicker = computed(() => {
  if (lettered.value) return mode.value === 'confirming' ? '' : 'Последний шаг'
  if (mode.value === 'email' && fresh) return 'Натальная карта · бесплатно'
  return ''
})
const headKey = computed(() => mode.value)

onMounted(() => {
  load()
  document.addEventListener('visibilitychange', onVisible)
  if (confirmToken) confirmByLink()
  else if (mode.value === 'confirm') resumeConfirm()
  else {
    const kept = keptLetter()
    if (kept) email.value = kept.email
    if (mode.value === 'sent') {
      // A letter sent from the home page or a landing, or this screen reloaded.
      if (kept) {
        letter.email = kept.email
        letter.flight += 1
        startWait(kept.wait)
        if (!kept.sent) note.value = 'Письмо уже в пути — новое можно попросить через минуту'
        focusCode()
      } else {
        mode.value = 'email'
      }
    }
  }
})

onUnmounted(() => {
  clearInterval(watchTimer)
  clearInterval(waitTimer)
  document.removeEventListener('visibilitychange', onVisible)
  if (!leaving.value) clearMark()
})
</script>

<template>
  <div class="site">
    <SiteHeader />
    <main class="login">
      <div class="login-side" :class="{ 'is-leaving': leaving }">
        <form class="login-card" novalidate @submit.prevent="submit">
          <span class="card-sheen" aria-hidden="true" />

          <Transition name="swap" mode="out-in">
            <div :key="headKey" class="card-head">
              <p v-if="kicker" class="step-kicker">{{ kicker }}</p>
              <h1>
                <template v-if="mode === 'confirming'">Открываем <em>кабинет</em></template>
                <template v-else-if="lettered">Письмо <em>летит</em> к вам</template>
                <template v-else-if="forgot || resetting">Новый <em>пароль</em></template>
                <template v-else-if="mode === 'password'">Вход <em>с паролем</em></template>
                <template v-else-if="fresh">Ваша карта — <em>в одном письме</em></template>
                <template v-else>Вход в <em>кабинет</em></template>
              </h1>
              <p>
                <template v-if="mode === 'confirming'">Проверяем ссылку — ещё мгновение, и кабинет откроется.</template>
                <template v-else-if="lettered">
                  Ссылка и код ушли на <strong class="address">{{ letter.email || 'вашу почту' }}</strong>.
                  Нажмите кнопку в письме — или введите код здесь.
                </template>
                <template v-else-if="forgot">Назовите почту кабинета — пришлём ссылку, по которой можно задать новый пароль.</template>
                <template v-else-if="resetting">Придумайте новый пароль — и кабинет откроется сразу.</template>
                <template v-else-if="mode === 'password'">Если вы задавали пароль в профиле. Нет пароля — войдите по письму.</template>
                <template v-else-if="fresh && birthWaiting">Укажите почту — пришлём ссылку, и кабинет откроется с готовой натальной картой. Пароль не нужен.</template>
                <template v-else-if="fresh">Укажите почту — пришлём ссылку. В кабинете останется назвать дату рождения, и карта готова. Пароль не нужен.</template>
                <template v-else>Укажите почту — пришлём ссылку и код. Кабинета ещё нет? Он откроется по тому же письму.</template>
              </p>
            </div>
          </Transition>

          <Transition name="swap" mode="out-in">
            <div v-if="lettered" key="letter" class="fields">
              <div class="flight" :class="{ 'is-opening': mode === 'confirming' }">
                <svg :key="letter.flight" class="flight-sky" viewBox="0 0 300 150" aria-hidden="true">
                  <defs>
                    <mask id="flight-reveal" maskUnits="userSpaceOnUse" x="0" y="0" width="300" height="150">
                      <path class="trail-draw" d="M150 92C190 96 236 70 268 22" pathLength="1" />
                    </mask>
                    <clipPath id="flight-pocket">
                      <rect x="2" y="-40" width="116" height="122" rx="10" />
                    </clipPath>
                    <linearGradient id="flight-gold" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0" stop-color="#f4dba6" />
                      <stop offset=".55" stop-color="#e3bd78" />
                      <stop offset="1" stop-color="#cf9f55" />
                    </linearGradient>
                    <linearGradient id="flight-flap" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0" stop-color="#fbe9c4" />
                      <stop offset="1" stop-color="#e6c07c" />
                    </linearGradient>
                    <radialGradient id="flight-glow">
                      <stop offset="0" stop-color="#ffe2a8" stop-opacity="0.75" />
                      <stop offset="1" stop-color="#ffe2a8" stop-opacity="0" />
                    </radialGradient>
                  </defs>
                  <path class="trail" d="M150 92C190 96 236 70 268 22" mask="url(#flight-reveal)" />
                  <g class="trail-stars">
                    <path d="M193 80.5q.6 4.4 5 5-4.4.6-5 5-.6-4.4-5-5 4.4-.6 5-5Z" />
                    <path d="M224 63.5q.5 4.5 4.5 5-4 .5-4.5 4.5-.5-4-4.5-4.5 4-.5 4.5-5Z" />
                    <path d="M249.5 41q.5 4.2 4 4.6-3.5.5-4 4-.5-3.5-4-4 3.5-.4 4-4.6Z" />
                  </g>
                  <g class="arrival">
                    <circle cx="268" cy="22" r="18" fill="url(#flight-glow)" />
                    <path d="M268 10q1.2 10.8 12 12-10.8 1.2-12 12-1.2-10.8-12-12 10.8-1.2 12-12Z" />
                  </g>
                  <ellipse class="env-glow" cx="150" cy="132" rx="62" ry="9" fill="url(#flight-glow)" />
                  <g class="env-fly">
                    <g transform="translate(98 56) scale(.87)">
                      <g class="env-in">
                        <rect class="env-back" x="2" y="2" width="116" height="80" rx="10" />
                        <path class="env-flap-back" d="M2 12A10 10 0 0 1 12 2h96a10 10 0 0 1 10 10L60 56Z" />
                        <g clip-path="url(#flight-pocket)">
                          <g class="env-paper">
                            <rect x="14" y="8" width="92" height="62" rx="5" />
                            <path d="M28 24h64M28 34h64M28 44h40" />
                          </g>
                        </g>
                        <path class="env-front" d="M2 26 60 52 118 26V72a10 10 0 0 1-10 10H12A10 10 0 0 1 2 72Z" />
                        <path class="env-flap" d="M2 12A10 10 0 0 1 12 2h96a10 10 0 0 1 10 10L60 56Z" />
                        <g class="env-seal">
                          <circle cx="60" cy="54" r="10" />
                          <path d="M60 47q.8 6.2 7 7-6.2.8-7 7-.8-6.2-7-7 6.2-.8 7-7Z" />
                        </g>
                        <g class="env-sparks">
                          <circle v-for="n in 8" :key="n" cx="60" cy="54" r="1.6" :style="{ '--a': `${n * 45 - 20}deg` }" />
                        </g>
                      </g>
                    </g>
                  </g>
                </svg>
                <p v-if="waiting" class="flight-status" role="status">
                  <span class="pulse" aria-hidden="true" />
                  Ждём вас — ссылка или код откроют кабинет
                </p>
              </div>

              <template v-if="waiting">
                <label v-if="!letter.editing" class="field">
                  <span class="field-label">Код из письма</span>
                  <input
                    ref="codeField"
                    v-model="code"
                    class="code-input"
                    type="text"
                    inputmode="numeric"
                    autocomplete="one-time-code"
                    maxlength="7"
                    placeholder="······"
                    aria-describedby="code-hint"
                    :disabled="pending"
                  />
                  <span id="code-hint" class="field-hint">Шесть цифр под кнопкой в письме — для письма, открытого на другом устройстве</span>
                </label>
                <p v-if="slip && !letter.editing" class="slip">
                  Может быть, почта —
                  <button
                    type="button"
                    class="forgot-link"
                    :disabled="pending"
                    @click="mode === 'confirm' ? changeAddress(slip) : otherAddress(slip)"
                  >{{ slip }}</button>?
                </p>
                <label v-if="letter.editing" class="field">
                  <span class="field-label">Почта для письма</span>
                  <input v-model="letter.value" type="email" autocomplete="email" inputmode="email" required />
                </label>
              </template>
            </div>

            <div v-else key="form" class="fields">
              <label v-if="!resetting" class="field">
                <span class="field-label">Почта</span>
                <input
                  ref="emailField"
                  v-model="email"
                  type="email"
                  autocomplete="email"
                  inputmode="email"
                  placeholder="name@mail.ru"
                  required
                  @input="begin"
                />
              </label>
              <p v-if="typedSlip && !asksPassword" class="slip is-left">
                Может быть, почта —
                <button type="button" class="forgot-link" @click="email = typedSlip">{{ typedSlip }}</button>?
              </p>
              <div v-if="asksPassword" class="field">
                <span class="field-head">
                  <label class="field-label" for="login-password">{{ resetting ? 'Новый пароль' : 'Пароль' }}</label>
                  <button v-if="mode === 'password'" type="button" class="forgot-link" @click="mode = 'forgot'">Забыли?</button>
                </span>
                <span class="password">
                  <input
                    id="login-password"
                    v-model="password"
                    :type="showPassword ? 'text' : 'password'"
                    :autocomplete="resetting ? 'new-password' : 'current-password'"
                    :placeholder="resetting ? 'Не короче 8 символов' : ''"
                    required
                  />
                  <button
                    type="button"
                    class="eye"
                    :aria-label="showPassword ? 'Скрыть пароль' : 'Показать пароль'"
                    :aria-pressed="showPassword"
                    @click="showPassword = !showPassword"
                  >
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path d="M2 12s3.6-6.5 10-6.5S22 12 22 12s-3.6 6.5-10 6.5S2 12 2 12Z" />
                      <circle cx="12" cy="12" r="3" />
                      <path v-if="showPassword" d="M4 20 20 4" />
                    </svg>
                  </button>
                </span>
              </div>
              <template v-if="mode === 'email' && askConsent">
                <label class="check consent">
                  <input v-model="consent" type="checkbox" />
                  <span class="check-box" aria-hidden="true" />
                  <span>
                    Даю согласие на обработку
                    <a href="/legal/consent" target="_blank" rel="noopener">персональных данных</a>
                  </span>
                </label>
                <p class="terms">
                  Открывая кабинет, вы принимаете условия
                  <a href="/legal/offer" target="_blank" rel="noopener">оферты</a> и
                  <a href="/legal/privacy" target="_blank" rel="noopener">политики конфиденциальности</a>.
                </p>
              </template>
            </div>
          </Transition>

          <Transition name="swap">
            <p v-if="message" class="error" role="alert">{{ message }}</p>
            <p v-else-if="note" class="note" role="status">✦ {{ note }}</p>
          </Transition>

          <a
            v-if="toMailbox"
            class="gold-cta"
            :href="box.url"
            target="_blank"
            rel="noopener"
            @click="queue('act', 'confirm:mailbox')"
          >
            <span>Открыть {{ box.label }}</span>
            <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M6 3h7v7M13 3 4 12" /></svg>
          </a>
          <button v-else class="gold-cta" type="submit" :disabled="pending">
            <span>{{ cta }}</span>
            <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2 8h11M9 4l4 4-4 4" /></svg>
          </button>

          <div v-if="mode === 'email'" class="step-actions is-center">
            <button type="button" class="quiet" :disabled="pending" @click="mode = 'password'">
              <svg viewBox="0 0 16 16" aria-hidden="true"><rect x="3" y="7" width="10" height="7" rx="2" /><path d="M5.5 7V5a2.5 2.5 0 0 1 5 0v2" /></svg>
              Войти с паролем
            </button>
          </div>
          <div v-else-if="mode === 'password'" class="step-actions is-center">
            <button type="button" class="quiet" :disabled="pending" @click="mode = 'email'">
              <svg viewBox="0 0 16 16" aria-hidden="true"><rect x="2" y="3.5" width="12" height="9" rx="2" /><path d="m2.5 4.5 5.5 4.5 5.5-4.5" /></svg>
              Войти по письму, без пароля
            </button>
          </div>
          <template v-else-if="waiting">
            <div v-if="letter.editing" class="step-actions">
              <button type="button" class="quiet" :disabled="pending" @click="letter.editing = false">
                <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M14 8H3M7 4 3 8l4 4" /></svg>
                Отмена
              </button>
            </div>
            <template v-else>
              <div class="step-actions">
                <button type="button" class="quiet" :disabled="pending || letter.wait > 0" @click="resend()">
                  <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M13.5 8A5.5 5.5 0 1 1 11.9 4M12.5 1.5v3h-3" /></svg>
                  <template v-if="letter.wait > 0">Ещё раз — через {{ waitText }}</template>
                  <template v-else>Отправить ещё раз</template>
                </button>
                <button
                  type="button"
                  class="quiet"
                  :disabled="pending"
                  @click="mode === 'confirm' ? editAddress() : otherAddress()"
                >Другая почта</button>
              </div>
              <p class="mail-tip">Письма нет во «Входящих»? Загляните в «Спам» или «Промоакции» — иногда оно прячется там.</p>
            </template>
          </template>
          <div v-if="forgot || resetting" class="step-actions">
            <button type="button" class="quiet" :disabled="pending" @click="mode = 'password'">
              <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M14 8H3M7 4 3 8l4 4" /></svg>
              Ко входу
            </button>
          </div>
        </form>

        <p class="sky-now">
          <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg>
          {{ today }}
        </p>
      </div>
    </main>
  </div>
</template>

<style scoped>
.login {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  min-height: 100vh;
  min-height: 100svh;
  padding: 110px clamp(20px, 8vw, 150px) 48px;
  pointer-events: none;
}
.login-side {
  display: grid;
  gap: 16px;
  width: min(392px, 100%);
  pointer-events: auto;
  transition: opacity 0.32s ease, filter 0.32s ease, transform 0.32s ease;
}
.login-side.is-leaving { opacity: 0; filter: blur(6px); transform: translateY(-8px) scale(0.98); pointer-events: none; }

/* The same glass as the home page form, a little deeper: here it is the whole page. */
.login-card {
  position: relative;
  display: grid;
  gap: 14px;
  overflow: hidden;
  padding: 22px 24px 22px;
  border-radius: 22px;
  border: 1px solid rgba(240, 210, 150, 0.22);
  background:
    radial-gradient(120% 70% at 0% 0%, rgba(255, 196, 120, 0.1), transparent 60%),
    linear-gradient(160deg, rgba(26, 23, 26, 0.62), rgba(8, 10, 18, 0.74));
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 240, 210, 0.08);
  backdrop-filter: blur(14px) saturate(1.2);
  -webkit-backdrop-filter: blur(14px) saturate(1.2);
  color: #efe7d8;
  animation: card-in 0.9s cubic-bezier(0.3, 0.7, 0.2, 1) 0.25s both;
}
.login-card::before {
  content: '';
  position: absolute;
  inset: 6px;
  border: 1px solid rgba(240, 210, 150, 0.08);
  border-radius: 17px;
  pointer-events: none;
}
.card-sheen {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: linear-gradient(115deg, transparent 35%, rgba(255, 236, 200, 0.08) 50%, transparent 65%);
  transform: translateX(-100%);
  animation: card-sheen 1.8s ease 0.9s forwards;
}


.card-head { display: grid; gap: 6px; margin: 4px 0 2px; }
.step-kicker { margin: 0; font-size: 11px; letter-spacing: 0.26em; text-transform: uppercase; color: rgba(233, 194, 124, 0.75); }
.card-head h1 {
  margin: 0;
  font-family: var(--serif);
  font-weight: 500;
  font-size: 34px;
  line-height: 1.08;
  color: #f6efe2;
}
.card-head em { font-style: italic; color: #f0cd8a; }
.card-head p:not(.step-kicker) { margin: 0; font-size: 15px; line-height: 1.55; color: rgba(236, 230, 220, 0.8); }

.fields { display: grid; gap: 14px; }


.field { display: grid; gap: 7px; min-width: 0; }
.field-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
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
.field input::placeholder { color: rgba(226, 220, 210, 0.38); }
.field input:hover:not(:disabled) { border-color: rgba(240, 210, 150, 0.32); }
.field input:focus {
  border-color: rgba(240, 205, 138, 0.7);
  background: rgba(255, 240, 210, 0.06);
  box-shadow: 0 0 0 3px rgba(240, 205, 138, 0.12);
}
.field input:disabled { opacity: 0.4; cursor: not-allowed; }
.field input::-webkit-calendar-picker-indicator { opacity: 0.6; cursor: pointer; }
/* Browsers paint autofilled fields light; keep them on the night. */
.field input:-webkit-autofill {
  -webkit-text-fill-color: #f6efe2;
  box-shadow: 0 0 0 40px #15141a inset;
  caret-color: #f6efe2;
}

.check {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  line-height: 16px;
  color: rgba(226, 220, 210, 0.7);
  cursor: pointer;
}
.check input { position: absolute; opacity: 0; pointer-events: none; }
.check-box {
  position: relative;
  flex: none;
  width: 13px;
  height: 13px;
  border-radius: 4px;
  border: 1px solid rgba(240, 210, 150, 0.4);
  transition: background 0.2s ease, border-color 0.2s ease;
}
.check-box::after {
  content: '';
  position: absolute;
  left: 4px;
  top: 1.5px;
  width: 3px;
  height: 6px;
  border: solid #2b1d0b;
  border-width: 0 1.5px 1.5px 0;
  transform: rotate(45deg) scale(0);
  transition: transform 0.2s ease;
}
.check input:checked + .check-box { background: #e9c47e; border-color: #e9c47e; }
.check input:checked + .check-box::after { transform: rotate(45deg) scale(1); }
.check input:focus-visible + .check-box { box-shadow: 0 0 0 3px rgba(240, 205, 138, 0.25); }
.consent { align-items: flex-start; font-size: 13px; line-height: 18px; }
.consent .check-box { margin-top: 2px; }
.consent a { color: #f0cd8a; text-decoration: underline; text-decoration-color: rgba(240, 205, 138, 0.4); text-underline-offset: 3px; }
.consent a:hover { text-decoration-color: currentColor; }
.terms { margin: 0; font-size: 12.5px; line-height: 18px; color: rgba(226, 220, 210, 0.6); }
.terms a { color: rgba(240, 205, 138, 0.9); text-decoration: underline; text-decoration-color: rgba(240, 205, 138, 0.35); text-underline-offset: 3px; }

.password { position: relative; display: block; }
.password input { padding-right: 46px; }
.eye {
  position: absolute;
  top: 50%;
  right: 6px;
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: none;
  color: rgba(226, 214, 192, 0.55);
  cursor: pointer;
  transform: translateY(-50%);
  transition: color 0.25s ease;
}
.eye:hover, .eye[aria-pressed='true'] { color: #f0cd8a; }
.eye:focus-visible { outline: 1px solid #f0cd8a; }
.eye svg { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 1.4; stroke-linecap: round; stroke-linejoin: round; }

.error {
  margin: 0;
  padding: 9px 12px;
  border-radius: 10px;
  border: 1px solid rgba(230, 140, 110, 0.3);
  background: rgba(200, 90, 60, 0.08);
  font-size: 13.5px;
  line-height: 1.4;
  color: #f2c3ae;
}

.note {
  margin: 0;
  padding: 9px 12px;
  border-radius: 10px;
  border: 1px solid rgba(240, 205, 138, 0.26);
  background: rgba(240, 205, 138, 0.06);
  font-size: 13.5px;
  line-height: 1.45;
  color: #f3dcae;
}
.forgot-link {
  padding: 0;
  border: 0;
  background: none;
  font: inherit;
  font-size: 12px;
  color: rgba(240, 205, 138, 0.8);
  cursor: pointer;
  text-decoration: underline;
  text-decoration-color: rgba(240, 205, 138, 0.3);
  text-underline-offset: 3px;
  transition: color 0.25s ease;
}
.forgot-link:hover { color: #f0cd8a; text-decoration-color: currentColor; }
.forgot-link:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 2px; border-radius: 4px; }

.gold-cta {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  width: 100%;
  margin-top: 4px;
  padding: 13px 24px;
  border: 0;
  border-radius: 999px;
  font: inherit;
  font-weight: 600;
  color: #2b1d0b;
  background: linear-gradient(180deg, #f4dba6 0%, #e3bd78 55%, #cf9f55 100%);
  box-shadow: inset 0 1px 0 rgba(255, 248, 228, 0.8), 0 8px 30px rgba(230, 170, 80, 0.32);
  cursor: pointer;
  transition: box-shadow 0.3s ease, filter 0.3s ease, opacity 0.3s ease;
}
.gold-cta svg { width: 15px; height: 15px; fill: none; stroke: currentColor; stroke-width: 1.6; stroke-linecap: round; stroke-linejoin: round; transition: transform 0.25s ease; }
.gold-cta:hover:not(:disabled) { filter: brightness(1.05); box-shadow: inset 0 1px 0 rgba(255, 248, 228, 0.8), 0 10px 38px rgba(230, 170, 80, 0.48); }
.gold-cta:hover:not(:disabled) svg { transform: translateX(4px); }
.gold-cta:focus-visible { outline: 2px solid #ffe2a8; outline-offset: 3px; }
.gold-cta:disabled { opacity: 0.6; cursor: progress; }

.step-actions { display: flex; justify-content: space-between; gap: 12px; margin-top: -4px; }
.quiet {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 6px 4px;
  border: 0;
  background: none;
  font: inherit;
  font-size: 13.5px;
  color: rgba(226, 220, 210, 0.72);
  cursor: pointer;
  transition: color 0.25s ease;
}
.quiet:hover:not(:disabled) { color: #f0cd8a; }
.quiet:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 2px; border-radius: 6px; }
.quiet:disabled { opacity: 0.5; cursor: progress; }
.quiet svg { width: 13px; height: 13px; fill: none; stroke: currentColor; stroke-width: 1.5; stroke-linecap: round; stroke-linejoin: round; }

/* The letter's six digits: wide, in two breaths, like on the letter itself. */
.field input.code-input {
  height: 58px;
  padding: 0 0 0 0.5em;
  font-size: 28px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.5em;
  text-align: center;
  color: #f4dba6;
}
.field input.code-input::placeholder { color: rgba(240, 210, 150, 0.28); letter-spacing: 0.5em; }
.field-hint { font-size: 12px; line-height: 1.45; color: rgba(226, 220, 210, 0.55); }

.step-actions.is-center { justify-content: center; }
.slip.is-left { margin-top: -6px; text-align: left; }

.sky-now {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  margin: 0;
  font-family: var(--serif);
  font-style: italic;
  font-size: 16px;
  color: rgba(242, 235, 223, 0.78);
  text-shadow: 0 1px 12px rgba(0, 0, 0, 0.7);
  animation: card-in 0.9s ease 0.6s both;
}
.sky-now svg { width: 9px; height: 9px; fill: #f0cd8a; filter: drop-shadow(0 0 5px rgba(255, 200, 110, 0.8)); }

a.gold-cta { box-sizing: border-box; text-decoration: none; }

/* ---- The letter: slides into the envelope, the flap closes, the seal lands, it flies off to a star. ---- */
.card-head .address { font-weight: 600; color: #f6efe2; overflow-wrap: anywhere; }
.flight { position: relative; margin: -4px 0 -2px; }
.flight-sky { display: block; width: 100%; max-width: 290px; height: auto; margin: 0 auto; overflow: visible; }

.env-in { transform-box: fill-box; transform-origin: 50% 100%; animation: env-in 0.5s cubic-bezier(0.3, 0.7, 0.2, 1) 0.1s both; }
.env-back { fill: #9a6d33; }
.env-flap-back { fill: #b4843f; transform-box: fill-box; transform-origin: 50% 0; transform: scaleY(0); animation: flap-fold 0.17s ease-in 0.86s both; }
.env-paper { transform: translateY(26px); animation: paper-in 0.62s cubic-bezier(0.5, 0, 0.3, 1) 0.28s both; }
.env-paper rect { fill: #fff8ea; }
.env-paper path { fill: none; stroke: rgba(150, 110, 50, 0.42); stroke-width: 3.4; stroke-linecap: round; }
.env-front, .env-flap { stroke: rgba(110, 72, 25, 0.35); stroke-width: 1.2; stroke-linejoin: round; }
.env-front { fill: url(#flight-gold); }
.env-flap { fill: url(#flight-flap); transform-box: fill-box; transform-origin: 50% 0; animation: flap-close 0.2s ease-out 1.03s both; }
.env-seal { transform-box: fill-box; transform-origin: center; animation: seal-in 0.42s cubic-bezier(0.3, 1.6, 0.5, 1) 1.22s both; }
.env-seal circle { fill: #1c1610; stroke: #f0cd8a; stroke-width: 1.4; }
.env-seal path { fill: #f0cd8a; }
.env-sparks circle { fill: #ffe2a8; opacity: 0; transform-box: fill-box; transform-origin: center; animation: spark 0.65s ease-out 1.3s both; }
.env-glow { transform-box: fill-box; transform-origin: center; animation: glow-out 0.9s ease 1.8s both; }
.env-fly { transform-box: view-box; transform-origin: 150px 92px; animation: env-fly 1.15s cubic-bezier(0.45, 0, 0.35, 1) 1.75s both; }

.trail { fill: none; stroke: rgba(240, 205, 138, 0.75); stroke-width: 1.6; stroke-linecap: round; stroke-dasharray: 0.1 6; opacity: 0.6; }
.trail-draw { fill: none; stroke: #fff; stroke-width: 16; stroke-dasharray: 1; stroke-dashoffset: 0; animation: trail-draw 1.05s cubic-bezier(0.45, 0, 0.35, 1) 1.85s both; }
.trail-stars path { fill: #f6dfae; opacity: 0.55; transform-box: fill-box; transform-origin: center; animation: star-pop 0.55s ease-out both, twinkle 2.8s ease-in-out infinite; }
.trail-stars path:nth-child(1) { animation-delay: 2.1s, 2.7s; }
.trail-stars path:nth-child(2) { animation-delay: 2.35s, 3.3s; }
.trail-stars path:nth-child(3) { animation-delay: 2.6s, 3.9s; }
.arrival { transform-box: fill-box; transform-origin: center; animation: arrive 0.7s cubic-bezier(0.3, 1.6, 0.5, 1) 2.8s both, glimmer 2.6s ease-in-out 3.6s infinite; }
.arrival path { fill: #ffe9bd; }

.flight-status {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  margin: 0;
  font-size: 12.5px;
  line-height: 1.4;
  text-align: center;
  color: rgba(243, 220, 174, 0.85);
  animation: card-in 0.7s ease 2.95s both;
}
.pulse { position: relative; flex: none; width: 7px; height: 7px; border-radius: 50%; background: #f0cd8a; box-shadow: 0 0 8px rgba(255, 200, 110, 0.8); }
.pulse::after { content: ''; position: absolute; inset: -5px; border-radius: 50%; border: 1px solid rgba(240, 205, 138, 0.6); animation: pulse 2s ease-out infinite; }

/* The letter's link is being opened: the sealed envelope waits, its seal breathing. */
.flight.is-opening .env-in,
.flight.is-opening .env-paper,
.flight.is-opening .env-flap-back,
.flight.is-opening .env-flap,
.flight.is-opening .env-sparks circle,
.flight.is-opening .env-glow,
.flight.is-opening .env-fly { animation: none; }
.flight.is-opening .env-seal { animation: seal-breathe 1.4s ease-in-out infinite; }
.flight.is-opening .trail,
.flight.is-opening .trail-stars,
.flight.is-opening .arrival { display: none; }

.slip { margin: 0; font-size: 13.5px; line-height: 1.5; text-align: center; color: rgba(226, 220, 210, 0.75); }
.slip .forgot-link { font-size: inherit; overflow-wrap: anywhere; }
.mail-tip { margin: -6px 0 0; font-size: 12.5px; line-height: 1.5; text-align: center; color: rgba(226, 220, 210, 0.55); }

@keyframes env-in { from { opacity: 0; transform: translateY(12px) scale(0.9); } }
@keyframes paper-in { from { transform: translateY(-28px); } }
@keyframes flap-fold { from { transform: scaleY(-0.6); } }
@keyframes flap-close { from { transform: scaleY(0); } }
@keyframes seal-in { from { opacity: 0; transform: scale(0); } }
@keyframes seal-breathe { 50% { transform: scale(1.14); } }
@keyframes spark {
  0% { opacity: 0; transform: rotate(var(--a)) translateX(0); }
  25% { opacity: 1; }
  100% { opacity: 0; transform: rotate(var(--a)) translateX(24px) scale(0.4); }
}
@keyframes glow-out { to { opacity: 0; transform: scale(0.4); } }
@keyframes env-fly {
  0% { transform: translate(0, 0) rotate(0deg) scale(1); }
  12% { transform: translate(-6px, 5px) rotate(5deg) scale(1); }
  40% { transform: translate(43px, -6px) rotate(-6deg) scale(0.82); }
  62% { transform: translate(74px, -23px) rotate(-14deg) scale(0.6); opacity: 1; }
  82% { transform: translate(99px, -46px) rotate(-20deg) scale(0.38); opacity: 0.9; }
  100% { transform: translate(118px, -70px) rotate(-26deg) scale(0.12); opacity: 0; }
}
@keyframes trail-draw { from { stroke-dashoffset: 1; } }
@keyframes star-pop {
  0% { opacity: 0; transform: scale(0) rotate(-45deg); }
  60% { opacity: 1; transform: scale(1.3); }
  100% { opacity: 0.55; transform: scale(1); }
}
@keyframes twinkle { 0%, 100% { opacity: 0.55; transform: scale(1); } 50% { opacity: 0.95; transform: scale(1.18); } }
@keyframes arrive { from { opacity: 0; transform: scale(0) rotate(-90deg); } }
@keyframes glimmer { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.75; transform: scale(0.88); } }
@keyframes pulse { from { opacity: 1; transform: scale(0.6); } to { opacity: 0; transform: scale(1.6); } }

.swap-enter-active, .swap-leave-active { transition: opacity 0.25s ease, transform 0.25s ease; }
.swap-enter-from { opacity: 0; transform: translateY(6px); }
.swap-leave-to { opacity: 0; transform: translateY(-6px); }

@keyframes card-in { from { opacity: 0; transform: translateY(16px); filter: blur(4px); } }
@keyframes card-sheen { to { transform: translateX(100%); } }

/* Phones: the sky keeps the top of the screen, the card rises from below as a sheet. */
@media (max-width: 760px) {
  .login { align-items: flex-end; justify-content: center; padding: 34vh 12px 16px; }
  .login-card { padding: 18px 18px 20px; }
  .card-head h1 { font-size: 28px; }
  /* 16px keeps iOS from zooming into a field on focus; the rest are thumb-sized targets. */
  .field input { font-size: 16px; }
  .eye { width: 40px; height: 40px; right: 3px; }
  .quiet { min-height: 40px; }
  .check { padding-block: 8px; margin-block: -8px; }
}

@media (prefers-reduced-motion: reduce) {
  .login-card, .card-sheen, .sky-now { animation: none; }
  .login-side.is-leaving { filter: none; transform: none; }
  /* The letter is already on its way: the trail and the star, without the flight. */
  .flight *, .flight-status, .pulse::after { animation: none !important; }
  .flight:not(.is-opening) .env-fly,
  .flight:not(.is-opening) .env-glow { display: none; }
}
</style>
