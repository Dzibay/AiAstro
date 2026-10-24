<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { adminApi } from '../../api/admin.js'
import { LETTER_STATUS, failed, fmt, usePagedList } from './shared.js'

/**
 * The letters: every kind the site can send — when it goes and to whom, a sample, the last 30 days —
 * and the journal of what was sent, what became of each letter and whether its button was pressed.
 */

const RULES = [
  { id: 'always', title: 'Уходят всегда', hint: 'Вход, пароль и оплата — их нельзя отключить.' },
  { id: 'notes', title: 'Напоминания и вести', hint: 'Только тем, у кого в профиле включены письма. Без подтверждённой почты не уходят.' },
  { id: 'operator', title: 'Вручную', hint: 'Отправляются из админки.' },
]
const FILTERS = [
  { id: '', label: 'Все' },
  { id: 'sent', label: 'Ушли' },
  { id: 'failed', label: 'Не ушли' },
  { id: 'off', label: 'Почта не настроена' },
  { id: 'clicked', label: 'С переходом' },
]

/* ---- What the site sends ---- */

const kinds = ref([])
const mailOn = ref(true)
const kindsError = ref('')
async function loadKinds() {
  kindsError.value = ''
  try {
    const data = await adminApi.letterKinds()
    kinds.value = data.kinds
    mailOn.value = data.mail_on
  } catch (caught) {
    kindsError.value = failed(caught)
  }
}
const groups = computed(() =>
  RULES.map((rule) => ({ ...rule, kinds: kinds.value.filter((k) => k.rule === rule.id) })).filter((g) => g.kinds.length),
)
const names = computed(() => Object.fromEntries(kinds.value.map((k) => [k.kind, k.name])))

const tiles = computed(() => {
  if (!kinds.value.length) return []
  const sum = (field) => kinds.value.reduce((total, k) => total + Number(k[field] || 0), 0)
  return [
    { label: 'Ушло за 30 дней', value: fmt.count(sum('sent')), hint: `видов писем: ${kinds.value.length}` },
    { label: 'Не ушло', value: fmt.count(sum('failed') + sum('off')), hint: 'ошибка почты или она не настроена' },
    { label: 'С переходом', value: fmt.count(sum('clicked')), hint: 'нажали кнопку в письме' },
  ]
})

/* ---- A sample of one kind ---- */

const dialog = ref(null)
const sample = reactive({ kind: '', subject: '', html: '', error: '', loading: false })
async function preview(kind) {
  Object.assign(sample, { kind: kind.kind, subject: kind.name, html: '', error: '', loading: true })
  await nextTick()
  if (!dialog.value.open) dialog.value.showModal()
  try {
    const data = await adminApi.letterPreview(kind.kind)
    if (sample.kind !== kind.kind) return
    Object.assign(sample, { subject: data.subject, html: data.html })
  } catch (caught) {
    sample.error = failed(caught)
  } finally {
    sample.loading = false
  }
}
function closePreview() {
  dialog.value?.close()
  sample.kind = ''
}

/* ---- The journal ---- */

const kindFilter = ref('')
const journal = ref(null)
const list = usePagedList((params) => adminApi.letters({ q: params.q, status: params.state, kind: kindFilter.value, offset: params.offset }))
const { q, filter, items, more, loading, error } = list
watch(kindFilter, () => list.load())

