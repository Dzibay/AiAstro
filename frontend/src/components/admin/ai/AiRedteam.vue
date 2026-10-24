<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import AiAnswer from './AiAnswer.vue'
import { adminApi } from '../../../api/admin.js'
import { CATEGORY_TONE, SOURCE_NOTES, answerCost, categoryName, modelName, money, seconds, sourceName } from '../../../views/admin/ai.js'
import { failed, fmt } from '../../../views/admin/shared.js'

/**
 * The provocation test: questions that try to lead the ИИ-астролог away — a new role, its
 * instructions, code, politics, frights, rudeness, a cry for help — each through the whole path on
 * the demo chart. Held: the topic is one of the expected, the answer passed the checks and nothing
 * forbidden got into it. Worth running after a change of the model, the style or the examples.
 */
const props = defineProps({
  data: { type: Object, required: true },
})
const emit = defineEmits(['spent', 'open'])

// Three at a time: quick enough, and gentle with the provider's limits.
const AT_ONCE = 3

const list = ref([])
const error = ref('')
const model = ref('')
const results = reactive({})
const running = ref(false)
const stopping = ref(false)
const open = ref(-1)
const onlyFailed = ref(false)
let alive = true

onMounted(async () => {
  try {
    list.value = (await adminApi.aiRedteamList()).items
  } catch (caught) {
    error.value = failed(caught)
  }
})
onBeforeUnmount(() => {
  alive = false
})

const savedModel = computed(() => props.data.settings.find((item) => item.key === 'ai_model')?.value || '')
const chosen = computed(() => props.data.models.find((item) => item.id === (model.value || savedModel.value)))
const estimate = computed(() => answerCost(chosen.value) * list.value.length)

const done = computed(() => Object.values(results).filter((item) => item.state === 'done' || item.state === 'error').length)
const passed = computed(() => Object.values(results).filter((item) => item.state === 'done' && item.passed).length)
const failedCount = computed(() => Object.values(results).filter((item) => item.state === 'error' || (item.state === 'done' && !item.passed)).length)
const spent = computed(() => Object.values(results).reduce((sum, item) => sum + (item.cost || 0), 0))
const rows = computed(() => list.value.filter((row) => {
  if (!onlyFailed.value) return true
  const result = results[row.index]
  return result && (result.state === 'error' || (result.state === 'done' && !result.passed))
}))

async function runOne(index) {
  results[index] = { state: 'running' }
  try {
    const answer = await adminApi.aiRedteam(index, model.value)
    if (alive) results[index] = { state: 'done', ...answer }
  } catch (caught) {
    if (alive) results[index] = { state: 'error', error: failed(caught) }
  }
}

async function runAll() {
  if (running.value) return
  running.value = true
  stopping.value = false
  open.value = -1
  for (const key of Object.keys(results)) delete results[key]
  const queue = list.value.map((row) => row.index)
  for (const index of queue) results[index] = { state: 'waiting' }
  const worker = async () => {
    while (queue.length && !stopping.value && alive) await runOne(queue.shift())
  }
  await Promise.all(Array.from({ length: AT_ONCE }, worker))
  for (const index of queue) delete results[index]
  running.value = false
  if (alive) emit('spent')
}

async function runAgain(index) {
  await runOne(index)
  emit('spent')
}

const STATE = {
  waiting: { label: 'в очереди', badge: 'is-plain' },
  running: { label: 'идёт…', badge: 'is-plain' },
  error: { label: 'ошибка', badge: 'is-bad' },
}
function state(index) {
  const result = results[index]
  if (!result) return null
  if (result.state === 'done') return result.passed ? { label: 'выдержал', badge: 'is-ok' } : { label: 'не выдержал', badge: 'is-bad' }
  return STATE[result.state]
}
</script>

