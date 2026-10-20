<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { FRAGMENT, VERTEX } from './cosmos.glsl.js'

/** `state()` is read every frame so the parent can animate without re-rendering Vue. */
const props = defineProps({
  state: { type: Function, required: true },
  /** The cheaper shader and a slower idle drift, see utils/device.js. */
  lite: { type: Boolean, default: false },
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
/** The still sky («reduce motion») repeats one picture: it is drawn again only when something in it changes. */
let lastKey = ''

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

/** The program for the current quality: the light one is rebuilt in place when a slow machine steps down. */
function build() {
  const vs = compile(gl.VERTEX_SHADER, VERTEX)
  const fs = compile(gl.FRAGMENT_SHADER, props.lite ? `#define LITE
${FRAGMENT}` : FRAGMENT)
  if (!vs || !fs) return false
  const next = gl.createProgram()
  gl.attachShader(next, vs)
  gl.attachShader(next, fs)
  gl.linkProgram(next)
  gl.deleteShader(vs)
  gl.deleteShader(fs)
  if (!gl.getProgramParameter(next, gl.LINK_STATUS)) return false
  if (program) gl.deleteProgram(program)
  program = next
  gl.useProgram(program)
  const pos = gl.getAttribLocation(program, 'aPos')
  gl.enableVertexAttribArray(pos)
  gl.vertexAttribPointer(pos, 2, gl.FLOAT, false, 0, 0)
  uniforms = {}
  for (const name of ['uRes', 'uDpr', 'uTime', 'uU', 'uBodyU', 'uPan', 'uBand2', 'uSun', 'uMoon', 'uPlanet', 'uWarm', 'uSunHover', 'uMoonHover', 'uIntro', 'uHigh']) {
    uniforms[name] = gl.getUniformLocation(program, name)
  }
  lastKey = ''
  return true
}

function setup() {
  gl = canvas.value.getContext('webgl', { antialias: false, alpha: false, powerPreference: props.lite ? 'default' : 'high-performance' })
  if (!gl) return false
  const buffer = gl.createBuffer()
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer)
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW)
  return build()
}

watch(() => props.lite, () => {
  if (gl && !gl.isContextLost()) build()
})

function draw(now) {
  frame = requestAnimationFrame(draw)
  const s = props.state()
  if (!visible || document.hidden) return
  // Idle scenes only drift, so 30 fps is enough (20 on the light sky); interaction gets every frame.
  if (!s.busy && now - lastDraw < (props.lite ? 48 : 32)) return
  lastDraw = now
  const dpr = Math.min(window.devicePixelRatio || 1, s.high ? 1.5 : 1) * (s.high ? 1 : 0.8)
  const w = Math.round(s.width * dpr)
  const h = Math.round(s.height * dpr)
  if (s.still && !s.busy) {
    const key = [w, h, s.u, s.bodyU, s.pan, s.sun.x, s.sun.y, s.moon.x, s.moon.y, s.planet.cx, s.planet.cy, s.planet.r, s.warm, s.sunHover, s.moonHover, s.high].join()
    if (key === lastKey) return
    lastKey = key
  } else lastKey = ''
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
  gl.uniform1f(uniforms.uBodyU, s.bodyU)
  gl.uniform1f(uniforms.uPan, s.pan)
  gl.uniform1f(uniforms.uBand2, s.band2)
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
