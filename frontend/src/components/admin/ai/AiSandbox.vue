<script setup>
import { computed, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import AiAnswer from './AiAnswer.vue'
import { adminApi } from '../../../api/admin.js'
import { CATEGORY_TONE, SOURCE_NOTES, categoryName, modelName, money, seconds, sourceName, tokens } from '../../../views/admin/ai.js'
import { failed } from '../../../views/admin/shared.js'

/**
 * A question to the ИИ-астролог outside the chat: for the demo chart or a real person's, with the
 * saved style or one being tried. The answer is shown as the chat would show it, with everything
 * behind it: the passport, the instructions, the raw text. Nothing reaches the person's conversation.
 */
const props = defineProps({
  data: { type: Object, required: true },
})
const emit = defineEmits(['spent', 'open'])

const route = useRoute()
const LENGTH = 600
const SAMPLES = [
  'Что моя Луна говорит о моих чувствах?',
  'Какие дни этого месяца лучше для важного разговора?',
  'Почему мне трудно начинать новое?',
  'Кто ты?',
  'Напиши код на Python',
]

const saved = (key) => props.data.settings.find((item) => item.key === key)?.value.trim() || props.data.defaults[key]

const form = reactive({
  question: '',
  who: route.query.user ? 'user' : 'demo',
  userId: String(route.query.user || ''),
  model: '',
  trying: false,
  style: saved('ai_style'),
  examples: saved('ai_examples'),
})
const busy = ref(false)
const error = ref('')
const result = ref(null)
const asked = ref('')

const userId = computed(() => (/^\d+$/.test(form.userId.trim()) ? Number(form.userId.trim()) : 0))
const canAsk = computed(() => props.data.ready && form.question.trim() && form.question.length <= LENGTH && !busy.value
  && (form.who === 'demo' || userId.value))

async function ask() {
  if (!canAsk.value) return
  busy.value = true
  error.value = ''
  const body = { question: form.question.trim(), model: form.model }
  if (form.who === 'user') body.user_id = userId.value
  if (form.trying) Object.assign(body, { style: form.style, examples: form.examples })
  try {
    result.value = await adminApi.aiPlayground(body)
    asked.value = body.question
    emit('spent')
  } catch (caught) {
    error.value = caught?.code === 'missing' ? 'Пользователя с таким ID нет' : caught?.code === 'no_birth' ? 'У этого пользователя нет даты рождения — карты нет' : failed(caught)
  } finally {
    busy.value = false
  }
}

function onKey(event) {
  if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) ask()
}
</script>

