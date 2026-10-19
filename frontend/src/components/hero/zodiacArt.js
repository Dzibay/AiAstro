/**
 * Engraving-style outlines of the zodiac animals, drawn in each constellation's own
 * 0..1000 box (the same box the projected stars live in, x right, y down), so the real
 * stars sit on the body: Hamal on the ram's head, Aldebaran as the bull's eye,
 * Antares as the scorpion's heart.
 *
 * Every figure is a list of strokes `{ pts, kind }`, already sampled into polylines:
 * `outline` is the silhouette, `detail` are ridges and joints, `hatch` is light shading.
 */

const STEPS = 10

/** Uniform Catmull-Rom through the points, sampled into a dense polyline. */
function spline(points, steps = STEPS) {
  if (points.length < 3) return points.map((p) => [...p])
  const out = []
  for (let i = 0; i < points.length - 1; i += 1) {
    const p0 = points[i - 1] || points[i]
    const p1 = points[i]
    const p2 = points[i + 1]
    const p3 = points[i + 2] || p2
    for (let s = 0; s < steps; s += 1) {
      const t = s / steps
      const t2 = t * t
      const t3 = t2 * t
      out.push([0, 1].map((k) => 0.5 * (
        2 * p1[k]
        + (-p0[k] + p2[k]) * t
        + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2
        + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t3
      )))
    }
  }
  out.push([...points[points.length - 1]])
  return out
}

function curve(points, kind = 'outline') {
  return { pts: spline(points), kind }
}

function tangentAt(pts, i) {
  const a = pts[Math.max(0, i - 1)]
  const b = pts[Math.min(pts.length - 1, i + 1)]
  const len = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1
  return [(b[0] - a[0]) / len, (b[1] - a[1]) / len]
}

/**
 * A tapered band along a spine: horns, legs, tails, the scorpion's segments.
 * `open` leaves the start uncapped so a limb grows out of the body instead of crossing it.
 * `joints` draws a slightly bowed cross line at every inner control point.
 */
function ribbon(points, widths, { open = false, joints = false, jointKind = 'detail' } = {}) {
  const pts = spline(points)
  const half = pts.map((_, i) => {
    const seg = Math.min(Math.floor(i / STEPS), widths.length - 2)
    const t = i / STEPS - seg
    const e = t * t * (3 - 2 * t)
    return (widths[seg] + (widths[seg + 1] - widths[seg]) * e) / 2
  })
  const left = []
  const right = []
  pts.forEach((p, i) => {
    const [tx, ty] = tangentAt(pts, i)
    left.push([p[0] - ty * half[i], p[1] + tx * half[i]])
    right.push([p[0] + ty * half[i], p[1] - tx * half[i]])
  })

  const cap = (index, forward) => {
    const r = half[index]
    if (r < 1.5) return []
    const [tx, ty] = tangentAt(pts, index)
    const p = pts[index]
    const dir = forward ? 1 : -1
    const list = []
    for (let k = 1; k < 8; k += 1) {
      const a = (k / 8) * Math.PI
      // From the left edge, round through the tip, to the right edge.
      const nx = -ty * Math.cos(a) + tx * dir * Math.sin(a)
      const ny = tx * Math.cos(a) + ty * dir * Math.sin(a)
      list.push([p[0] + nx * r, p[1] + ny * r])
    }
    return list
  }

  const last = pts.length - 1
  let outline = [...left, ...cap(last, true), ...right.reverse()]
  if (!open) outline = [...outline, ...cap(0, false).reverse(), left[0]]
  const strokes = [{ pts: outline, kind: 'outline' }]

  if (joints) {
    for (let c = 1; c < points.length - 1; c += 1) {
      const i = c * STEPS
      const [tx, ty] = tangentAt(pts, i)
      const r = half[i]
      const p = pts[i]
      strokes.push(curve([
        [p[0] - ty * r * 0.96, p[1] + tx * r * 0.96],
        [p[0] - tx * r * 0.22, p[1] - ty * r * 0.22],
        [p[0] + ty * r * 0.96, p[1] - tx * r * 0.96],
      ], jointKind))
    }
  }
  return strokes
}

