<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import ConfirmDialog from '../../components/admin/ConfirmDialog.vue'
import { adminApi } from '../../api/admin.js'
import { useToast } from '../../composables/useToast.js'
import { failed, fmt, openFaults, usePagedList } from './shared.js'

/**
 * The journal of errors: what broke on the server and in the visitors' browsers. The same error is
 * one line with a count; a line opens to the last traceback or stack, the page, the browser and the
 * person. «Исправлено» puts it away until it happens again — then it comes back, marked.
 */

const FILTERS = [
  { id: 'open', label: 'Открытые' },
  { id: 'resolved', label: 'Исправленные' },
  { id: 'all', label: 'Все' },
]
const SIDE = { back: { text: 'Сервер', tone: 'is-bad' }, front: { text: 'Браузер', tone: 'is-warn' } }

const { push } = useToast()
const totals = ref(null)
const list = usePagedList(async (params) => {
  const data = await adminApi.faults(params)
  totals.value = data.totals
  openFaults.value = data.totals.open
  return data
}, { state: 'open' })
const { q, filter, items, more, loading, error } = list
onMounted(() => list.load())

const tiles = computed(() => {
  const t = totals.value
  if (!t) return []
  return [
    { label: 'Открытых', value: fmt.count(t.open), hint: 'ещё не отмечены исправленными' },
    { label: 'Случались за сутки', value: fmt.count(t.day), hint: 'открытых, хотя бы раз' },
    { label: 'Случаев за сутки', value: fmt.count(t.times), hint: 'всего повторов' },
  ]
})

const shown = ref(0)
const details = reactive({})
const detailError = ref('')
async function toggle(fault) {
  detailError.value = ''
  if (shown.value === fault.id) {
    shown.value = 0
    return
  }
  shown.value = fault.id
  try {
    // The last occurrence may be newer than the one fetched before: always the fresh one.
    details[fault.id] = await adminApi.fault(fault.id)
  } catch (caught) {
    detailError.value = failed(caught)
  }
}

const busy = ref(0)
const actionError = ref('')
async function mark(fault, resolved) {
  busy.value = fault.id
  actionError.value = ''
  try {
    const result = await adminApi.setFaultResolved(fault.id, resolved)
    openFaults.value = result.open
    push(resolved ? 'Ошибка отмечена исправленной' : 'Ошибка снова в открытых')
    shown.value = 0
    await list.load()
  } catch (caught) {
    actionError.value = failed(caught)
  } finally {
    busy.value = 0
  }
}

const ask = reactive({ open: false, busy: false, error: '' })
async function resolveAll() {
  ask.busy = true
  ask.error = ''
  try {
    const result = await adminApi.resolveAllFaults()
    openFaults.value = result.open
    push(`Отмечено исправленными: ${fmt.count(result.resolved)}`)
    ask.open = false
    shown.value = 0
    await list.load()
  } catch (caught) {
    ask.error = failed(caught)
  } finally {
    ask.busy = false
  }
}
</script>

