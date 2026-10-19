<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { mulberry32 } from './celestial.js'

const props = defineProps({
  width: { type: Number, required: true },
  height: { type: Number, required: true },
  cx: { type: Number, required: true },
  cy: { type: Number, required: true },
  radius: { type: Number, required: true },
  sunX: { type: Number, required: true },
  sunY: { type: Number, required: true },
  moonX: { type: Number, required: true },
  moonY: { type: Number, required: true },
  light: { type: Number, required: true },
  night: { type: Number, required: true },
  horizon: { type: Number, required: true },
  quality: { type: Object, required: true },
})

const canvas = ref(null)
const supported = ref(true)
let albedo = null
let clouds = null
let frame = 0
let running = false
let context = null

function paintAlbedo(size) {
  const node = document.createElement('canvas')
  node.width = size
  node.height = size
  const g = node.getContext('2d')
  if (!g) return null
  const random = mulberry32(73)
  const mid = size / 2
  g.beginPath()
  g.arc(mid, mid, mid, 0, Math.PI * 2)
  g.clip()

  const base = g.createLinearGradient(0, 0, 0, size * 0.34)
  base.addColorStop(0, '#c9a36a')
  base.addColorStop(0.45, '#7d5a3c')
  base.addColorStop(1, '#3c4a5c')
  g.fillStyle = base
  g.fillRect(0, 0, size, size)

  for (let index = 0; index < 18; index += 1) {
    const x = mid + (random() - 0.5) * size * 0.8
    const y = mid + (random() - 0.42) * size * 0.7
    const rx = size * (0.035 + random() * 0.07)
    const ry = rx * (0.35 + random() * 0.5)
    g.fillStyle = random() > 0.5 ? 'rgba(92, 64, 40, 0.18)' : 'rgba(196, 164, 112, 0.14)'
    g.beginPath()
    g.ellipse(x, y, rx, ry, random() * Math.PI, 0, Math.PI * 2)
    g.fill()
  }

  g.lineCap = 'round'
  for (let index = 0; index < 34; index += 1) {
    const y = size * (0.18 + random() * 0.68)
    const amp = size * (0.008 + random() * 0.028)
    g.beginPath()
    g.moveTo(0, y)
    for (let x = 0; x <= size; x += 10) {
      const wave = Math.sin(x * 0.018 + index * 1.7) * amp + Math.sin(x * 0.047 + index) * amp * 0.45
      g.lineTo(x, y + wave)
    }
    g.strokeStyle = `rgba(${random() > 0.6 ? '255, 228, 190' : '42, 32, 24'}, ${0.05 + random() * 0.1})`
    g.lineWidth = 0.6 + random() * 1.8
    g.stroke()
  }

  for (let index = 0; index < 14; index += 1) {
    const x = size * (0.08 + random() * 0.84)
    const y = size * (0.04 + random() * 0.22)
    const r = size * (0.008 + random() * 0.016)
    g.beginPath()
    g.arc(x, y, r, 0, Math.PI * 2)
    g.fillStyle = 'rgba(28, 22, 16, 0.28)'
    g.fill()
    g.beginPath()
    g.arc(x - r * 0.22, y - r * 0.24, r * 0.68, 0, Math.PI * 2)
    g.fillStyle = 'rgba(236, 214, 176, 0.16)'
    g.fill()
    g.beginPath()
    g.arc(x, y, r, 0, Math.PI * 2)
    g.strokeStyle = 'rgba(255, 236, 210, 0.28)'
    g.lineWidth = Math.max(1, r * 0.08)
    g.stroke()
  }

  g.strokeStyle = 'rgba(212, 168, 92, 0.22)'
  g.lineWidth = 1.2
  for (let index = 0; index < 5; index += 1) {
    g.beginPath()
    g.moveTo(random() * size, random() * size)
    g.quadraticCurveTo(random() * size, random() * size, random() * size, random() * size)
    g.stroke()
  }

  for (let index = 0; index < 220; index += 1) {
    const x = random() * size
    const y = random() * size
    if ((x - mid) ** 2 + (y - mid) ** 2 > mid * mid) continue
    g.fillStyle = `rgba(255, 236, 210, ${0.04 + random() * 0.12})`
    g.fillRect(x, y, random() > 0.8 ? 1.6 : 1, 1)
  }

  const polar = g.createLinearGradient(0, 0, 0, size)
  polar.addColorStop(0, 'rgba(255, 244, 220, 0.16)')
  polar.addColorStop(0.4, 'rgba(0, 0, 0, 0)')
  polar.addColorStop(1, 'rgba(8, 12, 20, 0.28)')
  g.fillStyle = polar
  g.fillRect(0, 0, size, size)
  return node
}

