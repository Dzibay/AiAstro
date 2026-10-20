<script setup>
import { onMounted, reactive, ref } from 'vue'
import ConfirmDialog from '../../components/admin/ConfirmDialog.vue'
import { adminApi } from '../../api/admin.js'
import { useToast } from '../../composables/useToast.js'
import { failed, fmt, usePagedList } from './shared.js'

const FILTERS = [
  { id: '', label: 'Все' },
  { id: 'bought', label: 'Разбор открыт' },
  { id: 'linked', label: 'Общие' },
  { id: 'waiting', label: 'Ждут ответа' },
]
const SOURCE = { pay: 'оплата', admin: 'подарок' }

const { push } = useToast()
const list = usePagedList(adminApi.pairs)
const { q, filter, items, more, loading, error } = list
onMounted(() => list.load())

function sideState(side) {
  if (side.linked) return { text: 'свой кабинет', tone: 'is-ok' }
  if (side.filled) return { text: side.invite ? 'ответил по ссылке' : 'введён вручную', tone: 'is-plain' }
  return side.invite ? { text: 'ждём ответа', tone: 'is-warn' } : { text: 'без данных', tone: '' }
}

const busy = ref(0)
const actionError = ref('')
async function open(pair) {
  busy.value = pair.id
  actionError.value = ''
  try {
    await adminApi.setPairBought(pair.id, true)
    await list.load()
    push(`Разбор пары № ${pair.id} открыт — письма ушли`)
  } catch (caught) {
    actionError.value = failed(caught)
  } finally {
    busy.value = 0
  }
}

const ask = reactive({ open: false, pair: null, error: '', busy: false })
async function close() {
  ask.busy = true
  ask.error = ''
  try {
    await adminApi.setPairBought(ask.pair.id, false)
    push(`Разбор пары № ${ask.pair.id} закрыт`)
    ask.open = false
    await list.load()
  } catch (caught) {
    ask.error = failed(caught)
  } finally {
    ask.busy = false
  }
}
function toggle(pair) {
  if (pair.bought) Object.assign(ask, { open: true, pair, error: '' })
  else open(pair)
}
</script>

<template>
  <header class="adm-head">
    <div>
      <h1>Пары</h1>
      <p>Разбор пары один на двоих: открытый здесь, он открывается у обоих, и обоим уходит письмо.</p>
    </div>
  </header>

  <div class="adm-toolbar">
    <label class="adm-search">
      <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
      <input v-model="q" type="search" placeholder="Почта, имя или имя партнёра" aria-label="Поиск пар" autocomplete="off" />
    </label>
    <div class="adm-seg" role="group" aria-label="Какие пары">
      <button v-for="f in FILTERS" :key="f.id" type="button" :aria-pressed="filter === f.id" @click="filter = f.id">{{ f.label }}</button>
    </div>
  </div>

  <p v-if="error || actionError" class="error">{{ error || actionError }}</p>

  <section class="adm-panel" :class="{ 'adm-loading': loading }">
    <ul v-if="items.length" class="pr">
      <li v-for="pair in items" :key="pair.id" class="pr-row">
        <div class="pr-main">
          <div class="pr-title">
            <strong>Пара № {{ pair.id }}</strong>
            <span v-if="pair.sides.length > 1" class="adm-badge is-plain">общая</span>
            <span class="adm-dim">создана {{ fmt.day(pair.created_at) }}</span>
          </div>
          <ul class="pr-sides">
            <li v-for="side in pair.sides" :key="side.partner_id">
              <RouterLink :to="{ name: 'admin-user', params: { id: side.user_id } }" class="pr-user">{{ side.email }}</RouterLink>
              <span class="pr-arrow" aria-label="добавил(а) партнёра">→</span>
              <span>{{ side.name }}</span>
              <span class="adm-badge" :class="sideState(side).tone">{{ sideState(side).text }}</span>
            </li>
          </ul>
          <p v-if="pair.bought" class="pr-bought">
            Разбор открыт {{ fmt.day(pair.bought_at) }} · {{ SOURCE[pair.source] || 'оплата' }}<template v-if="pair.payer">: {{ pair.payer }}</template>
          </p>
        </div>
        <div class="pr-switch">
          <span class="adm-dim">Разбор</span>
          <button
            type="button"
            role="switch"
            class="adm-switch"
            :aria-checked="pair.bought"
            :aria-label="`Разбор пары № ${pair.id}`"
            :title="!pair.bought && !pair.sides.some((s) => s.filled) ? 'Откроется, когда будут данные партнёра' : ''"
            :disabled="busy === pair.id || (!pair.bought && !pair.sides.some((s) => s.filled))"
            @click="toggle(pair)"
          />
        </div>
      </li>
    </ul>
    <p v-else-if="!loading" class="adm-empty">Пар не нашлось.</p>
    <div v-if="more" class="adm-more">
      <button type="button" class="adm-btn" :disabled="loading" @click="list.loadMore()">Показать ещё</button>
    </div>
  </section>

  <ConfirmDialog
    :open="ask.open"
    title="Закрыть разбор пары?"
    :text="ask.pair ? `Разбор пары № ${ask.pair.id} закроется${ask.pair.sides.length > 1 ? ' у обоих партнёров' : ''}. Деньги этим не возвращаются — возврат делается в ЮKassa.` : ''"
    label="Закрыть разбор"
    :busy="ask.busy"
    :error="ask.error"
    @confirm="close"
    @cancel="ask.open = false"
  />
</template>

<style scoped>
.pr { display: grid; margin: 0; padding: 0; list-style: none; }
.pr-row { display: flex; align-items: center; justify-content: space-between; gap: 18px; padding: 14px 0; border-top: 1px solid var(--panel-line); }
.pr-row:first-child { border-top: 0; padding-top: 4px; }
.pr-main { display: grid; gap: 6px; min-width: 0; }
.pr-title { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 10px; }
.pr-sides { display: grid; gap: 4px; margin: 0; padding: 0; list-style: none; font-size: 15px; }
.pr-sides li { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 8px; }
.pr-user { color: var(--ink); text-decoration: none; overflow-wrap: anywhere; }
.pr-user:hover { color: var(--gold); text-decoration: underline; }
.pr-arrow { color: var(--soft); }
.pr-bought { margin: 0; color: var(--ok); font-size: 14px; }
.pr-switch { display: flex; flex: none; align-items: center; gap: 10px; font-size: 14px; }
@media (max-width: 640px) {
  .pr-row { align-items: flex-start; }
  .pr-switch .adm-dim { display: none; }
}
</style>
