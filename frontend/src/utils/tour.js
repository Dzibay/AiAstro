import { reactive } from 'vue'

/**
 * The cabinet's introductions (CabinetTour): `intro` — the whole cabinet, once the birth date has
 * drawn the person's star; `sky` — what «Небосвод» opened, once it is lit. Each is shown once per
 * account in this browser; the «?» by the star and the profile bring it back at will.
 *
 * A section's own «?» opens `section` — a short walk through the open section, with no scene and
 * nothing remembered: it is there whenever asked.
 *
 * `kind` is the tour on screen ('' when none), `scene` whether its opening scene is still up,
 * `step` the spotlight step; `pair` opens the intro with the pair just joined by an invitation;
 * `flare` lists the sections flaring gold on the sky (CabinetSky) while «Небосвод» catches fire.
 */

const KEY = 'astra.tour'

function read() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || '{}') || {}
  } catch {
    return {}
  }
}
const seenMap = reactive(read())

export const tour = reactive({ kind: '', scene: false, step: 0, pair: false, flare: [] })

export const tourSeen = (userId, kind) => Boolean(seenMap[`${userId}:${kind}`])

export function markTourSeen(userId, kind) {
  if (!userId || seenMap[`${userId}:${kind}`]) return
  seenMap[`${userId}:${kind}`] = true
  try {
    localStorage.setItem(KEY, JSON.stringify(seenMap))
  } catch {
    // Private mode: the tour is not offered again until the tab closes.
  }
}

/**
 * Opens a tour at its scene; `pair` puts the joined pair first (intro only). The section tour has
 * no scene: it opens at step -1, and CabinetTour finds what the open section shows before step 0.
 */
export function startTour(kind, { pair = false } = {}) {
  const scene = kind !== 'section'
  Object.assign(tour, { kind, scene, step: scene ? 0 : -1, pair, flare: [] })
}

export function stopTour() {
  Object.assign(tour, { kind: '', scene: false, step: 0, pair: false, flare: [] })
}
