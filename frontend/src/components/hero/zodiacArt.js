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

/** A closed ellipse, for heads, shells, pans and fish eyes. */
function ring(cx, cy, rx, ry, degrees = 0, kind = 'outline') {
  const a = (degrees * Math.PI) / 180
  const pts = []
  for (let i = 0; i <= 40; i += 1) {
    const t = (i / 40) * Math.PI * 2
    const x = Math.cos(t) * rx
    const y = Math.sin(t) * ry
    pts.push([cx + x * Math.cos(a) - y * Math.sin(a), cy + x * Math.sin(a) + y * Math.cos(a)])
  }
  return { pts, kind }
}

/** A head in profile for the human signs: the star sits on the face, the hair falls behind. */
function head(x, y, r, facing = 1) {
  const f = facing
  return [
    ring(x, y, r * 0.84, r),
    curve([[x - f * r * 0.2, y - r * 0.98], [x - f * r * 0.9, y - r * 0.6], [x - f * r * 1.1, y + r * 0.1], [x - f * r * 0.9, y + r * 0.9]], 'detail'),
    curl(x - f * r * 0.55, y - r * 0.35, r * 0.28, 1.2, 0.6),
    curl(x - f * r * 0.62, y + r * 0.3, r * 0.26, 1.2, 2.4),
    curve([[x + f * r * 0.3, y - r * 0.14], [x + f * r * 0.46, y - r * 0.2], [x + f * r * 0.56, y - r * 0.12]], 'detail'),
  ]
}

/** A pincer: the arm, the fixed finger tapering to a point, and the movable finger beside it. */
function claw(arm, hand, finger, armWidths = [40, 34, 30]) {
  return [
    ...ribbon(arm, armWidths, { open: true, joints: true }),
    ...ribbon(hand, [armWidths[armWidths.length - 1], 70, 44, 0]),
    curve(finger),
  ]
}

/** A limb with hatched joints, growing out of the body. */
function limb(points, widths) {
  return ribbon(points, widths, { open: true, joints: true, jointKind: 'hatch' })
}

/**
 * A fish designed facing +x around the origin, `len` long and `tall` high, with its tail at -x.
 * Returns strokes and the point where the tail ends, for the cord.
 */
