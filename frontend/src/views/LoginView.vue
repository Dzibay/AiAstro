<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SiteHeader from '../components/SiteHeader.vue'
import { webApi } from '../api/web.js'
import { ApiError, errorText } from '../api/http.js'
import { writeSession } from '../composables/useSession.js'
import { useSiteConfig } from '../composables/useSiteConfig.js'
import { useSky } from '../composables/useSky.js'
import { useHead } from '../utils/useHead.js'
import { birthSigns, skyOn } from '../utils/skyToday.js'

/**
 * Login lies on the same sky as the home page, in its own pose (router meta.sky: 'login').
 * Registration takes two steps: who you are, then your sky. The sky answers both: a star for
 * the name, the engraving of the Sun sign for the birth date (see NameMark.vue).
 */

/** The home page form leaves the birth data here for the second step. */
const BIRTH_KEY = 'astra-birth'
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

const route = useRoute()
const router = useRouter()
const { config, load } = useSiteConfig()
const { mark, markUser, clearMark } = useSky()

const mode = ref(route.query.mode === 'register' ? 'register' : 'login')
const step = ref(1)
const email = ref('')
const password = ref('')
const name = ref('')
const birth = reactive({ date: '', time: '', noTime: false, city: '' })
const consent = ref(false)
const showPassword = ref(false)
const message = ref('')
const pending = ref(false)
/** Set once the sky is entered: the card dissolves and the star stays for the cabinet. */
const leaving = ref(false)

const registering = computed(() => mode.value === 'register')
const onSky = computed(() => registering.value && step.value === 2)

const sky = skyOn(new Date())
const today = `Сегодня Луна ${sky.moon.in}, ${sky.phase}`

function isoDay(date) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}
const latest = isoDay(new Date())

const dateKnown = computed(() => /^\d{4}-\d{2}-\d{2}$/.test(birth.date) && birth.date >= '1900-01-01' && birth.date <= latest)
const timeKnown = computed(() => !birth.noTime && /^\d{2}:\d{2}$/.test(birth.time))

/**
 * Signs by the real longitudes, so a birthday on the cusp gets an honest answer. Without the
 * time the Sun is taken at noon; the Moon moves a sign in two days, so it waits for the time.
 */
const signs = computed(() => (dateKnown.value ? birthSigns(birth.date, timeKnown.value ? birth.time : '') : null))

watch([registering, name], ([on, value]) => { mark.name = on ? value : '' }, { immediate: true })
watch([registering, signs], ([on, value]) => {
  mark.sun = on && value ? value.sun : ''
  mark.moon = on && value ? value.moon : ''
}, { immediate: true })

/** The star settles on its own point of the sky and flashes once the name is typed. */
function settleStar() {
  const value = name.value.trim()
  if (!registering.value || !value || value === mark.place) return
  mark.place = value
  mark.flash += 1
}

watch(mode, (value) => {
  message.value = ''
  step.value = 1
  useHead({ title: value === 'register' ? 'Регистрация' : 'Вход', noindex: true })
}, { immediate: true })
watch(step, () => { message.value = '' })
// The header leads here as well, to the login side.
watch(() => route.query.mode, (value) => { mode.value = value === 'register' ? 'register' : 'login' })

/** The API's codes in the voice of the page; the rest falls back to the common texts. */
function say(error) {
  if (error instanceof ApiError && error.status < 500) {
    if (error.code === 'unauthorized') return 'Не узнаём эту почту с этим паролем'
    if (error.code === 'blocked') {
      const mail = config.value?.support_email
      return mail ? `Кабинет закрыт. Напишите нам: ${mail}` : 'Кабинет закрыт. Напишите в поддержку'
    }
    if (error.code === 'exists') return 'Эта почта уже открывала кабинет — войдите'
  }
  return errorText(error)
}

/** Step one is checked here, so a typo does not surface only after the second step. */
function checkWho() {
  if (!name.value.trim()) return 'Скажите, как к вам обращаться'
  if (!EMAIL.test(email.value.trim())) return 'Почта выглядит неполной'
  if (password.value.length < 8) return 'Пароль — не короче 8 символов'
  return ''
}

function toSky() {
  message.value = checkWho()
  if (message.value) return
  settleStar()
  step.value = 2
}

