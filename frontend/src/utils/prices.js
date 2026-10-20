import { computed } from 'vue'
import { useSiteConfig } from '../composables/useSiteConfig.js'

const money = (value) => `${Number(value).toLocaleString('ru-RU')} ₽`

/**
 * Prices as the admin sets them (GET /site/config → prices): the exact sum once it is set, «от … ₽»
 * until then — the offer is visible, the number comes later.
 */
export function usePrices() {
  const { config, load } = useSiteConfig()
  load()
  const raw = computed(() => config.value?.prices || {})
  const label = (key) => (raw.value[key] ? money(raw.value[key]) : 'от … ₽')
  return {
    prices: raw,
    sky: computed(() => label('sky')),
    /** «Небосвод» per month at its cheapest: «от» only when a longer plan comes out cheaper. */
    skyMonthly: computed(() => {
      const monthly = Number(raw.value.sky) || 0
      if (!monthly) return 'от … ₽'
      const cheapest = Math.min(
        monthly,
        ...[['sky_3', 3], ['sky_12', 12]].map(([key, months]) => Math.round(Number(raw.value[key]) / months) || monthly),
      )
      return cheapest < monthly ? `от ${money(cheapest)}` : money(monthly)
    }),
    synastry: computed(() => label('synastry')),
    synastrySky: computed(() => label('synastry_sky')),
    /** Whether the shop is set up in the admin: the pay buttons wait for it. */
    pay: computed(() => Boolean(config.value?.pay)),
  }
}
