<script setup>
import { ref } from 'vue'
import { useSiteConfig, fallbackConfig } from '../../composables/useSiteConfig.js'
import {
  canSharePictures, cssFont, downloadPicture, finishPicture, paintStar, PICTURE, sharePicture, startPicture,
} from '../../utils/sharePicture.js'

/**
 * The pair as a picture to save or send: two first names, the tone in a phrase and the five
 * spheres in stars. No dates, places or chart details — only what the two would tell a friend.
 */

const props = defineProps({
  mine: { type: String, required: true },
  theirs: { type: String, required: true },
  phrase: { type: String, default: '' },
  /** [{ id, score: 1..5 }] from the synastry. */
  spheres: { type: Array, default: () => [] },
})

const NAMES = { feelings: 'чувства', passion: 'притяжение', talk: 'разговоры', home: 'быт и опора', path: 'общий путь' }

const { config } = useSiteConfig()
const busy = ref(false)

/** The phrase broken into lines that fit the width. */
function wrap(ctx, text, width) {
  const lines = []
  let line = ''
  for (const word of text.split(' ')) {
    const next = line ? `${line} ${word}` : word
    if (ctx.measureText(next).width > width && line) {
      lines.push(line)
      line = word
    } else {
      line = next
    }
  }
  if (line) lines.push(line)
  return lines
}

async function draw() {
  const { W, H } = PICTURE
  const { canvas, ctx } = await startPicture(`${props.mine}${props.theirs}`)
  const caps = cssFont('--caps')
  const serif = cssFont('--serif')

  ctx.fillStyle = 'rgba(240, 205, 138, 0.85)'
  ctx.font = `600 40px ${caps}`
  ctx.fillText('совместимость', W / 2, 190)
  paintStar(ctx, W / 2 - 60, 262, 22, '#fff3d6')
  paintStar(ctx, W / 2 + 60, 262, 22, '#ffe4a8')

  ctx.fillStyle = '#f6efe2'
  ctx.font = `italic 500 92px ${serif}`
  ctx.fillText(`${props.mine} и ${props.theirs}`, W / 2, 410, W - 220)

  let y = 500
  if (props.phrase) {
    ctx.fillStyle = 'rgba(239, 231, 216, 0.84)'
    ctx.font = `italic 42px ${serif}`
    for (const line of wrap(ctx, props.phrase, W - 280).slice(0, 4)) {
      ctx.fillText(line, W / 2, y)
      y += 56
    }
  }

  ctx.strokeStyle = 'rgba(240, 205, 138, 0.3)'
  ctx.beginPath()
  ctx.moveTo(W / 2 - 220, y + 20)
  ctx.lineTo(W / 2 + 220, y + 20)
  ctx.stroke()

  const rows = props.spheres.filter((sphere) => NAMES[sphere.id])
  const top = Math.max(y + 110, 760)
  rows.forEach((sphere, index) => {
    const rowY = top + index * 92
    ctx.textAlign = 'left'
    ctx.fillStyle = 'rgba(226, 220, 210, 0.78)'
    ctx.font = `600 36px ${caps}`
    ctx.fillText(NAMES[sphere.id], 170, rowY)
    for (let star = 0; star < 5; star += 1) {
      paintStar(ctx, W - 410 + star * 58, rowY - 13, 17, star < sphere.score ? '#f0cd8a' : 'rgba(240, 205, 138, 0.18)')
    }
  })
  ctx.textAlign = 'center'

  ctx.fillStyle = 'rgba(240, 205, 138, 0.7)'
  ctx.font = `600 32px ${caps}`
  ctx.fillText((config.value?.site_name || fallbackConfig.site_name).toLowerCase(), W / 2, H - 120)

  return finishPicture(canvas)
}

const fileName = () => 'sovmestimost.png'

async function run(action) {
  if (busy.value) return
  busy.value = true
  try {
    const blob = await draw()
    if (!blob) return
    if (action === 'save') downloadPicture(blob, fileName())
    else await sharePicture(blob, fileName(), 'Совместимость', `${props.mine} и ${props.theirs}: ${props.phrase}`)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="pair-share">
    <button type="button" class="soft" :disabled="busy" @click="run('save')">
      <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 2.5v8M4.5 7L8 10.5L11.5 7M3 13.5h10" /></svg>
      Сохранить картинкой
    </button>
    <button v-if="canSharePictures" type="button" class="soft" :disabled="busy" @click="run('share')">
      <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 10V2.5M5 5.5L8 2.5L11 5.5M3.5 8.5v5h9v-5" /></svg>
      Поделиться
    </button>
  </div>
</template>

<style scoped>
.pair-share { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }
.soft {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 7px 14px;
  border-radius: 999px;
  border: 1px solid rgba(240, 210, 150, 0.26);
  background: rgba(255, 240, 210, 0.04);
  font: inherit;
  font-size: 12.5px;
  color: #efe7d8;
  cursor: pointer;
  transition: border-color 0.25s ease, color 0.25s ease, background 0.25s ease;
}
.soft svg { width: 13px; height: 13px; fill: none; stroke: currentColor; stroke-width: 1.4; stroke-linecap: round; stroke-linejoin: round; }
.soft:hover:not(:disabled) { border-color: rgba(240, 205, 138, 0.6); background: rgba(255, 240, 210, 0.08); color: #f0cd8a; }
.soft:disabled { opacity: 0.6; cursor: progress; }
.soft:focus-visible { outline: 2px solid #f0cd8a; outline-offset: 3px; }
</style>
