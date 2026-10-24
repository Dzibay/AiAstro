<script setup>
import { computed, inject, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ActivityCalendar from '../../components/admin/ActivityCalendar.vue'
import ConfirmDialog from '../../components/admin/ConfirmDialog.vue'
import UserChat from '../../components/admin/ai/UserChat.vue'
import { adminApi } from '../../api/admin.js'
import { useToast } from '../../composables/useToast.js'
import { PAYMENT_STATUS, PRODUCTS, eventText, failed, fmt, moscowDay, offerName, pageName, plural, seen, tourName } from './shared.js'
import { DEVICE_NAMES, WAY } from './way.js'

const route = useRoute()
const router = useRouter()
const { push } = useToast()
const list = inject('adminUsers', { update() {}, remove() {} })

const user = ref(null)
const partners = ref([])
const payments = ref([])
const error = ref('')
const busy = ref('')

async function load() {
  const id = route.params.id
  error.value = ''
  user.value = null
  try {
    const [one, pairs, paid] = await Promise.all([adminApi.user(id), adminApi.partners(id), adminApi.payments({ user: id })])
    if (id !== route.params.id) return
    user.value = one
    partners.value = pairs.items
    payments.value = paid.items
    skyDate.value = moscowDay(one.sky ? one.sky_until : Date.now() + 30 * 864e5)
  } catch (caught) {
    error.value = failed(caught)
  }
}
watch(() => route.params.id, (id) => id && load())
onMounted(load)

/* ---- The way at a glance: where the person came from, how far they went, what they did and did not ---- */

const journey = ref(null)
const journeyError = ref('')

async function loadJourney() {
  const id = route.params.id
  journey.value = null
  journeyError.value = ''
  try {
    const answer = await adminApi.journey(id)
    if (id === route.params.id) journey.value = answer
  } catch (caught) {
    journeyError.value = failed(caught)
  }
}
watch(() => route.params.id, (id) => id && loadJourney())
onMounted(loadJourney)

const times = (n) => `${n} ${plural(n, 'раз', 'раза', 'раз')}`
// The cabinet's actions, then the way to a purchase; extra — what the count or the note adds.
const ACTIONS = {
  birth: { label: 'Указал дату рождения' },
  intro: { label: 'Прошёл знакомство', part: 'Закрыл знакомство, не досмотрев' },
  chart: { label: 'Открыл карту' },
  game: { label: 'Собрал карту в игре', part: 'Начал игру, не закончил', extra: (n) => (n > 1 ? times(n) : '') },
  forecast: { label: 'Открыл прогноз', extra: (n) => (n > 1 ? times(n) : '') },
  pair: { label: 'Добавил пару', extra: (n) => `${n} ${plural(n, 'пара', 'пары', 'пар')}` },
  chat: { label: 'Спросил ИИ-астролога', extra: (n) => `${n} ${plural(n, 'вопрос', 'вопроса', 'вопросов')}` },
  sky_view: { label: 'Открыл «Небосвод»', money: true },
  offer: { label: 'Видел предложение', money: true, extra: (n) => `в ${n} ${plural(n, 'месте', 'местах', 'местах')}` },
  pick: { label: 'Выбрал срок', money: true },
  sky_paid: { label: 'Купил «Небосвод»', money: true, extra: (n) => (n > 1 ? times(n) : '') },
  pair_paid: { label: 'Купил разбор пары', money: true, extra: (n) => (n > 1 ? times(n) : '') },
}

const way = computed(() => {
  const j = journey.value
  if (!j) return null
  const steps = WAY.map((step, index) => {
    const mark = j.steps.find((s) => s.key === step.key) || { done: false, at: null }
    return { key: step.key, label: step.one, done: mark.done, at: mark.at, index }
  })
  const reached = steps.filter((s) => s.done).length
  const next = steps.find((s) => !s.done)
  if (next) next.next = true
  const actions = j.actions.map((a) => {
    const meta = ACTIONS[a.key] || { label: a.key }
    const part = Boolean(meta.part) && Boolean(a.note)
    return {
      key: a.key,
      money: Boolean(meta.money),
      state: part ? 'part' : a.done ? 'done' : 'no',
      label: part ? meta.part : meta.label,
      at: a.at,
      extra: a.done && a.count && meta.extra ? meta.extra(a.count) : '',
    }
  })
  const f = j.first
  return {
    steps,
    reached,
    next,
    unmarked: steps.some((s) => s.done && !s.at),
    cabinet: actions.filter((a) => !a.money),
    money: actions.filter((a) => a.money),
    cabinetDone: actions.filter((a) => !a.money && a.state === 'done').length,
    moneyDone: actions.filter((a) => a.money && a.state === 'done').length,
    source: !f ? '' : f.link ? `Ссылка «${f.link}»` : f.source || 'Прямой заход',
    landing: f?.landing ? pageName(f.landing) : '',
    device: f?.device ? DEVICE_NAMES[f.device] || f.device : '',
    firstAt: f?.at || null,
    tours: j.tours.map(tourName),
  }
})

/* ---- What the person did on the site, newest first ---- */

// Scroll marks, time on a page and visit starts crowd the list: shown only in the detailed view.
const QUIET = ['scroll', 'time', 'visit']
const PORTION = 25
const timeline = reactive({ items: [], more: false, loading: false, detailed: false, shown: PORTION, error: '' })
const timelineRows = computed(() => (timeline.detailed ? timeline.items : timeline.items.filter((item) => !QUIET.includes(item.kind))))
const timelineShown = computed(() => timelineRows.value.slice(0, timeline.shown))
const timelineMore = computed(() => timelineRows.value.length > timeline.shown || timeline.more)

async function loadEvents(before = '') {
  const id = route.params.id
  timeline.loading = true
  timeline.error = ''
  try {
    const answer = await adminApi.events(id, before)
    if (id !== route.params.id) return
    timeline.items = before ? [...timeline.items, ...answer.items] : answer.items
    timeline.more = answer.more
  } catch (caught) {
    timeline.error = failed(caught)
  } finally {
    timeline.loading = false
  }
}
function resetEvents() {
  Object.assign(timeline, { items: [], more: false, shown: PORTION, error: '' })
  loadEvents()
}
watch(() => route.params.id, (id) => id && resetEvents())
onMounted(resetEvents)

async function showMore() {
  timeline.shown += PORTION
  // Past what is loaded, the next portion comes from the server.
  if (timelineRows.value.length < timeline.shown && timeline.more) await loadEvents(timeline.items.at(-1).at)
}
/** Where it happened, when the line itself does not say. */
function where(item) {
  if (item.kind === 'payment') return item.page ? offerName(item.page) : ''
  if (['view', 'visit', 'scroll', 'time', 'goal', 'signup', 'confirm', 'birth', 'ref'].includes(item.kind) || !item.page) return ''
  return pageName(item.page)
}

function close() {
  router.push({ name: 'admin-users' })
}
function onKey(event) {
  if (event.key === 'Escape' && !ask.open) close()
}
onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))

