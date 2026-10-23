import { reactive } from 'vue'

/**
 * The natal sky game (NatalGame) and the chart page around it (CabinetView): `offer` — the card
 * asking whether to build the chart by hand is up; `open` — the game is on screen; `landing` — its
 * last picture is turning into the wheel, which already shows beneath it. `runs` counts the starts,
 * so a replay mounts the game afresh.
 */
export const game = reactive({ offer: false, open: false, landing: false, runs: 0 })

let supported = null

/** three.js r170 draws with WebGL2 only: asked once, and the test context let go at once. */
export function gameSupported() {
  if (supported === null) {
    try {
      const context = document.createElement('canvas').getContext('webgl2')
      supported = Boolean(context)
      context?.getExtension('WEBGL_lose_context')?.loseContext()
    } catch {
      supported = false
    }
  }
  return supported
}

export function startGame() {
  Object.assign(game, { offer: false, open: true, landing: false, runs: game.runs + 1 })
}

export function landGame() {
  game.landing = true
}

export function closeGame() {
  Object.assign(game, { offer: false, open: false, landing: false })
}
