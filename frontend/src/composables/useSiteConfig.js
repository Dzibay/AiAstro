import { ref } from 'vue'
import { siteApi } from '../api/site.js'

export const fallbackConfig = {
  site_name: 'Астра',
  tagline: 'Натальная карта обычным языком',
  support_email: '',
  prices: { sky: '', synastry: '', synastry_sky: '' },
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
