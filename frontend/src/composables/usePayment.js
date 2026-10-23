import { ref } from 'vue'
import { webApi } from '../api/web.js'
import { errorText } from '../api/http.js'
import { reachGoal } from '../utils/track.js'

/**
 * A payment at ЮKassa from a panel: `start` sends the person to ЮKassa's page. The way back is
 * the cabinet; the purchase opens when ЮKassa's notification arrives. A pending mark in
 * sessionStorage lets the cabinet wait for that opening and fire the Metrika goal once.
 */

const PENDING_KEY = 'astra.pay.pending'
const PENDING_TTL_MS = 30 * 60 * 1000
const SETTLE_MS = 90 * 1000
const SETTLE_EVERY_MS = 2500

function rememberPending(meta) {
  try {
    sessionStorage.setItem(PENDING_KEY, JSON.stringify({ ...meta, at: Date.now() }))
  } catch {
    /* private mode */
  }
}

function readPending() {
  try {
    const raw = sessionStorage.getItem(PENDING_KEY)
    if (!raw) return null
    const data = JSON.parse(raw)
    if (!data || typeof data !== 'object' || !data.at || Date.now() - data.at > PENDING_TTL_MS) {
      sessionStorage.removeItem(PENDING_KEY)
      return null
    }
    return data
  } catch {
    return null
  }
}

function clearPending() {
  try {
    sessionStorage.removeItem(PENDING_KEY)
  } catch {
    /* private mode */
  }
}

/** True once the account shows the purchase that was started before ЮKassa. */
function opened(pending, now) {
  if (pending.product === 'synastry') return Boolean(now.partnerBought)
  if (!now.sky) return false
  if (!pending.sky) return true
  return Boolean(pending.skyUntil && now.skyUntil && now.skyUntil !== pending.skyUntil)
}

/**
 * After return from ЮKassa: poll until the purchase is on the account, then fire
 * `astra.payment@success`. `probe(pending)` returns `{ sky, skyUntil, partnerBought }`.
 */
export async function settlePendingPayment(probe) {
  const pending = readPending()
  if (!pending) return false
  const deadline = Date.now() + SETTLE_MS
  while (Date.now() <= deadline) {
    try {
      const now = await probe(pending)
      if (opened(pending, now)) {
        clearPending()
        reachGoal('astra.payment@success')
        return true
      }
    } catch {
      /* network blip: keep waiting */
    }
    await new Promise((resolve) => setTimeout(resolve, SETTLE_EVERY_MS))
  }
  clearPending()
  return false
}

export function usePayment() {
  const busy = ref(false)
  const message = ref('')

  /**
   * `body` goes to the API; `baseline` is what the account looked like before the charge
   * (`sky`, `skyUntil`, `partnerBought`) so a renewal or a pair can be told apart from a cancel.
   */
  async function start(body, baseline = {}) {
    if (busy.value) return
    busy.value = true
    message.value = ''
    try {
      const { url, id } = await webApi.pay(body)
      rememberPending({
        id,
        product: body.product,
        partner: body.partner || null,
        sky: Boolean(baseline.sky),
        skyUntil: baseline.skyUntil || null,
        partnerBought: Boolean(baseline.partnerBought),
      })
      window.location.assign(url)
    } catch (error) {
      message.value = errorText(error)
      busy.value = false
    }
  }

  return { busy, message, start }
}
