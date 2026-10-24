<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AiJournal from '../../components/admin/ai/AiJournal.vue'
import AiOverview from '../../components/admin/ai/AiOverview.vue'
import AiRedteam from '../../components/admin/ai/AiRedteam.vue'
import AiSandbox from '../../components/admin/ai/AiSandbox.vue'
import AiSettings from '../../components/admin/ai/AiSettings.vue'
import { adminApi } from '../../api/admin.js'
import { failed } from './shared.js'

/**
 * The ИИ-астролог: how it is doing and what it costs, its settings, a sandbox to ask it as anyone,
 * the provocation test and the journal of every call. The tab is kept in the address.
 */

const TABS = [
  { id: 'overview', label: 'Обзор' },
  { id: 'settings', label: 'Настройки' },
  { id: 'sandbox', label: 'Песочница' },
  { id: 'redteam', label: 'Провокации' },
  { id: 'journal', label: 'Журнал' },
]
const PERIODS = [
  { days: 7, label: '7 дней' },
  { days: 30, label: '30 дней' },
  { days: 90, label: '90 дней' },
]

const route = useRoute()
const router = useRouter()
const tab = computed({
  get: () => (TABS.some((item) => item.id === route.query.tab) ? route.query.tab : 'overview'),
  set: (value) => router.replace({ query: { ...route.query, tab: value === 'overview' ? undefined : value } }),
})

const days = ref(30)
const data = ref(null)
const loading = ref(false)
const error = ref('')

async function load() {
  const asked = days.value
  loading.value = true
  error.value = ''
  try {
    const answer = await adminApi.ai(asked)
    if (asked === days.value) data.value = answer
  } catch (caught) {
    error.value = failed(caught)
  } finally {
    if (asked === days.value) loading.value = false
  }
}
watch(days, load)
onMounted(load)

const value = (key) => data.value?.settings.find((item) => item.key === key)?.value || ''
const STATUS = {
  off: { label: 'выключен', badge: 'is-plain' },
  test: { label: 'тест', badge: 'is-warn' },
  on: { label: 'включён', badge: 'is-ok' },
}
const status = computed(() => {
  if (!data.value) return null
  const mode = value('ai_mode') || 'off'
  if (mode !== 'off' && !data.value.ready) return { label: 'не подключён', badge: 'is-bad' }
  return STATUS[mode] || STATUS.off
})
</script>

<template>
  <header class="adm-head">
    <div>
      <h1>ИИ-астролог</h1>
      <p>Нейросеть Yandex AI Studio отвечает в чате кабинета по карте человека. Правила безопасности — в коде; здесь — режим, модель, лимиты, стиль и контроль.</p>
    </div>
    <span v-if="status" class="adm-badge ai-status" :class="status.badge">{{ status.label }}</span>
  </header>

  <div class="ai-bar">
    <div class="adm-seg ai-tabs" role="group" aria-label="Разделы">
      <button v-for="item in TABS" :key="item.id" type="button" :aria-pressed="tab === item.id" @click="tab = item.id">
        {{ item.label }}
      </button>
    </div>
    <div v-if="tab === 'overview'" class="adm-seg" role="group" aria-label="Период">
      <button v-for="p in PERIODS" :key="p.days" type="button" :aria-pressed="days === p.days" @click="days = p.days">{{ p.label }}</button>
    </div>
  </div>

  <p v-if="error" class="error">{{ error }}</p>
  <p v-else-if="!data" class="adm-dim">Загружаем…</p>

  <template v-if="data">
    <AiOverview v-if="tab === 'overview'" :data="data" :days="days" :class="{ 'adm-loading': loading }" @open="tab = $event" />
    <AiSettings v-else-if="tab === 'settings'" :data="data" @saved="load" />
    <AiSandbox v-else-if="tab === 'sandbox'" :data="data" @spent="load" @open="tab = $event" />
    <AiRedteam v-else-if="tab === 'redteam'" :data="data" @spent="load" @open="tab = $event" />
    <AiJournal v-else-if="tab === 'journal'" :models="data.models" />
  </template>
</template>

<style scoped>
.ai-status { align-self: center; font-size: 14px; }
.ai-bar { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 10px 16px; }
.ai-tabs { overflow-x: auto; scrollbar-width: none; max-width: 100%; }
.ai-tabs::-webkit-scrollbar { display: none; }
</style>
