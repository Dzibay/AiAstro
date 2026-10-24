<script setup>
import { computed, ref, watch } from 'vue'
import { adminApi } from '../../../api/admin.js'
import { useToast } from '../../../composables/useToast.js'
import { CATEGORY_TONE, SOURCE_NOTES, categoryName, money, seconds, sourceName } from '../../../views/admin/ai.js'
import { failed, fmt, plural } from '../../../views/admin/shared.js'

/**
 * One person's conversation with the ИИ-астролог, for the quality and the safety of the answers:
 * every turn with its topic, whether it was counted, who answered and at what price; the facts
 * remembered about the person; a pause after provocations. Opened by hand, not with the card.
 */
const props = defineProps({
  userId: { type: Number, required: true },
})
const { push } = useToast()

const chat = ref(null)
const loading = ref(false)
const busy = ref('')
const error = ref('')
const sure = ref(false)

async function load() {
  const id = props.userId
  loading.value = true
  error.value = ''
  try {
    const answer = await adminApi.userChat(id)
    if (id === props.userId) chat.value = answer
  } catch (caught) {
    error.value = failed(caught)
  } finally {
    loading.value = false
  }
}
watch(() => props.userId, () => {
  chat.value = null
  sure.value = false
})

const paused = computed(() => chat.value?.pause_until && new Date(chat.value.pause_until) > new Date())
const spent = computed(() => (chat.value?.items || []).reduce((sum, item) => sum + (item.cost || 0), 0))
const questions = computed(() => (chat.value?.items || []).filter((item) => item.role === 'user').length)

async function act(key, run, text) {
  busy.value = key
  error.value = ''
  try {
    await run()
    push(text)
    return true
  } catch (caught) {
    error.value = failed(caught)
    return false
  } finally {
    busy.value = ''
  }
}
async function unpause() {
  if (await act('pause', () => adminApi.unpauseUserChat(props.userId), 'Пауза снята')) chat.value.pause_until = null
}
async function forget() {
  if (!sure.value) {
    sure.value = true
    return
  }
  if (await act('memory', () => adminApi.forgetUserChat(props.userId), 'Память ИИ-астролога очищена')) chat.value.memory = []
  sure.value = false
}

const time = new Intl.DateTimeFormat('ru-RU', { hour: '2-digit', minute: '2-digit' })
</script>

