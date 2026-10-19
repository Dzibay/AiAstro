<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import SiteHeader from '../components/SiteHeader.vue'
import { webApi } from '../api/web.js'
import { ApiError, errorText } from '../api/http.js'
import { clearSession } from '../composables/useSession.js'
import { useSky } from '../composables/useSky.js'
import { SIGNS } from '../utils/skyToday.js'
import { formatDate } from '../utils/format.js'
import { useHead } from '../utils/useHead.js'

/**
 * The cabinet on the sky: the camera has flown onto the person's star (NameMark in the
 * 'cabinet' pose), and the panel stands beside it where the login card stood.
 */

const router = useRouter()
const { mark, markUser, clearMark } = useSky()
const user = ref(null)
const message = ref('')

useHead({ title: 'Кабинет', noindex: true })

const SIGN_BY_ID = Object.fromEntries(SIGNS.map((sign) => [sign.id, sign]))

const signLine = computed(() => {
  const sun = SIGN_BY_ID[mark.sun]
  if (!sun) return ''
  const moon = SIGN_BY_ID[mark.moon]
  return moon ? `Солнце ${sun.in}, Луна ${moon.in}` : `Солнце ${sun.in}`
})

const birthLine = computed(() => {
  const birth = user.value?.birth
  if (!birth) return ''
  return [formatDate(birth.date), birth.time, birth.place].filter(Boolean).join(' · ')
})

onMounted(async () => {
  try {
    user.value = await webApi.me()
    markUser(user.value)
  } catch (error) {
    if (error instanceof ApiError && (error.status === 401 || error.code === 'blocked')) {
      clearSession('web')
      router.push({ name: 'login' })
      return
    }
    message.value = errorText(error)
  }
})

onUnmounted(clearMark)

function logout() {
  clearSession('web')
  router.push('/')
}
</script>

<template>
  <div class="site">
    <SiteHeader />
    <main class="cabinet">
      <section class="cabinet-card" aria-live="polite">
        <span class="card-sheen" aria-hidden="true" />
        <p class="kicker">Кабинет</p>

        <p v-if="message" class="error">{{ message }}</p>

        <template v-else-if="user">
          <header class="card-head">
            <h1>Здравствуйте, <em>{{ user.name }}</em></h1>
            <p v-if="signLine">{{ signLine }}</p>
            <p v-else>Добавьте дату рождения — и небо нарисует ваш знак.</p>
          </header>

          <dl class="facts">
            <div v-if="birthLine"><dt>Рождение</dt><dd>{{ birthLine }}</dd></div>
            <div><dt>Почта</dt><dd>{{ user.email }}</dd></div>
            <div><dt>С нами</dt><dd>с {{ formatDate(user.created_at) }}</dd></div>
          </dl>

          <div class="readings">
            <h2>Разборы</h2>
            <p>Готовых разборов пока нет. Натальная карта появится здесь, как только расчёт будет подключён.</p>
          </div>

          <button type="button" class="quiet" @click="logout">Выйти</button>
        </template>

        <p v-else class="loading">Открываем ваше небо…</p>
      </section>
    </main>
  </div>
</template>

<style scoped>
.cabinet {
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

/* The login card's glass, wider: it waits for the flight to land before it rises. */
.cabinet-card {
  position: relative;
  display: grid;
  gap: 16px;
  width: min(420px, 100%);
  overflow: hidden;
  padding: 24px 26px;
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
  animation: card-in 0.9s cubic-bezier(0.3, 0.7, 0.2, 1) 0.9s both;
}
.cabinet-card::before {
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
  animation: card-sheen 1.8s ease 1.5s forwards;
}

.kicker { margin: 0; font-size: 10px; letter-spacing: 0.26em; text-transform: uppercase; color: rgba(233, 194, 124, 0.75); }

.card-head { display: grid; gap: 8px; }
.card-head h1 {
  margin: 0;
  font-family: var(--serif);
  font-weight: 500;
  font-size: 32px;
  line-height: 1.08;
  color: #f6efe2;
}
.card-head em { font-style: italic; color: #f0cd8a; }
.card-head p { margin: 0; font-family: var(--serif); font-style: italic; font-size: 17px; color: rgba(242, 228, 200, 0.82); }

.facts { display: grid; gap: 8px; margin: 0; padding: 14px 0; border-block: 1px solid rgba(240, 210, 150, 0.12); }
.facts div { display: flex; justify-content: space-between; gap: 16px; font-size: 14px; }
.facts dt { color: rgba(226, 220, 210, 0.55); }
.facts dd { margin: 0; text-align: right; color: #efe7d8; overflow-wrap: anywhere; }

.readings { display: grid; gap: 6px; }
.readings h2 { margin: 0; font-family: var(--serif); font-weight: 500; font-size: 20px; color: #f6efe2; }
.readings p { margin: 0; font-size: 14px; line-height: 1.5; color: rgba(226, 220, 210, 0.7); }

.error { margin: 0; font-size: 14px; color: #f2a48c; }
.loading { margin: 0; font-family: var(--serif); font-style: italic; font-size: 17px; color: rgba(242, 228, 200, 0.75); }

.quiet {
  justify-self: start;
  padding: 6px 4px;
  border: 0;
  background: none;
  font: inherit;
  font-size: 13.5px;
  color: rgba(226, 220, 210, 0.72);
  cursor: pointer;
  transition: color 0.25s ease;
}
.quiet:hover { color: #f0cd8a; }
.quiet:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 2px; border-radius: 6px; }

@keyframes card-in { from { opacity: 0; transform: translateY(16px); filter: blur(4px); } }
@keyframes card-sheen { to { transform: translateX(100%); } }

@media (max-width: 760px) {
  /* A sheet under the star, which keeps the top of the screen. */
  .cabinet { align-items: flex-end; justify-content: center; padding: 42vh 12px 16px; }
  .cabinet-card { padding: 20px 18px; }
  .card-head h1 { font-size: 28px; }
  .quiet { min-height: 40px; }
}

@media (prefers-reduced-motion: reduce) {
  .cabinet-card { animation: card-fade 0.4s ease both; }
  .card-sheen { animation: none; }
}
@keyframes card-fade { from { opacity: 0; } }
</style>
