<script setup>
import { onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useSession } from '../composables/useSession.js'
import { fallbackConfig, useSiteConfig } from '../composables/useSiteConfig.js'

const { webToken } = useSession()
const { config, load } = useSiteConfig()

onMounted(() => {
  load()
})
</script>

<template>
  <header class="header">
    <div class="wrap header-row">
      <RouterLink to="/" class="brand">
        <svg class="mark" viewBox="0 0 24 24" aria-hidden="true"><path d="M14.6 2.2A10 10 0 1 0 21.8 16a8.2 8.2 0 0 1-7.2-13.8Z" /></svg>
        <span>{{ config?.site_name || fallbackConfig.site_name }}</span>
      </RouterLink>
      <nav class="nav">
        <RouterLink class="nav-extra" :to="{ path: '/', hash: '#about' }">О проекте</RouterLink>
        <RouterLink class="nav-extra" :to="{ path: '/', hash: '#services' }">Услуги</RouterLink>
        <RouterLink v-if="webToken" class="nav-login" to="/cabinet">Кабинет</RouterLink>
        <RouterLink v-else class="nav-login" to="/login">Войти</RouterLink>
      </nav>
    </div>
  </header>
</template>
