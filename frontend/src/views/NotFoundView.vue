<script setup>
import { computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import SiteFrame from '../components/SiteFrame.vue'
import { supportOf, useSiteConfig } from '../composables/useSiteConfig.js'
import { readSession } from '../composables/useSession.js'
import { useHead } from '../utils/useHead.js'

/**
 * An address the site does not know: an old link, a typo. Not a silent jump to the home page —
 * the person sees what happened and the ways on: home, the free chart, the cabinet if signed in.
 * Search engines are told not to keep it.
 */

const { config, load } = useSiteConfig()
const support = computed(() => supportOf(config.value))
const signedIn = Boolean(readSession('web'))

useHead({ title: 'Страница не найдена', noindex: true })
onMounted(load)
</script>

<template>
  <SiteFrame>
    <section class="section lost">
      <div class="wrap lost-copy">
        <p class="eyebrow">Ошибка 404</p>
        <h1>Этой страницы нет <em>на нашей карте неба</em></h1>
        <p class="lost-lead">
          Возможно, ссылка устарела или в адресе опечатка. Звёзды на месте — вот куда можно пойти дальше.
        </p>
        <div class="lost-ways">
          <RouterLink class="gold-cta" to="/">На главную</RouterLink>
          <RouterLink v-if="signedIn" class="line-cta" :to="{ name: 'cabinet' }">В кабинет <span aria-hidden="true">→</span></RouterLink>
          <RouterLink v-else class="line-cta" to="/natalnaya-karta">Натальная карта бесплатно <span aria-hidden="true">→</span></RouterLink>
        </div>
        <p v-if="support" class="lost-help">
          Пришли по ссылке с нашего сайта? Напишите нам —
          <a :href="support.href" target="_blank" rel="noopener">{{ support.label }}</a>, поправим.
        </p>
      </div>
    </section>
  </SiteFrame>
</template>

<style scoped>
.lost { position: relative; z-index: 1; display: grid; align-content: center; min-height: calc(100svh - 120px); padding-top: 120px; }
/* The text lies on the sky; a soft night behind it keeps it legible over the stars, as on the landings. */
.lost::before {
  content: '';
  position: fixed;
  inset: 0;
  z-index: -1;
  pointer-events: none;
  background: linear-gradient(90deg, rgba(4, 6, 12, 0.7), rgba(4, 6, 12, 0.35) 55%, transparent 80%);
}
.lost-copy { width: min(720px, calc(100% - 40px)); }
.lost h1 { margin: 0 0 18px; font-family: var(--serif); font-weight: 500; font-size: clamp(38px, 6vw, 64px); line-height: 1.05; color: #f6efe2; }
.lost h1 em { font-style: italic; color: #f0cd8a; }
.lost-lead { margin: 0 0 30px; font-family: var(--serif); font-style: italic; font-size: 21px; line-height: 1.45; color: rgba(239, 231, 216, 0.85); }
.lost-ways { display: flex; flex-wrap: wrap; align-items: center; gap: 14px 18px; }
.lost-help { margin: 34px 0 0; font-size: 15px; line-height: 1.6; color: rgba(226, 220, 210, 0.7); }
.lost-help a { color: #f0cd8a; }

.gold-cta {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 14px 34px;
  border-radius: 999px;
  font-weight: 600;
  color: #2b1d0b;
  text-decoration: none;
  background: linear-gradient(180deg, #f4dba6 0%, #e3bd78 55%, #cf9f55 100%);
  box-shadow: inset 0 1px 0 rgba(255, 248, 228, 0.8), 0 8px 30px rgba(230, 170, 80, 0.32);
  transition: box-shadow 0.3s ease, filter 0.3s ease;
}
.gold-cta:hover { filter: brightness(1.05); box-shadow: inset 0 1px 0 rgba(255, 248, 228, 0.8), 0 10px 38px rgba(230, 170, 80, 0.48); }
.line-cta {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 12px 22px;
  border-radius: 999px;
  border: 1px solid rgba(240, 205, 138, 0.45);
  background: rgba(20, 18, 22, 0.45);
  color: #f3dcae;
  text-decoration: none;
  transition: border-color 0.3s ease, background 0.3s ease, color 0.3s ease;
}
.line-cta span { transition: transform 0.3s ease; }
.line-cta:hover { border-color: rgba(255, 220, 160, 0.8); background: rgba(255, 210, 126, 0.08); color: #ffe7b8; }
.line-cta:hover span { transform: translateX(3px); }
.gold-cta:focus-visible, .line-cta:focus-visible { outline: 2px solid #f0cd8a; outline-offset: 3px; }

@media (max-width: 760px) {
  .lost { min-height: 0; padding-top: 110px; }
  .lost-lead { font-size: 18px; }
  .lost-ways > * { width: 100%; justify-content: center; }
}
</style>
