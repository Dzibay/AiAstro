<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import SiteHeader from '../components/SiteHeader.vue'
import BirthForm from '../components/cabinet/BirthForm.vue'
import PairSky from '../components/cabinet/PairSky.vue'
import { loginSpot } from '../components/cabinet/layout.js'
import { clamp } from '../components/hero/sky.js'
import { webApi } from '../api/web.js'
import { ApiError, errorText } from '../api/http.js'
import { keepInvite, linkPendingInvite, pendingInvite } from '../composables/usePartners.js'
import { webToken, writeSession } from '../composables/useSession.js'
import { useSky } from '../composables/useSky.js'
import { useHead } from '../utils/useHead.js'

/**
 * The partner's side of an invitation (/invite/<token>). The login sky holds the inviter's star;
 * the partner's own lights up beside it as the data are typed, and stays lit once they are sent.
 * Only first names are shown here: the inviter's data stay theirs until the pair is joined.
 *
 * Without a cabinet the partner answers with the form, and may open a cabinet right after: the
 * page keeps a key of the answer, so the pair joins the cabinet opened now or later. With a
 * cabinet, the invitation is accepted from it, with the birth data it already holds.
 */

const route = useRoute()
const router = useRouter()
const { geo, markUser, clearMark } = useSky()

useHead({ title: 'Приглашение', noindex: true })

/** loading → open | accept | done | joined | own | taken | missing | error */
const state = ref('loading')
const message = ref('')
const invitation = ref(null)
const draft = reactive({ name: '', date: '', time: '' })
const flash = ref(false)
const token = computed(() => route.params.token)

/** The key of this very invitation, if the page answered it: a cabinet can still be opened for the pair. */
const kept = ref(null)

onMounted(async () => {
  try {
    invitation.value = await webApi.invitation(token.value)
    markUser({ name: invitation.value.inviter })
    const found = pendingInvite()
    kept.value = found && found.token === token.value ? found : null
    state.value = stateOf(invitation.value)
  } catch (error) {
    state.value = error instanceof ApiError && error.status === 404 ? 'missing' : 'error'
    message.value = errorText(error)
  }
})
onUnmounted(clearMark)

function stateOf(found) {
  if (found.own) return 'own'
  if (found.mine) return 'joined'
  if (found.linked) return 'taken'
  if (found.filled) return 'done'
  return webToken.value ? 'accept' : 'open'
}

function answer({ name, consent, share, birth }) {
  return webApi.answerInvitation(token.value, { name, consent, share, birth })
}
function onAnswered(next) {
  kept.value = { token: token.value, claim: next.claim, name: next.name, inviter: next.inviter }
  keepInvite(kept.value)
  invitation.value = next
  state.value = 'done'
  flash.value = true
}

// ---- With a cabinet already: accept from it ----

const acceptForm = reactive({ share: false, pending: false })

async function accept() {
  if (!acceptForm.share) {
    message.value = 'Отметьте согласие показать данные партнёру'
    return
  }
  message.value = ''
  acceptForm.pending = true
  try {
    const joined = await webApi.acceptInvitation(token.value, true)
    flash.value = true
    router.push({ path: '/cabinet/pair', query: { partner: joined.partner, joined: 1 } })
  } catch (error) {
    if (error instanceof ApiError && error.code === 'no_birth') {
      // The cabinet has no birth data yet: the form gives them, and the pair joins it right after.
      state.value = 'open'
      message.value = ''
      return
    }
    message.value = errorText(error)
  } finally {
    acceptForm.pending = false
  }
}

// ---- Just answered: a cabinet of one's own, the pair already in it ----

const signup = reactive({ email: '', password: '', consent: false, pending: false })

async function join() {
  if (!signup.consent) {
    message.value = 'Отметьте согласие на обработку данных'
    return
  }
  message.value = ''
  signup.pending = true
  try {
    if (!webToken.value) {
      const opened = await webApi.register({
        email: signup.email.trim(),
        password: signup.password,
        name: invitation.value.name,
        consent: true,
      })
      writeSession('web', opened.token)
    }
    const joined = await linkPendingInvite()
    router.push({ path: '/cabinet/pair', query: { partner: joined?.partner, joined: 1 } })
  } catch (error) {
    message.value = error instanceof ApiError && error.code === 'exists'
      ? 'Эта почта уже открывала кабинет — войдите, и пара присоединится к нему'
      : errorText(error)
  } finally {
    signup.pending = false
  }
}

