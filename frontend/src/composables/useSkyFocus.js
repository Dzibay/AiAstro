import { ref } from 'vue'

/**
 * Lets page copy point at the sky. The natal chart section lights a house sector on the
 * orbit while one of its spheres is hovered; the forecast preview turns the Sun and Moon.
 */

/** Orbit sectors for the spheres, radians clockwise from the apex, in list order. */
export const HOUSE_SECTORS = [
  { from: -1.5, to: -1.02, label: 'I' },
  { from: -1.0, to: -0.52, label: 'II' },
  { from: -0.5, to: -0.02, label: 'IV' },
  { from: 0.02, to: 0.5, label: 'V' },
  { from: 0.52, to: 1.0, label: 'VI · X' },
  { from: 1.02, to: 1.5, label: 'VII' },
]

const skyHouse = ref(-1)

/** Extra turn of the Sun and Moon along the orbit at the forecasts stop, radians. */
const skyTurn = ref(0)
const skyTurning = ref(false)
let tween = 0

/** Eases the Sun and Moon to a new turn, as the forecast preview switches between day and week. */
function turnSky(goal, duration = 1100) {
  cancelAnimationFrame(tween)
  skyTurning.value = false
  const from = skyTurn.value
  if (from === goal) return
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    skyTurn.value = goal
    return
  }
  const start = performance.now()
  skyTurning.value = true
  const step = (now) => {
    const t = Math.min(1, (now - start) / duration)
    const e = t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2
    skyTurn.value = from + (goal - from) * e
    if (t < 1) tween = requestAnimationFrame(step)
    else skyTurning.value = false
  }
  tween = requestAnimationFrame(step)
}

export function useSkyFocus() {
  return { skyHouse, skyTurn, skyTurning, turnSky }
}
