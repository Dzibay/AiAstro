<script setup>
import { computed, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { ApiError, errorText } from '../../api/http.js'
import { webToken, writeSession } from '../../composables/useSession.js'
import { forgetSignIn, letterRoute, startSignIn } from '../../composables/useSignIn.js'
import { likelyMeant } from '../../utils/mailbox.js'
import { queue, reachGoal } from '../../utils/track.js'

/**
 * The address and the gold button, right on the home page (the hero, the end of the journey): the
 * letter with the link and six digits leaves at once, and the login page's letter screen takes
 * over. A signed-in visitor gets the way to the cabinet instead.
 */
const props = defineProps({
  /** The funnel's start place (START_PLACES): hero | how | final. */
  place: { type: String, required: true },
  cta: { type: String, default: 'Получить карту бесплатно' },
})

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const QUIET = 'Пришлём ссылку для входа — пароль не нужен'

const router = useRouter()
const email = ref('')
const consent = ref(false)
const pending = ref(false)
const message = ref('')
/** The tick was missed: it glows once to show where it is. */
const nudged = ref(false)
const field = ref(null)
const uid = `start-${props.place}`
const slip = computed(() => (EMAIL.test(email.value.trim()) ? likelyMeant(email.value.trim()) : ''))

let begun = false
/** The first character of the address (typed or filled in): the funnel's step «Начали вводить почту». */
function begin() {
  if (begun) return
  begun = true
  queue('act', `email:${props.place}`)
}

function nudge() {
  nudged.value = false
  requestAnimationFrame(() => { nudged.value = true })
}

async function submit() {
  if (pending.value) return
  const address = email.value.trim()
  message.value = ''
  if (!EMAIL.test(address)) {
    message.value = address ? 'Почта выглядит неполной' : 'Укажите почту — на неё придёт ссылка'
    field.value?.focus()
    return
  }
  if (!consent.value) {
    message.value = 'Отметьте согласие — и письмо уйдёт'
    nudge()
    return
  }
  pending.value = true
  queue('act', `start:${props.place}`)
  try {
    const answer = await startSignIn({ email: address, consent: true, place: props.place })
    if (answer.token) {
      // The site's mail is not set up: the new cabinet opens at once.
      writeSession('web', answer.token)
      reachGoal('astra.registration@success')
      if (answer.user?.birth) reachGoal('astra.birth@save')
      forgetSignIn()
      await router.push('/cabinet')
    } else {
      await router.push(letterRoute(props.place))
    }
  } catch (error) {
    if (error instanceof ApiError && error.code === 'mail_off') message.value = 'Письма пока не отправляются — войдите с паролем'
    else message.value = errorText(error)
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <RouterLink v-if="webToken" class="start-cta is-solo" to="/cabinet" :data-track="`${place}:cabinet`">
    <span>Открыть кабинет</span>
    <svg class="start-arrow" viewBox="0 0 16 16" aria-hidden="true"><path d="M2 8h11M9 4l4 4-4 4" /></svg>
  </RouterLink>

  <form v-else class="start" novalidate @submit.prevent="submit">
    <div class="start-row">
      <label class="sr-only" :for="`${uid}-email`">Почта</label>
      <input
        :id="`${uid}-email`"
        ref="field"
        v-model="email"
        type="email"
        autocomplete="email"
        inputmode="email"
        enterkeyhint="send"
        placeholder="Ваша почта"
        :aria-invalid="message ? 'true' : undefined"
        @input="begin"
        :aria-describedby="`${uid}-say`"
      />
      <button class="start-cta" type="submit" :disabled="pending" :data-track="`${place}:start`">
        <span>{{ pending ? 'Отправляем…' : cta }}</span>
        <svg class="start-arrow" viewBox="0 0 16 16" aria-hidden="true"><path d="M2 8h11M9 4l4 4-4 4" /></svg>
      </button>
    </div>

    <p v-if="slip" class="start-slip">
      Может быть, почта —
      <button type="button" @click="email = slip">{{ slip }}</button>?
    </p>

    <label class="start-consent" :class="{ 'is-nudged': nudged }" @animationend="nudged = false">
      <input v-model="consent" type="checkbox" />
      <span class="tick" aria-hidden="true" />
      <span>
        Даю согласие на обработку <a href="/legal/consent" target="_blank" rel="noopener">персональных данных</a>
        и принимаю <a href="/legal/offer" target="_blank" rel="noopener">оферту</a>
      </span>
    </label>

    <p :id="`${uid}-say`" class="start-say" :class="{ 'is-error': message }" :role="message ? 'alert' : undefined">
      {{ message || QUIET }}
    </p>
  </form>
</template>

<style scoped>
.start {
  display: grid;
  gap: 12px;
  width: min(540px, 100%);
  margin: 0 auto;
  text-align: left;
}

/* The address and the button in one glass pill; on phones they stand one above the other. */
.start-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px;
  border-radius: 999px;
  border: 1px solid rgba(240, 210, 150, 0.32);
  background: rgba(8, 9, 16, 0.62);
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 240, 210, 0.06);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  transition: border-color 0.25s ease, box-shadow 0.25s ease;
}
.start-row:focus-within {
  border-color: rgba(240, 205, 138, 0.7);
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.35), 0 0 0 4px rgba(240, 205, 138, 0.12);
}
:global(.no-glass) .start-row { background: rgba(10, 11, 18, 0.92); backdrop-filter: none; -webkit-backdrop-filter: none; }

.start-row input {
  flex: 1;
  min-width: 0;
  height: 48px;
  padding: 0 8px 0 20px;
  border: 0;
  background: none;
  font: inherit;
  font-size: 16px;
  color: #f6efe2;
  outline: none;
}
.start-row input::placeholder { color: rgba(226, 220, 210, 0.5); }
.start-row input[aria-invalid='true']::placeholder { color: rgba(240, 170, 140, 0.7); }

