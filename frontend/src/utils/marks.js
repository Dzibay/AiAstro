import { reactive, watch } from 'vue'
import { webApi } from '../api/web.js'
import { webToken } from '../composables/useSession.js'

/**
 * What the person has been through in the cabinet: the tours (`tour:intro`, `tour:sky`) and the
 * newcomer steps that leave no other trace (`step:sun`, `step:chat`). Kept in the account
 * (GET /me → marks, POST /me/marks), so another device or another account in this browser
 * starts from its own.
 */

const state = reactive({ owner: null, set: new Set() })

/** Before marks lived in the account they were kept in this browser as { "<user id>:<name>": true }. */
const LEGACY = [['astra.tour', 'tour'], ['astra.newcomer', 'step']]
const NAME = /^[a-z][a-z-]{0,23}$/

function moveLegacy(userId) {
  const found = []
  for (const [key, kind] of LEGACY) {
    try {
      const saved = JSON.parse(localStorage.getItem(key) || '{}') || {}
      let changed = false
      for (const entry of Object.keys(saved)) {
        const [owner, name] = entry.split(':')
        if (Number(owner) !== userId) continue
        // The account takes only names it knows the shape of (as the server checks them).
        if (NAME.test(name || '')) found.push(`${kind}:${name}`)
        delete saved[entry]
        changed = true
      }
      if (!changed) continue
      if (Object.keys(saved).length) localStorage.setItem(key, JSON.stringify(saved))
      else localStorage.removeItem(key)
    } catch {
      // Private mode or a broken entry: nothing to move.
    }
  }
  return found
}

/** The person as read from GET /me: their marks become the cabinet's, with any still in flight kept. */
export function takeMarks(user) {
  if (!user?.id) return
  const own = state.owner === user.id ? [...state.set] : []
  state.owner = user.id
  state.set = new Set([...(user.marks || []), ...own])
  const legacy = moveLegacy(user.id).filter((name) => !state.set.has(name))
  if (!legacy.length) return
  legacy.forEach((name) => state.set.add(name))
  webApi.addMarks(legacy).catch(() => {})
}

export const hasMark = (userId, name) => state.owner === userId && state.set.has(name)

export function addMark(userId, name) {
  if (!userId || state.owner !== userId || state.set.has(name)) return
  state.set.add(name)
  // On a failure the mark holds for this visit; the next one may offer the tour again.
  webApi.addMarks([name]).catch(() => {})
}

watch(webToken, () => {
  state.owner = null
  state.set = new Set()
}, { flush: 'sync' })
