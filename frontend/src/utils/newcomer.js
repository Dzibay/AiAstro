import { reactive } from 'vue'

/**
 * The steps of «Путь новичка» that leave no trace on the server: the Sun read, a question asked.
 * Kept in this browser, per account, so the checklist remembers them between visits.
 */

const KEY = 'astra.newcomer'
const done = reactive(read())

function read() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || '{}') || {}
  } catch {
    return {}
  }
}

export function markStep(userId, step) {
  const key = `${userId}:${step}`
  if (!userId || done[key]) return
  done[key] = true
  try {
    localStorage.setItem(KEY, JSON.stringify(done))
  } catch {
    // Private mode: the step is remembered until the tab closes.
  }
}

export const stepDone = (userId, step) => Boolean(done[`${userId}:${step}`])
