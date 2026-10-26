<script setup>
import { computed, onUnmounted, ref } from 'vue'
import { webApi } from '../../api/web.js'
import { errorText } from '../../api/http.js'

/**
 * «Это вы?» for the profile's guarded steps (a new email, a new password, the deletion): the
 * password, or six digits from a letter to the account's own address. An account that came in by
 * the letter has no password, so it gets the code at once; one with a password may switch to the
 * code when the password is forgotten. The parent sends whichever is filled.
 */

const props = defineProps({
  hasPassword: { type: Boolean, default: false },
  /** The field's caption for the password. */
  label: { type: String, default: 'Пароль — для подтверждения' },
})
const password = defineModel('password', { type: String, default: '' })
const code = defineModel('code', { type: String, default: '' })

const byCode = ref(!props.hasPassword)
const sending = ref(false)
const sent = ref(false)
const wait = ref(0)
const error = ref('')
let timer = 0

function countdown(seconds) {
  clearInterval(timer)
  wait.value = seconds
  timer = setInterval(() => {
    wait.value -= 1
    if (wait.value <= 0) clearInterval(timer)
  }, 1000)
}
onUnmounted(() => clearInterval(timer))

async function ask() {
  if (sending.value || wait.value > 0) return
  sending.value = true
  error.value = ''
  try {
    const answer = await webApi.sendCode()
    sent.value = true
    countdown(answer.pause || 60)
  } catch (failure) {
    error.value = errorText(failure)
  } finally {
    sending.value = false
  }
}

function switchWay() {
  byCode.value = !byCode.value
  password.value = ''
  code.value = ''
  error.value = ''
}

const askLabel = computed(() => {
  if (sending.value) return 'Отправляем…'
  if (!sent.value) return 'Прислать код на почту'
  return wait.value > 0 ? `Ещё письмо — через ${wait.value} с` : 'Прислать ещё раз'
})
</script>

<template>
  <div class="guard">
    <label v-if="!byCode" class="field">
      <span class="field-label">{{ label }}</span>
      <input v-model="password" type="password" autocomplete="current-password" required />
    </label>

    <template v-else>
      <label v-if="sent" class="field">
        <span class="field-label">Код из письма</span>
        <input
          v-model="code"
          class="code"
          type="text"
          inputmode="numeric"
          autocomplete="one-time-code"
          maxlength="7"
          placeholder="······"
          required
        />
      </label>
      <p class="hint">
        {{ sent ? 'Письмо с шестью цифрами ушло на вашу почту — код действует один раз.' : 'Подтвердим, что это вы: пришлём на почту письмо с шестью цифрами.' }}
      </p>
    </template>

    <div class="ways">
      <button v-if="byCode" type="button" class="link" :disabled="sending || wait > 0" @click="ask">{{ askLabel }}</button>
      <button v-if="hasPassword" type="button" class="link is-quiet" @click="switchWay">
        {{ byCode ? 'Ввести пароль' : 'Забыли пароль? Код на почту' }}
      </button>
    </div>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
  </div>
</template>

<style scoped>
.guard { display: grid; gap: 10px; }
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
.field input.code { width: 11ch; font-size: 18px; letter-spacing: 0.3em; text-align: center; }

.ways { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 18px; }
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
}
.link:hover:not(:disabled) { text-decoration-color: currentColor; }
.link:disabled { opacity: 0.55; cursor: default; text-decoration: none; }
.link:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 2px; border-radius: 4px; }
.link.is-quiet { color: rgba(226, 220, 210, 0.7); text-decoration-color: rgba(226, 220, 210, 0.3); }

.hint { margin: 0; font-size: 13px; line-height: 1.5; color: rgba(226, 220, 210, 0.6); }
.error { margin: 0; font-size: 13.5px; color: #f2a48c; }

@media (max-width: 760px) {
  .link { min-height: 44px; }
}
</style>
