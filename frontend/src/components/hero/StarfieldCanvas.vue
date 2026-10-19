<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'

const ASSET = '/assets/astral/stars'

const props = defineProps({
  width: { type: Number, required: true },
  height: { type: Number, required: true },
  light: { type: Number, required: true },
  starColor: { type: String, required: true },
  quality: { type: Object, required: true },
})

const canvas = ref(null)
let stars = []
let sprites = {}
let tinted = new Map()
let frame = 0
let running = false
let context = null
let started = 0

function loadImage(src) {
  return new Promise((resolve) => {
    const image = new Image()
    image.onload = () => resolve(image)
    image.onerror = () => resolve(null)
    image.src = src
  })
}

async function loadSprites() {
  const names = ['star-small.svg', 'star-medium.svg', 'star-spark.svg', 'star-bright.svg']
  await Promise.all(names.map(async (name) => {
    const text = await fetch(`${ASSET}/${name}`).then((response) => response.text())
    const marked = text.replace('<svg ', '<svg width="128" height="128" ').replaceAll('currentColor', '#ffffff')
    const url = URL.createObjectURL(new Blob([marked], { type: 'image/svg+xml' }))
    sprites[name] = await loadImage(url)
  }))
  sprites['star-glow.webp'] = await loadImage(`${ASSET}/star-glow.webp`)
}

function tint(name, color) {
  const key = `${name}|${color}`
  const cached = tinted.get(key)
  if (cached) return cached
  const image = sprites[name]
  if (!image) return null
  const plate = document.createElement('canvas')
  plate.width = 128
  plate.height = 128
  const pen = plate.getContext('2d')
  pen.drawImage(image, 0, 0, 128, 128)
  pen.globalCompositeOperation = 'source-in'
  pen.fillStyle = color
  pen.fillRect(0, 0, 128, 128)
  tinted.set(key, plate)
  return plate
}

async function loadLayout() {
  const response = await fetch(`${ASSET}/starfield-layout.json`)
  const data = await response.json()
  stars = data.stars || []
}

function resize() {
  const node = canvas.value
  if (!node || props.width < 2 || props.height < 2) return
  const dpr = props.quality.dpr || 1
  node.width = Math.round(props.width * dpr)
  node.height = Math.round(props.height * dpr)
  context = node.getContext('2d', { alpha: true })
  if (context) context.setTransform(dpr, 0, 0, dpr, 0, 0)
}

function draw(now) {
  if (!context) return
  context.clearRect(0, 0, props.width, props.height)
  const scale = props.width / 1280
  const gain = (0.28 + (1 - props.light) * 0.72) * (props.quality.stars || 1)
  const t = props.quality.twinkle ? (now - started) / 1000 : 0
  for (const star of stars) {
    const sprite = star.sprite.endsWith('.svg') ? tint(star.sprite, props.starColor) : sprites[star.sprite]
    if (!sprite) continue
    const twinkle = props.quality.twinkle
      ? 0.62 + 0.38 * Math.sin(t * (star.group === 'far' ? 0.7 : 1.15) + star.phase * Math.PI * 2)
      : 1
    const burst = star.group === 'bright' && props.quality.twinkle
      ? 0.82 + 0.18 * Math.sin(t * 0.45 + star.phase * 4)
      : 1
    const alpha = Math.max(0, Math.min(1, star.brightness * twinkle * burst * gain))
    const unit = star.group === 'bright' ? 18 : star.group === 'mid' ? 11 : 5.5
    const size = Math.max(2, star.size * unit * scale)
    const x = star.x * props.width
    const y = star.y * props.height
    context.save()
    context.globalAlpha = alpha
    context.translate(x, y)
    if (star.group === 'bright' && props.quality.twinkle) context.rotate(t * 0.05 + star.phase)
    if (star.sprite.endsWith('.svg')) {
      context.drawImage(sprite, -size / 2, -size / 2, size, size)
    }
    context.restore()
    if (star.group === 'bright' && sprites['star-glow.webp']) {
      const glow = size * 2.4
      context.save()
      context.globalAlpha = alpha * 0.45
      context.drawImage(sprites['star-glow.webp'], x - glow / 2, y - glow / 2, glow, glow)
      context.restore()
    }
  }
}

function loop(now) {
  if (!running) return
  if (!document.hidden && document.body.classList.contains('sky-live')) draw(now)
  frame = requestAnimationFrame(loop)
}

function onVisibility() {
  if (!document.hidden && running) draw(performance.now())
}

watch(() => [props.width, props.height, props.quality.dpr], () => resize())

onMounted(async () => {
  started = performance.now()
  resize()
  await Promise.all([loadLayout(), loadSprites()])
  running = true
  document.addEventListener('visibilitychange', onVisibility)
  if (props.quality.reduce) draw(started)
  else frame = requestAnimationFrame(loop)
})

onUnmounted(() => {
  running = false
  cancelAnimationFrame(frame)
  document.removeEventListener('visibilitychange', onVisibility)
})
</script>

<template>
  <canvas ref="canvas" class="star-layer" aria-hidden="true" />
</template>
