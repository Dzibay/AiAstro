<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { useSession } from '../composables/useSession.js'
import { fallbackConfig, useSiteConfig } from '../composables/useSiteConfig.js'

const { webToken } = useSession()
const { config, load } = useSiteConfig()

const scrolled = ref(false)

function onScroll() {
  scrolled.value = window.scrollY > 24
}

onMounted(() => {
  load()
  onScroll()
  window.addEventListener('scroll', onScroll, { passive: true })
})

onUnmounted(() => {
  window.removeEventListener('scroll', onScroll)
})
</script>

<template>
  <header class="header" :class="{ 'is-scrolled': scrolled }">
    <span class="header-line" aria-hidden="true" />
    <div class="wrap header-row">
      <RouterLink to="/" class="brand">
        <svg class="mark" viewBox="0 0 24 24" aria-hidden="true"><path d="M14.6 2.2A10 10 0 1 0 21.8 16a8.2 8.2 0 0 1-7.2-13.8Z" /></svg>
        <span class="brand-name">{{ config?.site_name || fallbackConfig.site_name }}</span>
      </RouterLink>
      <nav class="nav">
        <RouterLink class="nav-extra" :to="{ path: '/', hash: '#about' }">О проекте</RouterLink>
        <RouterLink class="nav-extra" :to="{ path: '/', hash: '#services' }">Услуги</RouterLink>
        <RouterLink class="nav-login" :to="webToken ? '/cabinet' : '/login'">
          <span>{{ webToken ? 'Кабинет' : 'Войти' }}</span>
          <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3 8h9M8.5 4.5 12 8l-3.5 3.5" /></svg>
        </RouterLink>
      </nav>
    </div>
  </header>
</template>