<template>
  <section class="uc">
    <div class="uc-head">
      <h2>ИИ-астролог</h2>
      <span v-if="chat" class="adm-dim">{{ questions }} {{ plural(questions, 'вопрос', 'вопроса', 'вопросов') }}<template v-if="spent"> · {{ money(spent) }}</template></span>
    </div>

    <template v-if="!chat">
      <p class="uc-note">Переписка открывается только для проверки качества и безопасности ответов — так сказано в политике.</p>
      <button type="button" class="adm-btn" :disabled="loading" @click="load">{{ loading ? 'Загружаем…' : 'Открыть переписку' }}</button>
    </template>

    <template v-else>
      <div v-if="paused" class="uc-pause">
        <span class="adm-badge is-warn">пауза до {{ time.format(new Date(chat.pause_until)) }}</span>
        <span class="uc-note">три сообщения не по теме за полчаса</span>
        <button type="button" class="text-button" :disabled="Boolean(busy)" @click="unpause">Снять паузу</button>
      </div>

      <div class="uc-memory">
        <div class="uc-row">
          <h3>Помнит о человеке</h3>
          <button v-if="chat.memory.length" type="button" class="text-button" :class="{ 'uc-sure': sure }" :disabled="Boolean(busy)" @click="forget" @blur="sure = false">
            {{ sure ? 'Точно очистить?' : 'Очистить память' }}
          </button>
        </div>
        <ul v-if="chat.memory.length">
          <li v-for="fact in chat.memory" :key="fact">{{ fact }}</li>
        </ul>
        <p v-else class="uc-note">Пока ничего.</p>
      </div>

      <ol v-if="chat.items.length" class="uc-thread">
        <li v-for="item in chat.items" :key="item.id" :class="item.role === 'user' ? 'is-user' : 'is-astro'">
          <div class="uc-meta">
            <span class="adm-dim">{{ fmt.moment(item.created_at) }}</span>
            <template v-if="item.role === 'user'">
              <span v-if="item.category" class="adm-badge" :class="CATEGORY_TONE[item.category]">{{ categoryName(item.category) }}</span>
              <span v-if="item.category && !item.counted" class="adm-badge is-plain" title="Вопрос не по теме или провокация — в счёт вопросов дня не вошёл">не засчитан</span>
            </template>
            <template v-else>
              <span class="adm-badge" :class="item.source === 'ai' ? 'is-ok' : item.source === 'guard' ? 'is-plain' : 'is-bad'" :title="SOURCE_NOTES[item.source || '']">{{ sourceName(item.source) }}</span>
              <span v-if="item.flagged" class="adm-badge is-warn" title="Первый ответ модели не прошёл проверку">проверка</span>
              <span v-if="item.model" class="adm-dim num">{{ seconds(item.ms) }} · {{ money(item.cost) }}</span>
            </template>
          </div>
          <p class="uc-text">{{ item.text }}</p>
          <p v-if="item.error" class="error uc-error">{{ item.error }}</p>
        </li>
      </ol>
      <p v-else class="uc-empty">Человек ещё ничего не спрашивал.</p>

      <div class="adm-actions">
        <RouterLink :to="{ name: 'admin-ai', query: { tab: 'sandbox', user: userId } }" class="adm-btn">Спросить по его карте в песочнице</RouterLink>
        <button type="button" class="adm-btn" :disabled="loading" @click="load">Обновить</button>
      </div>
    </template>

    <p v-if="error" class="error">{{ error }}</p>
  </section>
</template>

<style scoped>
/* The card's own blocks (UserPanel) style only what they hold themselves: the same look here. */
.uc { display: grid; gap: 10px; padding: 18px 20px; border-bottom: 1px solid rgba(244, 239, 230, 0.07); }
.uc h2 { margin: 0; font-family: var(--sans); font-size: 15px; font-weight: 600; letter-spacing: 0.02em; line-height: 1.3; text-transform: uppercase; color: var(--muted); }
.uc-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.uc-note { margin: 0; color: var(--soft); font-size: 13px; }
.uc-empty { margin: 0; color: var(--soft); }
.uc > .adm-btn { justify-self: start; }
.uc h3 { margin: 0; font-family: var(--sans); font-size: 13px; font-weight: 600; color: var(--muted); }
.uc-pause { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 10px; }
.uc-memory { display: grid; gap: 6px; }
.uc-memory ul { display: grid; gap: 4px; margin: 0; padding-left: 18px; font-size: 14px; }
.uc-row { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; }
.uc-sure { color: var(--danger) !important; }
.uc-thread { display: grid; gap: 10px; max-height: 520px; margin: 4px 0 0; padding: 0 4px 0 0; overflow-y: auto; list-style: none; }
.uc-thread li { display: grid; gap: 4px; padding: 9px 11px; border-radius: 10px; font-size: 14px; }
.uc-thread .is-user { margin-left: 28px; background: rgba(255, 240, 210, 0.06); }
.uc-thread .is-astro { margin-right: 28px; border-left: 2px solid rgba(233, 200, 140, 0.45); background: rgba(0, 0, 0, 0.18); }
.uc-meta { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 8px; font-size: 12px; }
.uc-meta .adm-badge { padding: 1px 8px; font-size: 12px; }
.uc-text { margin: 0; line-height: 1.5; white-space: pre-wrap; overflow-wrap: anywhere; }
.uc-error { margin: 0; font-size: 13px; }
.num { font-variant-numeric: tabular-nums; }
</style>
