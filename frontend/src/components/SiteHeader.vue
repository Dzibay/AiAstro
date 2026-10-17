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
        <span class="mark" aria-hidden="true"></span>
        <span>{{ config?.site_name || fallbackConfig.site_name }}</span>
      </RouterLink>
      <nav class="nav">
        <RouterLink v-if="webToken" to="/cabinet">Кабинет</RouterLink>
        <RouterLink v-else to="/login">Войти</RouterLink>
      </nav>
    </div>
  </header>
</template>
