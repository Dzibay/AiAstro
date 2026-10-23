<script>
import { reactive, watch } from 'vue'
import { webToken } from '../../composables/useSession.js'

// The marks made on this visit, over what the forecast brought: they outlive the panel switching
// periods, and go with the account that made them.
const marks = reactive({})
watch(webToken, () => {
  for (const key of Object.keys(marks)) delete marks[key]
})
</script>

<script setup>
import { computed } from 'vue'
import { webApi } from '../../api/web.js'
import { errorText } from '../../api/http.js'
import { useToast } from '../../composables/useToast.js'

/**
 * The day's two or three things to do, from its transits and its Moon. A tick shows at once and
 * goes to the server (POST /me/forecast/tasks), which keeps the marks of the day for the account:
 * they wait on another device too. A tick the server refused goes back.
 */

const props = defineProps({
  /** [{ key, text, done }] as the forecast brings them. */
  tasks: { type: Array, required: true },
  /** The day, ISO: the forecast's `start`. */
  day: { type: String, required: true },
})

const busy = reactive(new Set())
const { push } = useToast()

const list = computed(() => props.tasks.map((task) => {
  const mark = marks[`${props.day}:${task.key}`]
  return { ...task, done: mark === undefined ? task.done : mark }
}))
const count = computed(() => list.value.filter((task) => task.done).length)

async function toggle(task) {
  if (busy.has(task.key)) return
  const id = `${props.day}:${task.key}`
  const done = !task.done
  marks[id] = done
  busy.add(task.key)
  try {
    const answer = await webApi.tickTask({ day: props.day, key: task.key, done })
    for (const item of props.tasks) marks[`${props.day}:${item.key}`] = answer.done.includes(item.key)
  } catch (error) {
    marks[id] = !done
    push(errorText(error))
  } finally {
    busy.delete(task.key)
  }
}
</script>

<template>
  <section class="block day-tasks" aria-labelledby="tasks-title">
    <h3 id="tasks-title" class="block-title">Дела дня</h3>
    <ul class="tasks">
      <li v-for="task in list" :key="task.key">
        <label class="task" :class="{ 'is-done': task.done }">
          <input type="checkbox" :checked="task.done" @change="toggle(task)" />
          <span class="box" aria-hidden="true">
            <svg viewBox="0 0 20 20"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg>
          </span>
          <span class="task-text">{{ task.text }}</span>
        </label>
      </li>
    </ul>
    <p class="tasks-note" aria-live="polite">
      <template v-if="count === list.length">Всё на сегодня отмечено — день прожит в лад с небом.</template>
      <template v-else-if="count">Отмечено {{ count }} из {{ list.length }}.</template>
      <template v-else>Небольшие дела в лад с сегодняшним небом — отмечайте сделанное.</template>
    </p>
  </section>
</template>

<style scoped>
.tasks { display: grid; gap: 8px; margin: 0; padding: 0; list-style: none; }
.task {
  position: relative;
  display: grid;
  grid-template-columns: 26px 1fr;
  align-items: start;
  gap: 12px;
  padding: 11px 14px;
  border-radius: 14px;
  border: 1px solid rgba(240, 210, 150, 0.14);
  background: rgba(255, 240, 210, 0.025);
  cursor: pointer;
  transition: border-color 0.25s ease, background 0.25s ease;
}
.task:hover { border-color: rgba(240, 205, 138, 0.45); }
.task input { position: absolute; opacity: 0; width: 1px; height: 1px; }
.task:has(input:focus-visible) { outline: 1px solid #f0cd8a; outline-offset: 2px; }
.box {
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  margin-top: 1px;
  border-radius: 8px;
  border: 1px solid rgba(240, 205, 138, 0.5);
  transition: background 0.3s ease, border-color 0.3s ease;
}
.box svg { width: 12px; height: 12px; fill: #2b1d0b; transform: scale(0); transition: transform 0.35s cubic-bezier(0.3, 1.6, 0.4, 1); }
.task-text { font-family: var(--book); font-size: 14.5px; line-height: 1.55; color: #efe7d8; transition: color 0.3s ease; }
.task.is-done { border-color: rgba(240, 205, 138, 0.35); background: rgba(240, 205, 138, 0.06); }
.task.is-done .box { background: linear-gradient(180deg, #f4dba6, #dcb36c); border-color: #f0cd8a; box-shadow: 0 0 10px rgba(255, 205, 120, 0.45); }
.task.is-done .box svg { transform: scale(1); }
.task.is-done .task-text { color: rgba(226, 220, 210, 0.6); text-decoration: line-through; text-decoration-color: rgba(240, 205, 138, 0.45); }
.tasks-note { margin: 0; font-family: var(--serif); font-style: italic; font-size: 15px; text-align: center; color: rgba(226, 220, 210, 0.6); }

@media (max-width: 760px) {
  .task { min-height: 44px; }
}
@media (prefers-reduced-motion: reduce) {
  .task, .box, .box svg, .task-text { transition: none; }
}
</style>
