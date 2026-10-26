<script setup>
import { computed, ref } from 'vue'
import { webApi } from '../../api/web.js'
import { errorText } from '../../api/http.js'
import { hasMark } from '../../utils/marks.js'
import { markStep, stepDone } from '../../utils/newcomer.js'
import { queue } from '../../utils/track.js'

/**
 * What a cabinet opened by the letter asks after the chart, one thing at a time: the name, then a
 * password — both by wish. «Не сейчас» puts each away for good (the marks `step:name-later`,
 * `step:password-later`); the profile keeps both fields. Before the chart is seen nothing is asked:
 * the sky comes first.
 */

const props = defineProps({
  user: { type: Object, required: true },
})
const emit = defineEmits(['updated'])

const name = ref('')
const password = ref('')
const busy = ref(false)
const error = ref('')
/** The thanks after the last answer, until the person leaves the overview. */
const thanks = ref('')
/** The name has just been given here: the password's card begins with the greeting. */
const greeted = ref(false)

const pending = computed(() => {
  const { user } = props
  if (!user.birth || !stepDone(user.id, 'chart')) return ''
  if (!user.name && !hasMark(user.id, 'step:name-later')) return 'name'
  if (!user.has_password && !hasMark(user.id, 'step:password-later')) return 'password'
  return ''
})
const shown = computed(() => pending.value || (thanks.value ? 'thanks' : ''))

async function answer(action) {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    await action()
  } catch (failure) {
    error.value = errorText(failure)
  } finally {
    busy.value = false
  }
}

function saveName() {
  const given = name.value.trim()
  if (!given) return
  answer(async () => {
    const next = await webApi.setName(given)
    greeted.value = true
    emit('updated', next)
    if (next.has_password) thanks.value = `Приятно познакомиться, ${next.name}!`
  })
}

function savePassword() {
  if (password.value.length < 8) {
    error.value = 'Пароль — от 8 символов'
    return
  }
  answer(async () => {
    const result = await webApi.setPassword({ password: password.value })
    password.value = ''
    thanks.value = 'Пароль задан — входите как удобнее: по ссылке из письма или с ним.'
    emit('updated', result.user)
  })
}

function later(what) {
  error.value = ''
  queue('act', `ask:${what}-later`)
  markStep(props.user.id, `${what}-later`)
}
</script>

<template>
  <section v-if="shown" class="ask" :class="{ 'is-thanks': shown === 'thanks' }" aria-live="polite">
    <template v-if="shown === 'name'">
      <h2 class="ask-title">Как к вам обращаться?</h2>
      <p class="ask-lead">Имя появится в приветствии, на звёздном паспорте и в приглашении партнёру.</p>
      <form class="ask-line" novalidate @submit.prevent="saveName">
        <input v-model="name" type="text" maxlength="80" autocomplete="given-name" placeholder="Ваше имя" aria-label="Ваше имя" />
        <button type="submit" class="ask-go" :disabled="!name.trim() || busy">Сохранить</button>
      </form>
    </template>

    <template v-else-if="shown === 'password'">
      <h2 class="ask-title">{{ greeted ? `Приятно познакомиться, ${user.name}!` : 'Вход без письма' }}</h2>
      <p class="ask-lead">
        {{ greeted ? 'И ещё одно — по желанию. ' : '' }}Сейчас вы входите по ссылке из письма. С паролем можно
        входить сразу, на любом устройстве.
      </p>
      <form class="ask-line" novalidate @submit.prevent="savePassword">
        <!-- The address beside the password: a password manager keeps the pair. -->
        <input class="visually-hidden" type="email" autocomplete="username" :value="user.email" readonly tabindex="-1" aria-hidden="true" />
        <input
          v-model="password"
          type="password"
          autocomplete="new-password"
          minlength="8"
          placeholder="От 8 символов"
          aria-label="Пароль — от 8 символов"
        />
        <button type="submit" class="ask-go" :disabled="!password || busy">Задать пароль</button>
      </form>
    </template>

    <p v-else class="ask-thanks" role="status">
      <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg>
      {{ thanks }}
    </p>

    <p v-if="error" class="ask-error" role="alert">{{ error }}</p>
    <div v-if="shown !== 'thanks'" class="ask-foot">
      <button type="button" class="ask-later" :disabled="busy" @click="later(shown)">Не сейчас</button>
      <span class="ask-note">{{ shown === 'name' ? 'Имя можно указать' : 'Пароль можно задать' }} и позже — в профиле</span>
    </div>
  </section>
