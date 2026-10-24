import { ref } from 'vue'
import { siteApi } from '../api/site.js'

export const fallbackConfig = {
  site_name: 'Астра',
  tagline: 'Натальная карта обычным языком',
  support_email: '',
  support_telegram: '',
  prices: { sky: '', sky_3: '', sky_12: '', synastry: '', synastry_sky: '' },
  pay: false,
  ready: false,
}

const config = ref(null)
let pending = null

export function useSiteConfig() {
  async function load() {
    if (config.value) return config.value
    if (!pending) {
      pending = siteApi
        .config()
        .then((data) => {
          config.value = { ...data, ready: true }
          return config.value
        })
        .catch(() => {
          config.value = { ...fallbackConfig }
          return config.value
        })
    }
    return pending
  }

  return { config, load }
}

/** Where to write to the support: Telegram first, it is answered sooner; then the mail; null — nowhere yet. */
export function supportOf(config) {
  const telegram = config?.support_telegram
  if (telegram) return { label: `@${telegram}`, href: `https://t.me/${telegram}`, kind: 'telegram' }
  const mail = config?.support_email
  if (mail) return { label: mail, href: `mailto:${mail}`, kind: 'mail' }
  return null
}
