<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import ChatAnswer from '../../components/cabinet/ChatAnswer.vue'
import PanelHead from '../../components/cabinet/PanelHead.vue'
import ReadingText from '../../components/cabinet/ReadingText.vue'
import { useChat } from '../../composables/useChat.js'
import { useSky } from '../../composables/useSky.js'
import { usePrices } from '../../utils/prices.js'
import { markStep } from '../../utils/newcomer.js'

/**
 * The conversation with the ИИ-астролог. It speaks in italic serif, the person in the plain face;
 * the questions to start with come from the person's own chart, the ones to ask next from its last
 * answer. A new answer is printed out. Without «Небосвод» there are two trial questions, then the
 * field gives way to the invitation; with it, a number of questions a day. After three turns away
 * from the chart the conversation rests for a few minutes.
 */

const props = defineProps({
  user: { type: Object, required: true },
})

const { chat, load, ask } = useChat()
const { mark } = useSky()
const { sky: skyPrice } = usePrices()

const LENGTH = 600
const STAR = 'M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z'

const draft = ref('')
const field = ref(null)
const body = ref(null)

const hasBirth = computed(() => Boolean(props.user.birth))
const locked = computed(() => chat.left === 0)
const empty = computed(() => chat.items.length === 0)

/* ---- The pause after turns away from the chart, and the day's questions ---- */

const clock = new Intl.DateTimeFormat('ru-RU', { hour: '2-digit', minute: '2-digit' })
const now = ref(Date.now())
let timer = 0
// The field comes back by itself when the pause is over.
watch(() => chat.pauseUntil, (until) => {
  clearTimeout(timer)
  now.value = Date.now()
  const wait = until ? new Date(until).getTime() - Date.now() : 0
  if (wait > 0) timer = setTimeout(() => { now.value = Date.now() }, Math.min(wait + 500, 2 ** 31 - 1))
}, { immediate: true })
onBeforeUnmount(() => clearTimeout(timer))
const paused = computed(() => Boolean(chat.pauseUntil) && new Date(chat.pauseUntil).getTime() > now.value)
const dayOver = computed(() => !locked.value && chat.todayLeft === 0)
const resting = computed(() => paused.value || dayOver.value)

const questionsWord = (n) => {
  const tens = n % 100
  const ones = n % 10
  if (tens > 10 && tens < 20) return 'вопросов'
  return ones === 1 ? 'вопрос' : ones >= 2 && ones <= 4 ? 'вопроса' : 'вопросов'
}
const leftWord = (n) => (n % 10 === 1 && n % 100 !== 11 ? 'остался' : 'осталось')
const perDay = computed(() => `${chat.daily} ${questionsWord(chat.daily)} в день`)

/** The questions to ask next: the last answer's own, or else the chart's suggestions not asked yet. */
const lastAnswer = computed(() => {
  const item = chat.items.at(-1)
  return item && item.role !== 'user' && item.reading?.kind === 'talk' && item.reading.follow?.length ? item : null
})
const suggestions = computed(() => {
  const asked = new Set(chat.items.filter((item) => item.role === 'user').map((item) => item.text))
  return chat.suggestions.filter((text) => !asked.has(text))
})
const trialNote = computed(() => {
  if (chat.left == null || chat.left === 0) return ''
  return chat.left === chat.trial
    ? `${chat.trial} вопроса в подарок — спросите о самом важном.`
    : 'Остался один вопрос в подарок.'
})
/** With «Небосвод», the day's count shows only when it runs low. */
const dayNote = computed(() => {
  const left = chat.todayLeft
  if (chat.left != null || left == null || left === 0 || left > 3) return ''
  return `Сегодня ${leftWord(left)} ${left} ${questionsWord(left)} из ${chat.daily}.`
})

/* ---- The answer being printed ---- */

