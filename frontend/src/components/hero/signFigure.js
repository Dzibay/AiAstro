import { PROJECTED, ZODIAC_BY_ID } from './zodiac.js'
import { ZODIAC_ART } from './zodiacArt.js'
import { starRadius } from './journey.js'

/**
 * A Sun sign drawn around a star, in the star's own coordinates, `span` across: the engraving's
 * strokes, the lines between the stars and the stars. The person's mark and a partner's star
 * on the pair page draw the same figure. Null for an unknown sign.
 */
export function signFigure(id, span) {
  const figure = ZODIAC_BY_ID[id]
  if (!figure) return null
  const map = ([x, y]) => `${((x / 1000 - 0.5) * span).toFixed(1)} ${((y / 1000 - 0.5) * span).toFixed(1)}`
  const stars = PROJECTED[id].map((p, index) => ({
    x: p.x * span,
    y: p.y * span,
    r: starRadius(figure.stars[index].mag) * 0.8,
  }))
  return {
    id,
    art: (ZODIAC_ART[id] || []).map((stroke, index) => ({ index, kind: stroke.kind, d: `M${stroke.pts.map(map).join('L')}` })),
    lines: figure.edges.map(([i, j]) => ({ key: `${i}-${j}`, a: stars[i], b: stars[j] })),
    stars,
  }
}
