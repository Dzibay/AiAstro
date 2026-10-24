import { reactive, watch } from 'vue'
import { webApi } from '../api/web.js'
import { ApiError, errorText } from '../api/http.js'
import { readSession, webToken } from './useSession.js'

/**
 * The conversation with the ИИ-астролог (GET/POST /me/chat). The history is asked once per visit
 * and kept while the person moves between sections; another session (a new login) starts afresh,
 * so one person's questions never show to the next.
 *
 * `left` is the trial questions left, or null with «Небосвод». The server counts them; the page
 * only shows the count and swaps the field for the invitation when it reaches zero. `todayLeft` of
 * `daily` — the questions left today (a Moscow day); `pauseUntil` — the end of the pause that
 * follows three turns away from the chart. Only the questions about the chart count.
 */

/** status: idle → loading → ready | error */
const blank = () => ({
  status: 'idle', items: [], left: null, trial: 2, todayLeft: null, daily: 20, pauseUntil: null, suggestions: [],
  message: '', sending: false, error: '', fresh: null,
})
const state = reactive(blank())
let pending = null
let owner = ''
let generation = 0

function reset() {
  generation += 1
  pending = null
  Object.assign(state, blank())
}

function load() {
  const session = readSession('web') || ''
  if (session !== owner) {
    reset()
    owner = session
  }
  if (state.status === 'ready' || pending) return pending || Promise.resolve()
  state.status = 'loading'
  const asked = generation
  pending = webApi
    .chat()
    .then((data) => {
      if (asked !== generation) return
      Object.assign(state, { items: data.items, trial: data.trial, suggestions: data.suggestions, ...counts(data), status: 'ready' })
    })
    .catch((error) => {
      if (asked !== generation) return
      state.message = errorText(error)
      state.status = 'error'
    })
    .finally(() => {
      if (asked === generation) pending = null
    })
  return pending
}

/** What the server says is left: the trial, the day, the pause. */
function counts(data) {
  return { left: data.left, todayLeft: data.today_left, daily: data.daily, pauseUntil: data.pause_until }
}

/**
 * Sends a question; the question shows at once, the answer replaces the waiting star. The new
 * answer's id is kept in `fresh`: the page prints it out.
 */
async function ask(text) {
  const question = text.trim()
  if (!question || state.sending) return false
  const asked = generation
  const draft = { id: `draft-${Date.now()}`, role: 'user', text: question, draft: true }
  state.items.push(draft)
  state.sending = true
  state.error = ''
  try {
    const data = await webApi.ask(question)
    if (asked !== generation) return false
    state.items.splice(state.items.indexOf(draft), 1, ...data.items)
    state.fresh = data.items.at(-1)?.id ?? null
    Object.assign(state, counts(data))
    return true
  } catch (error) {
    if (asked !== generation) return false
    state.items.splice(state.items.indexOf(draft), 1)
    // The trial or the day ended in another tab: the field gives way to the note.
    if (error instanceof ApiError && error.code === 'trial_over') state.left = 0
    else if (error instanceof ApiError && error.code === 'day_limit') state.todayLeft = 0
    else state.error = errorText(error)
    return false
  } finally {
    if (asked === generation) state.sending = false
  }
}

/** After the birth data change the suggestions speak of other planets: ask for them again. */
function forget() {
  reset()
}

/** A logout or another account clears the conversation at once, not only at the next look. */
watch(webToken, () => {
  reset()
  owner = ''
}, { flush: 'sync' })

export function useChat() {
  return { chat: state, load, ask, forget }
}
