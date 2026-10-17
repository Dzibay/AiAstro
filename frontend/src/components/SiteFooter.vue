<script setup>
import { onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { fallbackConfig, useSiteConfig } from '../composables/useSiteConfig.js'

const { config, load } = useSiteConfig()

onMounted(() => {
  load()
})
</script>

<template>
  <footer class="footer">
    <div class="wrap footer-row">
      <p>{{ config?.site_name || fallbackConfig.site_name }}</p>
      <nav class="footer-links">
        <RouterLink to="/legal/privacy">Конфиденциальность</RouterLink>
        <RouterLink to="/legal/offer">Оферта</RouterLink>
        <RouterLink to="/legal/consent">Согласие</RouterLink>
        <a v-if="config?.support_email" :href="`mailto:${config.support_email}`">{{ config.support_email }}</a>
      </nav>
    </div>
  </footer>
</template>
