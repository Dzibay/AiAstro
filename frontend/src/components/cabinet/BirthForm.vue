<script setup>
import { computed, reactive, ref, watch } from 'vue'
import PlaceInput from '../ui/PlaceInput.vue'
import { webApi } from '../../api/web.js'
import { errorText } from '../../api/http.js'
import { useSky } from '../../composables/useSky.js'
import { birthSigns } from '../../utils/skyToday.js'

/**
 * Birth data in the cabinet: added after «Заполню позже» or corrected later. The sky answers
 * while the date is typed, as on registration; on cancel the parent puts the saved sign back.
 *
 * The same form takes a partner's data: with a name, without touching the person's own sign
 * (`sky: false`), sent by `submit` and told to the sky as a `draft` while it is typed. On the
 * invitation page it also asks the partner's own consent.
 */

const props = defineProps({
  birth: { type: Object, default: null },
  withName: { type: Boolean, default: false },
  name: { type: String, default: '' },
  withConsent: { type: Boolean, default: false },
  /** Whether the date tries the person's own Sun sign on their star. */
  sky: { type: Boolean, default: true },
  /** ({ name, consent, birth }) → Promise of what `saved` carries. By default the person's own data. */
  submit: { type: Function, default: ({ birth }) => webApi.setBirth(birth) },
  submitLabel: { type: String, default: 'Сохранить' },
  cancellable: { type: Boolean, default: true },
})
const emit = defineEmits(['saved', 'cancel', 'draft'])

const { mark } = useSky()

function isoDay(date) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}
const latest = isoDay(new Date())

const saved = props.birth
const form = reactive({
  name: props.name,
  consent: false,
  date: saved?.date || '',
  time: saved?.time || '',
  noTime: Boolean(saved && !saved.time),
  city: saved?.place || '',
  place: saved?.lat != null ? { label: saved.place, lat: saved.lat, lon: saved.lon, tz: saved.tz } : null,
})
const pending = ref(false)
const message = ref('')
/** The reminder about suggestions waits until the person leaves the field. */
const typingCity = ref(false)

const dateKnown = computed(() => /^\d{4}-\d{2}-\d{2}$/.test(form.date) && form.date >= '1900-01-01' && form.date <= latest)
const timeKnown = computed(() => !form.noTime && /^\d{2}:\d{2}$/.test(form.time))
const unplaced = computed(() => !typingCity.value && form.city.trim().length > 1 && !form.place)

watch([dateKnown, () => form.date, timeKnown, () => form.time], () => {
  if (!props.sky) return
  const signs = dateKnown.value ? birthSigns(form.date, timeKnown.value ? form.time : '') : null
  mark.sun = signs?.sun || ''
  mark.moon = signs?.moon || ''
})

watch([() => form.name, dateKnown, timeKnown, () => form.time], () => {
  emit('draft', {
    name: form.name.trim(),
    date: dateKnown.value ? form.date : '',
    time: timeKnown.value ? form.time : '',
  })
}, { immediate: true })

