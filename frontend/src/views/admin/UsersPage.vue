<script setup>
import { onMounted, provide } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { adminApi } from '../../api/admin.js'
import { fmt, seen, usePagedList } from './shared.js'

const FILTERS = [
  { id: '', label: 'Все' },
  { id: 'sky', label: 'С «Небосводом»' },
  { id: 'paid', label: 'Платили' },
  { id: 'nobirth', label: 'Без даты рождения' },
  { id: 'unconfirmed', label: 'Почта не подтверждена' },
]

const route = useRoute()
const router = useRouter()
const list = usePagedList(adminApi.users)
const { q, filter, items, more, loading, error } = list
onMounted(() => list.load())

function open(user) {
  router.push({ name: 'admin-user', params: { id: user.id } })
}

// The card tells the list what changed in it, or that the person is gone.
provide('adminUsers', {
  update(user) {
    const row = items.value.find((item) => item.id === user.id)
    if (row) Object.assign(row, user)
  },
  remove(id) {
    items.value = items.value.filter((item) => item.id !== id)
  },
})
</script>

<template>
  <header class="adm-head">
    <div>
      <h1>Пользователи</h1>
      <p>Нажмите на строку — откроется карточка: календарь заходов, «Небосвод», пары и разборы, платежи, данные рождения, удаление.</p>
    </div>
  </header>

  <div class="adm-toolbar">
    <label class="adm-search">
      <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
      <input v-model="q" type="search" placeholder="Почта или имя" aria-label="Поиск по почте или имени" autocomplete="off" />
    </label>
    <div class="adm-seg" role="group" aria-label="Кого показать">
      <button v-for="f in FILTERS" :key="f.id" type="button" :aria-pressed="filter === f.id" @click="filter = f.id">{{ f.label }}</button>
    </div>
  </div>

  <p v-if="error" class="error">{{ error }}</p>

  <section class="adm-panel" :class="{ 'adm-loading': loading }">
    <table v-if="items.length" class="adm-table">
      <thead>
        <tr>
          <th>Пользователь</th>
          <th>Был</th>
          <th>Регистрация</th>
          <th>Рождение</th>
          <th>«Небосвод»</th>
          <th class="num">Пары</th>
          <th class="num">Оплачено</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="user in items"
          :key="user.id"
          class="is-link"
          :class="{ 'is-on': String(user.id) === route.params.id }"
          tabindex="0"
          @click="open(user)"
          @keydown.enter="open(user)"
        >
          <td class="wide">
            <span class="adm-who">
              <strong>{{ user.email }}</strong>
              <span>{{ user.name || 'без имени' }}<template v-if="user.blocked"> · заблокирован</template></span>
            </span>
          </td>
          <td data-label="Был" class="adm-seen" :title="user.last_seen ? fmt.moment(user.last_seen) : ''">{{ seen(user.last_seen) }}</td>
          <td data-label="С" class="adm-dim">{{ fmt.day(user.created_at) }}</td>
          <td data-label="Рождение">
            <span v-if="user.birth">{{ fmt.birth(user.birth.date) }}</span>
            <span v-else class="adm-dim">нет</span>
          </td>
          <td>
            <span v-if="user.sky" class="adm-badge is-ok">до {{ fmt.day(user.sky_until) }}</span>
            <span v-else class="adm-badge">нет</span>
          </td>
          <td data-label="Пары" class="num">{{ user.pairs }}</td>
          <td data-label="Оплачено" class="num">{{ user.paid ? fmt.rub(user.paid) : '—' }}</td>
        </tr>
      </tbody>
    </table>
    <p v-else-if="!loading" class="adm-empty">Никого не нашлось.</p>
    <div v-if="more" class="adm-more">
      <button type="button" class="adm-btn" :disabled="loading" @click="list.loadMore()">Показать ещё</button>
    </div>
  </section>

  <RouterView />
</template>