<template>
  <header class="adm-head">
    <div>
      <h1>Ошибки</h1>
      <p>
        Что сломалось на сервере и в браузерах посетителей. Одинаковые ошибки собраны в одну строку со счётчиком;
        исправленная, если повторится, вернётся в открытые с пометкой.
      </p>
    </div>
    <button v-if="totals?.open" type="button" class="adm-btn" @click="Object.assign(ask, { open: true, error: '' })">
      Отметить все исправленными
    </button>
  </header>

  <div v-if="tiles.length" class="ft-tiles">
    <div v-for="tile in tiles" :key="tile.label" class="adm-panel ft-tile">
      <span class="ft-tile-label">{{ tile.label }}</span>
      <strong class="ft-tile-value">{{ tile.value }}</strong>
      <span class="ft-tile-hint">{{ tile.hint }}</span>
    </div>
  </div>

  <div class="adm-toolbar">
    <label class="adm-search">
      <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
      <input v-model="q" type="search" placeholder="Текст, файл или адрес" aria-label="Поиск ошибок" autocomplete="off" />
    </label>
    <div class="adm-seg" role="group" aria-label="Какие ошибки">
      <button v-for="f in FILTERS" :key="f.id" type="button" :aria-pressed="filter === f.id" @click="filter = f.id">{{ f.label }}</button>
    </div>
  </div>

  <p v-if="error || actionError" class="error">{{ error || actionError }}</p>

  <section class="adm-panel" :class="{ 'adm-loading': loading }">
    <ul v-if="items.length" class="ft">
      <li v-for="fault in items" :key="fault.id" class="ft-row" :class="{ 'is-open': shown === fault.id }">
        <button type="button" class="ft-summary" :aria-expanded="shown === fault.id" @click="toggle(fault)">
          <span class="ft-main">
            <span class="ft-tags">
              <span class="adm-badge" :class="SIDE[fault.side]?.tone">{{ SIDE[fault.side]?.text || fault.side }}</span>
              <code class="ft-kind">{{ fault.kind }}</code>
              <span v-if="fault.resolved_at" class="adm-badge is-ok">исправлена {{ fmt.day(fault.resolved_at) }}</span>
              <span v-else-if="fault.returned" class="adm-badge is-bad">вернулась после исправления</span>
            </span>
            <span class="ft-message">{{ fault.message }}</span>
            <span class="ft-place">{{ fault.place || fault.path || 'место не известно' }}</span>
          </span>
          <span class="ft-when">
            <strong>×{{ fmt.count(fault.count) }}</strong>
            <span>{{ fmt.moment(fault.last_at) }}</span>
          </span>
        </button>

        <div v-if="shown === fault.id" class="ft-detail">
          <p v-if="detailError" class="error">{{ detailError }}</p>
          <template v-else-if="details[fault.id]">
            <dl class="ft-facts">
              <div><dt>Впервые</dt><dd>{{ fmt.moment(details[fault.id].first_at) }}</dd></div>
              <div><dt>Последний раз</dt><dd>{{ fmt.moment(details[fault.id].last_at) }}</dd></div>
              <div v-if="details[fault.id].path">
                <dt>{{ fault.side === 'back' ? 'Запрос' : 'Страница' }}</dt><dd><code>{{ details[fault.id].path }}</code></dd>
              </div>
              <div v-if="details[fault.id].place"><dt>Где в коде</dt><dd><code>{{ details[fault.id].place }}</code></dd></div>
              <div v-if="details[fault.id].agent"><dt>Браузер</dt><dd class="ft-agent">{{ details[fault.id].agent }}</dd></div>
              <div v-if="details[fault.id].email">
                <dt>Человек</dt>
                <dd><RouterLink :to="{ name: 'admin-user', params: { id: details[fault.id].user_id } }">{{ details[fault.id].email }}</RouterLink></dd>
              </div>
            </dl>
            <pre v-if="details[fault.id].detail" class="ft-trace">{{ details[fault.id].detail }}</pre>
            <p v-else class="adm-dim ft-none">Трассировки нет — только текст ошибки.</p>
          </template>
          <div class="adm-actions">
            <button
              v-if="!fault.resolved_at"
              type="button"
              class="adm-btn is-gold"
              :disabled="busy === fault.id"
              @click="mark(fault, true)"
            >
              Исправлено
            </button>
            <button v-else type="button" class="adm-btn" :disabled="busy === fault.id" @click="mark(fault, false)">
              Вернуть в открытые
            </button>
          </div>
        </div>
      </li>
    </ul>
    <p v-else-if="!loading" class="adm-empty">
      {{ filter === 'open' && !q ? 'Открытых ошибок нет — всё работает.' : 'Ошибок не нашлось.' }}
    </p>
    <div v-if="more" class="adm-more">
      <button type="button" class="adm-btn" :disabled="loading" @click="list.loadMore()">Показать ещё</button>
    </div>
  </section>

  <ConfirmDialog
    :open="ask.open"
    title="Отметить все ошибки исправленными?"
    text="Открытые ошибки уйдут в исправленные. Те, что повторятся, вернутся в открытые с пометкой."
    label="Отметить все"
    :busy="ask.busy"
    :error="ask.error"
    @confirm="resolveAll"
    @cancel="ask.open = false"
  />
</template>

<style scoped>
.ft-tiles { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
.ft-tile { display: grid; align-content: start; gap: 4px; padding: 14px 16px; }
.ft-tile-label { color: var(--muted); font-size: 13px; }
.ft-tile-value { font-size: 24px; font-weight: 600; line-height: 1.15; font-variant-numeric: tabular-nums; }
.ft-tile-hint { color: var(--soft); font-size: 12px; }

.ft { display: grid; margin: 0; padding: 0; list-style: none; }
.ft-row { border-top: 1px solid var(--panel-line); }
.ft-row:first-child { border-top: 0; }
.ft-summary {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  width: 100%;
  padding: 14px 6px;
  border: 0;
  border-radius: 10px;
  background: none;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s ease;
}
.ft-summary:hover, .ft-row.is-open .ft-summary { background: rgba(244, 239, 230, 0.04); }
.ft-summary:focus-visible { outline: 2px solid rgba(224, 193, 122, 0.45); outline-offset: -2px; }
.ft-main { display: grid; gap: 6px; min-width: 0; }
.ft-tags { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 10px; }
.ft-kind { color: var(--muted); font-size: 13px; }
.ft-message {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  color: var(--ink);
  font-size: 15px;
  line-height: 1.45;
  overflow-wrap: anywhere;
}
.ft-row.is-open .ft-message { display: block; }
.ft-place { color: var(--soft); font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 12.5px; overflow-wrap: anywhere; }
.ft-when { display: grid; flex: none; justify-items: end; gap: 2px; color: var(--soft); font-size: 13px; white-space: nowrap; }
.ft-when strong { color: var(--ink); font-size: 16px; font-variant-numeric: tabular-nums; }

.ft-detail { display: grid; gap: 14px; padding: 4px 6px 18px; }
.ft-facts { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 10px 18px; margin: 0; }
.ft-facts div { display: grid; gap: 2px; min-width: 0; }
.ft-facts dt { color: var(--soft); font-size: 12.5px; }
.ft-facts dd { margin: 0; font-size: 14px; overflow-wrap: anywhere; }
.ft-facts a { color: var(--gold); }
.ft-agent { color: var(--muted); font-size: 13px; }
.ft-trace {
  max-height: 340px;
  margin: 0;
  padding: 12px 14px;
  overflow: auto;
  border: 1px solid var(--panel-line);
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.3);
  color: #e6dccb;
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 12.5px;
  line-height: 1.5;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.ft-none { margin: 0; font-size: 14px; }

@media (max-width: 640px) {
  .ft-tiles { grid-template-columns: minmax(0, 1fr); }
  .ft-tile { grid-template-columns: 1fr auto; align-items: baseline; }
  .ft-tile-hint { grid-column: 1 / -1; }
  .ft-summary { flex-direction: column; gap: 8px; }
  .ft-when { grid-auto-flow: column; justify-items: start; gap: 10px; }
}
</style>