</template>

<style scoped>
/* A quiet card under the greeting: one question, one field, and a way past it. */
.ask {
  display: grid;
  gap: 10px;
  padding: 16px 18px 12px;
  border-radius: 16px;
  border: 1px solid rgba(240, 205, 138, 0.3);
  background: radial-gradient(120% 90% at 100% 0%, rgba(240, 205, 138, 0.08), transparent 65%), rgba(255, 240, 210, 0.02);
  animation: ask-in 0.5s ease both;
}
.ask.is-thanks { padding-bottom: 16px; }
.ask-title { margin: 0; font-family: var(--serif); font-weight: 500; font-size: 22px; line-height: 1.15; color: #f6efe2; }
.ask-lead { margin: -2px 0 2px; font-family: var(--book); font-size: 14.5px; line-height: 1.5; color: rgba(226, 220, 210, 0.75); }

.ask-line { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 8px; }
.ask-line input:not(.visually-hidden) {
  min-width: 0;
  height: 44px;
  padding: 0 14px;
  border-radius: 12px;
  border: 1px solid rgba(240, 210, 150, 0.22);
  background: rgba(255, 240, 210, 0.04);
  color: #f6efe2;
  font: inherit;
  font-size: 15px;
  color-scheme: dark;
  outline: none;
  transition: border-color 0.25s ease, background 0.25s ease, box-shadow 0.25s ease;
}
.ask-line input::placeholder { color: rgba(226, 220, 210, 0.42); }
.ask-line input:focus { border-color: rgba(240, 205, 138, 0.7); background: rgba(255, 240, 210, 0.06); box-shadow: 0 0 0 3px rgba(240, 205, 138, 0.12); }
.ask-go {
  height: 44px;
  padding: 0 18px;
  border-radius: 999px;
  border: 1px solid rgba(240, 205, 138, 0.6);
  background: rgba(240, 205, 138, 0.12);
  font: inherit;
  font-size: 14px;
  color: #f3dcae;
  white-space: nowrap;
  cursor: pointer;
  transition: background 0.25s ease, border-color 0.25s ease, opacity 0.25s ease;
}
.ask-go:hover:not(:disabled) { background: rgba(240, 205, 138, 0.2); border-color: rgba(240, 205, 138, 0.9); }
.ask-go:disabled { opacity: 0.45; cursor: default; }
.ask-go:focus-visible { outline: 2px solid #ffe2a8; outline-offset: 3px; }

.ask-foot { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 14px; }
.ask-later {
  padding: 4px 0;
  border: 0;
  background: none;
  font: inherit;
  font-size: 13px;
  color: rgba(226, 220, 210, 0.75);
  text-decoration: underline;
  text-decoration-color: rgba(226, 220, 210, 0.3);
  text-underline-offset: 3px;
  cursor: pointer;
}
.ask-later:hover { color: #f0cd8a; text-decoration-color: currentColor; }
.ask-later:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 2px; border-radius: 4px; }
.ask-note { font-size: 12.5px; color: rgba(226, 220, 210, 0.5); }
.ask-error { margin: 0; font-size: 13.5px; color: #f2a48c; }

.ask-thanks { display: flex; align-items: center; gap: 10px; margin: 0; font-family: var(--serif); font-style: italic; font-size: 17px; line-height: 1.35; color: #f3dcae; }
.ask-thanks svg { flex: none; width: 12px; height: 12px; fill: #f0cd8a; filter: drop-shadow(0 0 5px rgba(255, 200, 110, 0.8)); }

.visually-hidden { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }

@keyframes ask-in {
  from { opacity: 0; transform: translateY(6px); }
}

@media (max-width: 560px) {
  .ask-line { grid-template-columns: minmax(0, 1fr); }
  .ask-later { min-height: 44px; }
}
@media (prefers-reduced-motion: reduce) {
  .ask { animation: none; }
}
</style>
