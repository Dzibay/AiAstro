import { ref } from 'vue'
import { webApi } from '../api/web.js'
import { errorText } from '../api/http.js'

/**
 * A payment at ЮKassa from a panel: `start` sends the person to ЮKassa's page. The way back is
 * the cabinet; the purchase opens when ЮKassa's notification arrives.
 */
export function usePayment() {
  const busy = ref(false)
  const message = ref('')

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

  return { busy, message, start }
}
