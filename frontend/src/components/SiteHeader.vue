<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import BrandMark from './BrandMark.vue'
import { useSession } from '../composables/useSession.js'
import { fallbackConfig, useSiteConfig } from '../composables/useSiteConfig.js'

const { webToken } = useSession()
const { config, load } = useSiteConfig()
const route = useRoute()
/** In the cabinet, any of its sections, the way to the cabinet is not needed. */
const inCabinet = computed(() => route.path.startsWith('/cabinet'))

const links = [
  { id: 'how', label: 'О проекте', glyph: '☉' },
  { id: 'services', label: 'Услуги', glyph: '☽' },
  { id: 'forecasts', label: 'Прогнозы', glyph: '✦' },
]

const scrolled = ref(false)
const active = ref('')
const menuOpen = ref(false)

/** Home sections in page order; only the ones with a link get highlighted. */
const SECTIONS = ['how', 'services', 'forecasts', 'about', 'start']
const linked = new Set(links.map((link) => link.id))

// The section whose top has passed the middle of the screen is the one being read.
function spy() {
  if (route.path !== '/') {
    active.value = ''
    return
  }
  let current = ''
  for (const id of SECTIONS) {
    const node = document.getElementById(id)
    if (node && node.getBoundingClientRect().top < window.innerHeight * 0.5) current = id
  }
  active.value = linked.has(current) ? current : ''
}

function onScroll() {
  scrolled.value = window.scrollY > 24
  spy()
}

// Clicking the link for the hash already in the URL does not navigate, so scroll by hand.
function onNav(id) {
  menuOpen.value = false
  // Unlock the page right away: the router scrolls before the menu watcher would run.
  document.body.classList.remove('menu-open')
  if (route.path === '/' && route.hash === `#${id}`) {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })
  }
}

function onKey(event) {
  if (event.key === 'Escape') menuOpen.value = false
}

watch(menuOpen, (open) => {
  document.body.classList.toggle('menu-open', open)
})
watch(() => route.fullPath, () => {
  menuOpen.value = false
  requestAnimationFrame(spy)
})

onMounted(() => {
  load()
  onScroll()
  window.addEventListener('scroll', onScroll, { passive: true })
  window.addEventListener('resize', spy, { passive: true })
  window.addEventListener('keydown', onKey)
})

onUnmounted(() => {
  window.removeEventListener('scroll', onScroll)
  window.removeEventListener('resize', spy)
  window.removeEventListener('keydown', onKey)
  document.body.classList.remove('menu-open')
})
</script>

<template>
  <header class="header" :class="{ 'is-scrolled': scrolled, 'is-menu': menuOpen }">
    <div class="capsule">
      <span class="header-line" aria-hidden="true" />
      <RouterLink to="/" class="brand" aria-label="На главную">
        <BrandMark class="mark" />
        <span class="brand-text">
          <span class="brand-name">{{ config?.site_name || fallbackConfig.site_name }}</span>
          <span class="brand-sub">натальная карта</span>
        </span>
      </RouterLink>

      <nav class="nav" aria-label="Основное меню">
        <template v-for="(link, index) in links" :key="link.id">
          <span v-if="index" class="nav-sep" aria-hidden="true" />
          <RouterLink
            class="nav-extra"
            :class="{ 'is-active': active === link.id }"
            :to="{ path: '/', hash: `#${link.id}` }"
            :aria-current="active === link.id ? 'location' : undefined"
            @click="onNav(link.id)"
          >
            {{ link.label }}
          </RouterLink>
        </template>
      </nav>

      <div class="header-actions">
        <!-- In the cabinet the way to the cabinet is not needed. -->
        <RouterLink v-if="!inCabinet" class="nav-login" :to="webToken ? '/cabinet' : '/login'" data-track="header:login">
          <span>{{ webToken ? 'Кабинет' : 'Войти' }}</span>
          <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3 8h9M8.5 4.5 12 8l-3.5 3.5" /></svg>
        </RouterLink>
        <button
          type="button"
          class="burger"
          data-track="header:menu"
          :aria-expanded="menuOpen"
          aria-controls="mobile-menu"
          :aria-label="menuOpen ? 'Закрыть меню' : 'Открыть меню'"
          @click="menuOpen = !menuOpen"
        >
          <span /><span />
        </button>
      </div>
    </div>

    <Transition name="menu">
      <div v-if="menuOpen" id="mobile-menu" class="mobile-menu" @click.self="menuOpen = false">
        <BrandMark class="menu-emblem" aria-hidden="true" />
        <nav class="menu-links" aria-label="Мобильное меню">
          <RouterLink
            v-for="(link, index) in links"
            :key="link.id"
            class="menu-link"
            :class="{ 'is-active': active === link.id }"
            :style="{ '--i': index }"
            :to="{ path: '/', hash: `#${link.id}` }"
            @click="onNav(link.id)"
          >
            <span class="menu-glyph" aria-hidden="true">{{ link.glyph }}</span>
            <span>{{ link.label }}</span>
          </RouterLink>
        </nav>
        <RouterLink v-if="!inCabinet" class="menu-cta" :style="{ '--i': links.length }" :to="webToken ? '/cabinet' : '/login'" data-track="menu:login" @click="menuOpen = false">
          {{ webToken ? 'Открыть кабинет' : 'Войти в кабинет' }}
        </RouterLink>
      </div>
    </Transition>
  </header>
</template>
