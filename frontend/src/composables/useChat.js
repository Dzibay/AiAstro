import { reactive } from 'vue'
import { webApi } from '../api/web.js'
import { ApiError, errorText } from '../api/http.js'
import { readSession } from './useSession.js'

/**
 * The conversation with the astrologer (GET/POST /me/chat). The history is asked once per visit
 * and kept while the person moves between sections; another session (a new login) starts afresh,
 * so one person's questions never show to the next.
 *
 * `left` is the trial questions left, or null with «Небосвод». The server counts them; the page
 * only shows the count and swaps the field for the invitation when it reaches zero.
 */

/** status: idle → loading → ready | error */
const blank = () => ({ status: 'idle', items: [], left: null, trial: 2, suggestions: [], message: '', sending: false, error: '' })
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
      Object.assign(state, { items: data.items, left: data.left, trial: data.trial, suggestions: data.suggestions, status: 'ready' })
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

/** Sends a question; the question shows at once, the answer replaces the waiting star. */
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
    state.left = data.left
    return true
  } catch (error) {
    if (asked !== generation) return false
    state.items.splice(state.items.indexOf(draft), 1)
    // The trial ended in another tab: the field gives way to the invitation.
    if (error instanceof ApiError && error.code === 'trial_over') state.left = 0
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

export function useChat() {
  return { chat: state, load, ask, forget }
}