const typing = ref(null)
watch(() => chat.fresh, (id) => {
  typing.value = id
})
// While it waits, the line under the star changes now and then: the answer takes a few seconds.
const WAITING = ['ИИ-астролог смотрит на ваше небо…', 'Сверяет вопрос с вашей картой…', 'Подбирает слова…']
const waiting = ref(0)
let waitingTimer = 0
watch(() => chat.sending, (sending) => {
  clearInterval(waitingTimer)
  waiting.value = 0
  if (sending) waitingTimer = setInterval(() => { waiting.value = Math.min(waiting.value + 1, WAITING.length - 1) }, 2600)
})
onBeforeUnmount(() => clearInterval(waitingTimer))

onMounted(() => {
  if (hasBirth.value) load().then(() => scrollDown(false))
})

function paragraphs(text) {
  return text.split('\n\n')
}

/** The conversation scrolls above the field: the newest message is brought to its bottom. */
function scrollDown(smooth = true) {
  nextTick(() => {
    const scroller = body.value
    if (scroller) scroller.scrollTo({ top: scroller.scrollHeight, behavior: smooth ? 'smooth' : 'auto' })
  })
}
watch(() => [chat.items.length, chat.sending], () => scrollDown())

/** As the answer prints, the view follows it, unless the person has scrolled up to read. */
function follow() {
  const scroller = body.value
  if (scroller && scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight < 80) scroller.scrollTop = scroller.scrollHeight
}

async function send(text = draft.value) {
  const question = text.trim()
  if (!question || chat.sending || locked.value || resting.value) return
  if (question.length > LENGTH) {
    chat.error = `Вопрос слишком длинный — сократите его до ${LENGTH} знаков`
    return
  }
  const typed = text === draft.value
  if (typed) draft.value = ''
  nextTick(fit)
  const ok = await ask(question)
  if (ok) {
    // The person's star answers on the sky as the reply arrives.
    mark.flash += 1
    markStep(props.user.id, 'chat')
  } else if (typed && !draft.value) {
    draft.value = question
  }
  if (!locked.value && !resting.value) nextTick(() => field.value?.focus({ preventScroll: true }))
}

function onKey(event) {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault()
    send()
  }
}

/** The field grows with the question, up to five lines. */
function fit() {
  const element = field.value
  if (!element) return
  element.style.height = 'auto'
  element.style.height = `${Math.min(element.scrollHeight, 128)}px`
}
</script>