async function save() {
  if (props.withName && !form.name.trim()) {
    message.value = 'Укажите имя'
    return
  }
  if (!dateKnown.value) {
    message.value = 'Укажите дату рождения'
    return
  }
  if (props.withConsent && !form.consent) {
    message.value = 'Отметьте согласие на обработку данных'
    return
  }
  message.value = ''
  pending.value = true
  const birth = { date: form.date, time: timeKnown.value ? form.time : null, place: form.city.trim() || null }
  if (form.place) Object.assign(birth, { lat: form.place.lat, lon: form.place.lon })
  try {
    emit('saved', await props.submit({ name: form.name.trim(), consent: form.consent, birth }))
  } catch (error) {
    message.value = errorText(error)
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <form class="birth-form" novalidate @submit.prevent="save">
    <slot name="head">
      <header class="form-head">
        <h2>Данные <em>рождения</em></h2>
        <p>Дата даёт знак Солнца, время — Луну и дома, город — координаты и часовой пояс.</p>
      </header>
    </slot>

    <label v-if="withName" class="field">
      <span class="field-label">Имя</span>
      <input v-model="form.name" type="text" maxlength="80" autocomplete="off" />
    </label>

    <div class="form-row">
      <label class="field">
        <span class="field-label">Дата</span>
        <input v-model="form.date" type="date" min="1900-01-01" :max="latest" />
      </label>
      <div class="field">
        <span class="field-head">
          <label class="field-label" for="birth-time">Время</label>
          <label class="check">
            <input v-model="form.noTime" type="checkbox" />
            <span class="check-box" aria-hidden="true" />
            <span>не знаю</span>
          </label>
        </span>
        <input id="birth-time" v-model="form.time" type="time" :disabled="form.noTime" />
      </div>
    </div>

    <div class="field" @focusin="typingCity = true" @focusout="typingCity = false">
      <label class="field-label" for="birth-city">Город</label>
      <PlaceInput id="birth-city" v-model="form.city" v-model:place="form.place" />
      <p v-if="unplaced" class="hint">Выберите город из подсказок — без координат карта не посчитает дома.</p>
    </div>

    <p v-if="form.noTime" class="hint">Без времени карта обойдётся без домов и Асцендента. Время можно добавить позже.</p>

    <label v-if="withConsent" class="check consent">
      <input v-model="form.consent" type="checkbox" />
      <span class="check-box" aria-hidden="true" />
      <span>
        Даю согласие на обработку
        <a href="/legal/consent" target="_blank" rel="noopener">персональных данных</a>
      </span>
    </label>

    <Transition name="swap">
      <p v-if="message" class="error" role="alert">{{ message }}</p>
    </Transition>

    <div class="actions">
      <button class="gold-cta" type="submit" :disabled="pending">{{ pending ? 'Минуту…' : submitLabel }}</button>
      <button v-if="cancellable" type="button" class="quiet" :disabled="pending" @click="emit('cancel')">Отмена</button>
    </div>
  </form>
</template>

<style scoped>
.birth-form { display: grid; gap: 14px; }

.form-head { display: grid; gap: 6px; }
.form-head h2 { margin: 0; font-family: var(--serif); font-weight: 500; font-size: 28px; line-height: 1.08; color: #f6efe2; }
.form-head em { font-style: italic; color: #f0cd8a; }
.form-head p { margin: 0; font-size: 14px; line-height: 1.5; color: rgba(226, 220, 210, 0.7); }

.form-row { display: grid; grid-template-columns: minmax(0, 1.3fr) minmax(0, 1fr); gap: 12px; }
.field { display: grid; gap: 7px; min-width: 0; }
.field-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.field-label { line-height: 16px; font-size: 10.5px; letter-spacing: 0.24em; text-transform: uppercase; color: rgba(226, 214, 192, 0.66); }
.field > input, .field-head + input {
  width: 100%;
  min-width: 0;
  height: 44px;
  padding: 0 14px;
  border-radius: 12px;
  border: 1px solid rgba(240, 210, 150, 0.18);
  background: rgba(255, 240, 210, 0.04);
  color: #f6efe2;
  font: inherit;
  font-size: 15px;
  color-scheme: dark;
  outline: none;
  transition: border-color 0.25s ease, background 0.25s ease, box-shadow 0.25s ease;
}
.field input:hover:not(:disabled) { border-color: rgba(240, 210, 150, 0.32); }
.field input:focus {
  border-color: rgba(240, 205, 138, 0.7);
  background: rgba(255, 240, 210, 0.06);
  box-shadow: 0 0 0 3px rgba(240, 205, 138, 0.12);
}
.field input:disabled { opacity: 0.4; cursor: not-allowed; }
.field input::-webkit-calendar-picker-indicator { opacity: 0.6; cursor: pointer; }

.check {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  line-height: 16px;
  color: rgba(226, 220, 210, 0.7);
  cursor: pointer;
}
.check input { position: absolute; opacity: 0; pointer-events: none; }
.check-box {
  position: relative;
  flex: none;
  width: 13px;
  height: 13px;
  border-radius: 4px;
  border: 1px solid rgba(240, 210, 150, 0.4);
  transition: background 0.2s ease, border-color 0.2s ease;
}
.check-box::after {
  content: '';
  position: absolute;
  left: 4px;
  top: 1.5px;
  width: 3px;
  height: 6px;
  border: solid #2b1d0b;
  border-width: 0 1.5px 1.5px 0;
  transform: rotate(45deg) scale(0);
  transition: transform 0.2s ease;
}
.check input:checked + .check-box { background: #e9c47e; border-color: #e9c47e; }
.check input:checked + .check-box::after { transform: rotate(45deg) scale(1); }
.check input:focus-visible + .check-box { box-shadow: 0 0 0 3px rgba(240, 205, 138, 0.25); }

.consent { align-items: flex-start; font-size: 13px; line-height: 18px; }
.consent .check-box { margin-top: 2px; }
.consent a { color: #f0cd8a; text-decoration: underline; text-decoration-color: rgba(240, 205, 138, 0.4); text-underline-offset: 3px; }
.consent a:hover { text-decoration-color: currentColor; }

.hint { margin: 0; font-size: 12.5px; line-height: 1.45; color: rgba(233, 194, 124, 0.75); }

.error {
  margin: 0;
  padding: 9px 12px;
  border-radius: 10px;
  border: 1px solid rgba(230, 140, 110, 0.3);
  background: rgba(200, 90, 60, 0.08);
  font-size: 13.5px;
  line-height: 1.4;
  color: #f2c3ae;
}

.actions { display: flex; align-items: center; gap: 16px; margin-top: 2px; }
.gold-cta {
  flex: 1;
  padding: 12px 22px;
  border: 0;
  border-radius: 999px;
  font: inherit;
  font-weight: 600;
  color: #2b1d0b;
  background: linear-gradient(180deg, #f4dba6 0%, #e3bd78 55%, #cf9f55 100%);
  box-shadow: inset 0 1px 0 rgba(255, 248, 228, 0.8), 0 8px 30px rgba(230, 170, 80, 0.32);
  cursor: pointer;
  transition: box-shadow 0.3s ease, filter 0.3s ease, opacity 0.3s ease;
}
.gold-cta:hover:not(:disabled) { filter: brightness(1.05); box-shadow: inset 0 1px 0 rgba(255, 248, 228, 0.8), 0 10px 38px rgba(230, 170, 80, 0.48); }
.gold-cta:focus-visible { outline: 2px solid #ffe2a8; outline-offset: 3px; }
.gold-cta:disabled { opacity: 0.6; cursor: progress; }
.quiet {
  padding: 6px 4px;
  border: 0;
  background: none;
  font: inherit;
  font-size: 13.5px;
  color: rgba(226, 220, 210, 0.72);
  cursor: pointer;
  transition: color 0.25s ease;
}
.quiet:hover:not(:disabled) { color: #f0cd8a; }
.quiet:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 2px; border-radius: 6px; }

.swap-enter-active, .swap-leave-active { transition: opacity 0.25s ease, transform 0.25s ease; }
.swap-enter-from { opacity: 0; transform: translateY(6px); }
.swap-leave-to { opacity: 0; transform: translateY(-6px); }

@media (max-width: 760px) {
  .form-row { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 10px; }
  .field > input, .field-head + input { font-size: 16px; }
  .check { padding-block: 8px; margin-block: -8px; }
  .field-head { gap: 6px; }
  .field-head .check { gap: 7px; white-space: nowrap; }
  .field-head .field-label { letter-spacing: 0.18em; }
  .quiet { min-height: 40px; }
}
</style>
