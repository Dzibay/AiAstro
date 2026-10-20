import { reactive } from 'vue'

/**
 * What the visitor has already tried on the home sky: dragging the Sun or the Moon, opening a
 * constellation. Each hint stays until its own gesture is made once, then leaves for good.
 */
const STORE_KEY = 'aiastro_tried'

function read() {
  try {
    return JSON.parse(localStorage.getItem(STORE_KEY) || '{}') || {}
  } catch {
    return {}
  }
}

export const tried = reactive({ sun: false, figure: false, ...read() })

export function markTried(what) {
  if (tried[what]) return
  tried[what] = true
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify({ ...tried }))
  } catch {
    /* private mode: the hint leaves for this visit */
  }
}
