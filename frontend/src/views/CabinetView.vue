<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { RouterLink, RouterView, onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router'
import SiteHeader from '../components/SiteHeader.vue'
import CabinetSky from '../components/cabinet/CabinetSky.vue'
import CabinetTour from '../components/cabinet/CabinetTour.vue'
import NatalWheel from '../components/cabinet/NatalWheel.vue'
import PairSky from '../components/cabinet/PairSky.vue'
import SkyDome from '../components/sky/SkyDome.vue'
import { ROUTE_ORDER, SECTION_BY_ID } from '../components/cabinet/layout.js'
import { webApi } from '../api/web.js'
import { ApiError, errorText } from '../api/http.js'
import { clearSession } from '../composables/useSession.js'
import { useSky } from '../composables/useSky.js'
import { useChart } from '../composables/useChart.js'
import { useForecast } from '../composables/useForecast.js'
import { linkPendingInvite, pendingInvite, usePartners } from '../composables/usePartners.js'
import { useChat } from '../composables/useChat.js'
import { useHead } from '../utils/useHead.js'
import { startTour, stopTour, tour, tourSeen } from '../utils/tour.js'
import { takeMarks } from '../utils/marks.js'

/**
 * The cabinet's shell: the sky is the menu (CabinetSky, about the person's star) and one glass
 * panel holds whatever is open. On a phone the panel is a sheet from the bottom that can be
 * raised, lowered and swiped sideways to the next section.
 */

const route = useRoute()
const router = useRouter()
const { mark, markUser, clearMark } = useSky()
const { chart, load: loadChart, forget: forgetChart } = useChart()
const { forecasts, forget: forgetForecast } = useForecast()
const { partners, draft, hot, hotAspect, lit, syntheses, load: loadPartners, forgetSyntheses } = usePartners()
const { forget: forgetChat } = useChat()
const user = ref(null)
const message = ref('')
// What the person has been through (tours, newcomer steps) comes with them from the account,
// before anything asks whether a tour was seen.
watch(user, (current) => current && takeMarks(current), { flush: 'sync' })

useHead({ title: 'Кабинет', noindex: true })

const section = computed(() => route.meta.section || '')
const birthOpen = computed(() => route.name === 'cabinet-birth')

/** The wheel stands on the sky while the chart is open; its points choose the panel's reading. */
const selected = computed(() => (typeof route.params.item === 'string' ? route.params.item : ''))
watch(section, (id) => {
  if (id === 'chart' || id === 'forecast') loadChart()
}, { immediate: true })
/** In the forecast the same wheel carries the sky of the day or the week around it. */
const showWheel = computed(() => Boolean(user.value && chart.value && (section.value === 'chart' || section.value === 'forecast')))
const transitSky = computed((previous) => {
  if (section.value !== 'forecast') return null
  // While the other period loads, the wheel keeps the sky it has instead of blinking bare.
  return forecasts[route.query.period === 'week' ? 'week' : 'day'].data || previous || null
})
/** In «Пара» the partners' stars follow the panel: the one typed in, the open pair or all of them. */
watch(section, (id) => {
  if (id === 'pair') loadPartners()
}, { immediate: true })
const pairStars = computed(() => {
  const query = route.query
  if (query.add !== undefined || query.invite !== undefined) {
    if (!draft.name) return []
    return [{ id: 'draft', name: draft.name, date: draft.date, time: draft.time, lit: Boolean(draft.date) }]
  }
  const star = (item) => ({
    id: item.id,
    name: item.name,
    date: item.birth?.date || '',
    time: item.birth?.time || '',
    lit: Boolean(item.birth),
    hot: hot.value === item.id,
    flash: lit.value.has(item.id),
  })
  // An open pair keeps the others on the sky, stepped back, so another star can be pressed instead.
  const open = Number(query.partner) || 0
  return partners.value.map((item) => ({ ...star(item), open: item.id === open }))
})
const pairTone = computed(() => syntheses[Number(route.query.partner)]?.data?.tone || '')
/** A partner's star pressed on the sky opens its pair, as its row in the panel does. */
function openPair(id) {
  router.push({ name: 'cabinet-pair', query: { partner: id } })
}
function hoverPair(id) {
  hot.value = id
}
function selectPoint(id) {
  router.push({ name: 'cabinet-chart', params: id && id !== selected.value ? { item: id } : {} })
}
const kicker = computed(() => {
  if (section.value) return SECTION_BY_ID[section.value].label
  if (route.name === 'cabinet-profile') return 'Профиль'
  return birthOpen.value ? 'Данные рождения' : 'Кабинет'
})

/** next / prev slide the panel along the order of the sections, swap just fades it. */
const motion = ref('swap')
onBeforeRouteUpdate((to, from) => {
  const a = ROUTE_ORDER.indexOf(from.name)
  const b = ROUTE_ORDER.indexOf(to.name)
  motion.value = a < 0 || b < 0 ? 'swap' : b > a ? 'next' : 'prev'
  // The form may have left a sign it was trying on: put the saved one back.
  if (from.name === 'cabinet-birth' && user.value) markUser(user.value)
})

onMounted(async () => {
  try {
    user.value = await webApi.me()
    markUser(user.value)
    if (pendingInvite()) await joinPending()
  } catch (error) {
    if (error instanceof ApiError && (error.status === 401 || error.code === 'blocked')) {
      clearSession('web')
      router.push({ name: 'login' })
      return
    }
    message.value = errorText(error)
  }
})

onUnmounted(() => {
  clearMark()
  clearTimeout(tourTimer)
  stopTour()
})

/**
 * The introductions offer themselves once: the cabinet's, as soon as the birth date has drawn the
 * star (an invited partner's opens with the pair); «Небосвод»'s, once it is lit — after the dome
 * has had its moment. Never over the birth form, never over another tour.
 */
let tourTimer = 0
function offerTour() {
  clearTimeout(tourTimer)
  const current = user.value
  if (!current?.birth || tour.kind) return
  const kind = !tourSeen(current.id, 'intro') ? 'intro' : current.sky && !tourSeen(current.id, 'sky') ? 'sky' : ''
  if (!kind) return
  tourTimer = setTimeout(() => {
    if (tour.kind || route.name === 'cabinet-birth' || !user.value?.birth) return
    startTour(kind, { pair: kind === 'intro' && route.query.joined !== undefined })
  }, kind === 'sky' ? 2600 : 1800)
}
watch(() => [user.value?.id, Boolean(user.value?.birth), Boolean(user.value?.sky)], offerTour)
// Leaving the birth form for the overview is the moment the star is drawn.
watch(() => route.name, (name, from) => {
  if (from === 'cabinet-birth') offerTour()
})

/**
 * An invitation answered on this device before the cabinet was opened (or signed in to):
 * its pair joins this cabinet now, with the birth data given in the answer if the cabinet had none.
 */
async function joinPending() {
  try {
    const joined = await linkPendingInvite()
    if (!joined) return
    user.value = await webApi.me()
    markUser(user.value)
    forgetChart()
    forgetForecast()
    await loadPartners(true)
    router.replace({ name: 'cabinet-pair', query: { partner: joined.partner, joined: 1 } })
  } catch (error) {
    // The invitation was taken by another cabinet or withdrawn: the cabinet opens as it is.
    if (!(error instanceof ApiError)) throw error
  }
}

/** Back from the birth form: the way it came if it came from the overview, else to it. */
function leaveBirth() {
  if (window.history.state?.back === '/cabinet') router.back()
  else router.replace({ name: 'cabinet' })
}

function onSaved(next) {
  user.value = next
  forgetChart()
  forgetForecast()
  forgetSyntheses()
  forgetChat()
  markUser(next)
  mark.flash += 1
  leaveBirth()
}

/** The name or the email changed in the profile: nothing about the sky depends on them but the star's name. */
function onUpdated(next) {
  user.value = next
  markUser(next)
}

function logout() {
  clearSession('web')
  router.push('/')
}

/** After a change of panel the keyboard goes on from its title, not from the top of the page. */
const panel = ref(null)
function focusTitle() {
  const active = document.activeElement
  if (active && active !== document.body && !panel.value?.contains(active) && !active.closest?.('.cabinet-sky')) return
  panel.value?.querySelector('.panel-title, h2')?.focus({ preventScroll: true })
}

/* ---- The section's own «?»: a short walk through the open section (CabinetTour) ---- */

const sectionHelp = computed(() => (section.value && user.value ? SECTION_BY_ID[section.value]?.label || '' : ''))
async function openSectionTour() {
  if (route.params.item) {
    // One point of the chart is open: the walk goes through the whole chart.
    await router.push({ name: 'cabinet-chart' }).catch(() => {})
    await new Promise((resolve) => setTimeout(resolve, 600))
  }
  startTour('section')
}

/* ---- The phone sheet ---- */

const raised = ref(false)
const forcedUp = computed(() => Boolean(route.meta.full))
const up = computed(() => raised.value || forcedUp.value)
/** The height while a finger holds the handle, in px; null lets the CSS decide. */
const dragHeight = ref(null)
let drag = null

function sheetBounds() {
  const V = window.innerHeight
  return { low: V * 0.58, high: V - 72 }
}

function onHandleDown(event) {
  if (forcedUp.value) return
  const { low, high } = sheetBounds()
  drag = { y: event.clientY, from: up.value ? high : low, moved: false }
  event.currentTarget.setPointerCapture(event.pointerId)
}
function onHandleMove(event) {
  if (!drag) return
  const dy = drag.y - event.clientY
  if (Math.abs(dy) > 6) drag.moved = true
  if (!drag.moved) return
  const { low, high } = sheetBounds()
  dragHeight.value = Math.min(high + 12, Math.max(low - 60, drag.from + dy))
}
function onHandleUp() {
  if (!drag) return
  if (!drag.moved) raised.value = !raised.value
  else {
    const { low, high } = sheetBounds()
    raised.value = dragHeight.value > (low + high) / 2
  }
  drag = null
  dragHeight.value = null
}

/** A sideways swipe on the sheet moves to the neighbouring section. */
let touch = null
function onTouchStart(event) {
  const target = event.target
  if (event.touches.length !== 1 || target.closest('input, textarea, select, [data-no-swipe]')) {
    touch = null
    return
  }
  touch = { x: event.touches[0].clientX, y: event.touches[0].clientY }
}
function onTouchEnd(event) {
  if (!touch) return
  const dx = event.changedTouches[0].clientX - touch.x
  const dy = event.changedTouches[0].clientY - touch.y
  touch = null
  if (Math.abs(dx) < 60 || Math.abs(dx) < Math.abs(dy) * 2) return
  const index = ROUTE_ORDER.indexOf(route.name)
  if (index < 0) return
  const next = ROUTE_ORDER[index + (dx < 0 ? 1 : -1)]
  if (next) router.push({ name: next })
}

/** A field in the lowered sheet raises it: the keyboard would leave too little of it above. */
const PHONE = '(max-width: 760px)'
function onFocusIn(event) {
  if (up.value || !window.matchMedia(PHONE).matches) return
  if (event.target.matches('input:not([type=checkbox]):not([type=radio]), textarea, select')) raised.value = true
}

/**
 * The raised sheet and the keyboard on iPhone: Safari does not shrink the page under the keyboard
 * (Chrome does, see interactive-widget in index.html), so the sheet is fitted to what stays visible.
 */
const keyboard = ref(null)
function fitKeyboard() {
  const view = window.visualViewport
  const hidden = view ? window.innerHeight - view.height : 0
  keyboard.value = up.value && hidden > 120 && window.matchMedia(PHONE).matches
    ? { bottom: window.innerHeight - view.offsetTop - view.height, height: view.height - 8 }
    : null
}
watch(up, fitKeyboard)
onMounted(() => {
  window.visualViewport?.addEventListener('resize', fitKeyboard)
  window.visualViewport?.addEventListener('scroll', fitKeyboard)
})
onUnmounted(() => {
  window.visualViewport?.removeEventListener('resize', fitKeyboard)
  window.visualViewport?.removeEventListener('scroll', fitKeyboard)
})

// A new section starts with the sheet where the person left it, scrolled to its top.
watch(() => [route.name, route.params.item], () => {
  nextTick(() => panel.value?.querySelector('.panel-scroll')?.scrollTo({ top: 0 }))
})

const sheetStyle = computed(() => {
  if (dragHeight.value != null) return { height: `${dragHeight.value}px`, transition: 'none' }
  if (keyboard.value) return { bottom: `${keyboard.value.bottom}px`, height: `${keyboard.value.height}px`, transition: 'none' }
  return null
})
</script>

<template>
  <div class="site">
    <SiteHeader />
    <Transition name="wheel">
      <PairSky v-if="user && section === 'pair'" :stars="pairStars" :tone="pairTone" :aspect="hotAspect" @select="openPair" @hover="hoverPair" />
    </Transition>
    <Transition name="wheel">
      <SkyDome v-if="user && section === 'sky'" :lit="user.sky" />
    </Transition>
    <Transition name="wheel">
      <NatalWheel v-if="showWheel" :key="section" :chart="chart" :selected="selected" :forecast="transitSky" @select="selectPoint" />
    </Transition>
    <CabinetSky v-if="user" :section="section" :birth-open="birthOpen" :lit="Boolean(user.sky)" :flare="tour.flare" />
    <CabinetTour v-if="user" :user="user" />

    <main class="cabinet">
      <section
        ref="panel"
        class="cabinet-panel"
        :class="{ 'is-up': up, 'is-full': forcedUp }"
        :style="sheetStyle"
        aria-live="polite"
        @touchstart.passive="onTouchStart"
        @touchend="onTouchEnd"
        @focusin="onFocusIn"
      >
        <span class="card-sheen" aria-hidden="true" />
        <button
          v-if="!forcedUp"
          type="button"
          class="sheet-handle"
          :aria-expanded="up ? 'true' : 'false'"
          :aria-label="up ? 'Опустить панель' : 'Поднять панель'"
          @pointerdown="onHandleDown"
          @pointermove="onHandleMove"
          @pointerup="onHandleUp"
          @pointercancel="onHandleUp"
          @keydown.enter.prevent="raised = !raised"
          @keydown.space.prevent="raised = !raised"
        />

        <div class="panel-top">
          <p class="kicker">{{ kicker }}</p>
          <button
            v-if="sectionHelp"
            type="button"
            class="section-help"
            :class="{ 'is-on': tour.kind === 'section' }"
            :aria-label="`Как устроен раздел «${sectionHelp}»`"
            :title="`Как устроен раздел «${sectionHelp}»`"
            @click="openSectionTour"
          >?</button>
          <RouterLink v-if="route.name !== 'cabinet'" class="close" :to="{ name: 'cabinet' }" aria-label="Закрыть и вернуться к обзору">
            <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3 3L13 13M13 3L3 13" /></svg>
          </RouterLink>
          <RouterLink v-else-if="user" class="close gear" :to="{ name: 'cabinet-profile' }" aria-label="Профиль и настройки" title="Профиль и настройки">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M10.3 2.5h3.4l.5 2.6 1.7.9 2.5-.9 1.7 2.9-2 1.7v2l2 1.7-1.7 2.9-2.5-.9-1.7.9-.5 2.6h-3.4l-.5-2.6-1.7-.9-2.5.9-1.7-2.9 2-1.7v-2l-2-1.7 1.7-2.9 2.5.9 1.7-.9z" />
              <circle cx="12" cy="12" r="3.2" />
            </svg>
          </RouterLink>
        </div>

        <div class="panel-scroll">
          <p v-if="message" class="error">{{ message }}</p>
          <RouterView v-else-if="user" v-slot="{ Component, route: current }">
            <Transition :name="motion" mode="out-in" @after-enter="focusTitle">
              <component :is="Component" :key="current.name" :user="user" @saved="onSaved" @updated="onUpdated" @done="leaveBirth" @logout="logout" />
            </Transition>
          </RouterView>
          <p v-else class="loading">Открываем ваше небо…</p>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
.wheel-enter-active, .wheel-leave-active { transition: opacity 0.6s ease; }
.wheel-enter-from, .wheel-leave-to { opacity: 0; }

.cabinet {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  min-height: 100vh;
  min-height: 100svh;
  padding: 110px clamp(20px, 8vw, 150px) 40px;
  pointer-events: none;
}

/* The login card's glass, wider: it waits for the flight to land before it rises. */
.cabinet-panel {
  position: relative;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 14px;
  /* One width for the overview and the sections (layout.js, panelWidth): read, not glanced at. */
  width: min(clamp(420px, 36vw, 500px), 100%);
  max-height: calc(100vh - 150px);
  overflow: hidden;
  padding: 24px 26px;
  border-radius: 22px;
  border: 1px solid rgba(240, 210, 150, 0.22);
  background:
    radial-gradient(120% 70% at 0% 0%, rgba(255, 196, 120, 0.1), transparent 60%),
    linear-gradient(160deg, rgba(26, 23, 26, 0.62), rgba(8, 10, 18, 0.74));
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 240, 210, 0.08);
  backdrop-filter: blur(14px) saturate(1.2);
  -webkit-backdrop-filter: blur(14px) saturate(1.2);
  color: #efe7d8;
  pointer-events: auto;
  animation: card-in 0.9s cubic-bezier(0.3, 0.7, 0.2, 1) 0.9s both;
}
.cabinet-panel.is-full { height: calc(100vh - 150px); }
.cabinet-panel::before {
  content: '';
  position: absolute;
  inset: 6px;
  border: 1px solid rgba(240, 210, 150, 0.08);
  border-radius: 17px;
  pointer-events: none;
}
.card-sheen {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: linear-gradient(115deg, transparent 35%, rgba(255, 236, 200, 0.08) 50%, transparent 65%);
  transform: translateX(-100%);
  animation: card-sheen 1.8s ease 1.5s forwards;
}

