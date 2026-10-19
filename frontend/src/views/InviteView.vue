<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import SiteHeader from '../components/SiteHeader.vue'
import BirthForm from '../components/cabinet/BirthForm.vue'
import PairSky from '../components/cabinet/PairSky.vue'
import { loginSpot } from '../components/cabinet/layout.js'
import { clamp } from '../components/hero/sky.js'
import { webApi } from '../api/web.js'
import { ApiError, errorText } from '../api/http.js'
import { useSky } from '../composables/useSky.js'
import { useHead } from '../utils/useHead.js'

/**
 * The partner's side of an invitation (/invite/<token>): no account. The login sky holds the
 * inviter's star; the partner's own lights up beside it as the data are typed, and stays lit
 * once they are sent. Only first names are shown here: the inviter's data stay theirs.
 */

const route = useRoute()
const { geo, markUser, clearMark } = useSky()

useHead({ title: 'Приглашение', noindex: true })

/** loading → open | done | missing | error */
const state = ref('loading')
const message = ref('')
const invitation = ref(null)
const draft = reactive({ name: '', date: '', time: '' })
const flash = ref(false)

onMounted(async () => {
  try {
    invitation.value = await webApi.invitation(route.params.token)
    markUser({ name: invitation.value.inviter })
    state.value = invitation.value.filled ? 'done' : 'open'
  } catch (error) {
    state.value = error instanceof ApiError && error.status === 404 ? 'missing' : 'error'
    message.value = errorText(error)
  }
})
onUnmounted(clearMark)

function answer({ name, consent, birth }) {
  return webApi.answerInvitation(route.params.token, { name, consent, birth })
}
function onAnswered(next) {
  invitation.value = next
  state.value = 'done'
  flash.value = true
}

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
  if (state.value === 'done') {
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

        <template v-else-if="state === 'done'">
          <div class="card-head">
            <p class="step-kicker">Приглашение</p>
            <h1>Ваша звезда <em>зажглась</em></h1>
            <p>
              Теперь {{ invitation.inviter }} видит её рядом со своей.
              Свою карту вы можете открыть бесплатно — в собственном кабинете.
            </p>
          </div>
          <RouterLink class="gold-link" :to="{ name: 'login', query: { mode: 'register' } }">Открыть свою карту</RouterLink>
        </template>

        <BirthForm
          v-else
          with-name
          with-consent
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
