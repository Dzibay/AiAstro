<script setup>
import { computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { usePartners } from '../../composables/usePartners.js'
import { useChat } from '../../composables/useChat.js'
import { stepDone } from '../../utils/newcomer.js'

/**
 * «Путь новичка»: five first steps across the cabinet, each a star that lights when it is
 * taken. It shows the way to everything the cabinet holds and leaves once the path is walked.
 */

const props = defineProps({
  user: { type: Object, required: true },
})

const { partners, status: partnersStatus, load: loadPartners } = usePartners()
const { chat, load: loadChat } = useChat()
onMounted(() => {
  if (props.user.birth) loadPartners()
  // The question may have been asked before the path existed or on another device: the history knows.
  if (!stepDone(props.user.id, 'chat')) loadChat()
})
const asked = computed(() => stepDone(props.user.id, 'chat') || chat.items.some((item) => item.role === 'user'))

const steps = computed(() => {
  const birth = props.user.birth
  return [
    { id: 'birth', name: 'Указать дату рождения', why: 'небо нарисует ваш знак', done: Boolean(birth), to: { name: 'cabinet-birth' } },
    {
      id: 'place',
      name: 'Добавить время и город',
      why: 'появятся Асцендент и дома',
      done: Boolean(birth?.time && birth.lat != null),
      to: { name: 'cabinet-birth' },
    },
    { id: 'sun', name: 'Прочитать своё Солнце', why: 'главное о вашем характере', done: stepDone(props.user.id, 'sun'), to: { name: 'cabinet-chart', params: { item: 'sun' } } },
    { id: 'chat', name: 'Задать вопрос астрологу', why: 'два вопроса — в подарок', done: asked.value, to: { name: 'cabinet-chat' } },
    { id: 'pair', name: 'Добавить партнёра', why: 'увидеть пару по сферам жизни', done: partners.value.length > 0, to: { name: 'cabinet-pair', query: { add: '' } } },
  ]
})
const count = computed(() => steps.value.filter((step) => step.done).length)
const next = computed(() => steps.value.find((step) => !step.done) || null)
// The partners' and the question's steps are unknown until their lists are in: do not flash a path that will vanish.
const visible = computed(
  () => next.value && (!props.user.birth || partnersStatus.value !== 'loading') && (asked.value || chat.status !== 'loading'),
)
</script>

<template>
  <section v-if="visible" class="newcomer" aria-labelledby="newcomer-title">
    <div class="head">
      <h2 id="newcomer-title" class="title">Путь новичка</h2>
      <p class="progress" :aria-label="`Пройдено ${count} из ${steps.length}`">
        <span v-for="step in steps" :key="step.id" class="progress-star" :class="{ 'is-on': step.done }" aria-hidden="true">✦</span>
      </p>
    </div>
    <p class="count">Пройдено {{ count }} из {{ steps.length }} — следующий шаг светится</p>
    <ol class="steps">
      <li v-for="step in steps" :key="step.id" :class="{ 'is-done': step.done, 'is-next': step === next }">
        <RouterLink v-if="!step.done" class="step" :to="step.to">
          <span class="step-mark" aria-hidden="true" />
          <span class="step-name">{{ step.name }}</span>
          <span class="step-why">{{ step.why }}</span>
        </RouterLink>
        <span v-else class="step">
          <span class="step-mark" aria-hidden="true" />
          <span class="step-name">{{ step.name }}<span class="visually-hidden"> — готово</span></span>
        </span>
      </li>
    </ol>
  </section>
</template>

<style scoped>
/* Raised under the greeting and framed, so a newcomer sees where to begin. */
.newcomer {
  display: grid;
  gap: 8px;
  padding: 14px 16px 10px;
  border-radius: 16px;
  border: 1px solid rgba(240, 205, 138, 0.38);
  background: radial-gradient(120% 90% at 0% 0%, rgba(240, 205, 138, 0.1), transparent 65%), rgba(255, 240, 210, 0.02);
  box-shadow: 0 0 24px rgba(255, 200, 110, 0.06);
}
.count { margin: -4px 0 2px; font-size: 12.5px; color: rgba(226, 220, 210, 0.6); }
.head { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; }
.title { margin: 0; font-family: var(--caps); font-weight: 600; font-size: 16px; letter-spacing: 0.1em; color: rgba(240, 205, 138, 0.85); }
.progress { margin: 0; letter-spacing: 0.2em; font-size: 13px; }
.progress-star { color: rgba(240, 205, 138, 0.2); transition: color 0.6s ease; }
.progress-star.is-on { color: #f0cd8a; text-shadow: 0 0 6px rgba(255, 200, 110, 0.7); }

.steps { display: grid; gap: 0; margin: 0; padding: 0; list-style: none; }
.step {
  display: grid;
  grid-template-columns: 16px 1fr;
  column-gap: 10px;
  align-items: baseline;
  padding: 6px 8px;
  margin: 0 -8px;
  border-radius: 10px;
  color: #efe7d8;
  text-decoration: none;
  font-family: var(--book);
  font-size: 14.5px;
  transition: background 0.2s ease;
}
a.step:hover { background: rgba(240, 205, 138, 0.07); }
a.step:hover .step-name { color: #f0cd8a; }
a.step:focus-visible { outline: 1px solid #f0cd8a; outline-offset: -1px; }
.step-mark { width: 9px; height: 9px; justify-self: center; border-radius: 50%; border: 1px solid rgba(240, 205, 138, 0.45); transform: translateY(-1px); }
.is-next .step-mark { border-color: #f0cd8a; box-shadow: 0 0 0 3px rgba(240, 205, 138, 0.12); }
.is-done .step-mark { border-color: transparent; background: #f0cd8a; box-shadow: 0 0 8px rgba(255, 205, 120, 0.8); }
.is-done .step-name { color: rgba(226, 220, 210, 0.45); text-decoration: line-through; text-decoration-color: rgba(240, 205, 138, 0.35); }
.step-why { grid-column: 2; font-family: var(--serif); font-style: italic; font-size: 14.5px; line-height: 1.25; color: rgba(226, 220, 210, 0.55); }
.is-next .step-why { color: rgba(240, 205, 138, 0.75); }
.visually-hidden { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }

@media (max-width: 760px) {
  a.step { min-height: 44px; }
}
</style>