async function act(key, run) {
  busy.value = key
  error.value = ''
  try {
    return await run()
  } catch (caught) {
    error.value = failed(caught)
    return undefined
  } finally {
    busy.value = ''
  }
}

/* ---- «Небосвод» ---- */

const skyDate = ref('')
const today = computed(() => moscowDay())
const skyEnded = computed(() => user.value?.sky_until && !user.value.sky)

function applied(saved, text) {
  user.value = saved
  list.update(saved)
  skyDate.value = moscowDay(saved.sky ? saved.sky_until : Date.now() + 30 * 864e5)
  push(text)
}
async function extend(days) {
  const saved = await act(`sky${days}`, () => adminApi.setSky(user.value.id, { days }))
  if (saved) applied(saved, `«Небосвод» продлён на ${days} дн.: до ${fmt.long(saved.sky_until)}`)
}
async function setUntil() {
  const saved = await act('skyDate', () => adminApi.setSky(user.value.id, { until: skyDate.value }))
  if (saved) applied(saved, saved.sky ? `«Небосвод» до ${fmt.long(saved.sky_until)}` : '«Небосвод» закрыт')
}

/* ---- The email: confirmed by hand when the letter went astray ---- */

async function confirmEmail() {
  const saved = await act('email', () => adminApi.confirmUser(user.value.id))
  if (!saved) return
  user.value = saved
  list.update(saved)
  push(`Почта подтверждена: ${saved.email}`)
}