.panel-top { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 28px; }
.kicker { margin: 0; font-size: 10px; letter-spacing: 0.26em; text-transform: uppercase; color: rgba(233, 194, 124, 0.75); }
.section-help {
  position: relative;
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  margin-left: auto;
  padding: 0;
  border-radius: 50%;
  border: 1px solid rgba(240, 205, 138, 0.42);
  background: rgba(240, 205, 138, 0.05);
  font-family: var(--serif);
  font-size: 14px;
  line-height: 1;
  color: #f3dcae;
  cursor: pointer;
  transition: border-color 0.25s ease, background 0.25s ease, box-shadow 0.25s ease;
}
.section-help:hover, .section-help.is-on { border-color: #f0cd8a; background: rgba(240, 205, 138, 0.16); box-shadow: 0 0 14px rgba(255, 200, 110, 0.4); }
.section-help:focus-visible { outline: 2px solid #ffe2a8; outline-offset: 3px; }
/* A finger's target, larger than the circle. */
.section-help::after { content: ''; position: absolute; inset: -10px; border-radius: 50%; }
.close {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  margin: -4px -8px -4px 0;
  border-radius: 50%;
  color: rgba(242, 228, 200, 0.7);
  transition: color 0.25s ease, background 0.25s ease;
}
.close svg { width: 12px; height: 12px; stroke: currentColor; stroke-width: 1.4; stroke-linecap: round; fill: none; }
.close:hover { color: #f0cd8a; background: rgba(240, 205, 138, 0.08); }
.close:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 1px; }
/* On the overview the corner holds the way to the profile instead: an engraved gear. */
.gear { color: rgba(240, 205, 138, 0.6); }
.gear svg { width: 18px; height: 18px; stroke-width: 1.3; stroke-linejoin: round; transition: transform 0.6s ease; }
.gear:hover svg { transform: rotate(60deg); }

/* Reaches into the card's padding, so the glow of buttons at its edges is not cut square. */
.panel-scroll {
  min-height: 0;
  margin: 0 -20px -20px;
  padding: 0 20px 22px;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-width: thin;
  scrollbar-color: rgba(240, 205, 138, 0.25) transparent;
}

.sheet-handle { display: none; }

.error { margin: 0; font-size: 14px; color: #f2a48c; }
.loading { margin: 0; font-family: var(--serif); font-style: italic; font-size: 17px; color: rgba(242, 228, 200, 0.75); }

/* Panels change: along the order of the sections, or in place. */
.next-enter-active, .next-leave-active, .prev-enter-active, .prev-leave-active, .swap-enter-active, .swap-leave-active {
  transition: opacity 0.28s ease, transform 0.28s cubic-bezier(0.3, 0.7, 0.2, 1);
}
.next-enter-from, .prev-leave-to { opacity: 0; transform: translateX(18px); }
.next-leave-to, .prev-enter-from { opacity: 0; transform: translateX(-18px); }
.swap-enter-from { opacity: 0; transform: translateY(6px); }
.swap-leave-to { opacity: 0; transform: translateY(-6px); }

@keyframes card-in { from { opacity: 0; transform: translateY(16px); filter: blur(4px); } }
@keyframes card-sheen { to { transform: translateX(100%); } }

@media (max-width: 760px) {
  /* A sheet from the bottom, under the strip of sky with the star and the five sections. */
  .cabinet { display: block; min-height: 0; padding: 0; }
  .cabinet-panel {
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    width: auto;
    height: 58vh;
    height: 58svh;
    max-height: none;
    padding: 26px 18px calc(16px + env(safe-area-inset-bottom));
    border-radius: 22px 22px 0 0;
    border-bottom: 0;
    transition: height 0.45s cubic-bezier(0.3, 0.7, 0.2, 1);
    animation-name: sheet-in;
  }
  .cabinet-panel.is-up { height: calc(100vh - 72px); height: calc(100svh - 72px); }
  .panel-scroll { margin: 0 -14px -14px; padding: 0 14px 16px; }
  .cabinet-panel::before { inset: 6px 6px 0; border-bottom: 0; border-radius: 17px 17px 0 0; }
  .sheet-handle {
    display: block;
    position: absolute;
    top: 0;
    left: 50%;
    width: 120px;
    height: 36px;
    margin-left: -60px;
    padding: 0;
    border: 0;
    background: none;
    cursor: grab;
    touch-action: none;
  }
  .sheet-handle::after {
    content: '';
    position: absolute;
    top: 10px;
    left: 42px;
    right: 42px;
    height: 4px;
    border-radius: 2px;
    background: rgba(240, 210, 150, 0.35);
    transition: background 0.25s ease;
  }
  .sheet-handle:hover::after, .sheet-handle:focus-visible::after { background: rgba(240, 205, 138, 0.75); }
  .sheet-handle:focus-visible { outline: none; }
  .close { width: 44px; height: 44px; margin: -10px -12px -10px 0; }
}

@keyframes sheet-in { from { transform: translateY(40px); opacity: 0; } }

@media (prefers-reduced-motion: reduce) {
  .cabinet-panel { animation: card-fade 0.4s ease both; transition: none; }
  .card-sheen { animation: none; }
  .next-enter-from, .next-leave-to, .prev-enter-from, .prev-leave-to, .swap-enter-from, .swap-leave-to { transform: none; }
  .gear svg { transition: none; }
  .gear:hover svg { transform: none; }
}
@keyframes card-fade { from { opacity: 0; } }
</style>
