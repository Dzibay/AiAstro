import { computed } from 'vue'
import { useSiteConfig } from '../composables/useSiteConfig.js'

/**
 * Prices as the admin sets them (GET /site/config → prices). Until a price is set the page says
 * «от … ₽»: the offer is visible, the number comes later.
 */
export function usePrices() {
  const { config, load } = useSiteConfig()
  load()
  const raw = computed(() => config.value?.prices || {})
  const label = (key) => (raw.value[key] ? `от ${Number(raw.value[key]).toLocaleString('ru-RU')} ₽` : 'от … ₽')
  return {
    prices: raw,
    sky: computed(() => label('sky')),
    synastry: computed(() => label('synastry')),
    synastrySky: computed(() => label('synastry_sky')),
    /** Whether the shop is set up in the admin: the pay buttons wait for it. */
    pay: computed(() => Boolean(config.value?.pay)),
  }
}
