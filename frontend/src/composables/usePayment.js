import { onUnmounted, ref } from 'vue'
import { webApi } from '../api/web.js'
import { errorText } from '../api/http.js'

/**
 * A payment at ЮKassa from a panel: `start` sends the person to ЮKassa's page, `follow` meets
 * them on the way back (?paid=ID) and asks how the payment stands until it is settled: every
 * two seconds for about a minute, then it leaves a word and lets the notification do the rest.
 *
 * `result`: '' | 'checking' | 'succeeded' | 'canceled' | 'waiting'.
 */
export function usePayment() {
  const result = ref('')
  const busy = ref(false)
  const message = ref('')
  let timer = 0
  let alive = true
  onUnmounted(() => {
    alive = false
    clearTimeout(timer)
  })

  async function start(body) {
    if (busy.value) return
    busy.value = true
    message.value = ''
    try {
      const { url } = await webApi.pay(body)
      window.location.assign(url)
    } catch (error) {
      message.value = errorText(error)
      busy.value = false
    }
  }

  function follow(id, onPaid) {
    result.value = 'checking'
    const ask = async (tries) => {
      if (!alive) return
      try {
        const payment = await webApi.payment(id)
        if (!alive) return
        if (payment.status === 'succeeded') {
          await onPaid(payment)
          result.value = 'succeeded'
          return
        }
        if (payment.status === 'canceled' || payment.status === 'failed') {
          result.value = 'canceled'
          return
        }
      } catch (error) {
        // Not this person's payment, or none at all: nothing to report.
        if (error?.code === 'missing') {
          result.value = ''
          return
        }
      }
      if (tries >= 30) {
        result.value = 'waiting'
        return
      }
      timer = setTimeout(() => ask(tries + 1), 2000)
    }
    ask(0)
  }

  return { result, busy, message, start, follow }
}

/** The payment's id from ?paid=, or 0. */
export function paidId(query) {
  const id = Number(query.paid)
  return Number.isInteger(id) && id > 0 ? id : 0
}