<template>
  <div class="chat-panel" :class="{ 'is-talk': hasBirth && chat.status === 'ready' }">
    <template v-if="!hasBirth">
      <PanelHead lead="ИИ-астролог отвечает по вашей карте, а карте нужна дата рождения.">
        Разговор <em>с ИИ-астрологом</em>
      </PanelHead>
      <RouterLink class="add-birth" :to="{ name: 'cabinet-birth' }">
        <svg viewBox="0 0 20 20" aria-hidden="true"><path :d="STAR" /></svg>
        Добавить дату рождения
      </RouterLink>
    </template>

    <p v-else-if="chat.status === 'error'" class="error">{{ chat.message }}</p>
    <p v-else-if="chat.status !== 'ready'" class="loading">Открываем разговор…</p>

    <template v-else>
      <div ref="body" class="chat-body">
        <PanelHead :lead="empty ? 'Спросите о своей карте простыми словами — ИИ-астролог ответит с опорой на ваше небо.' : ''">
          Разговор <em>с ИИ-астрологом</em>
        </PanelHead>

        <ul v-if="empty && !locked && suggestions.length" class="starters" aria-label="С чего начать">
          <li v-for="text in suggestions" :key="text">
            <button type="button" class="starter" :disabled="chat.sending" @click="send(text)">
              <svg viewBox="0 0 20 20" aria-hidden="true"><path :d="STAR" /></svg>
              {{ text }}
            </button>
          </li>
        </ul>

        <ol v-if="!empty" class="thread" role="log" aria-label="Разговор">
          <li v-for="item in chat.items" :key="item.id" class="message" :class="[item.role === 'user' ? 'from-you' : 'from-astrologer', { 'has-reading': item.reading && item.reading.kind !== 'talk' }]">
            <span class="visually-hidden">{{ item.role === 'user' ? 'Вы:' : 'ИИ-астролог:' }}</span>
            <ChatAnswer
              v-if="item.reading?.kind === 'talk'"
              :reading="item.reading"
              :typing="item.id === typing"
              :followable="item === lastAnswer && !locked && !resting"
              :disabled="chat.sending"
              @ask="send"
              @grow="follow"
            />
            <ReadingText v-else-if="item.reading" :reading="item.reading" compact />
            <p v-for="(paragraph, index) in paragraphs(item.text)" v-else :key="index">{{ paragraph }}</p>
          </li>
          <li v-if="chat.sending" class="message waiting" aria-live="polite">
            <svg class="waiting-star" viewBox="0 0 20 20" aria-hidden="true"><path :d="STAR" /></svg>
            <Transition name="waiting" mode="out-in"><span :key="waiting">{{ WAITING[waiting] }}</span></Transition>
          </li>
        </ol>
      </div>

      <div class="composer-wrap">
        <div v-if="locked" class="unlock">
          <p class="unlock-note">Вопросы в подарок позади — надеемся, ИИ-астролог был вам полезен. В «Небосводе» — {{ perDay }}, а вместе с ними загораются полные прогнозы и звёздный календарь.</p>
          <RouterLink class="unlock-cta" v-seen="'sky:chat'" data-track="sky:chat" :to="{ name: 'cabinet-sky' }">
            <svg viewBox="0 0 20 20" aria-hidden="true"><path :d="STAR" /></svg>
            Зажечь Небосвод — {{ skyPrice }}
          </RouterLink>
        </div>

        <div v-else-if="paused" class="rest" role="status">
          <p class="rest-note">
            Небольшая пауза: ИИ-астролог говорит только о вашей карте и небе. Разговор продолжится
            в {{ clock.format(new Date(chat.pauseUntil)) }}.
          </p>
        </div>

        <div v-else-if="dayOver" class="rest" role="status">
          <p class="rest-note">На сегодня вопросы закончились: {{ perDay }}, новые появятся в полночь по Москве. А пока — что небо готовит на сегодня.</p>
          <RouterLink class="rest-link" :to="{ name: 'cabinet-forecast' }">Открыть прогноз на день</RouterLink>
        </div>

        <template v-else>
          <ul v-if="!empty && !lastAnswer && suggestions.length" class="more" aria-label="Можно спросить" data-no-swipe>
            <li v-for="text in suggestions" :key="text">
              <button type="button" class="more-chip" :disabled="chat.sending" @click="send(text)">{{ text }}</button>
            </li>
          </ul>
          <form class="composer" @submit.prevent="send()">
            <label class="visually-hidden" for="chat-question">Ваш вопрос ИИ-астрологу</label>
            <textarea
              id="chat-question"
              ref="field"
              v-model="draft"
              rows="1"
              :maxlength="LENGTH + 50"
              placeholder="Спросите о своём небе…"
              @input="fit"
              @keydown="onKey"
            />
            <button type="submit" class="send" :disabled="!draft.trim() || chat.sending" aria-label="Спросить">
              <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 13V3M3.5 7.5L8 3l4.5 4.5" /></svg>
            </button>
          </form>
          <p v-if="chat.error" class="error" role="alert">{{ chat.error }}</p>
          <p v-else-if="draft.length > LENGTH - 100" class="hint" :class="{ 'is-over': draft.length > LENGTH }">{{ draft.length }} / {{ LENGTH }}</p>
          <p v-else-if="trialNote" class="hint">
            {{ trialNote }}
            <RouterLink class="hint-link" v-seen="'sky:chat-hint'" data-track="sky:chat-hint" :to="{ name: 'cabinet-sky' }">{{ perDay }} — в «Небосводе»</RouterLink>
          </p>
          <p v-else-if="dayNote" class="hint">{{ dayNote }}</p>
        </template>
      </div>
    </template>
  </div>
</template>

