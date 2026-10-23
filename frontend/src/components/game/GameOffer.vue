<script setup>
import { computed, onMounted, ref } from 'vue'
import { useSky } from '../../composables/useSky.js'
import { wheelSpot } from '../cabinet/layout.js'

/**
 * The first look at the chart page asks whether to build the chart by hand (NatalGame) or to see
 * it at once. The card stands where the wheel is about to be drawn; on a phone, across the top.
 */

const emit = defineEmits(['play', 'skip'])
const { geo } = useSky()

const narrow = computed(() => geo.value.narrow)
const style = computed(() => {
  if (narrow.value) return null
  const spot = wheelSpot(geo.value)
  return { left: `${spot.x}px`, top: `${spot.y}px` }
})

const go = ref(null)
onMounted(() => go.value?.focus({ preventScroll: true }))
</script>

<template>
  <div class="game-offer" :class="{ 'is-narrow': narrow }" :style="style" role="dialog" aria-labelledby="game-offer-title">
    <svg class="emblem" viewBox="-50 -50 100 100" aria-hidden="true">
      <circle class="belt" r="44" />
      <circle class="belt faint" r="37" />
      <path
        v-for="i in 12"
        :key="i"
        class="tick"
        :d="`M${(37 * Math.cos((i * 30 * Math.PI) / 180)).toFixed(2)} ${(37 * Math.sin((i * 30 * Math.PI) / 180)).toFixed(2)}L${(44 * Math.cos((i * 30 * Math.PI) / 180)).toFixed(2)} ${(44 * Math.sin((i * 30 * Math.PI) / 180)).toFixed(2)}`"
      />
      <circle class="orbit" r="17" />
      <g class="turn">
        <path class="ray" d="M0 17L0 -40.5" />
        <circle class="earth" cx="0" cy="17" r="2.6" />
      </g>
      <circle class="sun" r="4.2" />
    </svg>
    <p class="kicker">Натальная карта</p>
    <h2 id="game-offer-title" class="title">Соберёте карту <em>сами</em>?</h2>
    <p class="text">
      Поставьте Солнце, Луну и планеты туда, где они были в момент вашего рождения, — и увидите,
      как из этого складывается карта. Пара минут.
    </p>
    <div class="actions">
      <button ref="go" type="button" class="go" @click="emit('play')">Построить</button>
      <button type="button" class="skip" @click="emit('skip')">Сразу показать карту</button>
    </div>
  </div>
</template>

<style scoped>
.game-offer {
  position: fixed;
  z-index: 3;
  width: 340px;
  padding: 18px 22px 18px;
  border-radius: 20px;
  border: 1px solid rgba(240, 210, 150, 0.32);
  background:
    radial-gradient(120% 80% at 50% 0%, rgba(255, 196, 120, 0.14), transparent 60%),
    linear-gradient(160deg, rgba(26, 23, 26, 0.84), rgba(8, 10, 18, 0.9));
  box-shadow: 0 24px 70px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 240, 210, 0.1);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  color: #efe7d8;
  text-align: center;
  transform: translate(-50%, -50%);
  animation: offer-in 0.7s cubic-bezier(0.3, 0.7, 0.2, 1) 0.9s both;
}
.game-offer.is-narrow {
  top: 70px;
  left: 12px;
  right: 12px;
  width: auto;
  transform: none;
}

.emblem { display: block; width: 92px; height: 92px; margin: 0 auto 6px; overflow: visible; }
.belt, .orbit, .tick { fill: none; stroke: rgba(240, 205, 138, 0.55); stroke-width: 0.8; }
.belt.faint, .orbit { stroke: rgba(240, 205, 138, 0.25); }
.tick { stroke: rgba(240, 205, 138, 0.4); }
.ray { stroke: #ffe2a8; stroke-width: 1.1; stroke-linecap: round; opacity: 0.85; filter: drop-shadow(0 0 2px rgba(255, 210, 130, 0.9)); }
.earth { fill: #8fc2ff; filter: drop-shadow(0 0 2px rgba(140, 190, 255, 0.9)); }
.sun { fill: #ffe7b0; filter: drop-shadow(0 0 5px rgba(255, 196, 110, 0.95)); }
.turn { transform-box: view-box; transform-origin: 0 0; animation: turn 14s linear infinite; }

.kicker { margin: 0; font-size: 10px; letter-spacing: 0.26em; text-transform: uppercase; color: rgba(233, 194, 124, 0.8); }
.title { margin: 6px 0 8px; font-family: var(--serif); font-weight: 400; font-size: 28px; line-height: 1.1; color: #fff3da; }
.title em { color: #f0cd8a; }
.text { margin: 0; font-family: var(--book); font-size: 15px; line-height: 1.5; color: rgba(239, 231, 216, 0.9); }

.actions { display: flex; flex-direction: column; align-items: center; gap: 6px; margin-top: 16px; }
.go, .skip { font: inherit; cursor: pointer; transition: background 0.25s ease, border-color 0.25s ease, color 0.25s ease, box-shadow 0.25s ease; }
.go {
  min-width: 170px;
  padding: 10px 24px;
  border-radius: 999px;
  border: 1px solid rgba(240, 205, 138, 0.7);
  background: linear-gradient(180deg, rgba(240, 205, 138, 0.3), rgba(240, 205, 138, 0.12));
  font-size: 15px;
  color: #fff1d4;
}
.go:hover { background: linear-gradient(180deg, rgba(240, 205, 138, 0.42), rgba(240, 205, 138, 0.18)); box-shadow: 0 6px 24px rgba(230, 170, 80, 0.28); }
.skip { padding: 8px 10px; border: 0; background: none; font-size: 13px; color: rgba(226, 220, 210, 0.65); }
.skip:hover { color: #f0cd8a; }
.go:focus-visible, .skip:focus-visible { outline: 2px solid #ffe2a8; outline-offset: 3px; border-radius: 999px; }
.is-narrow .go, .is-narrow .skip { min-height: 44px; }

@keyframes offer-in { from { opacity: 0; translate: 0 14px; filter: blur(4px); } }
@keyframes turn { to { transform: rotate(-360deg); } }

@media (prefers-reduced-motion: reduce) {
  .game-offer { animation: offer-fade 0.4s ease both; }
  .turn { animation: none; }
}
@keyframes offer-fade { from { opacity: 0; } }
</style>
