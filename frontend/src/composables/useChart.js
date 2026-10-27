import { ref, shallowRef, watch } from 'vue'
import { webApi } from '../api/web.js'
import { ApiError, errorText } from '../api/http.js'
import { webToken } from './useSession.js'

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
/**
 * What a chapter of the portrait speaks of, lit on the wheel together: { points, signs, houses }.
 * The pointer wins over it: a point under the pointer lights alone.
 */
const lens = shallowRef(null)
const readings = new Map()
let portraitRequest = null
let pending = null
// A request still in flight when the chart is forgotten must not write its stale answer back.
let generation = 0

async function load() {
  if (status.value === 'ready' || status.value === 'empty') return
  if (pending) return pending
  status.value = 'loading'
  const asked = generation
  pending = webApi
    .chart()
    .then((data) => {
      if (asked !== generation) return
      chart.value = data
      status.value = 'ready'
    })
    .catch((error) => {
      if (asked !== generation) return
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
  generation += 1
  pending = null
  chart.value = null
  lens.value = null
  status.value = 'idle'
  forgetReadings()
}

/** Another session (a logout, a login, another account) starts afresh: one person's data never show to the next. */
watch(webToken, () => forget(), { flush: 'sync' })

/** When «Небосвод» is lit or goes out: the texts come again, whole or veiled. */
function forgetReadings() {
  readings.clear()
  portraitRequest = null
}

/** The chart read as a whole: { reading, total, locked }, fetched once. */
function portrait() {
  if (!portraitRequest) {
    portraitRequest = webApi.portrait()
    portraitRequest.catch(() => {
      portraitRequest = null
    })
  }
  return portraitRequest
}

/** The reading of one point: { title, reading, aspects: [{ a, b, type, text }], locked }, fetched once. */
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
  return { chart, status, message, hot, lens, load, forget, forgetReadings, reading, portrait }
}
