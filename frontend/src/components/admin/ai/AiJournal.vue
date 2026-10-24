<script setup>
import { onMounted, ref, watch } from 'vue'
import { adminApi } from '../../../api/admin.js'
import { CATEGORY_TONE, KINDS, SOURCE_NOTES, categoryName, modelName, money, seconds, sourceName, tokens } from '../../../views/admin/ai.js'
import { failed, fmt } from '../../../views/admin/shared.js'

/**
 * Every call of the ИИ-астролог, newest first: the chat, the connection checks, the sandbox and the
 * provocations — who asked, the topic, who answered, the tokens, the price, the time and what went wrong.
 * A row opens to the question and the answer.
 */
defineProps({
  models: { type: Array, required: true },
})

const ONLY = [
  { id: '', label: 'Все' },
  { id: 'flagged', label: 'Отмечены проверкой' },
  { id: 'errors', label: 'С ошибкой' },
  { id: 'guard', label: 'Ответ сервиса' },
]

const kind = ref('')
const only = ref('')
const items = ref([])
const more = ref(false)
const loading = ref(false)
const error = ref('')
const open = ref(0)
let asked = 0

async function load(append = false) {
  const ticket = ++asked
  loading.value = true
  error.value = ''
  try {
    const before = append && items.value.length ? items.value[items.value.length - 1].id : 0
    const data = await adminApi.aiRuns({ kind: kind.value, only: only.value, before })
    if (ticket !== asked) return
    items.value = append ? [...items.value, ...data.items] : data.items
    more.value = data.more
  } catch (caught) {
    if (ticket === asked) error.value = failed(caught)
  } finally {
    if (ticket === asked) loading.value = false
  }
}
watch([kind, only], () => {
  open.value = 0
  load()
})
onMounted(load)

function toggle(id) {
  open.value = open.value === id ? 0 : id
}
</script>

<template>
  <section class="adm-panel">
    <div class="adm-panel-head">
      <h2>Журнал вызовов</h2>
      <p>каждое обращение к модели и каждый ответ сервиса</p>
    </div>
    <div class="jr-filters">
      <div class="adm-seg" role="group" aria-label="Откуда вызов">
        <button type="button" :aria-pressed="kind === ''" @click="kind = ''">Все</button>
        <button v-for="(label, id) in KINDS" :key="id" type="button" :aria-pressed="kind === id" @click="kind = id">{{ label }}</button>
      </div>
      <div class="adm-seg" role="group" aria-label="Какие">
        <button v-for="item in ONLY" :key="item.id" type="button" :aria-pressed="only === item.id" @click="only = item.id">{{ item.label }}</button>
      </div>
    </div>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-else-if="!items.length && !loading" class="adm-empty">Вызовов пока нет</p>

    <table v-if="items.length" class="adm-table jr-table" :class="{ 'adm-loading': loading }">
      <thead>
        <tr>
          <th>Когда</th>
          <th>Кто</th>
          <th>Тема</th>
          <th>Ответил</th>
          <th>Модель</th>
          <th class="num">Токены</th>
          <th class="num">Цена</th>
          <th class="num">Время</th>
        </tr>
      </thead>
      <tbody>
        <template v-for="row in items" :key="row.id">
          <tr class="is-link" :class="{ 'is-on': open === row.id }" tabindex="0" :aria-expanded="open === row.id" @click="toggle(row.id)" @keydown.enter.prevent="toggle(row.id)">
            <td data-label="Когда" class="adm-seen">{{ fmt.moment(row.at) }}</td>
            <td data-label="Кто" class="wide">
              <span class="adm-who">
                <strong>
                  <RouterLink v-if="row.user_id" :to="{ name: 'admin-user', params: { id: row.user_id } }" @click.stop>{{ row.email || `#${row.user_id}` }}</RouterLink>
                  <template v-else>—</template>
                </strong>
                <span>{{ KINDS[row.kind] || row.kind }}</span>
              </span>
            </td>
            <td data-label="Тема">
              <span v-if="row.category" class="adm-badge" :class="CATEGORY_TONE[row.category]">{{ categoryName(row.category) }}</span>
              <span v-else class="adm-dim">—</span>
            </td>
            <td data-label="Ответил">
              <span class="jr-flags">
                <span v-if="row.source" class="adm-badge" :class="row.source === 'ai' ? 'is-ok' : row.source === 'guard' ? 'is-plain' : 'is-bad'" :title="SOURCE_NOTES[row.source]">{{ sourceName(row.source) }}</span>
                <span v-if="row.flagged" class="adm-badge is-warn" title="Первый ответ модели не прошёл проверку">проверка</span>
                <span v-if="row.error" class="adm-badge is-bad" :title="row.error">ошибка</span>
              </span>
            </td>
            <td data-label="Модель" class="adm-dim">{{ row.model ? modelName(models, row.model) : '—' }}</td>
            <td data-label="Токены" class="num adm-dim" title="вход (из кэша) → ответ">
              <template v-if="row.prompt || row.output">{{ tokens(row.prompt) }} ({{ tokens(row.cached) }}) → {{ tokens(row.output) }}</template>
              <template v-else>—</template>
            </td>
            <td data-label="Цена" class="num">{{ row.cost ? money(row.cost) : '—' }}</td>
            <td data-label="Время" class="num adm-dim">{{ seconds(row.ms) }}</td>
          </tr>
          <tr v-if="open === row.id" class="jr-open">
            <td colspan="8" class="wide">
              <div class="jr-detail">
                <p v-if="row.question"><span class="adm-label">Вопрос</span>{{ row.question }}</p>
                <p v-if="row.answer"><span class="adm-label">Ответ</span>{{ row.answer }}</p>
                <p v-if="!row.question && !row.answer" class="adm-dim">Текста нет — так бывает у проверки связи и у ответов, удалённых вместе с перепиской.</p>
                <p v-if="row.error" class="error">{{ row.error }}</p>
              </div>
            </td>
          </tr>
        </template>
      </tbody>
    </table>

    <button v-if="more" type="button" class="adm-more" :disabled="loading" @click="load(true)">Показать ещё</button>
  </section>
</template>

<style scoped>
.jr-filters { display: flex; flex-wrap: wrap; gap: 10px 14px; margin-bottom: 16px; }
.jr-table a { color: var(--ink); text-decoration: none; }
.jr-table a:hover { color: var(--gold); }
.jr-flags { display: inline-flex; flex-wrap: wrap; gap: 4px; }
.jr-open td { padding-top: 0; }
.jr-detail { display: grid; gap: 10px; padding: 4px 4px 8px; }
.jr-detail p { margin: 0; font-size: 14px; line-height: 1.55; white-space: pre-wrap; overflow-wrap: anywhere; }
.jr-detail .adm-label { display: block; margin-bottom: 2px; }
</style>