<style scoped>
/* In the conversation only the messages scroll; the field stays under them. */
.chat-panel { display: grid; gap: 16px; align-content: start; }
.chat-panel.is-talk { grid-template-rows: minmax(0, 1fr) auto; height: 100%; }
.chat-body {
  display: grid;
  gap: 16px;
  align-content: start;
  min-height: 0;
  margin: 0 -10px;
  padding: 0 10px 4px;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-width: thin;
  scrollbar-color: rgba(240, 205, 138, 0.25) transparent;
  /* The older messages dissolve under the panel's top edge. */
  -webkit-mask-image: linear-gradient(180deg, transparent, #000 14px);
  mask-image: linear-gradient(180deg, transparent, #000 14px);
}

.starters { display: grid; gap: 8px; margin: 0; padding: 0; list-style: none; }
.starter {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 11px 14px;
  border-radius: 14px;
  border: 1px solid rgba(240, 210, 150, 0.16);
  background: rgba(255, 240, 210, 0.04);
  color: #efe7d8;
  font: inherit;
  font-size: 14px;
  line-height: 1.35;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.25s ease, background 0.25s ease;
}
.starter svg { flex: none; width: 9px; height: 9px; fill: #f0cd8a; opacity: 0.8; }
.starter:hover:not(:disabled) { border-color: rgba(240, 205, 138, 0.45); background: rgba(255, 210, 126, 0.07); }
.starter:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 2px; }
.starter:disabled { opacity: 0.5; cursor: default; }

.thread { display: grid; gap: 14px; margin: 0; padding: 0; list-style: none; }
.message p { margin: 0; }
.message p + p { margin-top: 10px; }
/* The person's words: the plain face, in a soft bubble to the right. */
.from-you {
  font-family: var(--book);
  justify-self: end;
  max-width: 86%;
  padding: 9px 14px;
  border-radius: 16px 16px 4px 16px;
  background: rgba(255, 240, 210, 0.08);
  font-size: 14.5px;
  line-height: 1.45;
  color: #f2ebdf;
  white-space: pre-line;
  overflow-wrap: anywhere;
}
.from-you:not(:first-child) { margin-top: 6px; }
/* The astrologer's: italic serif on the glass itself, under a gold hairline. */
.from-astrologer {
  padding-left: 14px;
  border-left: 1px solid rgba(240, 205, 138, 0.35);
  font-family: var(--serif);
  font-style: italic;
  font-size: 17px;
  line-height: 1.45;
  color: rgba(242, 232, 214, 0.92);
}
/* An answer in parts carries its own gold bar and labels, as the readings do. */
.from-astrologer.has-reading { padding-left: 0; border-left: 0; font-family: inherit; font-style: normal; }
.from-astrologer.has-reading + .from-you { margin-top: 10px; }
.waiting {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-left: 14px;
  font-family: var(--serif);
  font-style: italic;
  font-size: 16px;
  color: rgba(240, 205, 138, 0.85);
}
.waiting-star { width: 12px; height: 12px; fill: #f0cd8a; animation: twinkle 1.6s ease-in-out infinite; }

.composer-wrap { display: grid; gap: 8px; }
.more { display: flex; gap: 6px; margin: 0 -10px; padding: 0 10px 2px; overflow-x: auto; list-style: none; scrollbar-width: none; }
.more::-webkit-scrollbar { display: none; }
.more-chip {
  flex: none;
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid rgba(240, 210, 150, 0.18);
  background: rgba(255, 240, 210, 0.04);
  color: rgba(239, 231, 216, 0.85);
  font: inherit;
  font-size: 12.5px;
  white-space: nowrap;
  cursor: pointer;
  transition: border-color 0.25s ease, color 0.25s ease;
}
.more-chip:hover:not(:disabled) { border-color: rgba(240, 205, 138, 0.45); color: #f0cd8a; }
.more-chip:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 2px; }
.more-chip:disabled { opacity: 0.5; cursor: default; }

.composer {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 6px 6px 6px 16px;
  border-radius: 22px;
  border: 1px solid rgba(240, 210, 150, 0.22);
  background: rgba(255, 240, 210, 0.05);
  transition: border-color 0.25s ease;
}
.composer:focus-within { border-color: rgba(240, 205, 138, 0.55); }
.composer textarea {
  flex: 1;
  min-width: 0;
  max-height: 128px;
  padding: 7px 0;
  border: 0;
  background: none;
  color: #f2ebdf;
  font: inherit;
  font-size: 15px;
  line-height: 1.4;
  resize: none;
  outline: none;
}
.composer textarea::placeholder { color: rgba(226, 220, 210, 0.42); }
.send {
  display: grid;
  flex: none;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 0;
  border-radius: 50%;
  background: linear-gradient(180deg, #f4dba6, #dcb36c);
  color: #2b1d0b;
  cursor: pointer;
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.send svg { width: 14px; height: 14px; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
.send:hover:not(:disabled) { transform: translateY(-1px); }
.send:focus-visible { outline: 2px solid #ffe2a8; outline-offset: 2px; }
.send:disabled { opacity: 0.35; cursor: default; }

.hint { margin: 0; padding-left: 16px; font-size: 12px; color: rgba(226, 220, 210, 0.5); }
.hint.is-over { color: #f2a48c; }
.error { margin: 0; font-size: 13.5px; color: #f2a48c; }
.loading { margin: 0; font-family: var(--serif); font-style: italic; font-size: 17px; color: rgba(242, 228, 200, 0.75); }

.unlock { display: grid; gap: 12px; justify-items: start; }
.rest { display: grid; gap: 8px; justify-items: start; padding: 12px 16px; border-radius: 18px; border: 1px dashed rgba(240, 210, 150, 0.22); }
.rest-note { margin: 0; font-size: 13.5px; line-height: 1.5; color: rgba(239, 231, 216, 0.8); }
.rest-link { color: #f0cd8a; font-size: 13.5px; text-decoration: underline; text-decoration-color: rgba(240, 205, 138, 0.35); text-underline-offset: 3px; }
.rest-link:hover { text-decoration-color: currentColor; }
.waiting-enter-active, .waiting-leave-active { transition: opacity 0.35s ease; }
.waiting-enter-from, .waiting-leave-to { opacity: 0; }
.hint-link { margin-left: 4px; color: #f0cd8a; text-decoration: underline; text-decoration-color: rgba(240, 205, 138, 0.35); text-underline-offset: 3px; }
.hint-link:hover { text-decoration-color: currentColor; }
.unlock-note { margin: 0; font-size: 13.5px; line-height: 1.5; color: rgba(233, 194, 124, 0.8); }
.unlock-cta, .add-birth {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 11px 20px;
  border-radius: 999px;
  background: linear-gradient(180deg, #f4dba6, #dcb36c);
  color: #2b1d0b;
  font-size: 14.5px;
  font-weight: 600;
  text-decoration: none;
  box-shadow: 0 8px 26px rgba(230, 170, 80, 0.22);
  transition: box-shadow 0.25s ease, transform 0.25s ease;
}
.add-birth { justify-self: start; align-self: flex-start; }
.unlock-cta svg, .add-birth svg { width: 10px; height: 10px; fill: #5a3d12; }
.unlock-cta:hover, .add-birth:hover { box-shadow: 0 10px 34px rgba(230, 170, 80, 0.38); transform: translateY(-1px); }
.unlock-cta:focus-visible, .add-birth:focus-visible { outline: 2px solid #ffe2a8; outline-offset: 3px; }

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}

@keyframes twinkle {
  0%, 100% { opacity: 0.35; transform: scale(0.8); filter: drop-shadow(0 0 2px rgba(255, 200, 110, 0.4)); }
  50% { opacity: 1; transform: scale(1.1); filter: drop-shadow(0 0 7px rgba(255, 200, 110, 0.9)); }
}

@media (max-width: 760px) {
  .from-astrologer { font-size: 16px; }
  .send { width: 40px; height: 40px; }
  .composer textarea { font-size: 16px; }
  .starter { min-height: 44px; }
  .more-chip { min-height: 36px; }
}
@media (prefers-reduced-motion: reduce) {
  .waiting-star { animation: none; opacity: 1; }
}
</style>