function showInJournal(kind) {
  kindFilter.value = kind
  filter.value = ''
  journal.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

onMounted(() => {
  loadKinds()
  list.load()
})
</script>

<template>
  <header class="adm-head">
    <div>
      <h1>Письма</h1>
      <p>
        Все письма, которые отправляет сайт: когда и кому уходит каждое, как оно выглядит и что с ним стало. Переход — человек
        нажал кнопку в письме; почтовые фильтры иногда открывают ссылки сами, так что единичный переход сразу после отправки
        может быть проверкой почтового сервиса.
      </p>
    </div>
  </header>

  <p v-if="!mailOn" class="lt-off">
    Почта не настроена — письма не уходят, в журнале они отмечены «почта не настроена».
    <RouterLink :to="{ name: 'admin-settings' }">Настроить в «Настройках»</RouterLink>
  </p>

  <div v-if="tiles.length" class="lt-tiles">
    <div v-for="tile in tiles" :key="tile.label" class="adm-panel lt-tile">
      <span class="lt-tile-label">{{ tile.label }}</span>
      <strong class="lt-tile-value">{{ tile.value }}</strong>
      <span class="lt-tile-hint">{{ tile.hint }}</span>
    </div>
  </div>

  <p v-if="kindsError" class="error">{{ kindsError }}</p>

  <section v-for="group in groups" :key="group.id" class="adm-panel lt-group">
    <div class="lt-group-head">
      <h2>{{ group.title }}</h2>
      <span class="adm-dim">{{ group.hint }}</span>
    </div>
    <ul class="lt-kinds">
      <li v-for="kind in group.kinds" :key="kind.kind" class="lt-kind">
        <div class="lt-kind-main">
          <strong>{{ kind.name }}</strong>
          <span class="lt-kind-when">{{ kind.when }}</span>
          <span class="lt-kind-stats">
            <template v-if="kind.total">
              за 30 дней: ушло {{ fmt.count(kind.sent) }}<template v-if="kind.failed"> · не ушло {{ fmt.count(kind.failed) }}</template
              ><template v-if="kind.off"> · почта не настроена {{ fmt.count(kind.off) }}</template
              ><template v-if="kind.clicked"> · с переходом {{ fmt.count(kind.clicked) }}</template> · последнее {{ fmt.moment(kind.last_at) }}
            </template>
            <template v-else>за 30 дней не отправлялось</template>
          </span>
        </div>
        <div class="lt-kind-actions">
          <button type="button" class="adm-btn" @click="preview(kind)">Пример</button>
          <button v-if="kind.total" type="button" class="adm-btn" @click="showInJournal(kind.kind)">В журнал</button>
        </div>
      </li>
    </ul>
  </section>

  <div ref="journal" class="lt-journal-head">
    <h2>Журнал</h2>
    <span class="adm-dim">новые сверху; письма человека хранятся, пока существует его кабинет</span>
  </div>

  <div class="adm-toolbar">
    <label class="adm-search">
      <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
      <input v-model="q" type="search" placeholder="Почта или тема" aria-label="Поиск писем" autocomplete="off" />
    </label>
    <select v-model="kindFilter" class="adm-input lt-kind-select" aria-label="Вид письма">
      <option value="">Все виды</option>
      <option v-for="kind in kinds" :key="kind.kind" :value="kind.kind">{{ kind.name }}</option>
    </select>
    <div class="adm-seg" role="group" aria-label="Какие письма">
      <button v-for="f in FILTERS" :key="f.id" type="button" :aria-pressed="filter === f.id" @click="filter = f.id">{{ f.label }}</button>
    </div>
  </div>

  <p v-if="error" class="error">{{ error }}</p>

  <section class="adm-panel" :class="{ 'adm-loading': loading }">
    <ul v-if="items.length" class="lt-list">
      <li v-for="letter in items" :key="letter.id" class="lt-row">
        <span class="lt-when">{{ fmt.moment(letter.created_at) }}</span>
        <span class="lt-what">
          <strong>{{ names[letter.kind] || letter.name || letter.kind }}</strong>
          <span class="lt-subject">{{ letter.subject }}</span>
          <span class="lt-to">
            <RouterLink v-if="letter.user_id" :to="{ name: 'admin-user', params: { id: letter.user_id } }">{{ letter.email }}</RouterLink>
            <template v-else>{{ letter.email }}</template>
          </span>
          <span v-if="letter.error" class="lt-error">{{ letter.error }}</span>
        </span>
        <span class="lt-marks">
          <span class="adm-badge" :class="LETTER_STATUS[letter.status]?.tone">{{ LETTER_STATUS[letter.status]?.text || letter.status }}</span>
          <span v-if="letter.clicks" class="adm-badge is-ok" :title="`Первый переход ${fmt.moment(letter.clicked_at)}`">
            переход{{ letter.clicks > 1 ? ` ×${letter.clicks}` : '' }}
          </span>
        </span>
      </li>
    </ul>
    <p v-else-if="!loading" class="adm-empty">
      {{ q || filter || kindFilter ? 'Писем не нашлось.' : 'Писем пока не было.' }}
    </p>
    <div v-if="more" class="adm-more">
      <button type="button" class="adm-btn" :disabled="loading" @click="list.loadMore()">Показать ещё</button>
    </div>
  </section>

  <dialog ref="dialog" class="lt-dialog" aria-label="Пример письма" @cancel.prevent="closePreview" @click.self="closePreview">
    <div class="lt-dialog-body">
      <div class="lt-dialog-head">
        <div>
          <span class="adm-dim">Тема</span>
          <strong>{{ sample.subject }}</strong>
        </div>
        <button type="button" class="adm-btn" @click="closePreview">Закрыть</button>
      </div>
      <p class="adm-dim lt-dialog-note">Пример с выдуманными данными; кнопки в настоящих письмах ведут через счётчик переходов.</p>
      <p v-if="sample.error" class="error">{{ sample.error }}</p>
      <p v-else-if="sample.loading" class="adm-dim">Загружаем…</p>
      <iframe v-else-if="sample.html" class="lt-frame" sandbox="" :srcdoc="sample.html" :title="sample.subject" />
    </div>
  </dialog>
</template>

<style scoped>
.lt-off {
  margin: 0;
  padding: 12px 16px;
  border: 1px solid rgba(224, 193, 122, 0.3);
  border-radius: 14px;
  color: var(--gold);
  font-size: 15px;
}
.lt-off a { color: var(--ink); }

.lt-tiles { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
.lt-tile { display: grid; align-content: start; gap: 4px; padding: 14px 16px; }
.lt-tile-label { color: var(--muted); font-size: 13px; }
.lt-tile-value { font-size: 24px; font-weight: 600; line-height: 1.15; font-variant-numeric: tabular-nums; }
.lt-tile-hint { color: var(--soft); font-size: 12px; }

.lt-group { display: grid; gap: 6px; }
.lt-group-head, .lt-journal-head { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 14px; }
.lt-group-head h2, .lt-journal-head h2 { margin: 0; font-family: var(--sans); font-size: 18px; font-weight: 600; letter-spacing: 0; }
.lt-group-head .adm-dim, .lt-journal-head .adm-dim { font-size: 13.5px; }
.lt-journal-head { margin-top: 8px; scroll-margin-top: 20px; }
.lt-kinds { display: grid; margin: 0; padding: 0; list-style: none; }
.lt-kind { display: flex; align-items: center; justify-content: space-between; gap: 18px; padding: 12px 0; border-top: 1px solid var(--panel-line); }
.lt-kind:first-child { border-top: 0; }
.lt-kind-main { display: grid; gap: 3px; min-width: 0; }
.lt-kind-main strong { font-size: 15.5px; font-weight: 600; }
.lt-kind-when { color: var(--muted); font-size: 14px; line-height: 1.45; }
.lt-kind-stats { color: var(--soft); font-size: 13px; }
.lt-kind-actions { display: flex; flex: none; gap: 8px; }
.lt-kind-actions .adm-btn { padding: 6px 13px; font-size: 13.5px; }

.lt-kind-select { width: auto; max-width: 280px; padding: 9px 34px 9px 14px; border-radius: 999px; }

.lt-list { display: grid; margin: 0; padding: 0; list-style: none; }
.lt-row {
  display: grid;
  grid-template-columns: 8.4em minmax(0, 1fr) auto;
  align-items: start;
  gap: 4px 16px;
  padding: 12px 4px;
  border-top: 1px solid var(--panel-line);
  font-size: 14px;
}
.lt-row:first-child { border-top: 0; }
.lt-when { color: var(--soft); white-space: nowrap; }
.lt-what { display: grid; gap: 2px; min-width: 0; }
.lt-what strong { font-weight: 600; }
.lt-subject { color: var(--muted); overflow-wrap: anywhere; }
.lt-to { color: var(--soft); font-size: 13px; overflow-wrap: anywhere; }
.lt-to a { color: var(--gold); }
.lt-error { color: var(--danger); font-size: 13px; overflow-wrap: anywhere; }
.lt-marks { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 6px; }

.lt-dialog {
  width: min(720px, calc(100% - 24px));
  max-height: calc(100% - 24px);
  padding: 0;
  border: 1px solid rgba(244, 239, 230, 0.14);
  border-radius: 20px;
  background: #141c19;
  color: var(--ink);
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.5);
}
.lt-dialog::backdrop { background: rgba(4, 6, 10, 0.6); }
.lt-dialog-body { display: grid; gap: 10px; padding: 18px; }
.lt-dialog-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 14px; }
.lt-dialog-head div { display: grid; gap: 2px; min-width: 0; }
.lt-dialog-head .adm-dim { font-size: 12.5px; }
.lt-dialog-head strong { font-size: 16px; overflow-wrap: anywhere; }
.lt-dialog-note { margin: 0; font-size: 13px; }
.lt-frame { width: 100%; height: min(70vh, 760px); border: 0; border-radius: 12px; background: #0b0f14; }

@media (max-width: 640px) {
  .lt-tiles { grid-template-columns: minmax(0, 1fr); }
  .lt-tile { grid-template-columns: 1fr auto; align-items: baseline; }
  .lt-tile-hint { grid-column: 1 / -1; }
  .lt-kind { flex-direction: column; align-items: stretch; gap: 10px; }
  .lt-row { grid-template-columns: minmax(0, 1fr); }
  .lt-marks { justify-content: flex-start; }
}
</style>