/** A small open spiral, for wool curls and eyes. */
function curl(x, y, r, turn = 1.4, start = 0) {
  const pts = []
  for (let i = 0; i <= 18; i += 1) {
    const t = i / 18
    const a = start + t * turn * Math.PI * 2
    const rr = r * (1 - t * 0.55)
    pts.push([x + Math.cos(a) * rr, y + Math.sin(a) * rr])
  }
  return { pts, kind: 'hatch' }
}

function hatchRow(from, step, vector, count) {
  const list = []
  for (let i = 0; i < count; i += 1) {
    const x = from[0] + step[0] * i
    const y = from[1] + step[1] * i
    list.push({ pts: [[x, y], [x + vector[0], y + vector[1]]], kind: 'hatch' })
  }
  return list
}

/** Rotate a whole figure designed in its own frame into the constellation box. */
function place(strokes, [px, py], degrees) {
  const a = (degrees * Math.PI) / 180
  const c = Math.cos(a)
  const s = Math.sin(a)
  return strokes.map((stroke) => ({
    ...stroke,
    pts: stroke.pts.map(([x, y]) => [px + x * c - y * s, py + x * s + y * c]),
  }))
}

/* ---------- Aries: a leaping ram with its neck stretched forward, built level and tilted 33° ---------- */
function aries() {
  const ram = [
    // back and crest of the neck; Hamal rides the neck
    curve([[30, -50], [180, -88], [380, -100], [560, -104], [700, -112], [830, -128], [930, -144]]),
    // face: Sheratan on the brow, Mesarthim on the nose
    curve([[930, -144], [1010, -122], [1080, -82], [1140, -22], [1164, 12], [1150, 40], [1108, 52], [1060, 50], [1000, 66], [950, 62]]),
    // throat, chest, belly
    curve([[950, 62], [860, 82], [760, 122], [680, 172], [632, 204], [560, 218], [440, 222], [330, 210], [250, 190]]),
    // haunch round to the tail
    curve([[250, 190], [150, 180], [60, 150], [0, 100], [-20, 40], [-4, -8], [30, -50]]),
    // nostril, mouth, eye
    curve([[1128, -2], [1140, -12], [1150, -2]], 'detail'),
    curve([[1150, 40], [1110, 32], [1084, 38]], 'detail'),
    curve([[1012, -64], [1034, -78], [1058, -66], [1034, -56], [1012, -64]], 'detail'),
    // forelegs: one stretched forward, one tucked
    ...ribbon([[650, 140], [760, 190], [870, 222], [960, 252]], [86, 48, 30, 28], { open: true, joints: true, jointKind: 'hatch' }),
    ...ribbon([[600, 170], [690, 232], [764, 284], [702, 334]], [76, 44, 30, 28], { open: true, joints: true, jointKind: 'hatch' }),
    // hind legs pushing off
    ...ribbon([[176, 116], [150, 240], [120, 340], [90, 440]], [110, 56, 32, 28], { open: true, joints: true, jointKind: 'hatch' }),
    ...ribbon([[262, 140], [262, 250], [244, 340], [288, 430]], [90, 50, 32, 28], { open: true, joints: true, jointKind: 'hatch' }),
    // short raised tail towards 39 Ari
    ...ribbon([[30, -40], [-20, -80], [-70, -113]], [40, 26, 6], { open: true }),
    // the curled horn around the cheek, ridged
    ...ribbon(
      [[932, -150], [846, -146], [810, -56], [856, 30], [940, 42], [984, -18], [954, -72], [926, -56]],
      [58, 52, 46, 38, 28, 18, 9, 3],
      { joints: true },
    ),
    // fleece
    curl(140, -30, 26, 1.3, 0.4),
    curl(290, -40, 26, 1.3, 2.2),
    curl(440, -50, 24, 1.3, 1.1),
    curl(590, -46, 24, 1.3, 3.0),
    curl(220, 70, 28, 1.3, 2.6),
    curl(370, 50, 28, 1.3, 0.8),
    curl(520, 70, 26, 1.3, 1.7),
    curl(700, 0, 24, 1.3, 0.2),
    curl(80, 40, 22, 1.3, 1.2),
    curl(430, 150, 22, 1.3, 2.9),
  ]
  return place(ram, [40, 250], 33)
}

