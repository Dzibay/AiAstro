<script setup>
import { onMounted } from 'vue'
import { adminApi } from '../../api/admin.js'
import { PAYMENT_STATUS, PRODUCTS, fmt, usePagedList } from './shared.js'

const FILTERS = [
  { id: '', label: 'Все' },
  { id: 'succeeded', label: 'Оплачены' },
  { id: 'pending', label: 'Ждут оплаты' },
  { id: 'canceled', label: 'Отменены' },
]
const TONE = { succeeded: 'is-ok', pending: 'is-warn', canceled: 'is-bad', failed: 'is-bad' }

const list = usePagedList(({ q, state, offset }) => adminApi.payments({ q, status: state, offset }))
const { q, filter, items, more, loading, error } = list
onMounted(() => list.load())
</script>

<template>
  <header class="adm-head">
    <div>
      <h1>Платежи</h1>
      <p>Все попытки оплаты, новые сверху. Возврат делается в личном кабинете ЮKassa; доступ после него снимается в карточке человека.</p>
    </div>
  </header>

  <div class="adm-toolbar">
    <label class="adm-search">
      <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
      <input v-model="q" type="search" placeholder="Почта плательщика" aria-label="Поиск по почте" autocomplete="off" />
    </label>
    <div class="adm-seg" role="group" aria-label="Какие платежи">
      <button v-for="f in FILTERS" :key="f.id" type="button" :aria-pressed="filter === f.id" @click="filter = f.id">{{ f.label }}</button>
    </div>
  </div>

  <p v-if="error" class="error">{{ error }}</p>

  <section class="adm-panel" :class="{ 'adm-loading': loading }">
    <table v-if="items.length" class="adm-table">
      <thead>
        <tr>
          <th>Когда</th>
          <th>Кто</th>
          <th>Что</th>
          <th class="num">Сумма</th>
          <th>Статус</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="p in items" :key="p.id">
          <td class="adm-dim">{{ fmt.moment(p.paid_at || p.created_at) }}</td>
          <td class="wide">
            <RouterLink v-if="p.user_id" :to="{ name: 'admin-user', params: { id: p.user_id } }" class="pp-who">{{ p.email }}</RouterLink>
            <span v-else class="pp-who">{{ p.email }} <span class="adm-dim">· аккаунт удалён</span></span>
          </td>
          <td>{{ PRODUCTS[p.product] || p.title }}</td>
          <td class="num"><strong>{{ fmt.rub(p.amount) }}</strong></td>
          <td><span class="adm-badge" :class="TONE[p.status]">{{ PAYMENT_STATUS[p.status] || p.status }}</span></td>
        </tr>
      </tbody>
    </table>
    <p v-else-if="!loading" class="adm-empty">Платежей не нашлось.</p>
    <div v-if="more" class="adm-more">
      <button type="button" class="adm-btn" :disabled="loading" @click="list.loadMore()">Показать ещё</button>
    </div>
  </section>
</template>

<style scoped>
.pp-who { color: var(--ink); text-decoration: none; overflow-wrap: anywhere; }
a.pp-who:hover { color: var(--gold); text-decoration: underline; }
</style>