async function enter(request) {
  message.value = ''
  pending.value = true
  try {
    const result = await request()
    writeSession('web', result.token)
    try {
      sessionStorage.removeItem(BIRTH_KEY)
    } catch {
      /* private mode */
    }
    const next = typeof route.query.next === 'string' ? route.query.next : '/cabinet'
    const target = next.startsWith('/') && !next.startsWith('//') && !next.startsWith('/login')
      ? next
      : '/cabinet'
    // The card dissolves first, then the sky flies on to the cabinet with the person's star.
    leaving.value = true
    markUser(result.user)
    mark.flash += 1
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    await new Promise((resolve) => setTimeout(resolve, reduce ? 0 : 320))
    router.push(target)
  } catch (error) {
    if (error instanceof ApiError && error.code === 'exists') step.value = 1
    message.value = say(error)
  } finally {
    pending.value = false
  }
}

/** Registers with the birth data, or without it when the person fills it in later. */
function finish(withBirth) {
  if (!consent.value) {
    message.value = 'Отметьте согласие на обработку данных'
    return
  }
  if (withBirth && !dateKnown.value) {
    message.value = 'Укажите дату рождения — или заполните позже'
    return
  }
  const body = { email: email.value.trim(), password: password.value, name: name.value.trim(), consent: true }
  if (withBirth) {
    body.birth = { date: birth.date, time: timeKnown.value ? birth.time : null, place: birth.city.trim() || null }
  }
  enter(() => webApi.register(body))
}

function submit() {
  if (!registering.value) enter(() => webApi.login({ email: email.value.trim(), password: password.value }))
  else if (step.value === 1) toSky()
  else finish(true)
}

const cta = computed(() => {
  if (pending.value) return 'Минуту…'
  if (!registering.value) return 'Войти'
  return step.value === 1 ? 'Дальше' : 'Открыть моё небо'
})

onMounted(() => {
  load()
  try {
    const saved = JSON.parse(sessionStorage.getItem(BIRTH_KEY) || 'null')
    if (saved && typeof saved === 'object') {
      for (const key of ['date', 'time', 'city']) if (typeof saved[key] === 'string') birth[key] = saved[key]
      birth.noTime = saved.noTime === true
    }
  } catch {
    /* private mode or a broken value */
  }
})

