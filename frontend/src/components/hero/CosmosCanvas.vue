<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { FRAGMENT, VERTEX } from './cosmos.glsl.js'

/** `state()` is read every frame so the parent can animate without re-rendering Vue. */
const props = defineProps({
  state: { type: Function, required: true },
})
const emit = defineEmits(['unsupported'])

const canvas = ref(null)
let gl = null
let program = null
let frame = 0
let uniforms = {}
let start = 0
let lastDraw = 0
let visible = true
let observer

function compile(type, source) {
  const shader = gl.createShader(type)
  gl.shaderSource(shader, source)
  gl.compileShader(shader)
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    console.error(gl.getShaderInfoLog(shader))
    return null
  }
  return shader
}

function setup() {
  gl = canvas.value.getContext('webgl', { antialias: false, alpha: false, powerPreference: 'high-performance' })
  if (!gl) return false
  const vs = compile(gl.VERTEX_SHADER, VERTEX)
  const fs = compile(gl.FRAGMENT_SHADER, FRAGMENT)
  if (!vs || !fs) return false
  program = gl.createProgram()
  gl.attachShader(program, vs)
  gl.attachShader(program, fs)
  gl.linkProgram(program)
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) return false
  gl.useProgram(program)
  const buffer = gl.createBuffer()
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer)
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW)
  const pos = gl.getAttribLocation(program, 'aPos')
  gl.enableVertexAttribArray(pos)
  gl.vertexAttribPointer(pos, 2, gl.FLOAT, false, 0, 0)
  for (const name of ['uRes', 'uDpr', 'uTime', 'uU', 'uSun', 'uMoon', 'uPlanet', 'uWarm', 'uSunHover', 'uMoonHover', 'uIntro', 'uHigh']) {
    uniforms[name] = gl.getUniformLocation(program, name)
  }
  return true
}

function draw(now) {
  frame = requestAnimationFrame(draw)
  const s = props.state()
  if (!visible || document.hidden) return
  // Idle scenes only drift, so 30 fps is enough; interaction gets every frame.
  if (!s.busy && now - lastDraw < 32) return
  lastDraw = now
  const dpr = Math.min(window.devicePixelRatio || 1, s.high ? 1.5 : 1) * (s.high ? 1 : 0.8)
  const w = Math.round(s.width * dpr)
  const h = Math.round(s.height * dpr)
  const el = canvas.value
  if (el.width !== w || el.height !== h) {
    el.width = w
    el.height = h
  }
  gl.viewport(0, 0, w, h)
  gl.uniform2f(uniforms.uRes, s.width, s.height)
  gl.uniform1f(uniforms.uDpr, w / s.width)
  gl.uniform1f(uniforms.uTime, s.still ? 12 : (now - start) / 1000 + 12)
  gl.uniform1f(uniforms.uU, s.u)
  gl.uniform2f(uniforms.uSun, s.sun.x, s.sun.y)
  gl.uniform2f(uniforms.uMoon, s.moon.x, s.moon.y)
  gl.uniform3f(uniforms.uPlanet, s.planet.cx, s.planet.cy, s.planet.r)
  gl.uniform1f(uniforms.uWarm, s.warm)
  gl.uniform1f(uniforms.uSunHover, s.sunHover)
  gl.uniform1f(uniforms.uMoonHover, s.moonHover)
  gl.uniform1f(uniforms.uIntro, s.intro)
  gl.uniform1f(uniforms.uHigh, s.high ? 1 : 0)
  gl.drawArrays(gl.TRIANGLES, 0, 3)
}

onMounted(() => {
  if (!setup()) {
    emit('unsupported')
    return
  }
  start = performance.now()
  observer = new IntersectionObserver(([entry]) => {
    visible = entry.isIntersecting
  })
  observer.observe(canvas.value)
  frame = requestAnimationFrame(draw)
})

onUnmounted(() => {
  cancelAnimationFrame(frame)
  observer?.disconnect()
  gl?.getExtension('WEBGL_lose_context')?.loseContext()
})
</script>

<template>
  <canvas ref="canvas" class="cosmos-canvas" aria-hidden="true" />
</template>