/** Signed in elsewhere already: the kept key joins the pair to that cabinet. */
const login = computed(() => ({ name: 'login', query: { next: '/cabinet/pair' } }))

const shareLabel = computed(() => `Разрешаю показать мои данные рождения: ${invitation.value?.inviter || 'партнёр'} увидит их в разборе нашей пары`)

/** The inviter's star, where NameMark puts it on the login sky. */
const from = computed(() => (invitation.value ? loginSpot(geo.value, invitation.value.inviter) : null))

/**
 * The partner's star: across the free sky from the inviter's, beyond the engraving of their sign.
 * On a phone the strip above the sheet; on a desktop the sky between the orbit and the card.
 */
const area = computed(() => {
  const star = from.value
  if (!star) return null
  const { W, H, narrow } = geo.value
  if (narrow) {
    const top = 84
    const bottom = Math.max(top, (window.innerHeight || H) * 0.34 - 40)
    const x = star.x < W / 2 ? clamp(star.x + star.span * 0.9, W * 0.55, W - 60) : clamp(star.x - star.span * 0.9, 60, W * 0.45)
    return { x, y: clamp(star.y + 20, top, bottom), r: 40 }
  }
  const cardLeft = W - clamp(W * 0.08, 20, 150) - 392
  const left = W * 0.24
  const right = cardLeft - 60
  const x = star.x - left > right - star.x ? clamp(star.x - star.span * 0.85, left, right) : clamp(star.x + star.span * 0.85, left, right)
  // Above the orbit and its Sun, which take the lower half of the login sky.
  const y = clamp(star.y < H * 0.3 ? star.y + star.span * 0.45 : star.y - star.span * 0.45, 120, H * 0.5)
  return { x, y, r: 60 }
})

const stars = computed(() => {
  if (['done', 'joined', 'taken'].includes(state.value)) {
    return [{ id: 'me', name: invitation.value.name, date: draft.date, time: draft.time, lit: true, flash: flash.value }]
  }
  if (state.value !== 'open') return []
  const name = draft.name || invitation.value.name
  return name ? [{ id: 'me', name, date: draft.date, time: draft.time, lit: Boolean(draft.date) }] : []
})
</script>

