<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { acceptConsent, hasConsent } from '../utils/consent.js'

/**
 * The note about cookies: a small card in the corner, in the night's colours, that says plainly
 * what the browser keeps and leaves once it is accepted. It waits a moment so it never meets
 * the visitor before the page does.
 */

const open = ref(false)

onMounted(() => {
  if (!hasConsent()) setTimeout(() => { open.value = true }, 900)
})

function accept() {
  acceptConsent()
  open.value = false
}
</script>

<template>
  <Transition name="cookie">
    <section v-if="open" class="cookie" role="region" aria-labelledby="cookie-title">
      <svg class="cookie-star" viewBox="0 0 20 20" aria-hidden="true">
        <path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" />
      </svg>
      <div class="cookie-body">
        <h2 id="cookie-title" class="cookie-title">Немного звёздной пыли</h2>
        <p class="cookie-text">
          Сайт хранит в браузере cookie и похожие данные: чтобы помнить вход в кабинет и ваш выбор,
          а Яндекс Метрика — чтобы мы видели, что на сайте удобно. Оставаясь здесь, вы соглашаетесь с этим.
        </p>
        <div class="cookie-actions">
          <button type="button" class="cookie-accept" @click="accept">Принять</button>
          <RouterLink class="cookie-more" :to="{ name: 'legal', params: { page: 'privacy' }, hash: '#cookies' }">Подробнее</RouterLink>
        </div>
      </div>
    </section>
  </Transition>
</template>

<style scoped>
.cookie {
  position: fixed;
  z-index: 5;
  left: 20px;
  bottom: calc(20px + env(safe-area-inset-bottom));
  display: grid;
  grid-template-columns: 22px 1fr;
  gap: 14px;
  width: min(400px, calc(100vw - 40px));
  padding: 18px 20px 18px 18px;
  border-radius: 20px;
  border: 1px solid rgba(240, 210, 150, 0.22);
  background:
    radial-gradient(120% 90% at 0% 0%, rgba(240, 205, 138, 0.1), transparent 60%),
    linear-gradient(180deg, #17140f, #0c0b0a);
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 236, 200, 0.06);
  color: #efe7d8;
}
.cookie::after {
  content: '';
  position: absolute;
  inset: 5px;
  border-radius: 15px;
  border: 1px solid rgba(240, 210, 150, 0.08);
  pointer-events: none;
}

.cookie-star { width: 18px; height: 18px; margin-top: 3px; fill: #f0cd8a; filter: drop-shadow(0 0 6px rgba(255, 205, 120, 0.8)); animation: twinkle 3.2s ease-in-out infinite; }
@keyframes twinkle { 50% { opacity: 0.55; transform: scale(0.86); } }

.cookie-body { display: grid; gap: 8px; }
.cookie-title { margin: 0; font-family: var(--caps); font-weight: 600; font-size: 18px; letter-spacing: 0.06em; color: #f0cd8a; }
.cookie-text { margin: 0; font-family: var(--book); font-size: 14px; line-height: 1.55; color: rgba(239, 231, 216, 0.82); }

.cookie-actions { display: flex; align-items: center; gap: 18px; margin-top: 6px; }
.cookie-accept {
  min-height: 40px;
  padding: 9px 22px;
  border: 0;
  border-radius: 999px;
  background: linear-gradient(180deg, #f4dba6, #dcb36c);
  color: #2b1d0b;
  font-family: var(--sans);
  font-weight: 600;
  font-size: 14.5px;
  cursor: pointer;
  box-shadow: 0 8px 22px rgba(220, 179, 108, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.5);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.cookie-accept:hover { transform: translateY(-1px); box-shadow: 0 10px 26px rgba(220, 179, 108, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.5); }
.cookie-accept:focus-visible, .cookie-more:focus-visible { outline: 2px solid #f0cd8a; outline-offset: 3px; }
.cookie-more {
  font-family: var(--serif);
  font-style: italic;
  font-size: 16px;
  color: #f0cd8a;
  text-decoration: underline;
  text-decoration-color: rgba(240, 205, 138, 0.35);
  text-underline-offset: 3px;
}
.cookie-more:hover { text-decoration-color: currentColor; }

.cookie-enter-active, .cookie-leave-active { transition: opacity 0.5s ease, transform 0.5s cubic-bezier(0.2, 0.8, 0.2, 1); }
.cookie-enter-from, .cookie-leave-to { opacity: 0; transform: translateY(14px); }

/* Phones: across the bottom, slimmer, so it does not cover the form it is about. */
@media (max-width: 560px) {
  .cookie { left: 10px; right: 10px; bottom: calc(10px + env(safe-area-inset-bottom)); width: auto; gap: 10px; padding: 14px 16px 14px 14px; }
  .cookie-title { font-size: 16px; }
  .cookie-text { font-size: 13px; line-height: 1.5; }
  .cookie-accept { min-height: 44px; }
}

@media (prefers-reduced-motion: reduce) {
  .cookie-star { animation: none; }
  .cookie-enter-active, .cookie-leave-active { transition: opacity 0.2s ease; }
  .cookie-enter-from, .cookie-leave-to { transform: none; }
}
</style>
