<script setup>
/** The caption every stop opens with: its number, the signs the Sun is passing, and its name. */
defineProps({
  num: { type: String, required: true },
  signs: { type: String, default: '' },
  label: { type: String, required: true },
  align: { type: String, default: 'start' },
})
</script>

<template>
  <header class="stop-head" :class="`is-${align}`">
    <p class="stop-caption" data-reveal style="--r: 0">
      <span class="stop-num">{{ num }}</span>
      <span v-if="signs" class="stop-dot" aria-hidden="true">·</span>
      <span v-if="signs" class="stop-signs" aria-hidden="true">{{ signs }}</span>
      <span class="stop-dot" aria-hidden="true">·</span>
      <span>{{ label }}</span>
    </p>
    <div class="stop-rule" data-reveal style="--r: 1" aria-hidden="true">
      <span class="stop-rule-line" />
      <svg viewBox="0 0 20 20"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg>
      <span class="stop-rule-line" />
    </div>
    <h2 data-reveal style="--r: 2"><slot /></h2>
  </header>
</template>

<style scoped>
.stop-head { display: grid; justify-items: start; }
.stop-head.is-center { justify-items: center; text-align: center; }

.stop-caption {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0;
  font-size: 11px;
  letter-spacing: 0.34em;
  text-transform: uppercase;
  color: rgba(226, 214, 192, 0.72);
}
.stop-num { font-family: var(--serif); font-size: 14px; letter-spacing: 0.18em; color: #f0cd8a; }
.stop-dot { color: rgba(240, 205, 138, 0.6); letter-spacing: 0; }
.stop-signs {
  font-family: 'Segoe UI Symbol', 'Noto Sans Symbols', sans-serif;
  font-size: 13px;
  letter-spacing: 0.3em;
  color: #f0cd8a;
}

.stop-rule { display: flex; align-items: center; gap: 8px; margin: 14px 0 18px; color: #f0cd8a; }
.stop-rule-line { width: 64px; height: 1px; background: linear-gradient(90deg, rgba(240, 205, 138, 0.75), transparent); }
.stop-rule-line:first-child { width: 22px; background: linear-gradient(90deg, transparent, rgba(240, 205, 138, 0.75)); }
.is-center .stop-rule-line { width: 80px; }
.is-center .stop-rule-line:last-child { background: linear-gradient(90deg, rgba(240, 205, 138, 0.75), transparent); }
.is-center .stop-rule-line:first-child { background: linear-gradient(90deg, transparent, rgba(240, 205, 138, 0.75)); }
.stop-rule svg { width: 11px; height: 11px; fill: #ffe4ad; filter: drop-shadow(0 0 4px rgba(255, 200, 110, 0.85)); }

h2 {
  margin: 0;
  font-family: var(--serif);
  font-weight: 500;
  font-size: clamp(34px, 3.6vw, 50px);
  line-height: 1.02;
  color: #f6efe2;
  text-shadow: 0 0 28px rgba(255, 214, 150, 0.16), 0 2px 18px rgba(0, 0, 0, 0.6);
}
h2 :deep(em) {
  font-style: italic;
  background: linear-gradient(180deg, #ffe7b8, #e2b56c);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  text-shadow: none;
  filter: drop-shadow(0 0 16px rgba(255, 200, 110, 0.22));
}
</style>
