/**
 * The geometry of the natal sky game (NatalGame): the Solar System squeezed to fit a screen, with
 * the zodiac as a belt of twelve equal 30° sectors around the Sun. A sign is a direction: the line
 * of sight from the Earth through a body lights the sector of the belt it reaches.
 *
 * Everything here is flat, in the plane of the ecliptic: points are [x, y] with y to the north of
 * the vernal point's side, angles are ecliptic longitudes in degrees, counter-clockwise seen from
 * the north. The scene lays a point [x, y] at (x, 0, −y).
 */

/**
 * Orbit radii, not to scale: wide enough apart to grab, and with the inner two kept in the true
 * proportion to the Earth's, so Mercury and Venus never stray from the Sun further than they do
 * in the sky (about 28° and 47°).
 */
export const ORBITS = {
  mercury: 4.6,
  venus: 7.4,
  earth: 10,
  mars: 13.5,
  jupiter: 18,
  saturn: 21.5,
  uranus: 24.5,
  neptune: 27,
  pluto: 29.5,
}
export const MOON_ORBIT = 1.9
export const EARTH_RADIUS = 0.62

/** The belt of signs; its inner edge is 0.85 of the outer one, as on the wheel (NatalWheel). */
export const BELT = { inner: 34, outer: 40, mid: 37 }

/** Where the bodies stand on the wheel once the Earth is in the middle (NatalWheel: planets at 0.635 r or 0.68 r). */
export const wheelRadius = (houses) => BELT.outer * (houses ? 0.635 : 0.68)

/** The slow ones: they arrive by themselves in the finale. */
export const OUTER = ['jupiter', 'saturn', 'uranus', 'neptune', 'pluto']

const RAD = Math.PI / 180

export const wrap = (deg) => ((deg % 360) + 360) % 360
/** The signed turn from a to b, in (−180, 180]. */
export const gap = (a, b) => {
  const d = wrap(b - a)
  return d > 180 ? d - 360 : d
}
export const signAt = (lon) => Math.floor(wrap(lon) / 30) % 12

export const toward = (deg, r = 1) => [r * Math.cos(deg * RAD), r * Math.sin(deg * RAD)]
export const angleOf = ([x, y]) => wrap(Math.atan2(y, x) / RAD)
export const add = (a, b) => [a[0] + b[0], a[1] + b[1]]
export const sub = (a, b) => [a[0] - b[0], a[1] - b[1]]

/**
 * A ray from `from` heading `deg` meets the belt's middle circle (`from` is always inside it):
 * returns the point and its longitude seen from the Sun, which names the sign the ray lights.
 */
export function beltHit(from, deg, radius = BELT.mid) {
  const d = toward(deg)
  const b = from[0] * d[0] + from[1] * d[1]
  const c = from[0] * from[0] + from[1] * from[1] - radius * radius
  const s = -b + Math.sqrt(Math.max(0, b * b - c))
  const point = add(from, [d[0] * s, d[1] * s])
  return { point, lon: angleOf(point), length: s }
}

/** The heading from `from` to the point of the belt at longitude `lon`. */
export function aimAt(from, lon) {
  return angleOf(sub(toward(lon, BELT.mid), from))
}

/**
 * Where on an orbit of radius `r` (about the Sun) a body stands on the line of sight from `from`
 * toward the belt at `lon`. An inner orbit is crossed twice: the crossing nearest `near` (a
 * longitude on the orbit) is taken. Should the line pass the orbit by, the point where it comes
 * closest stands in, the body at its greatest elongation.
 */
export function onOrbit(from, lon, r, near = 0) {
  const t = toward(lon, BELT.mid)
  const span = Math.hypot(t[0] - from[0], t[1] - from[1])
  const d = [(t[0] - from[0]) / span, (t[1] - from[1]) / span]
  const b = from[0] * d[0] + from[1] * d[1]
  const c = from[0] * from[0] + from[1] * from[1] - r * r
  const disc = b * b - c
  if (disc < 0) return angleOf(add(from, [d[0] * -b, d[1] * -b]))
  const roots = [-b - Math.sqrt(disc), -b + Math.sqrt(disc)].filter((s) => s > 0)
  const options = roots.map((s) => angleOf(add(from, [d[0] * s, d[1] * s])))
  if (!options.length) return angleOf(add(from, [d[0] * -b, d[1] * -b]))
  return options.reduce((best, option) => (Math.abs(gap(near, option)) < Math.abs(gap(near, best)) ? option : best))
}