.start-cta {
  position: relative;
  display: inline-flex;
  flex: none;
  align-items: center;
  justify-content: center;
  gap: 12px;
  height: 48px;
  padding: 0 26px 0 28px;
  border: 0;
  border-radius: 999px;
  overflow: hidden;
  font: inherit;
  font-size: 15px;
  font-weight: 600;
  white-space: nowrap;
  text-decoration: none;
  color: #2b1d0b;
  background: linear-gradient(180deg, #f4dba6 0%, #e3bd78 55%, #cf9f55 100%);
  box-shadow:
    inset 0 1px 0 rgba(255, 248, 228, 0.8),
    inset 0 -1px 0 rgba(120, 80, 20, 0.35),
    0 6px 24px rgba(230, 170, 80, 0.3);
  cursor: pointer;
  transition: transform 0.25s ease, box-shadow 0.25s ease, filter 0.25s ease;
}
.start-cta::after {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: -60%;
  width: 45%;
  background: linear-gradient(100deg, transparent, rgba(255, 255, 255, 0.55), transparent);
  transform: skewX(-20deg);
  animation: sheen 5.5s ease-in-out 2s infinite;
}
.start-cta:hover { box-shadow: inset 0 1px 0 rgba(255, 248, 228, 0.9), inset 0 -1px 0 rgba(120, 80, 20, 0.35), 0 10px 34px rgba(240, 180, 90, 0.45); }
.start-cta:hover .start-arrow { transform: translateX(3px); }
.start-cta:focus-visible { outline: 2px solid #ffe2a8; outline-offset: 3px; }
.start-cta:disabled { cursor: progress; filter: saturate(0.7) brightness(0.92); }
.start-cta.is-solo { height: 54px; padding: 0 34px 0 36px; }
.start-arrow {
  width: 15px;
  height: 15px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.6;
  stroke-linecap: round;
  stroke-linejoin: round;
  transition: transform 0.25s ease;
}

.start-slip { margin: -2px 0 0 20px; font-size: 13px; color: rgba(236, 230, 220, 0.75); }
.start-slip button {
  padding: 0;
  border: 0;
  background: none;
  font: inherit;
  color: #f0cd8a;
  text-decoration: underline;
  text-underline-offset: 3px;
  cursor: pointer;
}

.start-consent {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin: 0 0 0 20px;
  font-size: 13px;
  line-height: 18px;
  color: rgba(236, 230, 220, 0.72);
  cursor: pointer;
}
.start-consent input { position: absolute; opacity: 0; pointer-events: none; }
.start-consent a { color: #f0cd8a; text-decoration: underline; text-decoration-color: rgba(240, 205, 138, 0.4); text-underline-offset: 3px; }
.start-consent a:hover { text-decoration-color: currentColor; }
.tick {
  position: relative;
  flex: none;
  width: 15px;
  height: 15px;
  margin-top: 1.5px;
  border-radius: 4px;
  border: 1px solid rgba(240, 210, 150, 0.55);
  background: rgba(8, 9, 16, 0.5);
  transition: background 0.2s ease, border-color 0.2s ease;
}
.tick::after {
  content: '';
  position: absolute;
  left: 4.5px;
  top: 1.5px;
  width: 3.5px;
  height: 7px;
  border: solid #2b1d0b;
  border-width: 0 1.6px 1.6px 0;
  transform: rotate(45deg) scale(0);
  transition: transform 0.2s ease;
}
.start-consent input:checked + .tick { background: #e9c47e; border-color: #e9c47e; }
.start-consent input:checked + .tick::after { transform: rotate(45deg) scale(1); }
.start-consent input:focus-visible + .tick { box-shadow: 0 0 0 3px rgba(240, 205, 138, 0.3); }
.start-consent.is-nudged .tick { animation: nudge 0.9s ease 2; }

.start-say { min-height: 18px; margin: 0 0 0 20px; font-size: 13px; line-height: 18px; color: rgba(236, 230, 220, 0.78); }
/* Both lines may fall on the planet's lit rim: a shade of their own keeps them readable. */
.start-consent, .start-say, .start-slip { text-shadow: 0 1px 2px rgba(0, 0, 0, 0.95), 0 0 14px rgba(0, 0, 0, 0.85); }
.start-say.is-error { color: #f3b49b; }

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}

@keyframes sheen {
  0%, 70% { left: -60%; }
  100% { left: 130%; }
}
@keyframes nudge {
  50% { border-color: #ffe2a8; box-shadow: 0 0 0 5px rgba(255, 214, 140, 0.28), 0 0 18px rgba(255, 200, 110, 0.6); }
}

@media (max-width: 560px) {
  .start-row { flex-direction: column; align-items: stretch; gap: 8px; padding: 0; border: 0; border-radius: 0; background: none; box-shadow: none; backdrop-filter: none; -webkit-backdrop-filter: none; }
  .start-row:focus-within { box-shadow: none; }
  .start-row input {
    flex: none;
    height: 52px;
    padding: 0 20px;
    border-radius: 999px;
    border: 1px solid rgba(240, 210, 150, 0.36);
    background: rgba(8, 9, 16, 0.72);
    text-align: center;
  }
  .start-row input:focus { border-color: rgba(240, 205, 138, 0.8); }
  .start-cta { height: 52px; }
  .start-consent, .start-say, .start-slip { margin-left: 4px; }
  .start-say { text-align: center; margin-left: 0; }
}

@media (prefers-reduced-motion: reduce) {
  .start-cta::after { animation: none; }
  .start-consent.is-nudged .tick { animation-iteration-count: 1; }
}
</style>