/* ---- Confirmations: closing «Небосвод», taking a reading back, deleting ---- */

const ask = reactive({ open: false, title: '', text: '', label: '', need: '', error: '', run: null })
function confirm(options) {
  Object.assign(ask, { open: true, error: '', need: '', ...options })
}
async function confirmed(typed) {
  ask.error = ''
  busy.value = 'confirm'
  try {
    await ask.run(typed)
    ask.open = false
  } catch (caught) {
    ask.error = failed(caught)
  } finally {
    busy.value = ''
  }
}

function closeSky() {
  confirm({
    title: 'Снять «Небосвод»?',
    text: `У ${user.value.email} сразу закроются прогнозы и ИИ-астролог. Деньги этим не возвращаются — возврат делается в ЮKassa.`,
    label: 'Снять',
    run: async () => {
      const saved = await adminApi.setSky(user.value.id, { days: 0 })
      applied(saved, '«Небосвод» снят')
    },
  })
}

/* ---- Pairs ---- */

const KIND = { linked: 'свой кабинет', invite: 'по приглашению', manual: 'введён вручную' }
const BY = { me: 'оплатил(а) сам(а)', partner: 'оплатил партнёр', gift: 'подарок' }

async function giveReading(partner) {
  const saved = await act(`pair${partner.id}`, () => adminApi.setBought(user.value.id, partner.id, true))
  if (saved) {
    Object.assign(partner, saved)
    push(`Разбор пары открыт: ${partner.name}${partner.kind === 'linked' ? ' — у обоих, письма ушли' : ''}`)
  }
}
function takeReading(partner) {
  confirm({
    title: 'Забрать разбор пары?',
    text: `Разбор пары с «${partner.name}» закроется${partner.kind === 'linked' ? ' у обоих партнёров' : ''}. Деньги этим не возвращаются.`,
    label: 'Забрать',
    run: async () => {
      const saved = await adminApi.setBought(user.value.id, partner.id, false)
      Object.assign(partner, saved)
      push(`Разбор пары закрыт: ${partner.name}`)
    },
  })
}
function toggleReading(partner) {
  if (partner.bought) takeReading(partner)
  else giveReading(partner)
}

/* ---- Birth data, past the person's own correction ---- */

const birth = reactive({ open: false, date: '', time: '' })
function editBirth() {
  Object.assign(birth, { open: !birth.open, date: user.value.birth?.date || '', time: user.value.birth?.time || '' })
}
async function saveBirth() {
  const old = user.value.birth || {}
  const saved = await act('birth', () =>
    adminApi.setBirth(user.value.id, { date: birth.date, time: birth.time || null, place: old.place || null, lat: old.lat ?? null, lon: old.lon ?? null }),
  )
  if (saved) {
    user.value = { ...user.value, ...saved }
    list.update(user.value)
    birth.open = false
    push('Данные рождения исправлены')
  }
}

/* ---- Deleting ---- */

function remove() {
  confirm({
    title: 'Удалить аккаунт навсегда?',
    text: 'Удалятся кабинет, пары этого человека и переписка с ИИ-астрологом. Платежи останутся в учёте; пары, общие с партнёрами, останутся у партнёров, им уйдёт письмо. Отменить нельзя.',
    label: 'Удалить навсегда',
    need: user.value.email,
    run: async (typed) => {
      await adminApi.deleteUser(user.value.id, typed)
      list.remove(user.value.id)
      push(`Аккаунт удалён: ${user.value.email}`)
      close()
    },
  })
}
</script>