/* ---------- Taurus: the charging forequarters, head low, horns to Elnath and ζ Tau ---------- */
function taurus() {
  return [
    // lyre horns, tips on Elnath and Tianguan
    ...ribbon([[540, 500], [450, 436], [330, 400], [206, 318], [117, 180]], [76, 54, 36, 18, 3], { joints: true }),
    ...ribbon([[470, 566], [340, 604], [200, 584], [80, 504], [0, 408]], [72, 50, 32, 16, 3], { joints: true }),
    // face: the Hyades V, nose down, Aldebaran the eye
    curve([[468, 546], [430, 612], [452, 682], [520, 732], [572, 750], [622, 738], [652, 700], [662, 630], [632, 560], [584, 506]]),
    curve([[536, 724], [550, 712], [566, 724]], 'detail'),
    curve([[596, 722], [610, 710], [624, 722]], 'detail'),
    curve([[522, 744], [572, 760], [620, 748]], 'detail'),
    curve([[436, 592], [459, 576], [486, 590], [459, 606], [436, 592]], 'detail'),
    curve([[500, 540], [540, 520], [590, 530]], 'hatch'),
    // ear
    curve([[604, 522], [682, 482], [724, 492], [684, 532], [634, 552]]),
    // crest of the neck and the hump that carries the Pleiades
    curve([[584, 490], [650, 430], [740, 372], [820, 332], [930, 318], [1060, 330]]),
    // dewlap down to the chest through λ Tau
    curve([[642, 722], [700, 772], [780, 802]]),
    // shoulder
    curve([[828, 420], [800, 520], [818, 600], [862, 646]], 'detail'),
    // forelegs: one raised through ξ/ο Tau, one folded under
    ...ribbon([[862, 640], [940, 722], [996, 802], [962, 882], [932, 952]], [116, 72, 46, 34, 30], { open: true, joints: true, jointKind: 'hatch' }),
    ...ribbon([[772, 776], [720, 860], [680, 920], [760, 962]], [84, 50, 34, 30], { open: true, joints: true, jointKind: 'hatch' }),
    // the body dissolves into the sky
    curve([[1060, 330], [1092, 450], [1072, 560], [1102, 680]], 'hatch'),
    curve([[960, 720], [1040, 700], [1100, 706]], 'hatch'),
    ...hatchRow([660, 600], [44, -26], [50, 40], 6),
    ...hatchRow([890, 400], [36, 6], [-6, 56], 5),
  ]
}

