<script setup>
// Astrolabe emblem: graduated limb, tilted orbit with the Moon and a bead, the Sun at the centre.
const C = 24
const ORBIT = { rx: 18.5, ry: 6.6, tilt: -28 }

function onOrbit(degrees) {
  const t = (degrees * Math.PI) / 180
  const a = (ORBIT.tilt * Math.PI) / 180
  const x = ORBIT.rx * Math.cos(t)
  const y = ORBIT.ry * Math.sin(t)
  return { x: C + x * Math.cos(a) - y * Math.sin(a), y: C + x * Math.sin(a) + y * Math.cos(a) }
}

const ticks = Array.from({ length: 48 }, (_, i) => {
  const a = (i / 48) * Math.PI * 2
  const inner = i % 12 === 0 ? 17.6 : i % 4 === 0 ? 18.8 : 19.6
  return {
    major: i % 12 === 0,
    d: `M${(C + Math.sin(a) * inner).toFixed(2)} ${(C - Math.cos(a) * inner).toFixed(2)}L${(C + Math.sin(a) * 20.6).toFixed(2)} ${(C - Math.cos(a) * 20.6).toFixed(2)}`,
  }
})

const moon = onOrbit(-58)
const bead = onOrbit(148)

function star(x, y, r) {
  const k = r * 0.24
  return `M${x} ${y - r}Q${x + k} ${y - k} ${x + r} ${y}Q${x + k} ${y + k} ${x} ${y + r}Q${x - k} ${y + k} ${x - r} ${y}Q${x - k} ${y - k} ${x} ${y - r}Z`
}
</script>

<template>
  <svg class="brand-mark" viewBox="0 0 48 48" aria-hidden="true">
    <g class="bm-limb">
      <circle class="bm-ring" :cx="C" :cy="C" r="21.6" />
      <path v-for="(tick, i) in ticks" :key="i" class="bm-tick" :class="{ 'is-major': tick.major }" :d="tick.d" />
    </g>
    <circle class="bm-ring bm-ring-inner" :cx="C" :cy="C" r="14.2" />
    <g class="bm-orbit">
      <ellipse class="bm-path" :cx="C" :cy="C" :rx="ORBIT.rx" :ry="ORBIT.ry" :transform="`rotate(${ORBIT.tilt} ${C} ${C})`" />
      <circle class="bm-bead" :cx="bead.x" :cy="bead.y" r="1.25" />
      <g :transform="`translate(${moon.x} ${moon.y}) rotate(-20) scale(0.29) translate(-12 -12)`">
        <circle class="bm-moon-back" cx="12" cy="12" r="10.5" />
        <path class="bm-moon" d="M14.6 2.2A10 10 0 1 0 21.8 16a8.2 8.2 0 0 1-7.2-13.8Z" />
      </g>
    </g>
    <path class="bm-sun-rays" :d="star(C, C, 7.4)" />
    <circle class="bm-sun" :cx="C" :cy="C" r="2.3" />
    <path class="bm-crown" :d="star(C, 1.6, 2.4)" />
  </svg>
</template>

<style scoped>
.brand-mark {
  overflow: visible;
  fill: none;
  stroke-linecap: round;
}
.bm-ring { stroke: #e2bd78; stroke-width: 1; }
.bm-ring-inner { stroke-width: 0.6; opacity: 0.55; }
.bm-tick { stroke: #e2bd78; stroke-width: 0.6; opacity: 0.7; }
.bm-tick.is-major { stroke-width: 1; opacity: 1; }
.bm-path { stroke: #f0d6a0; stroke-width: 0.8; opacity: 0.85; }
.bm-bead { fill: #ffe7b4; }
.bm-moon-back { fill: #0b0d17; }
.bm-moon { fill: #dfe7fb; filter: drop-shadow(0 0 4px rgba(190, 210, 255, 0.8)); }
.bm-sun-rays { fill: #ffe2a6; }
.bm-sun { fill: #fff6df; filter: drop-shadow(0 0 3px #ffc96e); }
.bm-crown { fill: #ffe7b4; }

.bm-limb,
.bm-orbit,
.bm-sun-rays {
  transform-box: view-box;
  transform-origin: 24px 24px;
  transition: transform 1.2s cubic-bezier(0.3, 0.7, 0.2, 1);
}
.bm-orbit { animation: bm-turn 40s linear infinite; }
.bm-sun-rays { animation: bm-breathe 5s ease-in-out infinite; }

@keyframes bm-turn { to { transform: rotate(360deg); } }
@keyframes bm-breathe {
  0%, 100% { transform: scale(1); opacity: 0.9; }
  50% { transform: scale(1.14); opacity: 1; }
}

@media (prefers-reduced-motion: reduce) {
  .bm-orbit, .bm-sun-rays { animation: none; }
}
</style>
