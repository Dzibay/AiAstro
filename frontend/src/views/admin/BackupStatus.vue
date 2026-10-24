<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { adminApi } from '../../api/admin.js'
import { useToast } from '../../composables/useToast.js'
import { failed, fmt, plural } from './shared.js'

/**
 * The copies of the base, under their settings: the last good copy, the last attempts, what lies on
 * the Disk now, «Сделать копию сейчас» and how to bring a copy back. stamp changes when a field of
 * the group is saved: the status is asked again.
 */

const props = defineProps({ stamp: { type: Number, default: 0 } })

const { push } = useToast()
const state = ref(null)
const error = ref('')
const starting = ref(false)
let timer = 0

async function load() {
  try {
    state.value = await adminApi.backups()
    error.value = ''
  } catch (caught) {
    error.value = failed(caught)
  }
}

onMounted(load)
watch(() => props.stamp, load)
onBeforeUnmount(() => clearTimeout(timer))

const latest = computed(() => state.value?.runs[0] || null)
const lastFailed = computed(() => (latest.value && latest.value.ok === false ? latest.value : null))

function size(bytes) {
  if (bytes == null) return ''
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} КБ`
  return `${(bytes / 1024 / 1024).toLocaleString('ru-RU', { maximumFractionDigits: 1 })} МБ`
}

/** While a copy is being made: the status every few seconds, then a word on how it went. */
function watchRun() {
  clearTimeout(timer)
  timer = setTimeout(async () => {
    await load()
    if (state.value?.running) {
      watchRun()
      return
    }
    if (latest.value?.ok) {
      push('Копия сохранена на Диске')
      copies.value = null
    }
  }, 3000)
}

async function makeNow() {
  starting.value = true
  error.value = ''
  try {
    await adminApi.backupNow()
    await load()
    watchRun()
  } catch (caught) {
    error.value = failed(caught)
  } finally {
    starting.value = false
  }
}

const copies = ref(null)
const copiesBusy = ref(false)
async function showCopies() {
  copiesBusy.value = true
  try {
    copies.value = await adminApi.backupCopies()
  } catch (caught) {
    copies.value = { items: [], error: failed(caught) }
  } finally {
    copiesBusy.value = false
  }
}

const restore = computed(() => {
  const db = state.value?.db || { name: 'aiastro', user: 'aiastro' }
  const file = copies.value?.items[0]?.name || state.value?.last?.name || 'astra-ГГГГ-ММ-ДД-ЧЧММ.dump'
  return [
    { text: 'Скачайте нужную копию с Диска и положите её на сервер, в папку с docker-compose.yml.' },
    { text: 'Остановите сайт, чтобы никто не писал в базу, пока она возвращается:', code: 'docker compose stop backend' },
    { text: 'Передайте файл базе:', code: `docker compose cp ${file} postgres:/tmp/restore.dump` },
    { text: 'Верните базу из копии — всё, что было после неё, заменится:', code: `docker compose exec postgres pg_restore --clean --if-exists --no-owner -U ${db.user} -d ${db.name} /tmp/restore.dump` },
    { text: 'Запустите сайт:', code: 'docker compose start backend' },
  ]
})
</script>

<template>
  <div class="bk">
    <p v-if="error" class="error">{{ error }}</p>
    <template v-if="state">
      <div class="bk-now">
        <div class="bk-summary">
          <p v-if="state.last" class="bk-last">
            Последняя копия — <strong>{{ fmt.moment(state.last.started_at) }}</strong>, {{ size(state.last.size) }}
          </p>
          <p v-else class="bk-last adm-dim">Копий ещё не было.</p>
          <p v-if="lastFailed" class="bk-fail">Последняя попытка не удалась: {{ lastFailed.error || 'причина не известна' }}</p>
          <p class="bk-plan">
            Каждый день после {{ String(state.hour).padStart(2, '0') }}:00 по Москве, в папку «{{ state.folder }}»; копии хранятся
            {{ state.keep }} {{ plural(state.keep, 'день', 'дня', 'дней') }}, три последние — всегда.
          </p>
        </div>
        <button type="button" class="adm-btn is-gold" :disabled="!state.on || state.running || starting" @click="makeNow">
          {{ state.running ? 'Копия делается…' : 'Сделать копию сейчас' }}
        </button>
      </div>

      <div v-if="state.runs.length" class="bk-block">
        <h3>Последние попытки</h3>
        <ul class="bk-list">
          <li v-for="run in state.runs" :key="run.id">
            <span class="bk-when">{{ fmt.moment(run.started_at) }}</span>
            <span v-if="run.ok" class="adm-badge is-ok">сохранена</span>
            <span v-else-if="run.ok === false" class="adm-badge is-bad">не удалась</span>
            <span v-else class="adm-badge is-warn">делается</span>
            <span class="bk-what">{{ run.ok === false ? run.error : size(run.size) }}{{ run.manual ? ' · вручную' : '' }}</span>
          </li>
        </ul>
      </div>

      <div v-if="state.on" class="bk-block">
        <h3>На Диске</h3>
        <button v-if="!copies" type="button" class="adm-btn" :disabled="copiesBusy" @click="showCopies">
          {{ copiesBusy ? 'Спрашиваем Диск…' : 'Показать копии' }}
        </button>
        <template v-else>
          <p v-if="copies.error" class="bk-fail">{{ copies.error }}</p>
          <ul v-else-if="copies.items.length" class="bk-list">
            <li v-for="copy in copies.items" :key="copy.name">
              <code class="bk-name">{{ copy.name }}</code>
              <span class="bk-what">{{ size(copy.size) }}</span>
            </li>
          </ul>
          <p v-else class="adm-dim">В папке пока нет копий.</p>
        </template>
      </div>

      <details class="bk-help">
        <summary>Как вернуть базу из копии</summary>
        <ol>
          <li v-for="(step, index) in restore" :key="index">
            {{ step.text }}
            <code v-if="step.code" class="bk-code">{{ step.code }}</code>
          </li>
        </ol>
      </details>
    </template>
  </div>
</template>

<style scoped>
.bk { display: grid; gap: 18px; margin-top: 18px; padding-top: 16px; border-top: 1px solid var(--panel-line); }
.bk p { margin: 0; }
.bk-now { display: flex; align-items: flex-start; justify-content: space-between; gap: 18px; }
.bk-summary { display: grid; gap: 6px; }
.bk-last { font-size: 15px; }
.bk-fail { color: #f0a59a; font-size: 14px; overflow-wrap: anywhere; }
.bk-plan { color: var(--soft); font-size: 13px; line-height: 1.5; }
.bk-block { display: grid; gap: 8px; justify-items: start; }
.bk-block h3 { margin: 0; color: var(--soft); font-size: 13px; font-weight: 500; }
.bk-list { display: grid; gap: 6px; width: 100%; margin: 0; padding: 0; list-style: none; }
.bk-list li { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 10px; font-size: 14px; }
.bk-when { min-width: 150px; font-variant-numeric: tabular-nums; }
.bk-what { color: var(--muted); overflow-wrap: anywhere; }
.bk-name { font-size: 13px; }
.bk-help summary { color: var(--gold); font-size: 14px; cursor: pointer; }
.bk-help ol { display: grid; gap: 10px; margin: 12px 0 0; padding-left: 20px; color: var(--muted); font-size: 14px; line-height: 1.5; }
.bk-code {
  display: block;
  margin-top: 4px;
  padding: 8px 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.25);
  color: var(--ink);
  font-size: 13px;
  overflow-wrap: anywhere;
  user-select: all;
}
@media (max-width: 640px) {
  .bk-now { flex-direction: column; }
  .bk-now .adm-btn { width: 100%; }
  .bk-when { min-width: 0; }
}
</style>