<template>
  <div class="rt">
    <section v-if="!data.ready" class="adm-panel">
      <p class="rt-off">Провокации идут через настоящую модель — сначала сохраните ключ и ID каталога.</p>
      <button type="button" class="adm-btn is-gold" @click="$emit('open', 'settings')">Открыть настройки</button>
    </section>

    <section class="adm-panel">
      <div class="adm-panel-head">
        <h2>Проверка на провокации</h2>
        <p>{{ list.length }} вопросов на демо-карте</p>
      </div>
      <p class="adm-note">
        Каждый вопрос проходит весь путь, как в чате: код, модель, проверку ответа. «Выдержал» — тема распознана верно,
        ответ прошёл проверку и в нём нет запретного. Прогоняйте после смены модели, стиля или примеров.
      </p>
      <div class="rt-controls">
        <label class="adm-label">
          Модель
          <select v-model="model" class="adm-input" :disabled="running">
            <option value="">Как в настройках — {{ modelName(data.models, savedModel) }}</option>
            <option v-for="item in data.models" :key="item.id" :value="item.id">{{ item.label }}</option>
          </select>
        </label>
        <button v-if="!running" type="button" class="adm-btn is-gold" :disabled="!data.ready || !list.length" @click="runAll">
          Прогнать все — ≈ {{ money(estimate) }}
        </button>
        <button v-else type="button" class="adm-btn" :disabled="stopping" @click="stopping = true">{{ stopping ? 'Останавливаем…' : 'Остановить' }}</button>
      </div>

      <div v-if="done || running" class="rt-summary">
        <div class="rt-progress"><i :style="{ width: `${list.length ? (done / list.length) * 100 : 0}%` }" /></div>
        <p>
          <strong class="num">{{ passed }}</strong> из {{ done }} выдержали
          <span v-if="failedCount" class="rt-bad">· не выдержали: {{ failedCount }}</span>
          <span class="adm-dim">· потрачено {{ money(spent) }}</span>
          <span v-if="running" class="adm-dim">· готово {{ done }} из {{ list.length }}</span>
        </p>
        <label v-if="failedCount" class="rt-only">
          <input v-model="onlyFailed" type="checkbox" />
          Только не выдержанные
        </label>
      </div>
    </section>

    <p v-if="error" class="error">{{ error }}</p>

    <section v-if="list.length" class="adm-panel rt-list">
      <ol>
        <li v-for="row in rows" :key="row.index" :class="{ 'is-open': open === row.index }">
          <button type="button" class="rt-row" :aria-expanded="open === row.index" :disabled="!results[row.index] || results[row.index].state !== 'done' && results[row.index].state !== 'error'" @click="open = open === row.index ? -1 : row.index">
            <span class="rt-n num">{{ row.index + 1 }}</span>
            <span class="rt-q">{{ row.question }}</span>
            <span class="rt-expect">
              <span v-for="category in row.expect" :key="category" class="rt-tag">{{ categoryName(category) }}</span>
            </span>
            <span class="rt-state">
              <span v-if="state(row.index)" class="adm-badge" :class="state(row.index).badge">{{ state(row.index).label }}</span>
            </span>
          </button>
          <div v-if="open === row.index && results[row.index]" class="rt-detail">
            <template v-if="results[row.index].state === 'done'">
              <div class="rt-meta">
                <span class="adm-badge" :class="CATEGORY_TONE[results[row.index].category]">{{ categoryName(results[row.index].category) }}</span>
                <span class="adm-badge is-plain" :title="SOURCE_NOTES[results[row.index].source]">{{ sourceName(results[row.index].source) }}</span>
                <span v-if="results[row.index].flagged" class="adm-badge is-warn">отмечен проверкой</span>
                <span class="adm-dim num">{{ seconds(results[row.index].ms) }} · {{ money(results[row.index].cost) }}</span>
              </div>
              <p v-if="!results[row.index].expect.includes(results[row.index].category)" class="rt-why">
                Ждали тему: {{ results[row.index].expect.map(categoryName).join(' или ') }}.
              </p>
              <p v-if="results[row.index].leaked.length" class="rt-why">В ответ попало запретное: {{ results[row.index].leaked.join(', ') }}.</p>
              <AiAnswer v-if="results[row.index].answer" :answer="results[row.index].answer" :key-line="results[row.index].key" :follow="results[row.index].follow" />
              <p v-else class="rt-why">Годного ответа нет — в чате ответил бы шаблон сайта.</p>
              <p v-if="results[row.index].error" class="error rt-error">{{ results[row.index].error }}</p>
            </template>
            <p v-else class="error rt-error">{{ results[row.index].error }}</p>
            <button type="button" class="text-button" :disabled="running" @click="runAgain(row.index)">Прогнать ещё раз</button>
          </div>
        </li>
      </ol>
      <p v-if="!rows.length" class="adm-empty">Все выдержали</p>
      <p class="adm-note rt-foot">Вопросов всего: {{ fmt.count(list.length) }}. Ответы сервиса (кризис, смена роли, брань) модель не вызывают и ничего не стоят.</p>
    </section>
  </div>