function paintClouds(size) {
  const node = document.createElement('canvas')
  node.width = size
  node.height = size
  const g = node.getContext('2d')
  if (!g) return null
  const random = mulberry32(19)
  const mid = size / 2
  g.beginPath()
  g.arc(mid, mid, mid, 0, Math.PI * 2)
  g.clip()
  for (let index = 0; index < 16; index += 1) {
    const y = size * (0.2 + random() * 0.62)
    const x = size * (0.15 + random() * 0.7)
    g.fillStyle = `rgba(255, 250, 242, ${0.05 + random() * 0.07})`
    g.beginPath()
    g.ellipse(x, y, size * (0.08 + random() * 0.16), size * (0.02 + random() * 0.035), random() * 0.4, 0, Math.PI * 2)
    g.fill()
  }
  return node
}

function resize() {
  const node = canvas.value
  if (!node || props.width < 2) return
  const dpr = props.quality.dpr
  node.width = Math.round(props.width * dpr)
  node.height = Math.round(props.height * dpr)
  context = node.getContext('2d', { alpha: true })
  supported.value = Boolean(context)
  if (!context) return
  context.setTransform(dpr, 0, 0, dpr, 0, 0)
  if (!albedo) albedo = paintAlbedo(900)
  if (!clouds) clouds = paintClouds(640)
}

