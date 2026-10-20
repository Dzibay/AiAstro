import { reactive } from 'vue'

/**
 * What the dome on the sky (SkyDome) and the panel of «Небосвод» (SkyPanel) share: the feature
 * under the pointer or the focus on either side (`focus`), the row opened by a press (`opened`),
 * the try-on of the lit sky, and the moment of lighting after a payment, when the
 * constellations catch fire one by one.
 */
const offer = reactive({ focus: '', opened: '', preview: false, celebrate: 0 })

export function useSkyOffer() {
  return offer
}