<template>
  <div class="invite-page">
    <SiteHeader />
    <PairSky v-if="from && stars.length" :stars="stars" :from="from" :area="area" />
    <main class="invite">
      <div class="invite-card" :class="{ 'is-wide': state === 'open' }">
        <span class="card-sheen" aria-hidden="true" />

        <p v-if="state === 'loading'" class="loading">Ищем приглашение…</p>

        <template v-else-if="state === 'missing'">
          <div class="card-head">
            <h1>Приглашение <em>не найдено</em></h1>
            <p>Возможно, ссылка скопирована не целиком. Попросите прислать её ещё раз.</p>
          </div>
          <RouterLink class="quiet-link" to="/">На главную</RouterLink>
        </template>

        <template v-else-if="state === 'error'">
          <div class="card-head">
            <h1>Небо <em>не ответило</em></h1>
            <p>{{ message }}</p>
          </div>
        </template>

        <template v-else-if="state === 'own'">
          <div class="card-head">
            <p class="step-kicker">Приглашение</p>
            <h1>Это ваше <em>приглашение</em></h1>
            <p>Отправьте эту ссылку партнёру: когда партнёр укажет свои данные, его звезда зажжётся у вас в кабинете.</p>
          </div>
          <RouterLink class="gold-link" to="/cabinet/pair">К вашим парам</RouterLink>
        </template>

        <template v-else-if="state === 'joined'">
          <div class="card-head">
            <p class="step-kicker">Приглашение</p>
            <h1>Пара уже <em>в вашем кабинете</em></h1>
            <p>Вы и {{ invitation.inviter }} видите её оба: если один из вас откроет разбор, он откроется у обоих.</p>
          </div>
          <RouterLink class="gold-link" to="/cabinet/pair">Открыть пару</RouterLink>
        </template>

        <template v-else-if="state === 'taken'">
          <div class="card-head">
            <p class="step-kicker">Приглашение</p>
            <h1>Звезда <em>уже зажглась</em></h1>
            <p>На это приглашение уже ответили, и пара стала общей. Если это были вы — войдите в тот кабинет.</p>
          </div>
          <RouterLink class="quiet-link" to="/">На главную</RouterLink>
        </template>

        <template v-else-if="state === 'accept'">
          <div class="card-head">
            <p class="step-kicker">Приглашение</p>
            <h1>{{ invitation.inviter }} <em>зовёт вас</em> на небо</h1>
            <p>
              У вас уже есть кабинет: звезда зажжётся по данным рождения из него, а пара появится у вас обоих.
              Если один из вас откроет разбор пары, он откроется у обоих.
            </p>
          </div>
          <form class="mini-form" novalidate @submit.prevent="accept">
            <label class="check consent">
              <input v-model="acceptForm.share" type="checkbox" />
              <span class="check-box" aria-hidden="true" />
              <span>{{ shareLabel }}</span>
            </label>
            <p v-if="message" class="error" role="alert">{{ message }}</p>
            <button class="gold-cta" type="submit" :disabled="acceptForm.pending">
              {{ acceptForm.pending ? 'Минуту…' : 'Зажечь звезду' }}
            </button>
          </form>
        </template>

        <template v-else-if="state === 'done'">
          <div class="card-head">
            <p class="step-kicker">Приглашение</p>
            <h1>Ваша звезда <em>зажглась</em></h1>
            <p v-if="kept">
              Теперь {{ invitation.inviter }} видит её рядом со своей. Откройте свой кабинет — бесплатно:
              там ваша карта, а ваша пара будет у вас обоих, и разбор, открытый одним, откроется у другого.
            </p>
            <p v-else>Теперь {{ invitation.inviter }} видит её рядом со своей.</p>
          </div>
          <form v-if="kept" class="mini-form" novalidate @submit.prevent="join">
            <template v-if="!webToken">
              <label class="field">
                <span class="field-label">Почта</span>
                <input v-model="signup.email" type="email" autocomplete="email" maxlength="254" />
              </label>
              <label class="field">
                <span class="field-label">Пароль</span>
                <input v-model="signup.password" type="password" autocomplete="new-password" minlength="8" maxlength="200" />
              </label>
            </template>
            <label class="check consent">
              <input v-model="signup.consent" type="checkbox" />
              <span class="check-box" aria-hidden="true" />
              <span>
                Даю согласие на обработку
                <a href="/legal/consent" target="_blank" rel="noopener">персональных данных</a>
              </span>
            </label>
            <p v-if="message" class="error" role="alert">{{ message }}</p>
            <button class="gold-cta" type="submit" :disabled="signup.pending">
              {{ signup.pending ? 'Минуту…' : webToken ? 'Добавить пару в мой кабинет' : 'Открыть кабинет' }}
            </button>
            <RouterLink v-if="!webToken" class="quiet-link" :to="login">У меня уже есть кабинет — войти</RouterLink>
          </form>
          <RouterLink v-else class="gold-link" :to="{ name: 'login', query: { mode: 'register' } }">Открыть свою карту</RouterLink>
        </template>

        <BirthForm
          v-else
          with-name
          with-consent
          :share-label="shareLabel"
          :name="invitation.name"
          :sky="false"
          :cancellable="false"
          :submit="answer"
          submit-label="Зажечь звезду"
          @draft="Object.assign(draft, $event)"
          @saved="onAnswered"
        >
          <template #head>
            <div class="card-head">
              <p class="step-kicker">Приглашение</p>
              <h1>{{ invitation.inviter }} <em>зовёт вас</em> на небо</h1>
              <p>
                Укажите свои данные рождения — и рядом с этой звездой зажжётся ваша.
                Регистрация не нужна; данные увидит только {{ invitation.inviter }}, в разборе вашей пары.
              </p>
            </div>
          </template>
        </BirthForm>
      </div>
    </main>
  </div>
</template>