<template>
  <div class="up-shade" @click="close" />
  <aside class="up" role="dialog" aria-modal="false" :aria-label="user ? `Карточка ${user.email}` : 'Карточка пользователя'">
    <header class="up-head">
      <div v-if="user" class="adm-who">
        <strong class="up-email">{{ user.email }}</strong>
        <span>{{ user.name || 'без имени' }} · № {{ user.id }} · с {{ fmt.day(user.created_at) }} · {{ seen(user.last_seen) }}</span>
      </div>
      <span v-else class="adm-dim">Загружаем…</span>
      <button type="button" class="adm-btn up-close" aria-label="Закрыть карточку" @click="close">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" /></svg>
      </button>
    </header>

    <p v-if="error" class="error up-error">{{ error }}</p>

    <div v-if="user" class="up-body">
      <section class="up-block">
        <div class="up-block-head">
          <h2>Путь</h2>
          <span v-if="way" class="adm-dim">{{ way.reached }} из {{ way.steps.length }} шагов</span>
        </div>
        <p v-if="journeyError" class="error">{{ journeyError }}</p>
        <p v-else-if="!way" class="up-empty">Загружаем…</p>
        <template v-else>
          <dl class="up-from">
            <div>
              <dt>Пришёл</dt>
              <dd>{{ way.source || 'неизвестно' }}<span v-if="way.firstAt" class="adm-dim"> · {{ fmt.day(way.firstAt) }}</span></dd>
            </div>
            <div v-if="way.landing || way.device">
              <dt>Вход</dt>
              <dd>{{ [way.landing, way.device].filter(Boolean).join(' · ') }}</dd>
            </div>
            <div>
              <dt>Визитов</dt>
              <dd>{{ fmt.count(journey.visits) }}<span class="adm-dim"> · последний {{ seen(journey.last_at || user.last_seen) }}</span></dd>
            </div>
            <div>
              <dt>Выручка</dt>
              <dd>
                <strong v-if="journey.revenue">{{ fmt.rub(journey.revenue) }}</strong>
                <span v-else class="adm-dim">0 ₽</span>
                <span v-if="journey.unfinished" class="adm-badge is-warn up-unpaid">{{ journey.unfinished }} {{ plural(journey.unfinished, 'оплата не завершена', 'оплаты не завершены', 'оплат не завершено') }}</span>
              </dd>
            </div>
          </dl>

          <ol class="up-way" :aria-label="`Путь: пройдено ${way.reached} из ${way.steps.length} шагов`">
            <li v-for="step in way.steps" :key="step.key" :class="{ 'is-done': step.done, 'is-next': step.next }">
              <i class="up-way-dot" aria-hidden="true">
                <svg v-if="step.done" viewBox="0 0 12 12"><path d="M2.5 6.2 5 8.6l4.6-5" /></svg>
              </i>
              <span class="up-way-name">{{ step.label }}</span>
              <span v-if="step.done" class="up-way-at" :class="{ 'adm-dim': !step.at }">{{ step.at ? fmt.moment(step.at) : 'без отметки' }}</span>
              <span v-else-if="step.next" class="up-way-at up-way-stop">не дошёл</span>
              <span v-else class="up-way-at" />
            </li>
          </ol>
          <p v-if="way.unmarked" class="up-note">«Без отметки» — шаг не записан, но следующий за ним сделан.</p>

          <div class="up-acts-head">
            <h3>В кабинете</h3>
            <span class="adm-dim">{{ way.cabinetDone }} из {{ way.cabinet.length }}</span>
          </div>
          <ul class="up-acts">
            <li v-for="a in way.cabinet" :key="a.key" :class="`is-${a.state}`">
              <i class="up-act-mark" aria-hidden="true">
                <svg v-if="a.state === 'done'" viewBox="0 0 12 12"><path d="M2.5 6.2 5 8.6l4.6-5" /></svg>
                <svg v-else-if="a.state === 'part'" viewBox="0 0 12 12"><path d="M3 6h6" /></svg>
              </i>
              <span class="up-act-name">{{ a.label }}</span>
              <span class="up-act-sub">{{ a.state === 'no' ? 'нет' : [a.at ? fmt.moment(a.at) : '', a.extra].filter(Boolean).join(' · ') }}</span>
            </li>
          </ul>
          <div class="up-acts-head">
            <h3>К покупке</h3>
            <span class="adm-dim">{{ way.moneyDone }} из {{ way.money.length }}</span>
          </div>
          <ul class="up-acts">
            <li v-for="a in way.money" :key="a.key" :class="[`is-${a.state}`, 'is-money']">
              <i class="up-act-mark" aria-hidden="true">
                <svg v-if="a.state === 'done'" viewBox="0 0 12 12"><path d="M2.5 6.2 5 8.6l4.6-5" /></svg>
              </i>
              <span class="up-act-name">{{ a.label }}</span>
              <span class="up-act-sub">{{ a.state === 'no' ? 'нет' : [a.at ? fmt.moment(a.at) : '', a.extra].filter(Boolean).join(' · ') }}</span>
            </li>
          </ul>
          <p v-if="way.tours.length" class="up-note">Подсказки досмотрены: {{ way.tours.join(', ') }}.</p>
        </template>
      </section>

      <section class="up-block">
        <div class="up-block-head">
          <h2>Активность</h2>
          <span class="adm-dim">московское время</span>
        </div>
        <ActivityCalendar :user-id="user.id" :last-seen="user.last_seen || ''" />
      </section>

      <UserChat :user-id="user.id" />

      <section class="up-block">
        <div class="up-block-head">
          <h2>Почта</h2>
          <span v-if="user.email_confirmed_at" class="adm-badge is-ok">подтверждена {{ fmt.day(user.email_confirmed_at) }}</span>
          <span v-else class="adm-badge is-warn">не подтверждена</span>
        </div>
        <template v-if="!user.email_confirmed_at">
          <p class="up-note">Кабинет откроется после подтверждения. Если письмо не дошло, а человек написал с этого адреса, подтвердите вручную.</p>
          <div class="adm-actions">
            <button type="button" class="adm-btn is-gold" :disabled="Boolean(busy)" @click="confirmEmail">Подтвердить почту</button>
          </div>
        </template>
      </section>

      <section class="up-block">
        <div class="up-block-head">
          <h2>«Небосвод»</h2>
          <span v-if="user.sky" class="adm-badge is-ok">до {{ fmt.long(user.sky_until) }}</span>
          <span v-else-if="skyEnded" class="adm-badge">закончился {{ fmt.day(user.sky_until) }}</span>
          <span v-else class="adm-badge">нет</span>
        </div>
        <p class="up-note">Продление считается от конца текущего срока. Оплаченное через ЮKassa открывается само.</p>
        <div class="adm-actions">
          <button v-for="d in [30, 90, 365]" :key="d" type="button" class="adm-btn" :disabled="Boolean(busy)" @click="extend(d)">+{{ d }} дн.</button>
          <button v-if="user.sky" type="button" class="adm-btn is-danger" :disabled="Boolean(busy)" @click="closeSky">Снять</button>
        </div>
        <form class="up-date" @submit.prevent="setUntil">
          <label class="adm-label">
            Действует до (включительно)
            <input v-model="skyDate" type="date" :min="today" required />
          </label>
          <button type="submit" class="adm-btn" :disabled="!skyDate || Boolean(busy)">Сохранить дату</button>
        </form>
      </section>

      <section class="up-block">
        <div class="up-block-head">
          <h2>Пары</h2>
          <span class="adm-dim">{{ partners.length }}</span>
        </div>
        <p class="up-note">Переключатель — платный разбор пары. У общей пары он откроется или закроется у обоих.</p>
        <ul v-if="partners.length" class="up-pairs">
          <li v-for="partner in partners" :key="partner.id">
            <div class="adm-who">
              <strong>{{ partner.name }}</strong>
              <span>
                {{ KIND[partner.kind] }} · {{ partner.birth ? `род. ${fmt.birth(partner.birth.date)}` : 'ждём данных' }}<template v-if="partner.left"> · партнёр удалил пару</template>
              </span>
              <span v-if="partner.bought" class="up-bought">разбор открыт {{ fmt.day(partner.bought_at) }} · {{ BY[partner.bought_by] || 'оплата' }}</span>
            </div>
            <button
              type="button"
              role="switch"
              class="adm-switch"
              :aria-checked="partner.bought"
              :aria-label="`Разбор пары с ${partner.name}`"
              :title="!partner.birth && !partner.bought ? 'Разбор откроется, когда будут данные партнёра' : ''"
              :disabled="Boolean(busy) || (!partner.birth && !partner.bought)"
              @click="toggleReading(partner)"
            />
          </li>
        </ul>
        <p v-else class="up-empty">Пар пока нет.</p>
      </section>

      <section class="up-block">
        <div class="up-block-head">
          <h2>Платежи</h2>
          <span class="adm-dim">оплачено {{ fmt.rub(user.paid) }}</span>
        </div>
        <ul v-if="payments.length" class="up-pays">
          <li v-for="p in payments" :key="p.id">
            <span class="adm-dim">{{ fmt.moment(p.paid_at || p.created_at) }}</span>
            <span class="up-pay-what">{{ PRODUCTS[p.product] || p.title }}</span>
            <strong class="num">{{ fmt.rub(p.amount) }}</strong>
            <span class="adm-badge" :class="{ 'is-ok': p.status === 'succeeded', 'is-bad': p.status === 'canceled' || p.status === 'failed', 'is-warn': p.status === 'pending' }">{{ PAYMENT_STATUS[p.status] || p.status }}</span>
          </li>
        </ul>
        <p v-else class="up-empty">Платежей не было.</p>
      </section>

      <section class="up-block">
        <div class="up-block-head">
          <h2>Данные рождения</h2>
          <span v-if="user.birth_locked" class="adm-badge is-warn">своя правка исчерпана</span>
        </div>
        <p v-if="user.birth" class="up-line">
          {{ fmt.birth(user.birth.date) }}<template v-if="user.birth.time">, {{ user.birth.time }}</template> · {{ user.birth.place || 'город не указан' }}
        </p>
        <p v-else class="up-line adm-dim">Не указаны.</p>
        <button v-if="!birth.open" type="button" class="adm-btn" @click="editBirth">Исправить</button>
        <form v-else class="up-date" @submit.prevent="saveBirth">
          <label class="adm-label">Дата<input v-model="birth.date" type="date" required /></label>
          <label class="adm-label">Время (пусто — неизвестно)<input v-model="birth.time" type="time" /></label>
          <div class="adm-actions">
            <button type="submit" class="adm-btn is-gold" :disabled="!birth.date || Boolean(busy)">Сохранить</button>
            <button type="button" class="adm-btn" @click="birth.open = false">Отмена</button>
          </div>
          <p class="up-note">Город остаётся прежним. Правка поддержки не тратит правку человека; пары без открытого разбора получат новые данные.</p>
        </form>
      </section>

      <section class="up-block">
        <div class="up-block-head">
          <h2>Действия на сайте</h2>
          <div class="adm-seg up-seg" role="group" aria-label="Сколько показывать">
            <button type="button" :aria-pressed="!timeline.detailed" @click="timeline.detailed = false">главное</button>
            <button type="button" :aria-pressed="timeline.detailed" @click="timeline.detailed = true">подробно</button>
          </div>
        </div>
        <p class="up-note">Всё по порядку, новые сверху, вместе с тем, что браузер делал до регистрации. Подробно — ещё прокрутка, время на странице и начала визитов.</p>
        <ul v-if="timelineShown.length" class="up-events">
          <li v-for="(item, index) in timelineShown" :key="`${item.at}:${item.kind}:${item.name}:${index}`" :class="{ 'is-pay': item.kind === 'payment' }">
            <span class="adm-dim">{{ fmt.moment(item.at) }}</span>
            <span>{{ eventText(item) }}<span v-if="where(item)" class="adm-dim"> · {{ where(item) }}</span></span>
          </li>
        </ul>
        <p v-else-if="timeline.loading" class="up-empty">Загружаем…</p>
        <p v-else-if="!timeline.error" class="up-empty">Действий пока нет.</p>
        <p v-if="timeline.error" class="error">{{ timeline.error }}</p>
        <button v-if="timelineShown.length && timelineMore" type="button" class="adm-btn" :disabled="timeline.loading" @click="showMore">Показать ещё</button>
      </section>

      <section class="up-block up-danger">
        <h2>Удаление</h2>
        <p class="up-note">Аккаунт удаляется навсегда, как при удалении из кабинета. Платежи остаются в учёте.</p>
        <button type="button" class="adm-btn is-danger" :disabled="Boolean(busy)" @click="remove">Удалить аккаунт…</button>
      </section>
    </div>

    <ConfirmDialog
      :open="ask.open"
      :title="ask.title"
      :text="ask.text"
      :label="ask.label"
      :need="ask.need"
      :busy="busy === 'confirm'"
      :error="ask.error"
      @confirm="confirmed"
      @cancel="ask.open = false"
    />
  </aside>