</template>

<style scoped>
.rt { display: grid; gap: 18px; }
.rt-off { margin: 0 0 12px; color: #e6c27a; font-size: 15px; }
.rt-controls { display: flex; flex-wrap: wrap; align-items: end; gap: 12px 16px; }
.rt-controls .adm-label { min-width: 260px; }
.rt-summary { display: grid; gap: 8px; margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--panel-line); }
.rt-summary p { margin: 0; font-size: 15px; }
.rt-summary strong { font-size: 20px; }
.rt-bad { color: var(--danger); }
.rt-progress { height: 8px; border-radius: 999px; background: rgba(0, 0, 0, 0.3); overflow: hidden; }
.rt-progress i { display: block; height: 100%; border-radius: 999px; background: var(--gold); transition: width 0.3s ease; }
.rt-only { display: inline-flex; align-items: center; gap: 8px; font-size: 14px; cursor: pointer; justify-self: start; }
.rt-only input { width: 16px; height: 16px; accent-color: var(--gold); }

.rt-list { padding: 8px 10px; }
.rt-list ol { margin: 0; padding: 0; list-style: none; }
.rt-list li { border-bottom: 1px solid var(--panel-line); }
.rt-list li:last-child { border-bottom: 0; }
.rt-row {
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr) minmax(0, 260px) 120px;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 11px 12px;
  border: 0;
  border-radius: 10px;
  background: none;
  color: var(--ink);
  font: inherit;
  font-size: 15px;
  text-align: left;
  cursor: pointer;
}
.rt-row:disabled { cursor: default; }
.rt-row:not(:disabled):hover, .is-open .rt-row { background: rgba(244, 239, 230, 0.04); }
.rt-n { color: var(--soft); font-size: 13px; }
.rt-q { overflow-wrap: anywhere; }
.rt-expect { display: flex; flex-wrap: wrap; gap: 4px; }
.rt-tag { padding: 1px 8px; border-radius: 999px; background: rgba(255, 240, 210, 0.06); color: var(--soft); font-size: 12px; }
.rt-state { justify-self: end; }
.rt-detail { display: grid; gap: 10px; justify-items: start; padding: 4px 12px 16px 54px; }
.rt-detail > * { max-width: 100%; }
.rt-meta { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 12px; font-size: 13px; }
.rt-why { margin: 0; color: #e6c27a; font-size: 14px; }
.rt-error { margin: 0; font-size: 14px; }
.rt-foot { margin: 12px 12px 6px; font-size: 13px; }

@media (max-width: 900px) {
  .rt-row { grid-template-columns: 26px minmax(0, 1fr) auto; }
  .rt-expect { grid-column: 2; grid-row: 2; }
  .rt-detail { padding-left: 12px; }
}
</style>
