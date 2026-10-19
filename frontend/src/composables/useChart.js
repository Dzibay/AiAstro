import { ref, shallowRef } from 'vue'
import { webApi } from '../api/web.js'
import { ApiError, errorText } from '../api/http.js'

/**
 * The person's natal chart, shared by the wheel on the sky and the panel beside it. Loaded once
 * per visit and forgotten when the birth data change; the readings are kept alongside.
 */

const chart = shallowRef(null)
/** idle → loading → ready | empty (no birth date yet) | error */
const status = ref('idle')
const message = ref('')
/** The point under the pointer, in the wheel or in the panel's list: its aspects light up. */
const hot = ref('')
const readings = new Map()
let pending = null

async function load() {
  if (status.value === 'ready' || status.value === 'empty') return
  if (pending) return pending
  status.value = 'loading'
  pending = webApi
    .chart()
    .then((data) => {
      chart.value = data
      status.value = 'ready'
    })
    .catch((error) => {
      if (error instanceof ApiError && error.code === 'no_birth') {
        status.value = 'empty'
        return
      }
      message.value = errorText(error)
      status.value = 'error'
    })
    .finally(() => {
      pending = null
    })
  return pending
}

/** After the birth data are saved: the next look recomputes. */
function forget() {
  chart.value = null
  status.value = 'idle'
  readings.clear()
}

/** The reading of one point: { title, text }, fetched once. */
function reading(id) {
  if (!readings.has(id)) {
    const request = webApi.chartItem(id)
    // A failed request is not kept, so the next look asks again.
    request.catch(() => readings.delete(id))
    readings.set(id, request)
  }
  return readings.get(id)
}

export function useChart() {
  return { chart, status, message, hot, load, forget, reading }
}
