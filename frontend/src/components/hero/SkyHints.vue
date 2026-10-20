<script setup>
/**
 * Two quiet captions on the home sky: a ghost hand at the Sun saying it can be pulled, and a word
 * under a glimmering constellation saying it opens. They only point; the gestures are the sky's own.
 */
defineProps({
  /** The Sun on screen ({ x, y, r }) while its hint is due, else null. */
  sun: { type: Object, default: null },
  /** True while the Sun is being nudged by the demo: the hand presses. */
  pressing: { type: Boolean, default: false },
  /** Where the constellation's caption goes ({ x, y }), else null. */
  figure: { type: Object, default: null },
})
</script>

<template>
  <div class="sky-hints" aria-hidden="true">
    <Transition name="hint">
      <div
        v-if="sun"
        class="hint hint-sun"
        :class="[`on-${sun.side}`, { 'is-pressing': pressing }]"
        :style="{ left: `${sun.x}px`, top: `${sun.y}px`, '--r': `${sun.r}px` }"
      >
        <span class="hint-text">Потяните Солнце<br>или Луну по&nbsp;орбите</span>
        <svg class="hand" viewBox="0 0 24 24">
          <path d="M9 11.5V5.2a1.6 1.6 0 0 1 3.2 0v5.3m0-1.3a1.6 1.6 0 0 1 3.2 0v1.6m0-.6a1.6 1.6 0 0 1 3.2 0v4.4c0 3.6-2.4 6.4-6 6.4h-.8c-2.2 0-3.6-.9-4.8-2.6l-2.6-3.8a1.5 1.5 0 0 1 2.3-1.9L9 14.6" />
        </svg>
      </div>
    </Transition>
    <Transition name="hint">
      <div v-if="figure" class="hint hint-figure" :style="{ left: `${figure.x}px`, top: `${figure.y}px` }">
        <span class="hint-dot" />
        <span class="hint-text">Нажмите на созвездие</span>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.sky-hints { position: absolute; inset: 0; z-index: 3; pointer-events: none; }

.hint {
  position: absolute;
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--serif);
  font-style: italic;
  font-size: 16px;
  line-height: 1.2;
  white-space: nowrap;
  color: #f6e2b8;
  text-shadow: 0 0 10px rgba(0, 0, 0, 0.9), 0 0 18px rgba(255, 200, 110, 0.35);
}

/*
 * The hand rests on the Sun and presses while the demo turns it; the words stand beside it on the
 * outer side of the orbit (on-left: the Sun is left of the centre, so the words go further left).
 */
.hint-sun { width: 0; height: 0; }
.hint-sun .hand { position: absolute; left: calc(var(--r) * 0.2); top: calc(var(--r) * 0.15); }
.hint-sun .hint-text { position: absolute; top: calc(var(--r) * 0.6); text-align: right; right: calc(var(--r) + 6px); }
.hint-sun.on-right .hint-text { right: auto; left: calc(var(--r) + 6px); text-align: left; }
.hand {
  width: 30px;
  height: 30px;
  flex: none;
  fill: rgba(255, 240, 210, 0.12);
  stroke: #ffe7b8;
  stroke-width: 1.3;
  stroke-linecap: round;
  stroke-linejoin: round;
  filter: drop-shadow(0 0 6px rgba(255, 210, 130, 0.7));
  transform-origin: 40% 20%;
  transition: transform 0.35s ease;
  animation: hand-float 2.6s ease-in-out infinite;
}
.hint-sun.is-pressing .hand { transform: scale(0.86); animation-play-state: paused; }

/* Under the constellation's name: centred on it. */
.hint-figure { transform: translate(-50%, 0); font-size: 15px; }
.hint-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #ffe2a8;
  box-shadow: 0 0 0 0 rgba(255, 226, 168, 0.6);
  animation: hint-ping 2.2s ease-out infinite;
}

@keyframes hand-float { 50% { translate: 3px 3px; } }
@keyframes hint-ping {
  0% { box-shadow: 0 0 0 0 rgba(255, 226, 168, 0.6); }
  80%, 100% { box-shadow: 0 0 0 10px rgba(255, 226, 168, 0); }
}

.hint-enter-active { transition: opacity 0.9s ease, filter 0.9s ease; }
.hint-leave-active { transition: opacity 0.5s ease; }
.hint-enter-from { opacity: 0; filter: blur(4px); }
.hint-leave-to { opacity: 0; }

@media (prefers-reduced-motion: reduce) {
  .hand, .hint-dot { animation: none; }
}
</style>
