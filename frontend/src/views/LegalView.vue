<script setup>
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import SiteFrame from '../components/SiteFrame.vue'
import { siteApi } from '../api/site.js'
import { errorText } from '../api/http.js'
import { useHead } from '../utils/useHead.js'

const route = useRoute()
const page = ref(null)
const message = ref('')

async function load() {
  page.value = null
  message.value = ''
  useHead({ title: 'Документ', noindex: true })
  try {
    page.value = await siteApi.legal(route.params.page)
    useHead({ title: page.value.title, noindex: true })
  } catch (error) {
    message.value = errorText(error)
  }
}

watch(() => route.params.page, load, { immediate: true })
</script>

<template>
  <SiteFrame>
    <article class="section">
      <div class="wrap narrow-copy">
        <p v-if="message" class="error">{{ message }}</p>
        <template v-else-if="page">
          <h1>{{ page.title }}</h1>
          <p v-for="(paragraph, index) in page.paragraphs" :key="index">{{ paragraph }}</p>
        </template>
        <p v-else>Загружаем текст…</p>
      </div>
    </article>
  </SiteFrame>
</template>
