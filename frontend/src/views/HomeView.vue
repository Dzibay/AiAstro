<script setup>
import { computed, onMounted } from 'vue'
import SiteFrame from '../components/SiteFrame.vue'
import HeroOrbit from '../components/HeroOrbit.vue'
import { fallbackConfig, useSiteConfig } from '../composables/useSiteConfig.js'
import { useHead } from '../utils/useHead.js'

const services = [
  {
    title: 'Натальная карта',
    text: 'Положения планет на момент рождения и что они значат в быту, работе и близких отношениях.',
  },
  {
    title: 'Период',
    text: 'Какие темы становятся громче в выбранные месяцы и где лучше не принимать решение с ходу.',
  },
  {
    title: 'Совместимость',
    text: 'Где два человека совпадают по ритму, а где им заранее нужны понятные правила.',
  },
]

const { config, load } = useSiteConfig()
const name = computed(() => config.value?.site_name || fallbackConfig.site_name)
const tagline = computed(() => config.value?.tagline || fallbackConfig.tagline)

onMounted(async () => {
  await load()
  useHead({
    title: `${name.value} — ${tagline.value}`,
    description: tagline.value,
  })
})
</script>

<template>
  <SiteFrame>
    <HeroOrbit :name="name" :tagline="tagline" />
    <section id="services" class="section">
      <div class="wrap">
        <h2>Что будет в разборе</h2>
        <div class="cards">
          <article v-for="service in services" :key="service.title" class="card">
            <h3>{{ service.title }}</h3>
            <p>{{ service.text }}</p>
          </article>
        </div>
      </div>
    </section>
    <section id="about" class="section section-quiet">
      <div class="wrap narrow-copy">
        <h2>Сейчас открыт кабинет</h2>
        <p>
          Можно зарегистрироваться и войти. Расчёт карты ещё не подключён: в кабинете видна учётная запись,
          готовых разборов там нет.
        </p>
      </div>
    </section>
  </SiteFrame>
</template>
