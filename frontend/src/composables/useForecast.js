import { reactive } from 'vue'
import { webApi } from '../api/web.js'
import { ApiError, errorText } from '../api/http.js'

/**
 * The day and the week (GET /me/forecast), shared by the forecast panel, the wheel's transits and
 * the overview's line about the Moon. Each period is asked once per visit and forgotten when the
 * birth data change or «Небосвод» opens.
 */

export const PERIODS = ['day', 'week']

/** status: idle → loading → ready | empty (no birth date yet) | error */
const blank = () => ({ status: 'idle', data: null, message: '' })
const state = reactive(Object.fromEntries(PERIODS.map((period) => [period, blank()])))
const pending = new Map()
// A request still in flight when the data are forgotten must not write its stale answer back.
let generation = 0

/** Where the person is now: the day starts at their midnight, not at the birthplace's. */
function zone() {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || ''
  } catch {
    return ''
  }
}

function load(period) {
  const entry = state[period]
  if (!entry || entry.status === 'ready' || entry.status === 'empty') return Promise.resolve()
  if (pending.has(period)) return pending.get(period)
  entry.status = 'loading'
  const asked = generation
  const request = webApi
    .forecast(period, zone())
    .then((data) => {
      if (asked !== generation) return
      entry.data = data
      entry.status = 'ready'
    })
    .catch((error) => {
      if (asked !== generation) return
      if (error instanceof ApiError && error.code === 'no_birth') {
        entry.status = 'empty'
        return
      }
      entry.message = errorText(error)
      entry.status = 'error'
    })
    .finally(() => {
      if (pending.get(period) === request) pending.delete(period)
    })
  pending.set(period, request)
  return request
}

function forget() {
  generation += 1
  for (const period of PERIODS) Object.assign(state[period], blank())
  pending.clear()
}

export function useForecast() {
  return { forecasts: state, load, forget }
}
