/**
 * The pictures a person can save or share (the star passport, the pair): drawn on a canvas in
 * the browser, nothing goes to the server. Here is what they have in common — the night sky, the
 * gold frame, the four-pointed star — and the way a finished picture leaves the page.
 */

export const PICTURE = { W: 1080, H: 1350 }

export const cssFont = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim() || 'Georgia, serif'

export const SYMBOLS = `'Segoe UI Symbol', 'Noto Sans Symbols', sans-serif`

/** A canvas with the sky and the double frame already painted; the stars follow `seedText`. */
export async function startPicture(seedText) {
  await document.fonts?.ready
  const { W, H } = PICTURE
  const canvas = document.createElement('canvas')
  canvas.width = W
  canvas.height = H
  const ctx = canvas.getContext('2d')

  const sky = ctx.createRadialGradient(W / 2, H * 0.32, 60, W / 2, H * 0.45, H * 0.85)
  sky.addColorStop(0, '#2a2140')
  sky.addColorStop(0.55, '#120f22')
  sky.addColorStop(1, '#06050c')
  ctx.fillStyle = sky
  ctx.fillRect(0, 0, W, H)

  let seed = [...seedText].reduce((sum, char) => sum + char.charCodeAt(0), 11)
  const random = () => {
    seed = (seed * 16807) % 2147483647
    return seed / 2147483647
  }
  for (let index = 0; index < 260; index += 1) {
    ctx.globalAlpha = 0.2 + random() * 0.7
    ctx.fillStyle = random() > 0.85 ? '#ffe4a8' : '#efe7d8'
    ctx.beginPath()
    ctx.arc(random() * W, random() * H, 0.6 + random() * 1.8, 0, Math.PI * 2)
    ctx.fill()
  }
  ctx.globalAlpha = 1

  // The folio's frame: a double gold rule.
  ctx.strokeStyle = 'rgba(240, 205, 138, 0.55)'
  ctx.lineWidth = 2
  ctx.strokeRect(60, 60, W - 120, H - 120)
  ctx.strokeStyle = 'rgba(240, 205, 138, 0.25)'
  ctx.strokeRect(76, 76, W - 152, H - 152)

  ctx.textAlign = 'center'
  ctx.textBaseline = 'alphabetic'
  return { canvas, ctx }
}

/** The four-pointed star of the brand, glowing. */
export function paintStar(ctx, x, y, r, color) {
  ctx.save()
  ctx.translate(x - r, y - r)
  ctx.scale(r / 10, r / 10)
  ctx.fillStyle = color
  ctx.shadowColor = 'rgba(255, 205, 120, 0.9)'
  ctx.shadowBlur = 24
  ctx.fill(new Path2D('M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z'))
  ctx.restore()
}

export const finishPicture = (canvas) => new Promise((resolve) => canvas.toBlob(resolve, 'image/png'))

export const canSharePictures = typeof navigator !== 'undefined' && typeof navigator.share === 'function'

export function downloadPicture(blob, fileName) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

/** The system share sheet with the picture; where files cannot be shared, the words alone. */
export async function sharePicture(blob, fileName, title, text) {
  const file = new File([blob], fileName, { type: 'image/png' })
  const data = { files: [file], title }
  try {
    if (navigator.canShare?.(data)) await navigator.share(data)
    else await navigator.share({ title, text })
  } catch {
    // The person closed the share sheet: nothing to say.
  }
}
