<script setup>
import { computed, reactive, ref } from 'vue'
import AiAnswer from './AiAnswer.vue'
import { adminApi } from '../../../api/admin.js'
import { errorText } from '../../../api/http.js'
import { useToast } from '../../../composables/useToast.js'
import { MODES, answerCost, modelName, money, seconds } from '../../../views/admin/ai.js'
import { failed } from '../../../views/admin/shared.js'

/**
 * The settings of the ИИ-астролог. Each field is saved apart and acts at once (the server reads
 * them again within a minute). The style and the examples are the admin's; the safety rules are
 * the code's and are only shown here.
 */
const props = defineProps({
  data: { type: Object, required: true },
})
const emit = defineEmits(['saved'])

const { push } = useToast()
// A copy: what is typed and not saved yet survives the page's reload of the numbers.
const items = ref(props.data.settings.map((item) => ({ ...item })))
const error = ref('')
const saving = ref('')

const item = (key) => items.value.find((entry) => entry.key === key)
const value = (key) => item(key)?.value || ''
const mode = computed(() => value('ai_mode') || 'off')
const modeNote = computed(() => MODES.find((entry) => entry.id === mode.value)?.note || '')

const LONG = { ai_style: 4000, ai_examples: 6000 }
// An empty style or examples means the standard ones: the field shows them.
for (const key of Object.keys(LONG)) {
  const entry = item(key)
  if (entry && !entry.value.trim()) entry.value = props.data.defaults[key]
}
const isDefault = (key) => value(key).trim() === props.data.defaults[key].trim()

async function save(entry, next = entry.value) {
  error.value = ''
  saving.value = entry.key
  // The standard text is saved as empty, so that the code's future wording reaches it too.
  const sent = entry.key in LONG && next.trim() === props.data.defaults[entry.key].trim() ? '' : next
  try {
    const saved = await adminApi.saveSetting({ key: entry.key, value: sent })
    Object.assign(entry, saved)
    if (entry.key in LONG && !entry.value.trim()) entry.value = props.data.defaults[entry.key]
    push(entry.secret && !next ? 'Ключ стёрт' : `Сохранено: ${entry.label}`)
    emit('saved')
  } catch (caught) {
    error.value = failed(caught)
  } finally {
    saving.value = ''
  }
}

function setMode(next) {
  if (next !== mode.value) save(item('ai_mode'), next)
}

function restore(key) {
  const entry = item(key)
  entry.value = props.data.defaults[key]
  save(entry, '')
}

const check = reactive({ busy: false, ok: false, text: '' })
async function runCheck() {
  check.busy = true
  check.text = ''
  try {
    const answer = await adminApi.aiCheck()
    check.ok = answer.ok
    check.text = answer.ok
      ? `Связь есть: ${modelName(props.data.models, answer.model)} ответила за ${seconds(answer.ms)}, вызов стоил ${money(answer.cost)}.`
      : `Модель не ответила: ${answer.error}`
    emit('saved')
  } catch (caught) {
    check.ok = false
    check.text = errorText(caught)
  } finally {
    check.busy = false
  }
}

const RULES = [
  'Сообщения о желании умереть или причинить себе вред, попытки сменить роль ИИ-астролога и брань распознаёт код — модель их не получает, отвечает сам сервис.',
  'Модель видит только «паспорт» — карту, небо и пары, рассчитанные сайтом, — и не придумывает положений планет и дат.',
  'Ответ показывается только после проверки: формат, длина, русский язык, без названия модели и инструкций, без пугающих слов и брани. Не прошёл — одна повторная попытка, потом шаблон сайта.',
  'Тон — только поддерживающий: сложное — это точка роста; без предсказаний болезней, смерти, измен и аварий, без медицинских, юридических и денежных советов.',
  'Вопросы не по теме, попытки сменить роль и грубость не списывают вопросы; три таких за полчаса — пауза 10 минут.',
  'В память не попадают здоровье, вера, взгляды, интимное, документы, телефоны и адреса.',
  'Модель не называет себя и разработчика, не пересказывает инструкции и не говорит о ценах.',
]
</script>