</template>

<style scoped>
.up-shade { position: fixed; inset: 0; z-index: 40; background: rgba(4, 6, 10, 0.45); animation: up-fade 0.2s ease; }
.up {
  position: fixed;
  z-index: 41;
  top: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  width: min(480px, 100%);
  border-left: 1px solid rgba(244, 239, 230, 0.12);
  background: #121a17;
  box-shadow: -30px 0 80px rgba(0, 0, 0, 0.4);
  animation: up-in 0.25s cubic-bezier(0.3, 0.7, 0.2, 1);
  font-size: 15px;
}
@keyframes up-in { from { translate: 40px 0; opacity: 0; } }
@keyframes up-fade { from { opacity: 0; } }
.up-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 20px;
  border-bottom: 1px solid rgba(244, 239, 230, 0.09);
}
.up-email { font-size: 17px; }
.up-close { flex: none; width: 38px; height: 38px; padding: 0; }
.up-close svg { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; }
.up-error { margin: 12px 20px 0; }
.up-body { flex: 1; overflow-y: auto; overscroll-behavior: contain; }
.up-block { display: grid; gap: 10px; padding: 18px 20px; border-bottom: 1px solid rgba(244, 239, 230, 0.07); }
.up-block h2 { margin: 0; font-family: var(--sans); font-size: 15px; font-weight: 600; letter-spacing: 0.02em; line-height: 1.3; text-transform: uppercase; color: var(--muted); }
.up-block-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.up-note { margin: 0; color: var(--soft); font-size: 13px; }
.up-line { margin: 0; }
.up-empty { margin: 0; color: var(--soft); }
.up-date { display: flex; flex-wrap: wrap; align-items: end; gap: 10px 12px; }
.up-pairs, .up-pays { display: grid; margin: 0; padding: 0; list-style: none; }
.up-pairs li { display: flex; align-items: center; justify-content: space-between; gap: 14px; padding: 10px 0; border-top: 1px solid rgba(244, 239, 230, 0.07); }
.up-pairs li:first-child, .up-pays li:first-child { border-top: 0; }
.up-bought { color: #9fd3a8 !important; }
.up-pays li { display: grid; grid-template-columns: 7.6em 1fr auto; align-items: center; gap: 2px 12px; padding: 8px 0; border-top: 1px solid rgba(244, 239, 230, 0.07); font-size: 14px; }
.up-pays .adm-badge { grid-column: 2 / -1; justify-self: start; }
.up-pay-what { min-width: 0; }
.up-seg button { padding: 4px 11px; font-size: 13px; }
.up-events { display: grid; margin: 0; padding: 0; list-style: none; font-size: 14px; }
.up-events li { display: grid; grid-template-columns: 7.6em 1fr; gap: 12px; padding: 6px 0; border-top: 1px solid rgba(244, 239, 230, 0.07); }
.up-events li:first-child { border-top: 0; }
.up-events li.is-pay { color: #9fd3a8; }
.num { font-variant-numeric: tabular-nums; }
.up-block > .adm-btn { justify-self: start; }
.up-danger { border-bottom: 0; }

/* The way */
.up-from { display: grid; gap: 6px; margin: 0; font-size: 14px; }
.up-from div { display: grid; grid-template-columns: 6.2em 1fr; gap: 12px; }
.up-from dt { color: var(--soft); }
.up-from dd { margin: 0; min-width: 0; overflow-wrap: anywhere; }
.up-unpaid { margin-left: 8px; }
.up-way { position: relative; display: grid; margin: 4px 0 0; padding: 0; list-style: none; font-size: 14px; }
.up-way li { position: relative; display: grid; grid-template-columns: 22px 1fr auto; align-items: center; gap: 10px; min-height: 30px; }
/* The line from a dot to the next: solid past the steps done, faint ahead. */
.up-way li:not(:last-child)::after {
  content: '';
  position: absolute;
  left: 10px;
  top: 21px;
  bottom: -9px;
  width: 2px;
  border-radius: 1px;
  background: rgba(244, 239, 230, 0.1);
}
.up-way li.is-done:not(:last-child)::after { background: var(--people); }
.up-way-dot {
  position: relative;
  z-index: 1;
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border: 2px solid rgba(244, 239, 230, 0.2);
  border-radius: 50%;
  background: #121a17;
}
.up-way-dot svg, .up-act-mark svg { width: 12px; height: 12px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
.is-done .up-way-dot { border-color: var(--people); background: var(--people); color: #0d1411; }
.is-next .up-way-dot { border-color: var(--danger); border-style: dashed; }
.up-way li:not(.is-done) .up-way-name { color: var(--soft); }
.up-way-at { color: var(--muted); font-size: 13px; font-variant-numeric: tabular-nums; white-space: nowrap; }
.up-way-stop { color: var(--danger); font-weight: 600; }
.up-acts-head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin-top: 6px; }
.up-acts-head h3 { margin: 0; font-family: var(--sans); font-size: 13px; font-weight: 600; color: var(--muted); }
.up-acts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px; margin: 0; padding: 0; list-style: none; }
.up-acts li {
  display: grid;
  grid-template-columns: 18px 1fr;
  grid-template-rows: auto auto;
  gap: 0 8px;
  padding: 7px 9px;
  border: 1px solid rgba(244, 239, 230, 0.08);
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.3;
}
.up-act-mark {
  grid-row: 1 / 3;
  display: grid;
  place-items: center;
  width: 18px;
  height: 18px;
  margin-top: 1px;
  border: 1.5px solid rgba(244, 239, 230, 0.2);
  border-radius: 50%;
}
.up-act-mark svg { width: 10px; height: 10px; }
.up-act-sub { color: var(--soft); font-size: 12px; }
.up-acts li.is-done { border-color: rgba(57, 135, 229, 0.35); background: rgba(57, 135, 229, 0.08); }
.up-acts li.is-done .up-act-mark { border-color: var(--people); background: var(--people); color: #0d1411; }
.up-acts li.is-money.is-done { border-color: rgba(184, 136, 44, 0.45); background: rgba(184, 136, 44, 0.1); }
.up-acts li.is-money.is-done .up-act-mark { border-color: var(--money); background: var(--money); }
.up-acts li.is-part { border-style: dashed; border-color: rgba(231, 160, 144, 0.45); }
.up-acts li.is-part .up-act-mark { border-color: var(--danger); color: var(--danger); }
.up-acts li.is-no .up-act-name { color: var(--soft); }
.up-acts li.is-no .up-act-sub { opacity: 0.7; }
.up-danger h2 { color: var(--danger); }
</style>
