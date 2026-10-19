/**
 * Hero geometry. The reference frame is 1770×889: orbit r = 554, planet R = 1180,
 * planet top 640, orbit centre 36 px below it. Everything scales with `u`.
 */

export const TAU = Math.PI * 2

/** Moon trails the Sun along the orbit by this angle, radians. */
export const MOON_OFFSET = 1.1
/** Sun angle limits, radians clockwise from the apex. At the ends one body sets behind the planet. */
export const SUN_MIN = -1.86
export const SUN_MAX = 0.76
export const SUN_HOME = -0.4

export function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

export function smoothstep(edge0, edge1, value) {
  const t = clamp((value - edge0) / (edge1 - edge0), 0, 1)
  return t * t * (3 - 2 * t)
}

export function signedAngle(theta) {
  let turn = ((theta % TAU) + TAU) % TAU
  if (turn > Math.PI) turn -= TAU
  return turn
}

export function layout(width, height) {
  const W = Math.max(width, 1)
  const H = Math.max(height, 1)
  const narrow = W < 760
  let u
  let planetTop
  if (narrow) {
    u = W / 700
    // Copy sits on top; the orbit opens below it so the Sun and Moon never cover the text.
    planetTop = Math.max(H * 0.78, 470 + 560 * u)
  } else {
    u = Math.min(H / 889, W / 1500)
    const orbitTop = Math.max(H * 0.137, 92)
    planetTop = orbitTop + 518 * u
  }
  const cx = W / 2
  const planetR = 1180 * u
  return {
    W,
    H,
    u,
    narrow,
    cx,
    orbit: { cx, cy: planetTop + 36 * u, r: 554 * u },
    planet: { cx, cy: planetTop + planetR, r: planetR, top: planetTop },
  }
}

export function onOrbit(orbit, theta, inset = 0) {
  const r = orbit.r - inset
  return { x: orbit.cx + r * Math.sin(theta), y: orbit.cy - r * Math.cos(theta) }
}

export function angleAt(orbit, x, y) {
  return Math.atan2(x - orbit.cx, -(y - orbit.cy))
}

/** 0 = cold night (Moon high, Sun set), 1 = warm (Sun high, Moon set). */
export function warmthOf(sunTheta) {
  const sunUp = Math.cos(sunTheta)
  const moonUp = Math.cos(sunTheta + MOON_OFFSET)
  return smoothstep(-0.9, 0.9, sunUp - moonUp + 0.15)
}
