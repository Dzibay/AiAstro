<script setup>
import { computed } from 'vue'
import StartForm from './home/StartForm.vue'
import { useSky } from '../composables/useSky.js'
import { clamp } from './hero/sky.js'

/**
 * The first stop of the home journey: the copy laid over the sky, which SkyStage draws, and the
 * address for the letter right under it — the whole way in starts here.
 */

const { geo, warm, openStop } = useSky()

const sceneStyle = computed(() => {
  const { u, orbit, narrow } = geo.value
  const k = clamp(u, 0.78, 1.2)
  return {
    '--u': u,
    '--k': k,
    '--copy-top': `${narrow ? 96 : orbit.cy - orbit.r + 76 * u}px`,
    '--warm': warm.value.toFixed(3),
  }
})

const phaseLabel = computed(() => {
  if (warm.value > 0.72) return 'Солнце в силе: тёплая атмосфера'
  if (warm.value < 0.28) return 'Луна в силе: ночная атмосфера'
  return 'Равновесие Солнца и Луны'
})
</script>

<template>
  <section class="hero" data-sky-stop="hero" :style="sceneStyle">
    <div class="hero-copy" :class="{ 'is-dimmed': openStop === 0 }">
      <p class="kicker">Ваше небо в день рождения</p>
      <div class="ornament" aria-hidden="true">
        <span class="ornament-line" />
        <span class="ornament-dot" />
        <svg viewBox="0 0 20 20" class="ornament-star"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg>
        <span class="ornament-dot" />
        <span class="ornament-line" />
      </div>
      <h1>Натальная карта<br /><em>простыми словами</em></h1>
      <p class="sub">Характер, любовь, работа и прогноз на каждый день — <br />по дате, времени и месту рождения</p>
      <div class="start-wrap">
        <StartForm place="hero" />
      </div>
      <p class="sr-only" aria-live="polite">{{ phaseLabel }}</p>
    </div>
  </section>
</template>

<style scoped>
.hero {
  position: relative;
  z-index: 1;
  height: 100vh;
  height: 100svh;
  min-height: 620px;
  overflow: hidden;
  color: #f3ece0;
  pointer-events: none;
}

/* ---------- Copy ---------- */
.hero-copy {
  position: absolute;
  z-index: 3;
  left: 50%;
  top: var(--copy-top);
  width: min(680px, calc(100% - 32px));
  transform: translateX(-50%);
  text-align: center;
  pointer-events: none;
}
.hero-copy > * { pointer-events: auto; }
.hero-copy::before {
  content: '';
  position: absolute;
  inset: -10% -12% -16%;
  z-index: -1;
  background: radial-gradient(closest-side, rgba(4, 6, 12, 0.7), rgba(4, 6, 12, 0.4) 60%, transparent);
  pointer-events: none;
}

.kicker {
  margin: 0;
  font-size: calc(11px * var(--k));
  letter-spacing: 0.42em;
  text-transform: uppercase;
  color: rgba(226, 214, 192, 0.72);
  animation: rise 1s ease 0.3s both;
}

.ornament {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  margin: calc(10px * var(--k)) auto calc(16px * var(--k));
  color: #f0cd8a;
  animation: rise 1s ease 0.4s both;
}
.ornament-line {
  width: calc(100px * var(--k));
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(240, 205, 138, 0.75));
}
.ornament-line:last-child { transform: scaleX(-1); }
.ornament-dot { width: 3px; height: 3px; border-radius: 50%; background: currentColor; opacity: 0.8; }
.ornament-star {
  width: calc(14px * var(--k));
  height: calc(14px * var(--k));
  fill: #ffe4ad;
  filter: drop-shadow(0 0 5px rgba(255, 200, 110, 0.9));
  animation: star-breathe 4s ease-in-out infinite;
}

.hero-copy h1 {
  margin: 0;
  font-family: var(--serif);
  font-weight: 500;
  font-size: calc(56px * var(--k));
  line-height: 1.02;
  letter-spacing: 0;
  color: #f6efe2;
  text-shadow: 0 0 28px rgba(255, 214, 150, 0.18), 0 2px 18px rgba(0, 0, 0, 0.6);
  animation: rise 1.1s ease 0.5s both;
}
.hero-copy h1 em { font-style: italic; color: #f0cd8a; }

.sub {
  margin: calc(16px * var(--k)) 0 0;
  font-size: calc(17px * var(--k));
  line-height: 1.5;
  color: rgba(236, 230, 220, 0.86);
  text-shadow: 0 1px 12px rgba(0, 0, 0, 0.7);
  animation: rise 1.1s ease 0.65s both;
}

.start-wrap { margin-top: calc(24px * var(--k)); animation: rise 1.1s ease 0.8s both; }

.hero-copy { transition: opacity 0.5s ease, filter 0.5s ease; }
.hero-copy.is-dimmed { opacity: 0.28; filter: blur(1px); }

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}

@keyframes rise {
  from { opacity: 0; transform: translateY(14px); }
  to { opacity: 1; transform: none; }
}
@keyframes star-breathe {
  0%, 100% { transform: scale(1) rotate(0deg); }
  50% { transform: scale(1.18) rotate(45deg); }
}

@media (max-width: 760px) {
  .hero { min-height: 780px; }
  .ornament { display: none; }
  .kicker { margin-bottom: 14px; letter-spacing: 0.32em; }
  .hero-copy h1 { font-size: 40px; }
  .sub { font-size: 16px; }
  .sub br { display: none; }
}

@media (prefers-reduced-motion: reduce) {
  .kicker, .ornament, .hero-copy h1, .sub, .start-wrap { animation: none; }
  .ornament-star { animation: none; }
}
</style>