<style scoped>
/* The sign-up right after the answer: the fields of BirthForm, which keeps its own scoped. */
.mini-form { display: grid; gap: 14px; }
.field { display: grid; gap: 7px; min-width: 0; }
.field-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.field-label { line-height: 16px; font-size: 10.5px; letter-spacing: 0.24em; text-transform: uppercase; color: rgba(226, 214, 192, 0.66); }
.field > input, .field-head + input {
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
.field input:hover:not(:disabled) { border-color: rgba(240, 210, 150, 0.32); }
.field input:focus {
  border-color: rgba(240, 205, 138, 0.7);
  background: rgba(255, 240, 210, 0.06);
  box-shadow: 0 0 0 3px rgba(240, 205, 138, 0.12);
}
.field input:disabled { opacity: 0.4; cursor: not-allowed; }
.field input::-webkit-calendar-picker-indicator { opacity: 0.6; cursor: pointer; }
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

.actions { display: flex; align-items: center; gap: 16px; margin-top: 2px; }
.gold-cta {
  flex: 1;
  padding: 12px 22px;
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
.gold-cta:hover:not(:disabled) { filter: brightness(1.05); box-shadow: inset 0 1px 0 rgba(255, 248, 228, 0.8), 0 10px 38px rgba(230, 170, 80, 0.48); }
.gold-cta:focus-visible { outline: 2px solid #ffe2a8; outline-offset: 3px; }
.gold-cta:disabled { opacity: 0.6; cursor: progress; }
.invite {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  min-height: 100vh;
  min-height: 100svh;
  padding: 110px clamp(20px, 8vw, 150px) 48px;
  pointer-events: none;
}

/* The login card's glass: here too it is the whole page. */
.invite-card {
  position: relative;
  display: grid;
  gap: 14px;
  width: min(392px, 100%);
  overflow: hidden;
  padding: 22px 24px;
  border-radius: 22px;
  border: 1px solid rgba(240, 210, 150, 0.22);
  background:
    radial-gradient(120% 70% at 0% 0%, rgba(255, 196, 120, 0.1), transparent 60%),
    linear-gradient(160deg, rgba(26, 23, 26, 0.62), rgba(8, 10, 18, 0.74));
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 240, 210, 0.08);
  backdrop-filter: blur(14px) saturate(1.2);
  -webkit-backdrop-filter: blur(14px) saturate(1.2);
  color: #efe7d8;
  pointer-events: auto;
  animation: card-in 0.9s cubic-bezier(0.3, 0.7, 0.2, 1) 0.25s both;
}
.invite-card::before {
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
.step-kicker { margin: 0; font-size: 10px; letter-spacing: 0.26em; text-transform: uppercase; color: rgba(233, 194, 124, 0.75); }
.card-head h1 {
  margin: 0;
  font-family: var(--serif);
  font-weight: 500;
  font-size: 30px;
  line-height: 1.08;
  color: #f6efe2;
}
.card-head em { font-style: italic; color: #f0cd8a; }
.card-head p:not(.step-kicker) { margin: 0; font-size: 14px; line-height: 1.5; color: rgba(226, 220, 210, 0.7); }

.loading { margin: 0; font-family: var(--serif); font-style: italic; font-size: 17px; color: rgba(242, 228, 200, 0.75); }

.gold-link {
  justify-self: start;
  padding: 12px 22px;
  border-radius: 999px;
  font-weight: 600;
  color: #2b1d0b;
  text-decoration: none;
  background: linear-gradient(180deg, #f4dba6 0%, #e3bd78 55%, #cf9f55 100%);
  box-shadow: inset 0 1px 0 rgba(255, 248, 228, 0.8), 0 8px 30px rgba(230, 170, 80, 0.32);
}
.gold-link:focus-visible { outline: 2px solid #ffe2a8; outline-offset: 3px; }
.quiet-link { justify-self: start; font-size: 13.5px; color: rgba(226, 220, 210, 0.72); text-underline-offset: 3px; }
.quiet-link:hover { color: #f0cd8a; }

@keyframes card-in { from { opacity: 0; transform: translateY(16px); filter: blur(4px); } }
@keyframes card-sheen { to { transform: translateX(100%); } }

@media (max-width: 760px) {
  .invite { align-items: flex-end; justify-content: center; padding: 34vh 12px 16px; }
  .invite-card { padding: 18px 18px 20px; }
  .card-head h1 { font-size: 26px; }
  .gold-link, .quiet-link { min-height: 44px; display: inline-flex; align-items: center; }
}
@media (prefers-reduced-motion: reduce) {
  .invite-card, .card-sheen { animation: none; }
}
</style>