/* ---------- Capricorn: the sea-goat, goat in front, scaled fish tail curling to Deneb Algedi ---------- */
function capricorn() {
  return [
    // horn sweeping back from the brow
    ...ribbon([[962, 162], [932, 70], [856, 8], [776, 18]], [40, 30, 16, 3], { joints: true }),
    // head: Algedi on the brow, Dabih at the eye
    curve([[942, 172], [1000, 150], [1042, 190], [1076, 258], [1080, 300], [1050, 322], [1010, 312], [972, 332]]),
    curve([[990, 214], [1006, 204], [1022, 216], [1006, 224], [990, 214]], 'detail'),
    curve([[1012, 316], [1004, 360], [986, 392]], 'detail'),
    curve([[952, 202], [890, 232], [870, 262], [930, 244]]),
    // neck and chest of the goat
    curve([[942, 176], [880, 278], [780, 350], [640, 378], [560, 376]]),
    curve([[972, 332], [900, 420], [820, 500], [760, 560], [680, 594], [580, 606]]),
    // folded forelegs, hooves on ψ and ω Cap
    ...ribbon([[784, 536], [834, 640], [744, 702], [664, 750]], [72, 42, 28, 24], { open: true, joints: true }),
    ...ribbon([[704, 566], [722, 690], [646, 768], [598, 832]], [64, 38, 28, 24], { open: true, joints: true }),
    // fish body with scale bands
    ...ribbon(
      [[620, 488], [452, 494], [300, 488], [182, 450], [82, 390], [22, 350]],
      [236, 228, 190, 120, 60, 26],
      { open: true, joints: true },
    ),
    // tail fin
    curve([[24, 346], [-14, 272], [-70, 196], [-124, 160], [-104, 236], [-52, 302], [4, 344]]),
    curve([[24, 356], [-24, 440], [-86, 516], [-136, 552], [-110, 470], [-50, 400], [4, 358]]),
    curve([[16, 346], [-52, 248]], 'hatch'),
    curve([[16, 348], [-88, 210]], 'hatch'),
    curve([[16, 356], [-62, 456]], 'hatch'),
    curve([[16, 358], [-100, 520]], 'hatch'),
    curl(380, 470, 22, 1.2, 0.5),
    curl(250, 452, 18, 1.2, 2.0),
    ...hatchRow([840, 260], [-36, 18], [-20, 60], 5),
  ]
}

/* ---------- Scorpio: claws reaching to Acrab and ρ Sco, Antares as the heart, sting at Shaula ---------- */
function scorpio() {
  const body = ribbon(
    [[910, 228], [800, 262], [683, 292], [604, 372], [532, 482], [488, 604], [472, 762], [452, 904], [382, 984], [252, 1006], [122, 982], [44, 902], [58, 826], [118, 764]],
    [150, 150, 134, 112, 92, 72, 50, 44, 42, 40, 38, 34, 28, 6],
    { joints: true },
  )
  const sting = curve([[118, 764], [150, 742], [178, 750], [160, 770], [126, 772]])

  const leg = (points) => ribbon(points, [16, 12, 8, 4], { open: true, joints: true, jointKind: 'hatch' })
  const legs = [
    leg([[850, 196], [830, 118], [770, 74], [728, 70]]),
    leg([[796, 212], [748, 136], [686, 112], [646, 118]]),
    leg([[742, 228], [672, 170], [610, 162], [574, 174]]),
    leg([[690, 250], [612, 220], [556, 230], [526, 252]]),
    leg([[868, 290], [884, 380], [852, 452], [826, 480]]),
    leg([[816, 314], [810, 410], [762, 474], [732, 494]]),
    leg([[760, 336], [716, 432], [660, 460], [628, 466]]),
    leg([[708, 356], [636, 418], [578, 426], [548, 418]]),
  ].flat()

  const claw = (arm, hand, finger) => [
    ...ribbon(arm, [40, 34, 30], { open: true, joints: true }),
    ...ribbon(hand, [30, 70, 44, 0]),
    curve(finger),
  ]

  return [
    ...body,
    sting,
    ...legs,
    // upper claw past Dschubba to Acrab
    ...claw(
      [[930, 176], [966, 112], [990, 40]],
      [[990, 40], [1020, -20], [1052, -82], [1062, -146]],
      [[1036, -12], [1086, -52], [1104, -112], [1082, -156]],
    ),
    // lower claw past π and ρ Sco
    ...claw(
      [[940, 270], [990, 322], [1010, 392]],
      [[1010, 392], [1062, 432], [1124, 452], [1186, 452]],
      [[1052, 452], [1104, 484], [1164, 486], [1196, 468]],
    ),
    // carapace ridge and eyes
    curve([[960, 196], [920, 232], [870, 252]], 'detail'),
    curl(948, 214, 8, 1, 0),
    curl(946, 246, 8, 1, 0),
  ]
}

export const ZODIAC_ART = {
  aries: aries(),
  taurus: taurus(),
  capricorn: capricorn(),
  scorpio: scorpio(),
}