<template>
  <div class="as">
    <p v-if="error" class="error">{{ error }}</p>

    <section class="adm-panel">
      <div class="adm-panel-head">
        <h2>Подключение</h2>
        <span class="adm-badge" :class="data.ready ? 'is-ok' : 'is-warn'">{{ data.ready ? 'ключ и каталог заданы' : 'нужны ключ и каталог' }}</span>
      </div>

      <div class="as-field">
        <span class="adm-label">Режим</span>
        <div class="adm-seg" role="group" aria-label="Режим">
          <button v-for="entry in MODES" :key="entry.id" type="button" :aria-pressed="mode === entry.id" :disabled="saving === 'ai_mode'" @click="setMode(entry.id)">
            {{ entry.label }}
          </button>
        </div>
        <p class="adm-note as-tight">{{ modeNote }}</p>
        <p v-if="mode !== 'off' && !data.ready" class="as-warn">Пока ключ и каталог не заданы, отвечают шаблоны.</p>
      </div>

      <form v-if="item('ai_testers')" class="as-field" @submit.prevent="save(item('ai_testers'))">
        <label class="adm-label" for="as-testers">{{ item('ai_testers').label }}</label>
        <div class="as-row">
          <input id="as-testers" v-model="item('ai_testers').value" class="adm-input" type="text" autocomplete="off" placeholder="you@example.ru, tester@example.ru" />
          <button class="adm-btn" type="submit" :disabled="saving === 'ai_testers'">Сохранить</button>
        </div>
        <p class="adm-note as-tight">В режиме «Тест» модель отвечает только этим почтам: зайдите в кабинет под одной из них и поговорите с ИИ-астрологом.</p>
      </form>

      <div class="as-grid">
        <form class="as-field" @submit.prevent="save(item('ai_api_key'))">
          <label class="adm-label" for="as-key">{{ item('ai_api_key').label }}</label>
          <div class="as-row">
            <input
              id="as-key"
              v-model="item('ai_api_key').value"
              class="adm-input"
              type="password"
              autocomplete="off"
              :placeholder="item('ai_api_key').filled ? 'Ключ сохранён — введите новый, чтобы заменить' : 'AQVN…'"
            />
            <button class="adm-btn" type="submit" :disabled="!item('ai_api_key').value || saving === 'ai_api_key'">Сохранить</button>
          </div>
          <button v-if="item('ai_api_key').filled" class="text-button as-erase" type="button" :disabled="saving === 'ai_api_key'" @click="save(item('ai_api_key'), '')">Стереть ключ</button>
        </form>
        <form class="as-field" @submit.prevent="save(item('ai_folder'))">
          <label class="adm-label" for="as-folder">{{ item('ai_folder').label }}</label>
          <div class="as-row">
            <input id="as-folder" v-model="item('ai_folder').value" class="adm-input" type="text" autocomplete="off" placeholder="b1g…" />
            <button class="adm-btn" type="submit" :disabled="saving === 'ai_folder'">Сохранить</button>
          </div>
        </form>
      </div>
      <p class="adm-note as-tight">Ключ хранится на сервере и на страницу не возвращается. Сервисному аккаунту достаточно роли <code>ai.languageModels.user</code>.</p>

      <div class="as-check">
        <button type="button" class="adm-btn is-gold" :disabled="!data.ready || check.busy" @click="runCheck">{{ check.busy ? 'Проверяем…' : 'Проверить связь' }}</button>
        <span v-if="!data.ready" class="adm-dim">Сначала сохраните ключ и ID каталога.</span>
        <span v-else-if="check.text" :class="check.ok ? 'as-ok' : 'error'">{{ check.text }}</span>
      </div>
    </section>

    <section class="adm-panel">
      <div class="adm-panel-head">
        <h2>Модель</h2>
        <p>цены Yandex AI Studio с НДС, ₽ за 1000 токенов</p>
      </div>
      <div class="as-grid">
        <form class="as-field" @submit.prevent="save(item('ai_model'))">
          <label class="adm-label" for="as-model">{{ item('ai_model').label }}</label>
          <div class="as-row">
            <select id="as-model" v-model="item('ai_model').value" class="adm-input">
              <option v-for="model in data.models" :key="model.id" :value="model.id">{{ model.label }}</option>
            </select>
            <button class="adm-btn" type="submit" :disabled="saving === 'ai_model'">Сохранить</button>
          </div>
        </form>
        <form class="as-field" @submit.prevent="save(item('ai_trial_model'))">
          <label class="adm-label" for="as-trial">{{ item('ai_trial_model').label }}</label>
          <div class="as-row">
            <select id="as-trial" v-model="item('ai_trial_model').value" class="adm-input">
              <option value="">Та же, что основная</option>
              <option v-for="model in data.models" :key="model.id" :value="model.id">{{ model.label }}</option>
            </select>
            <button class="adm-btn" type="submit" :disabled="saving === 'ai_trial_model'">Сохранить</button>
          </div>
        </form>
      </div>
      <p class="adm-note as-tight">Без «Небосвода» у человека два пробных вопроса — от них зависит, купит ли он. Их можно отдать модели сильнее: вопросов мало, расход небольшой.</p>
      <div class="as-scroll">
        <table class="adm-table as-prices">
          <thead>
            <tr><th>Модель</th><th class="num">Вход</th><th class="num">Вход из кэша</th><th class="num">Ответ</th><th class="num">≈ за ответ</th></tr>
          </thead>
          <tbody>
            <tr v-for="model in data.models" :key="model.id" :class="{ 'is-on': model.id === value('ai_model') }">
              <td>
                {{ model.label }}
                <span v-if="model.id === value('ai_model')" class="adm-badge is-ok">основная</span>
                <span v-if="model.id === value('ai_trial_model')" class="adm-badge is-warn">пробные</span>
              </td>
              <td class="num">{{ model.input.toLocaleString('ru-RU') }}</td>
              <td class="num">{{ model.cached.toLocaleString('ru-RU') }}</td>
              <td class="num">{{ model.output.toLocaleString('ru-RU') }}</td>
              <td class="num">{{ money(answerCost(model)) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="adm-note as-tight">«≈ за ответ» — оценка для обычного вопроса: около 3 500 токенов на вход (правила, карта, разговор) и 400 на ответ. Точный расход — в «Журнале».</p>
    </section>

    <section class="adm-panel">
      <div class="adm-panel-head">
        <h2>Лимиты</h2>
      </div>
      <div class="as-grid">
        <form class="as-field" @submit.prevent="save(item('ai_daily_limit'))">
          <label class="adm-label" for="as-daily">{{ item('ai_daily_limit').label }}</label>
          <div class="as-row">
            <input id="as-daily" v-model="item('ai_daily_limit').value" class="adm-input" type="text" inputmode="numeric" autocomplete="off" />
            <button class="adm-btn" type="submit" :disabled="saving === 'ai_daily_limit'">Сохранить</button>
          </div>
          <p class="adm-note as-tight">Считаются только вопросы, получившие ответ; день — по Москве. Пробные вопросы без «Небосвода» — внутри этого лимита.</p>
        </form>
        <form class="as-field" @submit.prevent="save(item('ai_month_budget'))">
          <label class="adm-label" for="as-budget">{{ item('ai_month_budget').label }}</label>
          <div class="as-row">
            <input id="as-budget" v-model="item('ai_month_budget').value" class="adm-input" type="text" inputmode="numeric" autocomplete="off" />
            <button class="adm-btn" type="submit" :disabled="saving === 'ai_month_budget'">Сохранить</button>
          </div>
          <p class="adm-note as-tight">Потрачено в этом месяце: {{ money(data.spent) }}. Когда бюджет исчерпан, до 1-го числа отвечают шаблоны; 0 — модель не вызывается.</p>
        </form>
      </div>
    </section>

    <section class="adm-panel">
      <div class="adm-panel-head">
        <h2>Если человеку очень плохо</h2>
      </div>
      <p class="adm-note">
        Когда человек пишет о желании умереть или причинить себе вред, ИИ-астролог не отвечает как астролог и не тратит вопрос:
        сервис сам показывает заботливый текст с бесплатным номером психологической помощи и 112. Код ловит такие слова ещё до модели,
        а если их распознала модель — её ответ заменяется этим же текстом. Позвоните на номер сами перед запуском: он должен работать.
      </p>
      <form class="as-field" @submit.prevent="save(item('ai_helpline'))">
        <label class="adm-label" for="as-helpline">{{ item('ai_helpline').label }}</label>
        <div class="as-row as-short">
          <input id="as-helpline" v-model="item('ai_helpline').value" class="adm-input" type="text" inputmode="tel" autocomplete="off" />
          <button class="adm-btn" type="submit" :disabled="saving === 'ai_helpline'">Сохранить</button>
        </div>
      </form>
      <div class="as-preview">
        <span class="adm-label">Что увидит человек</span>
        <AiAnswer :answer="data.crisis.answer" :key-line="data.crisis.key" />
      </div>
    </section>

    <section v-for="key in ['ai_style', 'ai_examples']" :key="key" class="adm-panel">
      <div class="adm-panel-head">
        <h2>{{ item(key).label }}</h2>
        <span class="adm-badge" :class="isDefault(key) ? 'is-plain' : 'is-warn'">{{ isDefault(key) ? 'стандартный текст' : 'ваш текст' }}</span>
      </div>
      <p v-if="key === 'ai_style'" class="adm-note">Как говорит ИИ-астролог: тон, длина, на что опираться. Правила безопасности и формат ответа — в коде, их здесь не нужно повторять.</p>
      <p v-else class="adm-note">Два-три образца «Вопрос: … / Ответ: … / Ключ: …». Модель берёт из них манеру, а не факты: данные в примерах вымышлены. Попробовать текст до сохранения можно в «Песочнице».</p>
      <form class="as-field" @submit.prevent="save(item(key))">
        <textarea :id="`as-${key}`" v-model="item(key).value" class="adm-input as-text" :class="{ 'is-long': key === 'ai_examples' }" :maxlength="LONG[key]" spellcheck="true" :aria-label="item(key).label" />
        <div class="as-text-foot">
          <span class="adm-dim num">{{ item(key).value.length }} / {{ LONG[key] }}</span>
          <button v-if="!isDefault(key)" type="button" class="text-button" :disabled="saving === key" @click="restore(key)">Вернуть стандартный</button>
          <button class="adm-btn" type="submit" :disabled="saving === key">Сохранить</button>
        </div>
      </form>
    </section>

    <section class="adm-panel">
      <div class="adm-panel-head">
        <h2>Правила безопасности</h2>
        <span class="adm-badge is-plain">в коде, не меняются здесь</span>
      </div>
      <ul class="as-rules">
        <li v-for="rule in RULES" :key="rule">{{ rule }}</li>
      </ul>
      <p class="adm-note as-tight">Полный текст инструкций, который получает модель, виден в «Песочнице» под ответом.</p>
    </section>
  </div>
</template>

<style scoped>
.as { display: grid; gap: 18px; }
.as-field { display: grid; gap: 6px; margin: 0 0 16px; align-content: start; }
.as-field:last-child { margin-bottom: 0; }
.as-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 18px; }
.as-row { display: flex; align-items: stretch; gap: 10px; }
.as-row .adm-input { flex: 1; min-width: 0; }
.as-row .adm-btn { flex: none; }
.as-short { max-width: 420px; }
.as-tight { margin: 2px 0 0; }
.as-warn { margin: 2px 0 0; color: #e6c27a; font-size: 14px; }
.as-erase { justify-self: start; font-size: 13px; }
.as-check { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 14px; margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--panel-line); font-size: 14px; }
.as-ok { color: var(--ok); }
code { font-size: 13.5px; padding: 1px 6px; border-radius: 6px; background: rgba(255, 240, 210, 0.07); }

.as-scroll { margin-top: 14px; overflow-x: auto; }
.as-prices td .adm-badge { margin-left: 6px; }
.as-prices tr.is-on { background: rgba(244, 239, 230, 0.04); }

.as-preview { display: grid; gap: 8px; margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--panel-line); }

.as-text { min-height: 180px; }
.as-text.is-long { min-height: 320px; }
.as-text-foot { display: flex; flex-wrap: wrap; align-items: center; justify-content: flex-end; gap: 8px 16px; }
.as-text-foot .adm-dim { margin-right: auto; font-size: 13px; }

.as-rules { display: grid; gap: 8px; margin: 0; padding-left: 1.2em; font-size: 14.5px; line-height: 1.5; }

@media (max-width: 900px) {
  .as-grid { grid-template-columns: minmax(0, 1fr); }
}
@media (max-width: 640px) {
  .as-row { flex-wrap: wrap; }
  .as-row .adm-btn { flex: 1; }
}
</style>