onUnmounted(() => {
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

          <div class="mode-toggle" role="group" aria-label="Вход или регистрация">
            <span class="mode-thumb" :class="{ 'is-right': registering }" aria-hidden="true" />
            <button type="button" :aria-pressed="!registering" @click="mode = 'login'">Вход</button>
            <button type="button" :aria-pressed="registering" @click="mode = 'register'">Регистрация</button>
          </div>

          <Transition name="swap" mode="out-in">
            <div :key="registering ? `step-${step}` : 'login'" class="card-head">
              <p v-if="registering" class="step-kicker">Шаг {{ step }} из 2</p>
              <h1>
                <template v-if="!registering">С <em>возвращением</em></template>
                <template v-else-if="step === 1">Откройте <em>своё</em> небо</template>
                <template v-else>Ваше <em>небо</em></template>
              </h1>
              <p>
                <template v-if="!registering">Ваше небо на месте. Войдите, чтобы продолжить.</template>
                <template v-else-if="step === 1">Назовите себя — и на небе зажжётся ваша звезда.</template>
                <template v-else>Дата покажет знак Солнца, время — Луну. Натальная карта бесплатна навсегда.</template>
              </p>
            </div>
          </Transition>

          <Transition name="swap" mode="out-in">
            <div v-if="!onSky" key="who" class="fields">
              <div class="reveal" :class="{ 'is-open': registering }" :inert="!registering">
                <label class="field">
                  <span class="field-label">Как вас зовут</span>
                  <input
                    v-model="name"
                    type="text"
                    autocomplete="given-name"
                    placeholder="Имя"
                    maxlength="40"
                    :tabindex="registering ? 0 : -1"
                    @blur="settleStar"
                  />
                </label>
              </div>
              <label class="field">
                <span class="field-label">Почта</span>
                <input v-model="email" type="email" autocomplete="email" inputmode="email" required />
              </label>
              <div class="field">
                <label class="field-label" for="login-password">Пароль</label>
                <span class="password">
                  <input
                    id="login-password"
                    v-model="password"
                    :type="showPassword ? 'text' : 'password'"
                    :autocomplete="registering ? 'new-password' : 'current-password'"
                    :placeholder="registering ? 'Не короче 8 символов' : ''"
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
            </div>

            <div v-else key="sky" class="fields">
              <div class="form-row">
                <label class="field">
                  <span class="field-label">Дата рождения</span>
                  <input v-model="birth.date" type="date" min="1900-01-01" :max="latest" />
                </label>
                <div class="field">
                  <span class="field-head">
                    <label class="field-label" for="login-time">Время</label>
                    <label class="check">
                      <input v-model="birth.noTime" type="checkbox" />
                      <span class="check-box" aria-hidden="true" />
                      <span>не знаю</span>
                    </label>
                  </span>
                  <input id="login-time" v-model="birth.time" type="time" :disabled="birth.noTime" />
                </div>
              </div>
              <label class="field">
                <span class="field-label">Город рождения</span>
                <input v-model="birth.city" type="text" placeholder="Например, Казань" autocomplete="off" />
              </label>
              <label class="check consent">
                <input v-model="consent" type="checkbox" />
                <span class="check-box" aria-hidden="true" />
                <span>
                  Даю согласие на обработку
                  <a href="/legal/consent" target="_blank" rel="noopener">персональных данных</a>
                </span>
              </label>
            </div>
          </Transition>

          <Transition name="swap">
            <p v-if="message" class="error" role="alert">{{ message }}</p>
          </Transition>

          <button class="gold-cta" type="submit" :disabled="pending">
            <span>{{ cta }}</span>
            <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2 8h11M9 4l4 4-4 4" /></svg>
          </button>
          <div v-if="onSky" class="step-actions">
            <button type="button" class="quiet" :disabled="pending" @click="step = 1">
              <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M14 8H3M7 4 3 8l4 4" /></svg>
              Назад
            </button>
            <button type="button" class="quiet" :disabled="pending" @click="finish(false)">Заполню позже</button>
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

.mode-toggle {
  position: relative;
  display: grid;
  grid-template-columns: 1fr 1fr;
  padding: 3px;
  border-radius: 999px;
  border: 1px solid rgba(240, 210, 150, 0.22);
  background: rgba(255, 240, 210, 0.03);
}
.mode-toggle button {
  position: relative;
  padding: 7px 14px;
  border: 0;
  background: none;
  font: inherit;
  font-size: 13px;
  letter-spacing: 0.04em;
  color: rgba(226, 220, 210, 0.7);
  cursor: pointer;
  transition: color 0.3s ease;
}
.mode-toggle button[aria-pressed='true'] { color: #2b1d0b; }
.mode-toggle button:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 2px; border-radius: 999px; }
.mode-thumb {
  position: absolute;
  top: 3px;
  bottom: 3px;
  left: 3px;
  width: calc(50% - 3px);
  border-radius: 999px;
  background: linear-gradient(180deg, #f4dba6, #dcb36c);
  transition: transform 0.45s cubic-bezier(0.3, 0.7, 0.2, 1);
}
.mode-thumb.is-right { transform: translateX(100%); }

.card-head { display: grid; gap: 6px; margin: 4px 0 2px; }
.step-kicker { margin: 0; font-size: 10px; letter-spacing: 0.26em; text-transform: uppercase; color: rgba(233, 194, 124, 0.75); }
.card-head h1 {
  margin: 0;
  font-family: var(--serif);
  font-weight: 500;
  font-size: 32px;
  line-height: 1.05;
  color: #f6efe2;
}
.card-head em { font-style: italic; color: #f0cd8a; }
.card-head p:not(.step-kicker) { margin: 0; font-size: 14px; line-height: 1.5; color: rgba(226, 220, 210, 0.7); }

.fields { display: grid; gap: 14px; }

/* The name field opens as a row, so the card grows instead of jumping. */
.reveal {
  display: grid;
  grid-template-rows: 0fr;
  margin-bottom: -14px;
  opacity: 0;
  transition: grid-template-rows 0.45s cubic-bezier(0.3, 0.7, 0.2, 1), margin 0.45s cubic-bezier(0.3, 0.7, 0.2, 1), opacity 0.3s ease;
}
.reveal > * { min-height: 0; overflow: hidden; }
.reveal.is-open { grid-template-rows: 1fr; margin-bottom: 0; opacity: 1; }

.form-row { display: grid; grid-template-columns: 1.3fr 1fr; gap: 12px; }
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
  .form-row { gap: 10px; }
}

@media (prefers-reduced-motion: reduce) {
  .login-card, .card-sheen, .sky-now { animation: none; }
  .reveal, .mode-thumb { transition: none; }
  .login-side.is-leaving { filter: none; transform: none; }
}
</style>
