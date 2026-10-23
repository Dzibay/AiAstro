<script setup>
import { RouterView, useRoute } from 'vue-router'
import SkyStage from './components/SkyStage.vue'
import { useToast } from './composables/useToast.js'
import CookieNote from './components/CookieNote.vue'

const { items } = useToast()
const route = useRoute()
</script>

<template>
  <!-- One sky for every route that asks for it, so moving between them never restarts it. -->
  <SkyStage v-if="route.meta.sky" />
  <RouterView />
  <div class="toasts" aria-live="polite">
    <p v-for="item in items" :key="item.id" class="toast">{{ item.text }}</p>
  </div>
  <!-- The operator's pages are not the visitor's site: no cookie note over the figures. -->
  <CookieNote v-if="!route.path.startsWith('/admin')" />
</template>
