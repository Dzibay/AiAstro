<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useSession } from '../composables/useSession.js'
import { useSky } from '../composables/useSky.js'
import { clamp } from './hero/sky.js'

/** The first stop of the home journey: the copy laid over the sky, which SkyStage draws. */

const { webToken } = useSession()
const chartTo = computed(() => (webToken.value ? '/cabinet' : '/login?mode=register'))
const { geo, warm, openStop } = useSky()

const sceneStyle = computed(() => {
  const { u, orbit, narrow } = geo.value
  const k = clamp(u, 0.78, 1.2)
  return {
    '--u': u,
    '--k': k,
    '--copy-top': `${narrow ? 96 : orbit.cy - orbit.r + 100 * u}px`,
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
      <p class="kicker">Твоя личная карта</p>
      <div class="ornament" aria-hidden="true">
        <span class="ornament-line" />
        <span class="ornament-dot" />
        <svg viewBox="0 0 20 20" class="ornament-star"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg>
        <span class="ornament-dot" />
        <span class="ornament-line" />
      </div>
      <h1>Астрология<br />нового поколения</h1>
      <p class="sub">Глубокий анализ вашей натальной карты <br />и точные прогнозы на будущее с помощью ИИ</p>
      <RouterLink class="cta" :to="chartTo">
        <span>Узнать свою карту</span>
        <svg class="cta-arrow" viewBox="0 0 16 16" aria-hidden="true"><path d="M2 8h11M9 4l4 4-4 4" /></svg>
      </RouterLink>
      <p class="hint">
        <svg class="hint-icon" viewBox="0 0 28 30" aria-hidden="true">
          <path d="M23 3C26 12 20 22 7 25" />
          <path d="M11 20.5 6.5 25.2 12 28" />
          <path d="M19.5 6.5 23 2.5 26.5 6.8" />
        </svg>
        <span>Перемещайте Солнце и Луну, <br />чтобы изменить тему</span>
      </p>
      <p class="sr-only" aria-live="polite">{{ phaseLabel }}</p>
    </div>

    <aside class="note note-left">
      <span class="note-icon" aria-hidden="true">
        <svg viewBox="0 0 20 20"><path d="M10 1Q11 9 19 10Q11 11 10 19Q9 11 1 10Q9 9 10 1Z" /></svg>
      </span>
      <span class="note-text">
        <strong>Натальная карта</strong>
        <span>Ваш уникальный путь<br />и потенциал</span>
      </span>
    </aside>
    <aside class="note note-right">
      <span class="note-icon" aria-hidden="true">
        <svg viewBox="0 0 20 20" class="compass">
          <circle cx="10" cy="10" r="6.2" />
          <path d="M10 2.5v15M2.5 10h15" />
          <path class="fill" d="M10 5.5 11.2 10 10 14.5 8.8 10Z" />
        </svg>
      </span>
      <span class="note-text">
        <strong>Прогнозы</strong>
        <span>Важные события<br />и возможности</span>
      </span>
    </aside>

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
  inset: -12% -10% -4%;
  z-index: -1;
  background: radial-gradient(closest-side, rgba(4, 6, 12, 0.55), transparent);
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
  margin: calc(14px * var(--k)) auto calc(26px * var(--k));
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
  font-size: calc(58px * var(--k));
  line-height: 0.98;
  letter-spacing: 0;
  color: #f6efe2;
  text-shadow: 0 0 28px rgba(255, 214, 150, 0.18), 0 2px 18px rgba(0, 0, 0, 0.6);
  animation: rise 1.1s ease 0.5s both;
}

.sub {
  margin: calc(26px * var(--k)) 0 0;
  font-size: calc(15.5px * var(--k));
  line-height: 1.55;
  color: rgba(226, 220, 210, 0.78);
  animation: rise 1.1s ease 0.65s both;
}

.cta {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 14px;
  margin-top: calc(30px * var(--k));
  padding: calc(14px * var(--k)) calc(34px * var(--k)) calc(14px * var(--k)) calc(36px * var(--k));
  border-radius: 999px;
  overflow: hidden;
  text-decoration: none;
  font-size: calc(14.5px * var(--k));
  font-weight: 600;
  color: #2b1d0b;
  background: linear-gradient(180deg, #f4dba6 0%, #e3bd78 55%, #cf9f55 100%);
  box-shadow:
    inset 0 1px 0 rgba(255, 248, 228, 0.8),
    inset 0 -1px 0 rgba(120, 80, 20, 0.35),
    0 0 0 1px rgba(255, 220, 160, 0.35),
    0 8px 30px rgba(230, 170, 80, 0.32),
    0 0 60px rgba(255, 190, 100, 0.15);
  transition: transform 0.25s ease, box-shadow 0.25s ease;
  animation: rise 1.1s ease 0.8s both;
}
.cta::after {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: -60%;
  width: 45%;
  background: linear-gradient(100deg, transparent, rgba(255, 255, 255, 0.55), transparent);
  transform: skewX(-20deg);
  animation: sheen 5.5s ease-in-out 2s infinite;
}
.cta:hover {
  transform: translateY(-2px);
  box-shadow:
    inset 0 1px 0 rgba(255, 248, 228, 0.9),
    inset 0 -1px 0 rgba(120, 80, 20, 0.35),
    0 0 0 1px rgba(255, 220, 160, 0.5),
    0 12px 40px rgba(240, 180, 90, 0.45),
    0 0 90px rgba(255, 190, 100, 0.25);
}
.cta:focus-visible { outline: 2px solid #ffe2a8; outline-offset: 4px; }
.cta-arrow {
  width: 15px;
  height: 15px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.6;
  stroke-linecap: round;
  stroke-linejoin: round;
  transition: transform 0.25s ease;
}
.cta:hover .cta-arrow { transform: translateX(4px); }

.hint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin: calc(34px * var(--k)) 0 0;
  font-size: calc(11.5px * var(--k));
  line-height: 1.45;
  text-align: left;
  color: rgba(214, 208, 198, 0.62);
  animation: rise 1.1s ease 1s both;
}
.hint-icon {
  width: 24px;
  height: 26px;
  flex: none;
  fill: none;
  stroke: rgba(240, 214, 160, 0.75);
  stroke-width: 1.2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

/* ---------- Corner notes ---------- */
.note {
  position: absolute;
  z-index: 3;
  bottom: calc(118px * var(--k));
  display: flex;
  align-items: flex-start;
  gap: 16px;
  animation: rise 1.2s ease 1.1s both;
}
.note-left { left: clamp(20px, 2.7vw, 48px); }
.note-right { right: clamp(20px, 2.7vw, 48px); }
.note-icon {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  flex: none;
  border-radius: 50%;
  border: 1px solid rgba(232, 206, 158, 0.45);
  background: rgba(10, 10, 16, 0.35);
  box-shadow: 0 0 18px rgba(255, 200, 120, 0.12);
}
.note-icon svg {
  width: 15px;
  height: 15px;
  fill: #f0d7a4;
}
.note-icon .compass { fill: none; stroke: #f0d7a4; stroke-width: 1; }
.note-icon .compass .fill { fill: #f0d7a4; stroke: none; }
.note-text { display: grid; gap: 4px; }
.note-text strong {
  font-weight: 400;
  font-size: 14px;
  color: #f2ebdf;
}
.note-text span {
  font-size: 11.5px;
  line-height: 1.45;
  color: rgba(214, 208, 198, 0.6);
}

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
@keyframes sheen {
  0%, 70% { left: -60%; }
  100% { left: 130%; }
}
@keyframes star-breathe {
  0%, 100% { transform: scale(1) rotate(0deg); }
  50% { transform: scale(1.18) rotate(45deg); }
}

@media (max-width: 760px) {
  .hero { min-height: 780px; }
  .hero-copy h1 { font-size: 40px; }
  .sub { font-size: 15px; }
  .sub br { display: none; }
  .note { bottom: 22px; gap: 10px; }
  .note-icon { width: 28px; height: 28px; }
  .note-text span { display: none; }
}

@media (prefers-reduced-motion: reduce) {
  .kicker, .ornament, .hero-copy h1, .sub, .cta, .hint, .note { animation: none; }
  .cta::after, .ornament-star { animation: none; }
}
</style>
