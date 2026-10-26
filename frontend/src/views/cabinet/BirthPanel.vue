<script setup>
import { computed, onMounted } from 'vue'
import BirthForm from '../../components/cabinet/BirthForm.vue'
import { supportOf, useSiteConfig } from '../../composables/useSiteConfig.js'
import { reachGoal } from '../../utils/track.js'

/**
 * The birth data, opened from the person's star or the overview. CabinetView leads back.
 *
 * A chart, a pair and a forecast are bought for these data: the first correction is the
 * person's own, the next ones go through the support. A time unknown before can always be added.
 */

const props = defineProps({
  user: { type: Object, required: true },
})
const emit = defineEmits(['saved', 'done'])

const { config, load } = useSiteConfig()
onMounted(load)

const locked = computed(() => Boolean(props.user.birth_locked))
/** Locked, the form stays only to add the time, if it was unknown. */
const timeOnly = computed(() => locked.value && !props.user.birth?.time)
const support = computed(() => supportOf(config.value))

/** The first date of birth is a Metrika goal: the chart can be built from here. */
function saved(user) {
  if (!props.user.birth && user?.birth) reachGoal('astra.birth@save')
  emit('saved', user)
}
</script>

<template>
  <div class="birth-panel">
    <BirthForm v-if="!locked || timeOnly" :birth="user.birth" @saved="saved" @cancel="emit('done')">
      <template v-if="timeOnly" #head>
        <header class="form-head">
          <h2>Данные <em>рождения</em></h2>
          <p>
            Дата и город уже исправлялись — их следующую правку внесёт поддержка.
            Время рождения можно добавить всегда: оно откроет дома и Асцендент.
          </p>
        </header>
      </template>
      <template v-else-if="!user.birth" #head>
        <header class="form-head">
          <h2>Нарисуем ваше <em>небо</em></h2>
          <p>
            Дата даст знак Солнца, время — Луну и дома, город — координаты. Точное время можно добавить и позже —
            карта построится и без него.
          </p>
        </header>
      </template>
      <template v-else-if="user.birth" #head>
        <header class="form-head">
          <h2>Данные <em>рождения</em></h2>
          <p>
            Исправить данные можно один раз — от них зависят карта, пары и разборы; дальше поможет поддержка.
            Добавить время, если оно было неизвестно, можно всегда.
          </p>
        </header>
      </template>
    </BirthForm>

    <section v-else class="locked">
      <h2>Данные <em>рождения</em></h2>
      <dl>
        <div><dt>Дата</dt><dd>{{ user.birth.date.split('-').reverse().join('.') }}</dd></div>
        <div><dt>Время</dt><dd>{{ user.birth.time }}</dd></div>
        <div v-if="user.birth.place"><dt>Город</dt><dd>{{ user.birth.place }}</dd></div>
      </dl>
      <p>
        Свою правку вы уже сделали: от этих данных зависят карта, пары и купленные разборы.
        Если в них ошибка, напишите в поддержку<template v-if="support"> — <a :href="support.href" target="_blank" rel="noopener">{{ support.label }}</a></template>,
        и мы исправим.
      </p>
      <button type="button" class="quiet" @click="emit('done')">Назад</button>
    </section>
  </div>
</template>

<style scoped>
.form-head { display: grid; gap: 6px; }
.form-head h2, .locked h2 { margin: 0; font-family: var(--serif); font-weight: 500; font-size: 26px; color: #f6efe2; }
.form-head em, .locked em { font-style: italic; color: #f0cd8a; }
.form-head p, .locked p { margin: 0; font-size: 14px; line-height: 1.5; color: rgba(226, 220, 210, 0.7); }
.locked { display: grid; gap: 14px; }
.locked dl { display: grid; gap: 8px; margin: 0; }
.locked dl div { display: flex; justify-content: space-between; gap: 16px; padding-bottom: 8px; border-bottom: 1px solid rgba(240, 210, 150, 0.1); }
.locked dt { font-size: 12px; letter-spacing: 0.14em; text-transform: uppercase; color: rgba(233, 194, 124, 0.7); }
.locked dd { margin: 0; color: #efe7d8; }
.locked a { color: #f0cd8a; text-underline-offset: 3px; }
.quiet {
  justify-self: start;
  min-height: 40px;
  padding: 0 18px;
  border-radius: 999px;
  border: 1px solid rgba(240, 210, 150, 0.22);
  background: rgba(255, 240, 210, 0.04);
  color: #efe7d8;
  font: inherit;
  cursor: pointer;
}
.quiet:hover { border-color: rgba(240, 205, 138, 0.5); }
</style>
