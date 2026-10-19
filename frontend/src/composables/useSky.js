import { reactive, ref, shallowRef } from 'vue'
import { layout } from '../components/hero/sky.js'

/**
 * The sky lives once, at App level (SkyStage), and outlives page changes. Pages talk to it here:
 * the home page drives it by scroll through a journey source; its hero copy reads the layout back.
 */

/** Layout of the stage, see sky.js layout(). */
const geo = shallowRef(layout(1280, 720))
/** Smoothed scroll position as a float stop index, see journey.js. */
const journey = ref(0)
/** How much the Sun dominates the scene, 0..1. */
const warm = ref(0.5)
/** Stop of the open constellation card, or -1. */
const openStop = ref(-1)

/**
 * The page that scrolls the sky: { at() → exact journey for the current scroll, next(atEnd) }.
 * Without one the sky rests at the start.
 */
const source = shallowRef(null)

/**
 * The person's own mark on the login sky: the star of their name and, once the birth date
 * is known, the engraving of their Sun sign around it. `place` is the name the star
 * was placed by (set once the name is typed), `flash` counts its flashes;
 * `sun` and `moon` are sign ids from skyToday.js, '' while unknown.
 */
const mark = reactive({ name: '', place: '', flash: 0, sun: '', moon: '' })

export function useSky() {
  return { geo, journey, warm, openStop, source, mark }
}
