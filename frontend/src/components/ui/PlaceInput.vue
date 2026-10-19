<script setup>
import { computed, onUnmounted, ref, useId } from 'vue'
import { webApi } from '../../api/web.js'

/**
 * The birth city with suggestions from the geocoder (GET /api/web/places). The text is the
 * v-model; picking a suggestion also sets `place` ({ label, lat, lon, tz }), and typing again
 * forgets it, so coordinates never belong to a different word than the one in the field.
 * The list opens in the flow of the form, not over it: the cards around clip their overflow.
 */

const props = defineProps({
  modelValue: { type: String, default: '' },
  place: { type: Object, default: null },
  id: { type: String, default: '' },
  placeholder: { type: String, default: 'Например, Казань' },
})
const emit = defineEmits(['update:modelValue', 'update:place'])

const DELAY = 350
/** Answers already seen in this tab: Backspace and retyping do not ask the server again. */
const seen = new Map()

const listId = useId()
const open = ref(false)
const options = ref([])
const active = ref(-1)
/** '' | 'loading' | 'empty' | 'error' */
const status = ref('')
let timer = 0
let asked = 0

const found = computed(() => Boolean(props.place && props.place.label === props.modelValue))

function close() {
  open.value = false
  active.value = -1
}

async function ask(query) {
  const key = query.toLocaleLowerCase('ru')
  const ticket = ++asked
  if (seen.has(key)) {
    show(seen.get(key))
    return
  }
  status.value = 'loading'
  try {
    const result = await webApi.places(query)
    seen.set(key, result)
    // A slow answer to an older word must not replace the list for the newer one.
    if (ticket === asked) show(result)
  } catch {
    if (ticket === asked) {
      options.value = []
      status.value = 'error'
      open.value = true
    }
  }
}

function show(result) {
  options.value = result
  status.value = result.length ? '' : 'empty'
  active.value = -1
  open.value = true
}

function onInput(event) {
  const text = event.target.value
  emit('update:modelValue', text)
  if (props.place) emit('update:place', null)
  clearTimeout(timer)
  const query = text.trim()
  if (query.length < 2) {
    asked += 1
    options.value = []
    status.value = ''
    close()
    return
  }
  timer = setTimeout(() => ask(query), DELAY)
}

function pick(option) {
  emit('update:modelValue', option.label)
  emit('update:place', { label: option.label, lat: option.lat, lon: option.lon, tz: option.tz })
  options.value = []
  status.value = ''
  close()
}

function onKey(event) {
  if (!open.value || !options.value.length) {
    if (event.key === 'ArrowDown' && options.value.length) open.value = true
    return
  }
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault()
    const step = event.key === 'ArrowDown' ? 1 : -1
    active.value = (active.value + step + options.value.length) % options.value.length
  } else if (event.key === 'Enter' && active.value >= 0) {
    // Enter picks the city here instead of sending the whole form.
    event.preventDefault()
    pick(options.value[active.value])
  } else if (event.key === 'Escape') {
    event.preventDefault()
    close()
  }
}

function onFocus() {
  if (!found.value && (options.value.length || status.value === 'empty')) open.value = true
}

onUnmounted(() => clearTimeout(timer))
</script>

