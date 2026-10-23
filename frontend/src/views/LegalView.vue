<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import SiteFrame from '../components/SiteFrame.vue'
import { siteApi } from '../api/site.js'
import { errorText } from '../api/http.js'
import { useHead } from '../utils/useHead.js'

/**
 * A document of the site — the offer, the privacy policy, the consent — set like a book's appendix:
 * contents first, then numbered sections and clauses, and the other two documents at the end.
 */

const DOCS = [
  { slug: 'offer', name: 'Публичная оферта' },
  { slug: 'privacy', name: 'Политика конфиденциальности' },
  { slug: 'consent', name: 'Согласие на обработку данных' },
  { slug: 'cookies', name: 'Политика использования cookie' },
]

const route = useRoute()
const page = ref(null)
const message = ref('')

const updated = computed(() => {
  if (!page.value?.updated) return ''
  const date = new Date(`${page.value.updated}T12:00:00`)
  return new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' }).format(date)
})
const others = computed(() => DOCS.filter((doc) => doc.slug !== route.params.page))

async function load() {
  page.value = null
  message.value = ''
  useHead({ title: 'Документ', noindex: true })
  try {
    page.value = await siteApi.legal(route.params.page)
    useHead({ title: page.value.title })
    await nextTick()
    if (route.hash) document.getElementById(route.hash.slice(1))?.scrollIntoView()
  } catch (error) {
    message.value = errorText(error)
  }
}

watch(() => route.params.page, load, { immediate: true })
</script>

<template>
  <SiteFrame>
    <article class="section legal">
      <div class="wrap narrow-copy">
        <p v-if="message" class="error">{{ message }}</p>
        <template v-else-if="page">
          <p class="eyebrow">Документы</p>
          <h1>{{ page.title }}</h1>
          <p class="lead">{{ page.lead }}</p>
          <p class="updated">Редакция от {{ updated }}</p>

          <nav class="contents" aria-label="Содержание">
            <p class="contents-title">Содержание</p>
            <ol>
              <li v-for="section in page.sections" :key="section.id">
                <a :href="`#${section.id}`">{{ section.title }}</a>
              </li>
            </ol>
          </nav>

          <section v-for="(section, s) in page.sections" :id="section.id" :key="section.id" class="part">
            <h2><span class="part-number">{{ s + 1 }}.</span> {{ section.title }}</h2>
            <ol class="clauses">
              <li v-for="(item, i) in section.items" :key="i">
                <span class="clause-number">{{ s + 1 }}.{{ i + 1 }}.</span>
                <div class="clause-text">
                  <template v-if="typeof item === 'string'">{{ item }}</template>
                  <template v-else>
                    {{ item.text }}
                    <ul>
                      <li v-for="(line, l) in item.list" :key="l">{{ line }}</li>
                    </ul>
                  </template>
                </div>
              </li>
            </ol>
          </section>

          <footer class="others">
            <span class="others-star" aria-hidden="true">✦</span>
            <p>Другие документы:</p>
            <RouterLink v-for="doc in others" :key="doc.slug" :to="{ name: 'legal', params: { page: doc.slug } }">{{ doc.name }}</RouterLink>
          </footer>
        </template>
        <p v-else class="loading">Загружаем текст…</p>
      </div>
    </article>
  </SiteFrame>
</template>

<style scoped>
.legal h1 { font-size: clamp(40px, 6vw, 64px); line-height: 1.05; }
.lead { margin: 0 0 10px; font-family: var(--serif); font-style: italic; font-size: 21px; line-height: 1.45; color: rgba(239, 231, 216, 0.85); }
.updated { margin: 0 0 30px; font-family: var(--caps); font-weight: 600; font-size: 14px; letter-spacing: 0.1em; color: rgba(240, 205, 138, 0.7); }

.contents { margin: 0 0 40px; padding: 20px 24px; border-radius: 18px; border: 1px solid rgba(240, 210, 150, 0.16); background: linear-gradient(180deg, rgba(240, 205, 138, 0.05), transparent); }
.contents-title { margin: 0 0 10px; font-family: var(--caps); font-weight: 600; font-size: 17px; letter-spacing: 0.1em; color: #f0cd8a; }
.contents ol { margin: 0; padding-left: 1.4em; columns: 2; column-gap: 28px; font-family: var(--book); font-size: 15px; line-height: 1.75; color: rgba(240, 205, 138, 0.6); }
.contents li { break-inside: avoid; }
.contents a { color: #efe7d8; text-decoration: none; }
.contents a:hover { color: #f0cd8a; text-decoration: underline; text-decoration-color: rgba(240, 205, 138, 0.4); text-underline-offset: 3px; }

.part { scroll-margin-top: 100px; margin: 0 0 34px; }
.part h2 { margin: 0 0 14px; padding-bottom: 10px; border-bottom: 1px solid rgba(240, 210, 150, 0.14); font-family: var(--caps); font-weight: 600; font-size: 24px; letter-spacing: 0.04em; color: #f6efe2; }
.part-number { color: #f0cd8a; }

.clauses { display: grid; gap: 12px; margin: 0; padding: 0; list-style: none; }
.clauses > li { display: grid; grid-template-columns: 3.2em 1fr; font-family: var(--book); font-size: 16px; line-height: 1.7; color: #e6dfd2; }
.clause-number { color: rgba(240, 205, 138, 0.65); font-variant-numeric: tabular-nums; }
.clause-text ul { margin: 6px 0 0; padding: 0; list-style: none; display: grid; gap: 4px; }
.clause-text ul li { position: relative; padding-left: 1.4em; }
.clause-text ul li::before { content: '✦'; position: absolute; left: 0; top: 0.1em; font-size: 0.7em; color: #f0cd8a; }

.others { display: flex; flex-wrap: wrap; align-items: baseline; gap: 8px 20px; margin-top: 48px; padding-top: 22px; border-top: 1px solid rgba(240, 210, 150, 0.14); }
.others-star { color: #f0cd8a; }
.others p { margin: 0; font-family: var(--serif); font-style: italic; font-size: 17px; color: rgba(226, 220, 210, 0.65); }
.others a { font-family: var(--serif); font-size: 18px; color: #f0cd8a; text-decoration: underline; text-decoration-color: rgba(240, 205, 138, 0.35); text-underline-offset: 3px; }
.others a:hover { text-decoration-color: currentColor; }
.loading { font-family: var(--serif); font-style: italic; color: rgba(226, 220, 210, 0.6); }

@media (max-width: 640px) {
  .lead { font-size: 18px; }
  .contents { padding: 16px 18px; }
  .contents ol { columns: 1; }
  .part h2 { font-size: 21px; }
  .clauses > li { grid-template-columns: 2.8em 1fr; font-size: 15px; line-height: 1.65; }
}
</style>