<template>
  <div class="sb">
    <section v-if="!data.ready" class="adm-panel">
      <p class="sb-off">Песочница спрашивает настоящую модель — сначала сохраните ключ и ID каталога.</p>
      <button type="button" class="adm-btn is-gold" @click="$emit('open', 'settings')">Открыть настройки</button>
    </section>

    <section class="adm-panel">
      <div class="adm-panel-head">
        <h2>Вопрос</h2>
        <p>вызов стоит как обычный ответ и попадает в журнал</p>
      </div>
      <form class="sb-form" @submit.prevent="ask">
        <textarea v-model="form.question" class="adm-input sb-question" :maxlength="LENGTH + 50" placeholder="Спросите как человек в чате…" aria-label="Вопрос" @keydown="onKey" />
        <div class="sb-samples">
          <button v-for="text in SAMPLES" :key="text" type="button" class="sb-chip" @click="form.question = text">{{ text }}</button>
        </div>

        <div class="sb-options">
          <div class="as-field">
            <span class="adm-label">Чья карта</span>
            <div class="adm-seg" role="group" aria-label="Чья карта">
              <button type="button" :aria-pressed="form.who === 'demo'" @click="form.who = 'demo'">Демо: 23 июля 1992, Москва</button>
              <button type="button" :aria-pressed="form.who === 'user'" @click="form.who = 'user'">Пользователь</button>
            </div>
          </div>
          <label v-if="form.who === 'user'" class="adm-label">
            ID пользователя
            <input v-model="form.userId" class="adm-input sb-id" type="text" inputmode="numeric" autocomplete="off" placeholder="например, 42" />
          </label>
          <label class="adm-label">
            Модель
            <select v-model="form.model" class="adm-input">
              <option value="">Как в настройках — {{ modelName(data.models, data.settings.find((item) => item.key === 'ai_model')?.value) }}</option>
              <option v-for="model in data.models" :key="model.id" :value="model.id">{{ model.label }}</option>
            </select>
          </label>
        </div>
        <p v-if="form.who === 'user'" class="adm-note sb-tight">Берутся его карта, небо, пары, память и последние реплики разговора. В его переписку и память ничего не пишется.</p>

        <label class="sb-try">
          <input v-model="form.trying" type="checkbox" />
          Попробовать свой стиль и примеры, не сохраняя
        </label>
        <div v-if="form.trying" class="sb-texts">
          <label class="adm-label">Стиль ответов<textarea v-model="form.style" class="adm-input" maxlength="4000" /></label>
          <label class="adm-label">Примеры<textarea v-model="form.examples" class="adm-input sb-examples" maxlength="6000" /></label>
        </div>

        <div class="sb-send">
          <span class="adm-dim num">{{ form.question.length }} / {{ LENGTH }} · Ctrl+Enter</span>
          <button type="submit" class="adm-btn is-gold" :disabled="!canAsk">{{ busy ? 'Модель думает…' : 'Спросить' }}</button>
        </div>
        <p v-if="error" class="error">{{ error }}</p>
      </form>
    </section>

    <section v-if="result" class="adm-panel" :class="{ 'adm-loading': busy }">
      <div class="adm-panel-head">
        <h2>Ответ</h2>
        <p>{{ asked }}</p>
      </div>
      <div class="sb-meta">
        <span class="adm-badge" :class="result.source === 'ai' ? 'is-ok' : result.source === 'guard' ? 'is-plain' : 'is-bad'" :title="SOURCE_NOTES[result.source]">{{ sourceName(result.source) }}</span>
        <span v-if="result.category" class="adm-badge" :class="CATEGORY_TONE[result.category]">{{ categoryName(result.category) }}</span>
        <span v-if="result.flagged" class="adm-badge is-warn" title="Первый ответ модели не прошёл проверку, ответ взят со второй попытки или заменён шаблоном">отмечен проверкой</span>
        <template v-if="result.model">
          <span class="adm-dim">{{ modelName(data.models, result.model) }}</span>
          <span class="adm-dim num">{{ seconds(result.ms) }}</span>
          <span class="adm-dim num">{{ money(result.cost) }}</span>
          <span class="adm-dim num" title="Токены: вход (из них из кэша) → ответ">{{ tokens(result.prompt) }} ({{ tokens(result.cached) }}) → {{ tokens(result.output) }}</span>
        </template>
      </div>

      <AiAnswer v-if="result.answer" :answer="result.answer" :key-line="result.key" :follow="result.follow" />
      <p v-else class="sb-stub">Модель не дала годного ответа — в чате человек увидел бы ответ шаблона сайта.</p>
      <p v-if="result.error" class="error sb-error">{{ result.error }}</p>
      <p v-if="result.remember?.length" class="sb-remember">
        <span class="adm-label">Запомнил бы о человеке</span>
        <span v-for="fact in result.remember" :key="fact" class="adm-badge is-plain">{{ fact }}</span>
      </p>

      <details v-if="result.passport" class="sb-more">
        <summary>Паспорт: что модель знает о человеке и небе</summary>
        <pre>{{ result.passport }}</pre>
      </details>
      <details v-if="result.rules" class="sb-more">
        <summary>Инструкции модели: правила из кода, стиль и примеры</summary>
        <pre>{{ result.rules }}</pre>
      </details>
      <details v-if="result.raw" class="sb-more">
        <summary>Сырой ответ модели</summary>
        <pre>{{ result.raw }}</pre>
      </details>
    </section>
  </div>
</template>

<style scoped>
.sb { display: grid; gap: 18px; }
.sb-off { margin: 0 0 12px; color: #e6c27a; font-size: 15px; }
.sb-form { display: grid; gap: 14px; }
.sb-question { min-height: 96px; }
.sb-samples { display: flex; flex-wrap: wrap; gap: 6px; margin-top: -6px; }
.sb-chip {
  padding: 5px 12px;
  border: 1px solid var(--panel-line);
  border-radius: 999px;
  background: rgba(255, 240, 210, 0.03);
  color: var(--muted);
  font: inherit;
  font-size: 13px;
  cursor: pointer;
}
.sb-chip:hover { color: var(--ink); border-color: rgba(233, 200, 140, 0.4); }
.sb-options { display: flex; flex-wrap: wrap; align-items: end; gap: 12px 18px; }
.as-field { display: grid; gap: 6px; }
.sb-id { width: 140px; }
.sb-tight { margin: -6px 0 0; }
.sb-try { display: inline-flex; align-items: center; gap: 8px; font-size: 14px; cursor: pointer; justify-self: start; }
.sb-try input { width: 16px; height: 16px; accent-color: var(--gold); }
.sb-texts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.sb-texts textarea { min-height: 200px; }
.sb-send { display: flex; align-items: center; justify-content: flex-end; gap: 14px; }
.sb-send .adm-dim { margin-right: auto; font-size: 13px; }

.sb-meta { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 12px; margin-bottom: 14px; font-size: 13px; }
.sb-stub { margin: 0; color: #e6c27a; font-size: 15px; }
.sb-error { margin: 10px 0 0; font-size: 14px; }
.sb-remember { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin: 14px 0 0; }
.sb-remember .adm-label { margin-right: 4px; }
.sb-more { margin-top: 14px; border-top: 1px solid var(--panel-line); padding-top: 12px; }
.sb-more summary { cursor: pointer; color: var(--muted); font-size: 14px; }
.sb-more summary:hover { color: var(--ink); }
.sb-more pre {
  max-height: 420px;
  margin: 10px 0 0;
  padding: 12px 14px;
  overflow: auto;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.25);
  font-size: 12.5px;
  line-height: 1.5;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

@media (max-width: 900px) {
  .sb-texts { grid-template-columns: minmax(0, 1fr); }
}
</style>