function render(now) {
  const ctx = context
  if (!ctx || !albedo || props.radius < 8) return
  const { width, height, cx, cy, radius } = props
  ctx.clearRect(0, 0, width, height)

  const dx = props.sunX - cx
  const dy = props.sunY - cy
  const dist = Math.hypot(dx, dy) || 1
  const ux = dx / dist
  const uy = dy / dist
  const warm = props.light
  const glowInner = warm > 0.45 ? '255, 214, 150' : '255, 176, 96'
  const glowOuter = props.night > 0.55 ? '126, 168, 206' : '232, 168, 96'
  const atmosphere = ctx.createRadialGradient(cx, cy, radius * 0.9, cx, cy, radius * 1.12)
  atmosphere.addColorStop(0, 'rgba(0, 0, 0, 0)')
  atmosphere.addColorStop(0.55, `rgba(${glowInner}, ${0.08 + props.horizon * 0.18})`)
  atmosphere.addColorStop(0.78, `rgba(${glowOuter}, ${0.18 + props.night * 0.22})`)
  atmosphere.addColorStop(1, 'rgba(0, 0, 0, 0)')
  ctx.fillStyle = atmosphere
  ctx.beginPath()
  ctx.arc(cx, cy, radius * 1.12, 0, Math.PI * 2)
  ctx.fill()

  ctx.save()
  ctx.beginPath()
  ctx.arc(cx, cy, radius, 0, Math.PI * 2)
  ctx.clip()
  ctx.drawImage(albedo, cx - radius, cy - radius, radius * 2, radius * 2)

  const hx = cx + ux * radius
  const hy = cy + uy * radius
  const shade = ctx.createLinearGradient(hx, hy, cx - ux * radius, cy - uy * radius)
  shade.addColorStop(0, `rgba(255, 220, 170, ${0.08 + warm * 0.1})`)
  shade.addColorStop(0.42, 'rgba(255, 255, 255, 0)')
  shade.addColorStop(1, `rgba(3, 8, 18, ${0.28 + props.night * 0.42})`)
  ctx.fillStyle = shade
  ctx.fillRect(cx - radius, cy - radius, radius * 2, radius * 2)

  const spot = ctx.createRadialGradient(
    cx + ux * radius * 0.46,
    cy + uy * radius * 0.46,
    radius * 0.05,
    cx + ux * radius * 0.2,
    cy + uy * radius * 0.2,
    radius * 0.72,
  )
  spot.addColorStop(0, `rgba(255, 236, 200, ${0.08 + warm * 0.08})`)
  spot.addColorStop(1, 'rgba(255, 236, 200, 0)')
  ctx.fillStyle = spot
  ctx.fillRect(cx - radius, cy - radius, radius * 2, radius * 2)

  const mdx = props.moonX - cx
  const mdy = props.moonY - cy
  const md = Math.hypot(mdx, mdy) || 1
  if (props.night > 0.35) {
    const moonLight = ctx.createRadialGradient(
      cx + (mdx / md) * radius * 0.7,
      cy + (mdy / md) * radius * 0.7,
      radius * 0.05,
      cx,
      cy,
      radius,
    )
    moonLight.addColorStop(0, `rgba(176, 206, 230, ${props.night * 0.16})`)
    moonLight.addColorStop(1, 'rgba(176, 206, 230, 0)')
    ctx.fillStyle = moonLight
    ctx.fillRect(cx - radius, cy - radius, radius * 2, radius * 2)
  }

  if (clouds && props.quality.clouds) {
    const spin = ((now / 1000) * 0.015) % (Math.PI * 2)
    ctx.save()
    ctx.translate(cx, cy)
    ctx.rotate(spin)
    ctx.globalAlpha = 0.22 + warm * 0.18
    ctx.drawImage(clouds, -radius, -radius, radius * 2, radius * 2)
    ctx.restore()
  } else if (clouds) {
    ctx.globalAlpha = 0.2
    ctx.drawImage(clouds, cx - radius, cy - radius, radius * 2, radius * 2)
  }
  ctx.restore()

  ctx.beginPath()
  ctx.arc(cx, cy, radius - 1.5, 0, Math.PI * 2)
  ctx.strokeStyle = warm > 0.62 ? 'rgba(92, 64, 34, 0.55)' : `rgba(${glowOuter}, ${0.45 + props.night * 0.4})`
  ctx.lineWidth = 2.4
  ctx.stroke()

  const starY = props.cy - props.radius
  if (starY > 40 && starY < height) {
    ctx.save()
    ctx.translate(cx, starY + 10)
    ctx.strokeStyle = `rgba(226, 196, 130, ${0.45 + warm * 0.35})`
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.moveTo(0, -7)
    ctx.lineTo(0, 7)
    ctx.moveTo(-7, 0)
    ctx.lineTo(7, 0)
    ctx.moveTo(-4, -4)
    ctx.lineTo(4, 4)
    ctx.moveTo(4, -4)
    ctx.lineTo(-4, 4)
    ctx.stroke()
    ctx.restore()
  }
}

function loop(now) {
  if (!running) return
  frame = requestAnimationFrame(loop)
  if (!document.hidden) render(now)
}

onMounted(() => {
  resize()
  if (props.quality.reduce) {
    render(0)
    return
  }
  running = true
  frame = requestAnimationFrame(loop)
})

onUnmounted(() => {
  running = false
  cancelAnimationFrame(frame)
})

watch(
  () => [props.width, props.height, props.quality.dpr],
  () => {
    resize()
    if (props.quality.reduce) render(performance.now())
  },
)

watch(
  () => [props.sunX, props.sunY, props.light, props.moonX, props.moonY, props.horizon, props.night],
  () => {
    if (props.quality.reduce) render(performance.now())
  },
)
</script>

<template>
  <canvas v-show="supported" ref="canvas" class="planet-layer" aria-hidden="true"></canvas>
  <div
    v-if="!supported"
    class="planet-fallback"
    :style="{
      left: `${cx - radius}px`,
      top: `${cy - radius}px`,
      width: `${radius * 2}px`,
      height: `${radius * 2}px`,
    }"
  ></div>
</template>