function fish(len, tall) {
  const L = len
  const H = tall
  return [
    curve([[-0.34 * L, 0], [-0.18 * L, -0.34 * H], [0.08 * L, -0.5 * H], [0.32 * L, -0.38 * H], [0.5 * L, -0.04 * H], [0.46 * L, 0.12 * H]]),
    curve([[0.46 * L, 0.12 * H], [0.3 * L, 0.36 * H], [0.06 * L, 0.46 * H], [-0.18 * L, 0.32 * H], [-0.34 * L, 0]]),
    // forked tail
    curve([[-0.34 * L, 0], [-0.5 * L, -0.24 * H], [-0.64 * L, -0.46 * H], [-0.58 * L, -0.1 * H], [-0.54 * L, 0], [-0.58 * L, 0.1 * H], [-0.64 * L, 0.46 * H], [-0.5 * L, 0.24 * H], [-0.34 * L, 0]]),
    curve([[-0.38 * L, -0.02 * H], [-0.58 * L, -0.34 * H]], 'hatch'),
    curve([[-0.38 * L, 0.02 * H], [-0.58 * L, 0.34 * H]], 'hatch'),
    // dorsal and belly fins
    curve([[0.02 * L, -0.49 * H], [-0.08 * L, -0.74 * H], [-0.2 * L, -0.66 * H], [-0.2 * L, -0.33 * H]]),
    curve([[-0.02 * L, 0.45 * H], [-0.12 * L, 0.62 * H], [-0.2 * L, 0.32 * H]]),
    // gill, eye, mouth
    curve([[0.26 * L, -0.38 * H], [0.2 * L, 0], [0.26 * L, 0.34 * H]], 'detail'),
    ring(0.36 * L, -0.12 * H, 0.04 * L, 0.04 * L, 0, 'detail'),
    curve([[0.5 * L, 0.02 * H], [0.42 * L, 0.06 * H]], 'detail'),
    // scales
    ...[-0.2, -0.06, 0.08].flatMap((sx) => [-0.22, 0, 0.22].map((sy) => curve(
      [[(sx + 0.05) * L, (sy - 0.1) * H], [sx * L, sy * H], [(sx + 0.05) * L, (sy + 0.1) * H]],
      'hatch',
    ))),
  ]
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

/* ---------- Gemini: the twins side by side, heads on Castor and Pollux, feet at Tejat and Alhena ---------- */
function gemini() {
  return [
    // Castor, one arm raised to θ Gem, the other on his brother's shoulder through ι Gem
    ...head(139, 91, 50, 1),
    ...ribbon([[186, 142], [300, 196], [440, 276], [586, 380]], [54, 118, 122, 98]),
    ...limb([[384, 196], [404, 112], [474, 44], [562, 2]], [40, 32, 26, 20]),
    ...limb([[300, 230], [232, 292], [180, 346], [150, 360]], [36, 30, 26, 20]),
    ...limb([[570, 362], [722, 452], [897, 528], [976, 526]], [72, 52, 34, 24]),
    ...limb([[556, 392], [652, 520], [764, 622], [834, 640]], [66, 48, 32, 24]),
    // Pollux, a hand hanging to κ Gem, legs through Mekbuda and λ Gem
    ...head(16, 267, 48, 1),
    ...ribbon([[50, 316], [120, 400], [200, 490], [268, 560]], [52, 110, 116, 96]),
    ...limb([[40, 352], [18, 400], [12, 440], [22, 482]], [34, 28, 24, 20]),
    ...limb([[256, 548], [447, 635], [600, 740], [748, 828], [806, 842]], [72, 54, 40, 30, 24]),
    ...limb([[228, 580], [262, 700], [288, 825], [384, 900]], [66, 48, 34, 26]),
    // tunic folds
    ...hatchRow([300, 180], [44, 30], [-30, 50], 6),
    ...hatchRow([90, 350], [34, 38], [-40, 34], 5),
  ]
}

/* ---------- Cancer: the crab with Praesepe at the heart of its shell, legs to Acubens and Altarf ---------- */
function cancer() {
  const leg = (points) => limb(points, [34, 24, 16, 6])
  return [
    ring(450, 466, 186, 146),
    curve([[300, 420], [380, 380], [450, 370], [520, 380], [600, 420]], 'detail'),
    curve([[310, 540], [380, 570], [450, 578], [520, 570], [590, 540]], 'detail'),
    curve([[450, 370], [440, 470], [450, 578]], 'hatch'),
    ...hatchRow([330, 450], [26, 0], [8, 50], 10),
    // eyes on stalks
    ...ribbon([[420, 330], [410, 290], [404, 262]], [14, 10, 8], { open: true }),
    ...ribbon([[480, 330], [490, 290], [496, 262]], [14, 10, 8], { open: true }),
    curl(404, 256, 9, 1, 0),
    curl(496, 256, 9, 1, 0),
    // claws: the left one closes on ι Cnc
    ...claw(
      [[372, 340], [320, 250], [334, 168]],
      [[334, 168], [360, 96], [388, 0]],
      [[350, 128], [306, 78], [312, 16], [352, -10]],
      [44, 36, 30],
    ),
    ...claw(
      [[528, 340], [584, 250], [574, 168]],
      [[574, 168], [556, 96], [530, 4]],
      [[560, 128], [610, 80], [608, 20], [568, -8]],
      [44, 36, 30],
    ),
    ...leg([[620, 420], [730, 382], [810, 442], [850, 524]]),
    ...leg([[632, 480], [748, 482], [816, 562], [836, 652]]),
    ...leg([[612, 540], [706, 594], [762, 702], [764, 802]]),
    ...leg([[570, 590], [648, 704], [704, 852], [765, 1000]]),
    ...leg([[280, 420], [170, 382], [90, 442], [50, 524]]),
    ...leg([[268, 480], [152, 482], [84, 562], [64, 652]]),
    ...leg([[288, 540], [194, 594], [148, 702], [146, 802]]),
    ...leg([[330, 590], [278, 704], [244, 780], [235, 863]]),
  ]
}

/* ---------- Leo: the lion walking west, the Sickle as its mane, Regulus at the heart, tail at Denebola ---------- */
function leo() {
  return [
    // face to the west: Rasalas on the brow, ε Leo at the eye
    curve([[930, 236], [976, 238], [1010, 268], [1036, 314], [1042, 352], [1022, 374], [1030, 398], [996, 418], [950, 420]]),
    curl(992, 318, 12, 1.1, 0.4),
    curve([[1036, 346], [1012, 352], [1000, 370]], 'detail'),
    curve([[1022, 376], [990, 392], [962, 390]], 'detail'),
    // mane through Adhafera, Algieba and η Leo
    curve([[930, 236], [880, 196], [800, 204], [736, 260], [700, 340], [692, 430], [712, 520], [760, 590], [840, 624], [890, 600], [930, 540], [950, 420]]),
    curve([[900, 250], [840, 250], [790, 300]], 'detail'),
    curve([[910, 300], [830, 320], [770, 380]], 'detail'),
    curve([[920, 360], [840, 400], [760, 460]], 'detail'),
    curve([[930, 410], [860, 470], [800, 540]], 'detail'),
    curl(760, 300, 22, 1.3, 0.5),
    curl(740, 420, 24, 1.3, 2.0),
    curl(780, 540, 22, 1.3, 1.2),
    curl(860, 580, 20, 1.3, 2.8),
    // back through Zosma, haunch, belly
    curve([[740, 300], [620, 360], [480, 404], [360, 420], [262, 450], [212, 510], [204, 600], [232, 676]]),
    curve([[800, 610], [740, 708], [640, 736], [500, 742], [390, 724]]),
    curve([[300, 520], [290, 600], [330, 660]], 'detail'),
    // legs: Regulus at the top of the near foreleg
    ...limb([[838, 640], [846, 760], [836, 880], [868, 952]], [104, 66, 46, 40]),
    ...limb([[770, 680], [746, 800], [722, 890], [744, 952]], [90, 58, 42, 38]),
    ...limb([[310, 620], [348, 750], [306, 850], [318, 952]], [140, 76, 48, 40]),
    ...limb([[236, 640], [232, 770], [200, 862], [222, 952]], [96, 60, 42, 38]),
    // tail curling down to Denebola, ending in a tuft
    ...ribbon([[214, 500], [140, 520], [80, 560], [30, 604]], [26, 18, 14, 10], { open: true }),
    curve([[34, 600], [6, 590], [-24, 618], [-14, 650], [16, 650], [30, 628], [34, 600]]),
    curve([[20, 610], [-4, 630]], 'hatch'),
    ...hatchRow([440, 470], [50, 0], [-14, 60], 7),
  ]
}

/* ---------- Virgo: the winged maiden lying along the ecliptic, wing tip at Vindemiatrix, Spica the wheat ear ---------- */
function virgo() {
  return [
    // head on Zavijava, looking west
    ...head(960, 462, 44, 1),
    ...ribbon([[600, 566], [700, 540], [810, 512], [912, 494]], [112, 96, 110, 44], { open: true }),
    // the gown down to the feet at Syrma and μ Vir, with its folds
    ...ribbon([[620, 560], [470, 590], [310, 618], [150, 638], [24, 646]], [124, 168, 176, 150, 84], { open: true }),
    curve([[610, 506], [622, 560], [610, 618]], 'detail'),
    curve([[600, 570], [420, 604], [230, 634], [60, 650]], 'detail'),
    curve([[590, 530], [440, 548], [260, 586], [110, 616]], 'hatch'),
    curve([[590, 610], [430, 650], [250, 672], [110, 668]], 'hatch'),
    // the arm with the ear of wheat
    ...limb([[790, 530], [690, 640], [580, 704], [520, 722]], [44, 36, 30, 26]),
    curve([[620, 688], [520, 724], [430, 764], [330, 800]], 'detail'),
    ...[0, 1, 2, 3].flatMap((k) => {
      const x = 470 - k * 34
      const y = 744 + k * 14
      return [
        curve([[x, y], [x - 28, y - 30], [x - 52, y - 30]], 'hatch'),
        curve([[x, y], [x - 20, y + 24], [x - 46, y + 30]], 'hatch'),
      ]
    }),
    // the wing rising from the shoulders, feathered
    curve([[780, 490], [716, 390], [640, 300], [560, 236], [450, 196], [380, 190]]),
    curve([[380, 190], [410, 236], [404, 270], [446, 300], [450, 344], [500, 370], [512, 416], [566, 436], [592, 474], [660, 488]]),
    curve([[720, 450], [650, 370], [580, 300], [490, 240]], 'detail'),
    ...[[436, 250], [470, 300], [514, 352], [560, 404], [616, 452]].map(([x, y]) => curve([[x, y], [x + 40, y - 4], [x + 80, y - 20]], 'hatch')),
  ]
}

/* ---------- Libra: the balance hanging from Zubeneschamali, beam to Zubenelgenubi, pans below ---------- */
function libra() {
  const pan = (hx, hy, cx, rim, w, depth) => [
    curve([[cx - w, rim], [cx - w * 0.7, rim + depth * 0.7], [cx, rim + depth], [cx + w * 0.7, rim + depth * 0.7], [cx + w, rim]]),
    ring(cx, rim, w, 18),
    curve([[hx, hy], [cx - w + 8, rim]], 'detail'),
    curve([[hx, hy], [cx, rim - 16]], 'detail'),
    curve([[hx, hy], [cx + w - 8, rim]], 'detail'),
    ...hatchRow([cx - w * 0.6, rim + 26], [w * 0.24, 0], [w * 0.06, depth * 0.5], 6),
  ]
  return [
    // the hanger ring around Zubeneschamali and the shank
    ring(565, 22, 30, 30),
    ...ribbon([[568, 52], [590, 170], [606, 282]], [16, 20, 26]),
    curve([[606, 280], [612, 236], [606, 200]], 'hatch'),
    // the beam, tilted, with knobs at both ends
    ...ribbon([[344, 268], [475, 285], [606, 302], [737, 319], [868, 336]], [14, 22, 36, 22, 14], { joints: true }),
    ring(344, 268, 18, 18),
    ring(868, 336, 18, 18),
    ...pan(344, 286, 344, 880, 128, 108),
    ...pan(868, 354, 868, 840, 128, 90),
  ]
}

/* ---------- Sagittarius: the centaur archer, the Teapot's bow drawn, the arrow on Alnasl ---------- */
function sagittarius() {
  return [
    // the man: head, torso rising from the horse, a cape flying back to Nunki and τ Sgr
    ...head(436, 86, 50, 1),
    ...ribbon([[474, 460], [446, 260], [434, 140]], [116, 128, 56], { open: true }),
    curve([[400, 170], [300, 140], [190, 143], [90, 180], [0, 256]]),
    curve([[0, 256], [100, 250], [200, 230], [300, 250], [392, 290]]),
    curve([[380, 200], [260, 190], [130, 220]], 'hatch'),
    curve([[380, 240], [260, 222], [150, 240]], 'hatch'),
    // the arms: one holds the bow at Kaus Media, one draws the string
    ...limb([[480, 194], [600, 280], [700, 350], [756, 400]], [42, 34, 28, 24]),
    ...limb([[420, 210], [350, 280], [420, 326], [508, 334]], [40, 32, 28, 24]),
    // the bow from Kaus Borealis to Kaus Australis and its string
    ...ribbon([[649, 73], [736, 200], [770, 405], [742, 600], [695, 744]], [6, 18, 28, 18, 6], { joints: true }),
    curve([[649, 73], [508, 334]], 'detail'),
    curve([[508, 334], [695, 744]], 'detail'),
    // the arrow, its head on Alnasl
    curve([[490, 330], [1000, 462]]),
    curve([[1000, 462], [956, 432], [962, 454], [952, 478], [1000, 462]]),
    curve([[500, 332], [480, 306], [450, 304]], 'detail'),
    curve([[500, 332], [474, 344], [446, 340]], 'detail'),
    // the horse body: back to Ascella at the rump, belly, chest
    curve([[414, 440], [330, 430], [260, 422], [150, 420], [86, 446], [56, 520], [86, 600], [150, 640]]),
    curve([[200, 652], [320, 664], [460, 644], [544, 600], [560, 520], [520, 440]]),
    ...hatchRow([180, 480], [44, 0], [-10, 60], 8),
    // legs: a foreleg kicking up to η Sgr
    ...limb([[520, 600], [636, 690], [712, 800], [789, 927]], [80, 52, 36, 28]),
    ...limb([[460, 630], [480, 760], [440, 860], [430, 952]], [84, 54, 36, 28]),
    ...limb([[150, 620], [130, 750], [170, 850], [150, 952]], [104, 58, 36, 28]),
    ...limb([[220, 640], [240, 762], [206, 862], [214, 952]], [88, 54, 36, 28]),
    // tail
    ...ribbon([[80, 456], [30, 520], [12, 620], [36, 720]], [26, 40, 30, 4], { open: true }),
    curve([[50, 500], [30, 600], [36, 690]], 'hatch'),
  ]
}

/* ---------- Aquarius: the water bearer, the Water Jar in his hands, the stream down past Skat ---------- */
function aquarius() {
  // The stream: two banks and the ripples between them.
  const stream = [[220, 282], [170, 360], [147, 432], [150, 520], [168, 592], [136, 653], [90, 730], [43, 806], [24, 900], [40, 990]]
  const wave = (dx, kind) => curve(stream.map(([x, y], i) => [x + dx * (1 + i * 0.1) + (i % 2 ? 9 : -9), y]), kind)
  return [
    // the man: Sadalmelik at the near shoulder, Sadalsuud at the back
    ...head(586, 168, 50, -1),
    ...ribbon([[584, 226], [606, 330], [630, 450], [656, 620]], [70, 160, 136, 210]),
    curve([[566, 450], [630, 462], [696, 446]], 'detail'),
    ...hatchRow([590, 490], [26, 0], [14, 116], 5),
    ...hatchRow([570, 300], [6, 30], [50, 0], 4),
    // arms: both hands on the jar, one reaching back to Albali
    ...limb([[540, 270], [455, 239], [380, 232], [350, 236]], [48, 40, 32, 28]),
    ...limb([[560, 330], [470, 320], [390, 286]], [42, 34, 28]),
    ...limb([[660, 300], [800, 400], [920, 480], [1000, 505]], [52, 40, 30, 24]),
    // legs striding from under the tunic
    ...limb([[616, 640], [606, 790], [596, 950], [556, 976]], [70, 52, 38, 26]),
    ...limb([[694, 640], [748, 790], [796, 940], [842, 962]], [70, 52, 38, 26]),
    // the Water Jar tipped forward, mouth down to the west
    ring(300, 222, 76, 52, -28),
    ...ribbon([[246, 254], [228, 268], [214, 284]], [40, 34, 46], { open: true }),
    curve([[340, 180], [374, 160], [384, 196], [360, 214]], 'detail'),
    curve([[262, 196], [300, 230], [346, 250]], 'hatch'),
    // the stream
    wave(-28, 'outline'),
    wave(0, 'detail'),
    wave(28, 'outline'),
    ...stream.slice(1, -1).map(([x, y], i) => curve([[x - 16, y - 8], [x, y + 4], [x + 16, y - 8]], 'hatch')),
    curl(0, 394, 14, 1.2, 0.4),
  ]
}

/* ---------- Pisces: two fish tied by a cord knotted at Alrescha, the Circlet as the western fish ---------- */
function pisces() {
  return [
    // the western fish around the Circlet, facing west
    ...place(fish(270, 150), [906, 784], 0),
    // the northern fish rising to τ Psc
    ...place(fish(250, 112), [310, 222], -94),
    // the cord: from one tail through δ and ε Psc to the knot, then up to the other tail
    ...ribbon([[760, 784], [716, 730], [600, 704], [448, 699], [366, 691], [250, 712], [135, 743], [40, 790], [8, 806]], [10, 10, 10, 10, 10, 10, 10, 10, 10], { open: true }),
    ...ribbon([[8, 806], [60, 720], [115, 654], [206, 511], [270, 420], [304, 346]], [10, 10, 10, 10, 10, 10], { open: true }),
    curl(0, 807, 26, 1.6, 0),
    curl(4, 806, 14, 1.4, 2),
  ]
}

export const ZODIAC_ART = {
  aries: aries(),
  taurus: taurus(),
  gemini: gemini(),
  cancer: cancer(),
  leo: leo(),
  virgo: virgo(),
  libra: libra(),
  scorpio: scorpio(),
  sagittarius: sagittarius(),
  capricorn: capricorn(),
  aquarius: aquarius(),
  pisces: pisces(),
}