<template>
  <div class="place" :class="{ 'is-open': open }">
    <span class="place-box">
      <input
        :id="id || undefined"
        :value="modelValue"
        type="text"
        role="combobox"
        autocomplete="off"
        maxlength="120"
        :placeholder="placeholder"
        :aria-expanded="open && options.length > 0"
        :aria-controls="listId"
        aria-autocomplete="list"
        :aria-activedescendant="active >= 0 ? `${listId}-${active}` : undefined"
        @input="onInput"
        @keydown="onKey"
        @focus="onFocus"
        @blur="close"
      />
      <svg v-if="found" class="place-found" viewBox="0 0 20 20" aria-hidden="true">
        <path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" />
      </svg>
      <span v-else-if="status === 'loading'" class="place-wait" aria-hidden="true" />
    </span>

    <ul v-show="open && options.length" :id="listId" class="place-list" role="listbox">
      <li
        v-for="(option, index) in options"
        :id="`${listId}-${index}`"
        :key="option.label"
        role="option"
        :aria-selected="index === active"
        :class="{ 'is-active': index === active }"
        @mousedown.prevent="pick(option)"
        @mousemove="active = index"
      >
        <span class="place-name">{{ option.name }}</span>
        <span v-if="option.region" class="place-region">{{ option.region }}</span>
      </li>
    </ul>

    <p v-if="open && status === 'empty'" class="place-note">Не нашли такого места — проверьте написание</p>
    <p v-else-if="open && status === 'error'" class="place-note">Подсказки сейчас недоступны. Город сохранится как написан</p>
    <span class="sr-only" aria-live="polite">{{ found ? 'Город найден на карте' : open && options.length ? `Подсказок: ${options.length}` : '' }}</span>
  </div>
</template>

<style scoped>
.place { display: grid; gap: 6px; min-width: 0; }
.place-box { position: relative; display: block; }

/* The same field as the rest of the form around it. */
.place input {
  width: 100%;
  min-width: 0;
  height: 44px;
  padding: 0 40px 0 14px;
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
.place input::placeholder { color: rgba(226, 220, 210, 0.38); }
.place input:hover { border-color: rgba(240, 210, 150, 0.32); }
.place input:focus {
  border-color: rgba(240, 205, 138, 0.7);
  background: rgba(255, 240, 210, 0.06);
  box-shadow: 0 0 0 3px rgba(240, 205, 138, 0.12);
}

/* A small star: the city is on the map, the chart will know its coordinates. */
.place-found {
  position: absolute;
  top: 50%;
  right: 15px;
  width: 11px;
  height: 11px;
  fill: #f0cd8a;
  filter: drop-shadow(0 0 5px rgba(255, 200, 110, 0.85));
  transform: translateY(-50%);
  animation: found-in 0.5s cubic-bezier(0.3, 0.7, 0.2, 1) both;
}
.place-wait {
  position: absolute;
  top: 50%;
  right: 16px;
  width: 6px;
  height: 6px;
  margin-top: -3px;
  border-radius: 50%;
  background: #f0cd8a;
  animation: wait 1.1s ease-in-out infinite;
}

.place-list {
  display: grid;
  margin: 0;
  padding: 4px;
  list-style: none;
  border-radius: 12px;
  border: 1px solid rgba(240, 210, 150, 0.16);
  background: rgba(10, 11, 18, 0.55);
  animation: list-in 0.25s ease both;
}
.place-list li {
  display: flex;
  align-items: baseline;
  gap: 8px;
  min-width: 0;
  padding: 9px 10px;
  border-radius: 9px;
  cursor: pointer;
  transition: background 0.15s ease;
}
.place-list li.is-active { background: rgba(240, 205, 138, 0.1); }
.place-name { flex: none; font-family: var(--serif); font-size: 17px; color: #f6efe2; }
.place-region { min-width: 0; overflow: hidden; font-size: 12.5px; color: rgba(226, 220, 210, 0.55); text-overflow: ellipsis; white-space: nowrap; }
.place-list li.is-active .place-name { color: #f0cd8a; }

.place-note { margin: 0; font-size: 12.5px; line-height: 1.4; color: rgba(226, 220, 210, 0.6); }

.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }

@keyframes found-in { from { opacity: 0; transform: translateY(-50%) scale(0.2) rotate(-45deg); } }
@keyframes wait { 50% { opacity: 0.25; transform: scale(0.6); } }
@keyframes list-in { from { opacity: 0; transform: translateY(-4px); } }

@media (max-width: 760px) {
  .place input { font-size: 16px; }
  .place-list li { min-height: 44px; align-items: center; }
}

@media (prefers-reduced-motion: reduce) {
  .place-found, .place-list { animation: none; }
  .place-wait { animation-duration: 2.4s; }
}
</style>
