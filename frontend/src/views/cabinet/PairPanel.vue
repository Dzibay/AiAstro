<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import PanelHead from '../../components/cabinet/PanelHead.vue'
import ReadingStories from '../../components/cabinet/ReadingStories.vue'
import BirthForm from '../../components/cabinet/BirthForm.vue'
import PairSpheres from '../../components/sky/PairSpheres.vue'
import PairShare from '../../components/sky/PairShare.vue'
import PairYears from '../../components/sky/PairYears.vue'
import { ASPECTS, POINTS, SIGN_BY_ID } from '../../components/cabinet/astro.js'
import { errorText } from '../../api/http.js'
import { webApi } from '../../api/web.js'
import { inviteLink, usePartners } from '../../composables/usePartners.js'
import { useToast } from '../../composables/useToast.js'
import { formatDate } from '../../utils/format.js'
import { usePrices } from '../../utils/prices.js'
import { usePayment } from '../../composables/usePayment.js'
import { birthSigns } from '../../utils/skyToday.js'

/**
 * «Пара»: the list of pairs, the two ways to a partner and the pair itself.
 *
 * ?add — the partner's data typed in by hand, ?invite — a link for the partner to fill in,
 * ?partner=<id> — one pair: the stars, the tone in a phrase, the five spheres, the key aspects,
 * the reading's first screen and the nearest of its five years for free; the full reading — read
 * as screens, with the years and the pair's plan — once it is bought. The sky (CabinetView → PairSky) follows the same query.
 * ?partner=<id>&edit — the data of a partner typed in by hand, corrected until the reading is bought.
 *
 * A pair joined by an invitation is shared by two cabinets: a reading bought on either side is
 * open on both, and stays open on one side when the other deletes the pair.
 */

const props = defineProps({
  user: { type: Object, required: true },
})
const emit = defineEmits(['updated'])
const { prices, pay: payOn, synastry: pairPrice, synastrySky: pairSkyPrice } = usePrices()

const route = useRoute()
const router = useRouter()
const { push } = useToast()
const {
  partners, status, message, draft, hot, hotAspect, lit, syntheses, opening,
  load, add, invite, update, remove, synastry, clearDraft, seen, celebrate,
  share: sharePair,
} = usePartners()

const mode = computed(() => {
  if (route.query.add !== undefined) return 'add'
  if (route.query.invite !== undefined) return 'invite'
  if (!route.query.partner) return 'list'
  return route.query.edit !== undefined && partner.value?.editable ? 'edit' : 'pair'
})
const partnerId = computed(() => Number(route.query.partner) || 0)
const partner = computed(() => partners.value.find((item) => item.id === partnerId.value) || null)
const pair = computed(() => (partner.value?.birth ? syntheses[partner.value.id] || null : null))

function go(query) {
  router.push({ name: 'cabinet-pair', query })
}

onMounted(() => load())

/* ---- Buying the reading, and the way back from ЮKassa ---- */

const { busy: paying, message: payMessage, start } = usePayment()
const priceSet = computed(() => Boolean(prices.value[props.user.sky ? 'synastry_sky' : 'synastry']))
function buy() {
  if (partner.value && payOn.value && priceSet.value) {
    start(
      { product: 'synastry', partner: partner.value.id },
      { partnerBought: partner.value.bought },
    )
  }
}
watch(partner, (value) => {
  if (value?.birth) synastry(value.id)
}, { immediate: true })
// A pair that is not in the list (deleted elsewhere, a stale link) leads back to the list.
watch([status, partnerId], () => {
  if (status.value === 'ready' && partnerId.value && !partner.value) router.replace({ name: 'cabinet-pair' })
})
watch(mode, () => {
  hotAspect.value = null
  if (mode.value !== 'add' && mode.value !== 'invite') clearDraft()
})

/* ---- What happened to the pair while it was closed: said once, then the mark goes out ---- */

const NEWS = {
  filled: (name) => `Пришёл ответ на приглашение: ${name} — вторая звезда зажглась.`,
  linked: () => 'У партнёра теперь свой кабинет: пара стала общей, она видна вам обоим.',
  paid: (name, both) => (both ? 'Для вас обоих: партнёру платить не нужно.' : 'Он останется с этой парой — возвращайтесь к нему, когда захочется.'),
  bought: () => 'Его открыл партнёр — для вас обоих.',
  gift: () => 'Подарок: мы открыли для вас полный разбор этой пары.',
  left: () => 'Партнёр удалил пару у себя. У вас она остаётся — со всем, что было открыто.',
  joined: (name) => `Пара теперь в вашем кабинете и общая с партнёром ${name}: разбор, открытый одним из вас, откроется у обоих.`,
}
/** The reading opened (bought here, by the partner, or given): the sky and the panel celebrate it once. */
const OPENED = new Set(['paid', 'bought', 'gift'])
const news = ref('')
watch(partner, (value, old) => {
  if (!value) return
  if (value.id !== old?.id) news.value = route.query.joined ? 'joined' : ''
  if (value.news) {
    // Just joined from this side: the pair's own news about the joining would say it the other way round.
    if (news.value !== 'joined') news.value = value.news
    if (OPENED.has(value.news) && value.bought) celebrate(value.id)
    seen(value.id)
  }
}, { immediate: true })
const newsText = computed(() => (news.value && partner.value ? NEWS[news.value]?.(partner.value.name, linked.value) || '' : ''))
const opened = computed(() => OPENED.has(news.value))

/** The reading has just opened: the haze over it melts, top to bottom, once per opening. */
const revealedKey = ref(0)
const revealing = computed(() => Boolean(opening.value) && opening.value.id === partner.value?.id && opening.value.key !== revealedKey.value)
function revealed() {
  if (opening.value) revealedKey.value = opening.value.key
}

/* ---- Waiting for invitations: the list is asked again, and a star that lit up flashes ---- */

const waiting = computed(() => partners.value.some((item) => !item.birth && (item.invite || item.waiting_share)))
let timer = 0
function poll() {
  if (document.visibilityState !== 'visible') return
  load(true).then((fresh) => {
    for (const id of fresh) {
      const item = partners.value.find((entry) => entry.id === id)
      if (item) push(`${item.name}: звезда зажглась`)
    }
    if (fresh.length) {
      setTimeout(() => {
        lit.value = new Set([...lit.value].filter((id) => !fresh.includes(id)))
      }, 2000)
    }
  })
}
watch(waiting, (on) => {
  clearInterval(timer)
  if (on) timer = setInterval(poll, 15000)
}, { immediate: true })
onUnmounted(() => {
  clearInterval(timer)
  clearDraft()
  hot.value = null
  hotAspect.value = null
})

/* ---- The two ways to a partner ---- */

function onDraft(next) {
  Object.assign(draft, next)
}

/** The partner typed on the «Совместимость» landing (LandingView), read once for the form by hand. */
const PARTNER_KEY = 'astra-partner'
function readCarried() {
  try {
    const saved = JSON.parse(sessionStorage.getItem(PARTNER_KEY) || 'null')
    if (!saved || typeof saved !== 'object' || !saved.birth || typeof saved.birth.date !== 'string') return null
    return { name: typeof saved.name === 'string' ? saved.name : '', birth: saved.birth }
  } catch {
    return null
  }
}
const carried = readCarried()

async function addByHand({ name, birth }) {
  return add({ name, birth })
}
function onAdded(created) {
  clearDraft()
  try {
    sessionStorage.removeItem(PARTNER_KEY)
  } catch {
    /* private mode */
  }
  router.replace({ name: 'cabinet-pair', query: { partner: created.id } })
}

function editByHand({ name, birth }) {
  return update(partner.value.id, { name, birth })
}
function onEdited(changed) {
  push('Данные партнёра исправлены')
  router.replace({ name: 'cabinet-pair', query: { partner: changed.id } })
}

/** The invitation says who calls: a cabinet opened by the letter gives its name first. */
const myName = ref('')
const nameMissing = computed(() => !props.user.name && !myName.value.trim())
async function introduce() {
  if (props.user.name) return
  emit('updated', await webApi.setName(myName.value.trim()))
}

const inviteName = ref('')
const inviting = ref(false)
const inviteMessage = ref('')
watch(inviteName, (name) => {
  if (mode.value === 'invite') Object.assign(draft, { name: name.trim(), date: '', time: '' })
})
async function sendInvite() {
  const name = inviteName.value.trim()
  if (!name) {
    inviteMessage.value = 'Укажите имя'
    return
  }
  if (nameMissing.value) {
    inviteMessage.value = 'Укажите и своё имя — партнёр увидит, от кого приглашение'
    return
  }
  inviteMessage.value = ''
  inviting.value = true
  try {
    await introduce()
    const created = await add({ name })
    await invite(created.id)
    inviteName.value = ''
    clearDraft()
    router.replace({ name: 'cabinet-pair', query: { partner: created.id } })
  } catch (error) {
    inviteMessage.value = errorText(error)
  } finally {
    inviting.value = false
  }
}

/* ---- One pair ---- */

const link = computed(() => (partner.value?.invite ? inviteLink(partner.value.invite) : ''))
const copied = ref(false)
async function copyLink() {
  try {
    await navigator.clipboard.writeText(link.value)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2200)
  } catch {
    push('Не получилось скопировать — выделите ссылку и скопируйте её вручную')
  }
}
const canShare = typeof navigator !== 'undefined' && typeof navigator.share === 'function'
function shareLink() {
  const text = props.user.name ? `${props.user.name} приглашает вас зажечь свою звезду рядом` : 'Вас приглашают зажечь свою звезду рядом'
  navigator.share({ title: 'Астра', text, url: link.value }).catch(() => {})
}
const relinking = ref(false)
async function makeLink() {
  if (nameMissing.value) return
  relinking.value = true
  try {
    await introduce()
    await invite(partner.value.id)
  } catch (error) {
    push(errorText(error))
  } finally {
    relinking.value = false
  }
}

/** The partner has joined, but does not see this side's data yet: the consent opens them. */
const sharing = ref(false)
async function showMine() {
  sharing.value = true
  try {
    await sharePair(partner.value.id)
    push('Готово: теперь партнёр видит вашу звезду')
  } catch (error) {
    push(errorText(error))
  } finally {
    sharing.value = false
  }
}

const linked = computed(() => partner.value?.kind === 'linked' && !partner.value.left)
const boughtLine = computed(() => {
  const item = partner.value
  if (!item?.bought) return ''
  const when = item.bought_at ? ` ${formatDate(item.bought_at.slice(0, 10))}` : ''
  if (item.bought_by === 'partner') return `Разбор открыл партнёр${when} — для вас обоих.`
  if (item.bought_by === 'gift') return `Разбор открыт в подарок${when}.`
  return linked.value ? `Вы открыли разбор${when} — для вас обоих.` : `Вы открыли разбор${when}.`
})

/* ---- The pair's day: with the bought reading and «Небосвод» ---- */

const forecast = ref(null)
const forecastFailed = ref(false)
const zone = (() => {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || ''
  } catch {
    return ''
  }
})()
watch(() => [partner.value?.id, partner.value?.bought, props.user.sky, pair.value?.data?.locked], async ([id, bought, , locked]) => {
  forecast.value = null
  forecastFailed.value = false
  if (!id || !bought || locked !== false) return
  try {
    const data = await webApi.pairForecast(id, zone)
    if (partner.value?.id === id) forecast.value = data
  } catch {
    forecastFailed.value = true
  }
}, { immediate: true })
const TONE_WORD = { easy: 'легко', calm: 'ровно', tense: 'бережно' }

const birthLine = computed(() => {
  const birth = partner.value?.birth
  if (!birth) return ''
  return [formatDate(birth.date), birth.time, birth.place].filter(Boolean).join(' · ')
})

const aspects = computed(() => (pair.value?.data?.aspects || []).map((aspect) => ({
  ...aspect,
  key: `${aspect.a}-${aspect.b}-${aspect.type}`,
  mine: POINTS[aspect.a].glyph,
  theirs: POINTS[aspect.b].glyph,
  aspect: ASPECTS[aspect.type],
})))
const moreAspects = computed(() => Math.max(0, (pair.value?.data?.aspects_total || 0) - aspects.value.length))
const moreAspectsWord = computed(() => {
  const count = moreAspects.value
  const teen = count % 100 >= 11 && count % 100 <= 14
  if (count % 10 === 1 && !teen) return 'связь'
  return count % 10 >= 2 && count % 10 <= 4 && !teen ? 'связи' : 'связей'
})
/** The aspects whose interpretation is open: a list of twenty paragraphs reads as a wall, so each opens on its own. */
const openAspects = ref(new Set())
function toggleAspect(aspect) {
  if (!aspect.text) return
  const next = new Set(openAspects.value)
  if (next.has(aspect.key)) next.delete(aspect.key)
  else next.add(aspect.key)
  openAspects.value = next
}
watch(partnerId, () => {
  openAspects.value = new Set()
})
const aspectTexts = computed(() => aspects.value.some((aspect) => aspect.text))

/* ---- The reading as screens, and its five years ---- */

const stories = ref(null)
const yearsPart = computed(() => pair.value?.data?.reading?.parts?.find((part) => part.kind === 'years') || null)
function openYears() {
  const index = pair.value.data.reading.parts.indexOf(yearsPart.value)
  stories.value?.open(index)
}

function setAspect(aspect) {
  hotAspect.value = aspect ? { a: aspect.a, b: aspect.b, type: aspect.type } : null
}
const hotKey = computed(() => (hotAspect.value ? `${hotAspect.value.a}-${hotAspect.value.b}-${hotAspect.value.type}` : ''))

const asking = ref(false)
const removing = ref(false)
watch(partnerId, () => {
  asking.value = false
})
async function confirmRemove() {
  removing.value = true
  try {
    await remove(partner.value.id)
    push('Пара удалена')
    router.replace({ name: 'cabinet-pair' })
  } catch (error) {
    push(errorText(error))
  } finally {
    removing.value = false
    asking.value = false
  }
}

/* ---- The list: each pair's tone, its signs beside the person's own, and whether its reading is open ---- */

const TONE_COLOUR = { easy: '#f0cd8a', tense: '#e08a76', mixed: '#eab48a', calm: '#e6e0f4' }
const TONE_PAIR = { easy: 'лёгкая пара', tense: 'пара с искрой', mixed: 'многогранная пара', calm: 'спокойная пара' }

function status_of(item, tone) {
  if (item.waiting_share) return 'общая · ждём данных партнёра'
  if (!item.birth) return item.invite ? 'ждём ответа по ссылке' : 'без данных'
  const kind = item.left ? 'партнёр удалил пару' : { linked: 'общая', invite: 'по ссылке' }[item.kind] || ''
  return [TONE_PAIR[tone] || 'звезда горит', kind].filter(Boolean).join(' · ')
}

const mySigns = computed(() => (props.user.birth ? birthSigns(props.user.birth.date, props.user.birth.time) : null))
/** ☉ the person's sign × the partner's, and ☽ the same once the partner's time is known. */
function signsOf(item) {
  const theirs = item.birth ? birthSigns(item.birth.date, item.birth.time) : null
  if (!theirs) return null
  const mine = mySigns.value
  const line = (point, own, word, their) => ({
    point: POINTS[point].glyph,
    mine: own ? SIGN_BY_ID[own].glyph : '',
    theirs: SIGN_BY_ID[their].glyph,
    label: `${POINTS[point].name}: ${own ? `${word} ${SIGN_BY_ID[own].in}, ` : ''}партнёра ${SIGN_BY_ID[their].in}`,
  })
  const lines = [line('sun', mine?.sun, 'ваше', theirs.sun)]
  if (theirs.moon) lines.push(line('moon', mine?.moon, 'ваша', theirs.moon))
  return { lines, label: lines.map((entry) => entry.label).join('; ') }
}

const rows = computed(() => partners.value.map((item) => {
  const tone = item.birth ? item.tone || syntheses[item.id]?.data?.tone || '' : ''
  return { item, colour: TONE_COLOUR[tone] || '#f3dcae', status: status_of(item, tone), signs: signsOf(item) }
}))
</script>

<template>
  <div class="pair-panel">
    <!-- ---- By hand ---- -->
    <BirthForm
      v-if="mode === 'add'"
      with-name
      :name="carried?.name || ''"
      :birth="carried?.birth || null"
      :sky="false"
      :submit="addByHand"
      submit-label="Зажечь звезду"
      @draft="onDraft"
      @saved="onAdded"
      @cancel="go({})"
    >
      <template #head>
        <PanelHead lead="Имя зажжёт звезду на небе, дата и время — её знаки, город — дома.">
          Данные <em>партнёра</em>
        </PanelHead>
      </template>
    </BirthForm>

    <!-- ---- A partner typed in by hand, corrected ---- -->
    <BirthForm
      v-else-if="mode === 'edit'"
      :key="`edit-${partner.id}`"
      with-name
      :name="partner.name"
      :birth="partner.birth"
      :sky="false"
      :submit="editByHand"
      submit-label="Сохранить"
      @saved="onEdited"
      @cancel="go({ partner: partner.id })"
    >
      <template #head>
        <PanelHead lead="Данные партнёра можно исправлять, пока разбор пары не открыт: потом он держится за них.">
          Данные <em>партнёра</em>
        </PanelHead>
      </template>
    </BirthForm>

    <!-- ---- By invitation ---- -->
    <form v-else-if="mode === 'invite'" class="invite-form" novalidate @submit.prevent="sendInvite">
      <PanelHead lead="Партнёр откроет ссылку, увидит ваше небо и сам укажет свои данные — без регистрации. А откроет свой кабинет — пара станет общей: разбор, открытый одним из вас, откроется у обоих.">
        <em>Приглашение</em>
      </PanelHead>
      <label class="field">
        <span class="field-label">Как зовут партнёра</span>
        <input v-model="inviteName" type="text" maxlength="80" autocomplete="off" />
      </label>
      <label v-if="!user.name" class="field">
        <span class="field-label">Как вас представить</span>
        <input v-model="myName" type="text" maxlength="80" autocomplete="given-name" placeholder="Ваше имя — его увидит партнёр" />
      </label>
      <p v-if="inviteMessage" class="error" role="alert">{{ inviteMessage }}</p>
      <div class="actions">
        <button class="gold-cta" type="submit" :disabled="inviting">{{ inviting ? 'Минуту…' : 'Отправить приглашение' }}</button>
        <button type="button" class="quiet" :disabled="inviting" @click="go({})">Отмена</button>
      </div>
      <p class="invite-consent">Отправляя приглашение, вы соглашаетесь показать партнёру свои данные рождения: они нужны, чтобы построить разбор вашей пары.</p>
    </form>

    <p v-else-if="status === 'error'" class="error">{{ message }}</p>
    <p v-else-if="status !== 'ready'" class="loading">Ищем ваши звёзды…</p>

    <!-- ---- One pair ---- -->
    <template v-else-if="mode === 'pair' && partner">
      <div v-if="newsText" class="news" :class="{ 'is-opening': opened }" role="status">
        <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg>
        <p>
          <span v-if="opened" class="news-title">Разбор открыт — навсегда</span>
          {{ newsText }}
        </p>
      </div>

      <template v-if="partner.waiting_share">
        <PanelHead :lead="`Пара уже общая. Как только ${partner.name} укажет в своём кабинете данные рождения, на небе зажжётся вторая звезда — ничего делать не нужно.`">
          Ждём <em>звезду</em>
        </PanelHead>
      </template>

      <template v-else-if="!partner.birth">
        <PanelHead :lead="`Когда ${partner.name} откроет ссылку и укажет данные рождения, на небе зажжётся вторая звезда.`">
          Ждём <em>ответа</em>
        </PanelHead>
        <div v-if="link" class="link-box">
          <input class="link" :value="link" readonly aria-label="Ссылка-приглашение" @focus="$event.target.select()" />
          <div class="link-actions">
            <button type="button" class="soft-button" @click="copyLink">{{ copied ? 'Скопировано' : 'Скопировать ссылку' }}</button>
            <button v-if="canShare" type="button" class="quiet" @click="shareLink">Поделиться</button>
          </div>
          <p class="hint">Ссылка ведёт только к этой паре: по ней видно лишь ваше имя, не ваши данные.</p>
        </div>
        <form v-else class="name-ask" novalidate @submit.prevent="makeLink">
          <label v-if="!user.name" class="field">
            <span class="field-label">Как вас представить</span>
            <input v-model="myName" type="text" maxlength="80" autocomplete="given-name" placeholder="Ваше имя — его увидит партнёр" />
          </label>
          <button type="submit" class="soft-button" :disabled="relinking || nameMissing">Получить ссылку</button>
        </form>
      </template>

      <template v-else>
        <PanelHead :lead="pair?.data?.phrase || ''">Вы и <em>{{ partner.name }}</em></PanelHead>
        <p class="birth-line">{{ birthLine }}</p>
        <p v-if="linked" class="shared-note">Общая пара: её видите вы оба.</p>
        <p v-else-if="partner.left && news !== 'left'" class="shared-note">Партнёр удалил пару у себя — у вас она остаётся.</p>

        <div v-if="linked && !partner.shared" class="share-box">
          <p>{{ partner.name }} пока не видит вашу звезду: в общей паре ваши данные рождения откроются партнёру только с вашего согласия.</p>
          <button type="button" class="soft-button" :disabled="sharing" @click="showMine">
            {{ sharing ? 'Минуту…' : 'Показать партнёру мои данные' }}
          </button>
        </div>

        <template v-if="pair?.status === 'empty'">
          <p class="quiet-text">Чтобы сложить две карты, нужна и ваша — укажите свою дату рождения.</p>
          <RouterLink class="add-birth" :to="{ name: 'cabinet-birth' }">
            <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg>
            Добавить дату рождения
          </RouterLink>
        </template>
        <div v-else-if="pair?.status === 'error'" class="retry">
          <p class="error">{{ pair.message }}</p>
          <button type="button" class="quiet" @click="synastry(partner.id, true)">Попробовать ещё раз</button>
        </div>
        <p v-else-if="!pair?.data" class="loading">Складываем две карты…</p>

        <template v-else>
          <section v-if="pair.data.spheres?.length" class="block" aria-labelledby="spheres-title">
            <h3 id="spheres-title" class="block-title">Пять сфер</h3>
            <PairSpheres :spheres="pair.data.spheres" />
            <PairShare :mine="user.name || 'Я'" :theirs="partner.name" :phrase="pair.data.phrase" :spheres="pair.data.spheres" />
          </section>

          <section class="block" aria-labelledby="aspects-title">
            <h3 id="aspects-title" class="block-title">{{ pair.data.locked ? 'Ключевые аспекты' : 'Все связи ваших карт' }}</h3>
            <ul v-if="aspects.length" class="chips">
              <li v-for="aspect in aspects" :key="aspect.key">
                <button
                  type="button"
                  class="chip"
                  :class="{ 'is-on': hotKey === aspect.key, 'has-text': aspect.text, 'is-open': openAspects.has(aspect.key) }"
                  :aria-label="aspect.title"
                  :aria-expanded="aspect.text ? openAspects.has(aspect.key) : undefined"
                  @click="toggleAspect(aspect)"
                  @pointerenter="setAspect(aspect)"
                  @pointerleave="setAspect(null)"
                  @focus="setAspect(aspect)"
                  @blur="setAspect(null)"
                >
                  <span class="chip-glyphs" aria-hidden="true">
                    <span class="glyph-mine">{{ aspect.mine }}</span>
                    <span :class="`tone-${aspect.aspect.tone}`">{{ aspect.aspect.glyph }}</span>
                    <span class="glyph-theirs">{{ aspect.theirs }}</span>
                  </span>
                  <span class="chip-text" aria-hidden="true">{{ aspect.title }}</span>
                  <svg v-if="aspect.text" class="chip-fold" viewBox="0 0 12 12" aria-hidden="true"><path d="M3 4.5L6 7.5L9 4.5" /></svg>
                  <span v-if="aspect.text && openAspects.has(aspect.key)" class="chip-desc">{{ aspect.text }}</span>
                </button>
              </li>
            </ul>
            <p v-else class="quiet-text">Тесных аспектов между картами нет: связь складывается из времени и выбора.</p>
            <p v-if="aspectTexts" class="aspects-hint">Нажмите на связь — откроется её толкование.</p>
            <p v-if="pair.data.locked && moreAspects > 0" class="quiet-text">
              И ещё {{ moreAspects }} {{ moreAspectsWord }} между картами — каждая с толкованием в разборе пары.
            </p>
          </section>

          <template v-if="pair.data.locked">
            <section class="block" aria-labelledby="reading-title">
              <h3 id="reading-title" class="block-title">Разбор пары</h3>
              <ReadingStories ref="stories" :reading="pair.data.reading" locked name="Разбор пары" locked-title="Дальше — в полном разборе">
                <template #locked>
                  <div class="unlock in-stories">
                    <p class="unlock-note">
                      Разбор открывается один раз и остаётся с этой парой навсегда<template v-if="linked">
                      — у вас обоих</template>.
                    </p>
                    <button type="button" class="unlock-cta" v-seen="'pair:stories'" data-track="pair:stories" :disabled="paying || !payOn || !priceSet" @click="buy">
                      <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg>
                      <template v-if="paying">Открываем ЮKassa…</template>
                      <template v-else>Открыть разбор — {{ user.sky ? pairSkyPrice : pairPrice }}</template>
                    </button>
                    <p v-if="!payOn" class="unlock-note">Оплата откроется совсем скоро.</p>
                  </div>
                </template>
              </ReadingStories>
            </section>
            <PairYears v-if="yearsPart" :part="yearsPart" locked @open="openYears" />
            <div class="unlock">
              <p class="unlock-note">
                Дальше — что стоит за каждой из пяти сфер, главные связи ваших карт, где планеты партнёра
                стоят в ваших домах, каким получается ваш союз и куда он растёт, ваши ближайшие пять лет
                по периодам и план пары из конкретных шагов. На каждом экране — что с этим делать.
                Разбор открывается один раз и остаётся с этой парой навсегда<template v-if="linked">
                — у вас обоих: партнёру платить не нужно</template>.
              </p>
              <dl class="pair-prices">
                <div :class="{ 'is-mine': !user.sky }"><dt>Отдельно</dt><dd>{{ pairPrice }}</dd></div>
                <div class="with-sky" :class="{ 'is-mine': user.sky }"><dt>С Небосводом</dt><dd>{{ pairSkyPrice }}</dd></div>
              </dl>
              <button type="button" class="unlock-cta" v-seen="'pair:panel'" data-track="pair:panel" :disabled="paying || !payOn || !priceSet" @click="buy">
                <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg>
                <template v-if="paying">Открываем ЮKassa…</template>
                <template v-else-if="linked">Открыть разбор для нас обоих — {{ user.sky ? pairSkyPrice : pairPrice }}</template>
                <template v-else>Открыть разбор — {{ user.sky ? pairSkyPrice : pairPrice }}</template>
              </button>
              <p v-if="payMessage" class="pay-error" role="alert">{{ payMessage }}</p>
              <p v-else-if="!payOn" class="unlock-note">Оплата откроется совсем скоро.</p>
              <RouterLink v-if="!user.sky" class="sky-link" v-seen="'sky:pair-price'" data-track="sky:pair-price" :to="{ name: 'cabinet-sky' }">
                С «Небосводом» каждый разбор пары дешевле →
              </RouterLink>
            </div>
          </template>
          <template v-else>
            <section class="block reading-open" :class="{ 'is-revealing': revealing }" aria-labelledby="reading-title" @animationend.self="revealed">
              <h3 id="reading-title" class="block-title">Разбор пары</h3>
              <p v-if="boughtLine" class="bought-line">{{ boughtLine }}</p>
              <ReadingStories ref="stories" :reading="pair.data.reading" name="Разбор пары" />
            </section>
            <PairYears v-if="yearsPart" :part="yearsPart" @open="openYears" />

            <section class="block" aria-labelledby="pair-day-title">
              <h3 id="pair-day-title" class="block-title">Ваш день вдвоём</h3>
              <template v-if="forecast?.locked">
                <p class="quiet-text">
                  Как сегодняшнее небо проходит по связям ваших карт и какой день недели для вас двоих самый лёгкий —
                  это прогноз пары, он открыт с «Небосводом».
                </p>
                <RouterLink class="sky-link" v-seen="'sky:pair-day'" data-track="sky:pair-day" :to="{ name: 'cabinet-sky' }">Открыть «Небосвод» →</RouterLink>
              </template>
              <template v-else-if="forecast">
                <p class="day-text">{{ forecast.text }}</p>
                <ul v-if="forecast.lit.length" class="lit">
                  <li v-for="(item, index) in forecast.lit" :key="index">
                    <span class="lit-planet">{{ item.planet_name }}</span> · {{ item.title }}
                  </li>
                </ul>
                <ol class="week" aria-label="Неделя пары">
                  <li v-for="(day, index) in forecast.week" :key="day.date" :class="[`tone-${day.tone}`, { 'is-today': index === 0 }]">
                    <span class="week-day">{{ index === 0 ? 'сегодня' : day.weekday.slice(0, 2) }}</span>
                    <span class="week-dot" aria-hidden="true" />
                    <span class="week-tone">{{ TONE_WORD[day.tone] }}</span>
                  </li>
                </ol>
              </template>
              <p v-else-if="forecastFailed" class="quiet-text">Небо пары сейчас не ответило — загляните чуть позже.</p>
              <p v-else class="loading">Смотрим на небо над вами двумя…</p>
            </section>
          </template>
        </template>
      </template>

      <footer class="pair-foot">
        <button type="button" class="quiet" @click="go({})">← Все пары</button>
        <button v-if="partner.editable && partner.birth" type="button" class="quiet" @click="go({ partner: partner.id, edit: null })">Исправить данные</button>
        <span v-if="asking" class="confirm">
          Удалить пару?
          <button type="button" class="quiet danger" :disabled="removing" @click="confirmRemove">Да</button>
          <button type="button" class="quiet" :disabled="removing" @click="asking = false">Нет</button>
        </span>
        <button v-else type="button" class="quiet" @click="asking = true">Удалить</button>
      </footer>
    </template>

    <!-- ---- The list ---- -->
    <template v-else>
      <PanelHead lead="Две карты рядом: где вы звучите в унисон и чему учитесь друг у друга.">
        Совместимость <em>двоих</em>
      </PanelHead>

      <ul v-if="partners.length" class="pairs">
        <li v-for="{ item, colour, status: line, signs } in rows" :key="item.id">
          <RouterLink
            class="pair-row"
            :class="{ 'is-waiting': !item.birth, 'is-bought': item.bought, 'is-hot': hot === item.id }"
            :style="{ '--tone': colour }"
            :to="{ name: 'cabinet-pair', query: { partner: item.id } }"
            @pointerenter="hot = item.id"
            @pointerleave="hot = null"
            @focus="hot = item.id"
            @blur="hot = null"
          >
            <!-- The pair as on the sky: the person's star, the thread in the pair's tone, the partner's star. -->
            <svg class="pair-mini" viewBox="0 0 60 40" aria-hidden="true">
              <path class="mini-thread" d="M7 31Q27 5 50 15" />
              <circle class="mini-mine" cx="7" cy="31" r="2.2" />
              <g transform="translate(50 15)">
                <template v-if="item.birth">
                  <circle class="mini-halo" r="8" />
                  <path v-if="item.bought" class="mini-spike" d="M0 -9Q0.7 -0.7 9 0Q0.7 0.7 0 9Q-0.7 0.7 -9 0Q-0.7 -0.7 0 -9Z" />
                  <circle class="mini-theirs" r="2.6" />
                </template>
                <circle v-else class="mini-wait" r="3.2" />
              </g>
            </svg>
            <span class="pair-name">{{ item.name }}</span>
            <span class="pair-status">{{ line }}</span>
            <span v-if="item.birth" class="pair-badge" :class="item.bought ? 'is-open' : 'is-closed'">
              <svg v-if="item.bought" viewBox="0 0 20 20" aria-hidden="true"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg>
              <svg v-else viewBox="0 0 12 14" aria-hidden="true"><rect x="1.5" y="6" width="9" height="7" rx="1.6" /><path d="M3.6 6V4.3a2.4 2.4 0 0 1 4.8 0V6" /></svg>
              {{ item.bought ? 'разбор открыт' : 'разбор закрыт' }}
            </span>
            <span v-if="signs" class="pair-signs" :aria-label="signs.label">
              <span v-for="entry in signs.lines" :key="entry.point" class="sign-line" aria-hidden="true">
                <span class="sign-point">{{ entry.point }}</span>
                <template v-if="entry.mine"><span class="glyph-mine">{{ entry.mine }}</span><span class="sign-x">×</span></template>
                <span class="glyph-theirs">{{ entry.theirs }}</span>
              </span>
            </span>
            <span v-if="item.news" class="pair-news" aria-label="Есть новости" />
          </RouterLink>
        </li>
      </ul>
      <p v-else class="quiet-text">
        Добавьте второго человека: введите данные сами или отправьте ссылку — по ней партнёр укажет их без регистрации.
      </p>

      <div class="ways">
        <button type="button" class="gold-cta" @click="go({ add: null })">Ввести данные</button>
        <button type="button" class="soft-button" @click="go({ invite: null })">Отправить приглашение</button>
      </div>
      <p v-if="!user.birth" class="hint">Для совместимости понадобится и ваша карта: <RouterLink :to="{ name: 'cabinet-birth' }">укажите свою дату рождения</RouterLink>.</p>
    </template>
  </div>
</template>

<style scoped>
.pair-panel { display: grid; gap: 18px; }

.loading { margin: 0; font-family: var(--serif); font-style: italic; font-size: 17px; color: rgba(242, 228, 200, 0.75); }
.error { margin: 0; font-size: 14px; color: #f2a48c; }
.quiet-text { margin: 0; font-size: 14.5px; line-height: 1.55; color: rgba(226, 220, 210, 0.66); }
.hint { margin: 0; font-size: 12.5px; line-height: 1.5; color: rgba(233, 194, 124, 0.75); }
.hint a { color: #f0cd8a; text-underline-offset: 3px; }
.birth-line { margin: -8px 0 0; text-align: center; font-family: var(--serif); font-style: italic; font-size: 16px; color: rgba(226, 220, 210, 0.6); }
.retry { display: grid; gap: 6px; justify-items: start; }

/* ---- The list: a card for each pair, its little sky on the left ---- */
.pairs { display: grid; gap: 8px; margin: 0; padding: 0; list-style: none; }
.pair-row {
  position: relative;
  display: grid;
  grid-template-columns: 56px minmax(0, 1fr) auto;
  grid-template-areas:
    'mini name badge'
    'mini status signs';
  column-gap: 12px;
  row-gap: 3px;
  align-items: center;
  padding: 12px 16px 12px 10px;
  border-radius: 16px;
  border: 1px solid rgba(240, 210, 150, 0.14);
  background:
    radial-gradient(70% 120% at 0% 50%, color-mix(in srgb, var(--tone) 9%, transparent), transparent 70%),
    linear-gradient(160deg, rgba(255, 240, 210, 0.035), rgba(255, 240, 210, 0.01));
  color: #efe7d8;
  text-decoration: none;
  transition: border-color 0.25s ease, background-color 0.25s ease, box-shadow 0.3s ease, transform 0.25s ease;
}
.pair-row.is-bought { border-color: rgba(240, 205, 138, 0.3); }
.pair-row:hover, .pair-row.is-hot {
  border-color: rgba(240, 205, 138, 0.55);
  background-color: rgba(240, 205, 138, 0.05);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25), inset 0 1px 0 rgba(255, 240, 210, 0.06);
}
.pair-row:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 2px; }

.pair-mini { grid-area: mini; width: 56px; height: 38px; overflow: visible; }
.mini-thread { fill: none; stroke: var(--tone); stroke-width: 1.1; stroke-linecap: round; opacity: 0.75; transition: opacity 0.25s ease, stroke-width 0.25s ease; }
.pair-row.is-waiting .mini-thread { stroke-dasharray: 1.5 3; opacity: 0.5; }
.pair-row:hover .mini-thread, .pair-row.is-hot .mini-thread { opacity: 1; stroke-width: 1.5; }
.mini-mine { fill: #f0cd8a; filter: drop-shadow(0 0 3px rgba(255, 205, 130, 0.9)); }
.mini-halo { fill: color-mix(in srgb, var(--tone) 22%, transparent); }
.mini-theirs { fill: #fff6f2; filter: drop-shadow(0 0 3px #ffb9a4); }
.mini-spike { fill: rgba(255, 228, 190, 0.75); }
.mini-wait { fill: none; stroke: #f3dcae; stroke-width: 1; stroke-dasharray: 2 2.4; opacity: 0.75; }

.pair-name { grid-area: name; overflow: hidden; font-family: var(--serif); font-size: 19px; line-height: 1.2; white-space: nowrap; text-overflow: ellipsis; }
.pair-status { grid-area: status; font-family: var(--serif); font-style: italic; font-size: 14.5px; line-height: 1.3; color: rgba(226, 220, 210, 0.6); }

.pair-badge {
  grid-area: badge;
  justify-self: end;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 9px 2px 7px;
  border-radius: 999px;
  font-size: 11px;
  letter-spacing: 0.06em;
  white-space: nowrap;
}
.pair-badge svg { width: 9px; height: 10px; }
.pair-badge.is-open { color: #f3dcae; border: 1px solid rgba(240, 205, 138, 0.45); background: rgba(240, 205, 138, 0.08); }
.pair-badge.is-open svg { fill: #f0cd8a; filter: drop-shadow(0 0 4px rgba(255, 200, 110, 0.85)); }
.pair-badge.is-closed { color: rgba(226, 220, 210, 0.5); border: 1px solid rgba(226, 220, 210, 0.14); }
.pair-badge.is-closed svg { fill: none; stroke: currentColor; stroke-width: 1.2; }

.pair-signs {
  grid-area: signs;
  justify-self: end;
  display: inline-flex;
  gap: 10px;
  font-family: 'Segoe UI Symbol', 'Noto Sans Symbols', sans-serif;
  font-size: 14px;
  white-space: nowrap;
}
.sign-line { display: inline-flex; align-items: baseline; gap: 3px; }
.sign-point { font-size: 11.5px; color: rgba(226, 220, 210, 0.45); }
.sign-x { font-family: var(--serif); font-size: 12px; color: rgba(226, 220, 210, 0.4); }

.ways { display: flex; flex-wrap: wrap; gap: 10px; }
.ways .gold-cta { flex: none; }

.pair-news {
  position: absolute;
  top: -3px;
  right: -3px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #f0cd8a;
  box-shadow: 0 0 8px 2px rgba(240, 205, 138, 0.6);
}

/* ---- One pair: what happened, and the shared pair ---- */
.news {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  margin: 0;
  padding: 10px 14px;
  border-radius: 14px;
  border: 1px solid rgba(240, 205, 138, 0.35);
  background: rgba(240, 205, 138, 0.06);
  font-family: var(--serif);
  font-style: italic;
  font-size: 15.5px;
  line-height: 1.4;
  color: #f3dcae;
}
.news p { margin: 0; }
.news svg { flex: none; width: 10px; height: 10px; margin-top: 6px; fill: #f0cd8a; filter: drop-shadow(0 0 5px rgba(255, 200, 110, 0.8)); }
/* The reading has opened: the note glows gold once, its star flares, a sheen runs across it. */
.news.is-opening {
  position: relative;
  overflow: hidden;
  padding: 14px 16px;
  border-color: rgba(240, 205, 138, 0.6);
  background:
    radial-gradient(90% 140% at 0% 0%, rgba(255, 214, 140, 0.16), transparent 65%),
    rgba(240, 205, 138, 0.05);
  animation: news-glow 2.6s ease 0.2s both;
}
.news.is-opening::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(105deg, transparent 35%, rgba(255, 240, 205, 0.18) 50%, transparent 65%);
  transform: translateX(-100%);
  animation: news-sheen 1.6s ease 0.9s forwards;
  pointer-events: none;
}
.news.is-opening svg { width: 14px; height: 14px; margin-top: 4px; animation: news-star 1.4s cubic-bezier(0.2, 0.7, 0.2, 1) 0.3s both; }
.news-title { display: block; margin-bottom: 2px; font-style: normal; font-size: 19px; color: #f6e2b4; }

/* The haze over the reading melts from the top down, as it opens. */
.reading-open.is-revealing {
  -webkit-mask-image: linear-gradient(180deg, #000 40%, transparent 60%);
  mask-image: linear-gradient(180deg, #000 40%, transparent 60%);
  -webkit-mask-size: 100% 250%;
  mask-size: 100% 250%;
  -webkit-mask-repeat: no-repeat;
  mask-repeat: no-repeat;
  animation: reveal 2.6s cubic-bezier(0.35, 0.1, 0.25, 1) 0.4s both;
}

@keyframes news-glow {
  0% { box-shadow: 0 0 0 0 rgba(240, 205, 138, 0); }
  30% { box-shadow: 0 0 34px 2px rgba(240, 205, 138, 0.28); }
  100% { box-shadow: 0 0 0 0 rgba(240, 205, 138, 0); }
}
@keyframes news-sheen { to { transform: translateX(100%); } }
@keyframes news-star {
  0% { transform: scale(0.3) rotate(-45deg); opacity: 0; }
  60% { transform: scale(1.35) rotate(8deg); opacity: 1; }
  100% { transform: scale(1) rotate(0); }
}
@keyframes reveal {
  from { -webkit-mask-position: 0 100%; mask-position: 0 100%; }
  to { -webkit-mask-position: 0 0; mask-position: 0 0; }
}
@keyframes reveal-fade { from { opacity: 0; } }
.shared-note { margin: -10px 0 0; text-align: center; font-size: 12.5px; letter-spacing: 0.04em; color: rgba(233, 194, 124, 0.75); }
.invite-consent { margin: 0; font-size: 13px; line-height: 1.5; color: rgba(226, 220, 210, 0.6); }
.share-box { display: grid; gap: 10px; padding: 12px 14px; border-radius: 14px; border: 1px dashed rgba(240, 205, 138, 0.35); }
.share-box p { margin: 0; font-size: 14px; line-height: 1.5; color: rgba(226, 220, 210, 0.75); }
.bought-line { margin: 0 0 6px; font-size: 13px; color: rgba(233, 194, 124, 0.8); }

/* ---- The pair's day ---- */
.day-text { margin: 0; font-family: var(--book); font-size: 15px; line-height: 1.6; color: #efe7d8; }
.lit { display: grid; gap: 4px; margin: 10px 0 0; padding: 0; list-style: none; font-size: 13.5px; color: rgba(226, 220, 210, 0.7); }
.lit-planet { color: #f0cd8a; }
.week { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 4px; margin: 14px 0 0; padding: 0; list-style: none; }
.week li { position: relative; display: grid; justify-items: center; gap: 6px; padding: 8px 2px; border-radius: 12px; border: 1px solid rgba(240, 210, 150, 0.1); }
.week li.is-today { border-color: rgba(240, 205, 138, 0.45); }
.week-day { font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; color: rgba(226, 214, 192, 0.66); }
.week-dot { width: 8px; height: 8px; border-radius: 50%; background: rgba(226, 220, 210, 0.45); }
.week .tone-easy .week-dot { background: #f0cd8a; box-shadow: 0 0 8px rgba(240, 205, 138, 0.7); }
.week .tone-tense .week-dot { background: #d98b7a; }
/* The tone is the dot's colour: seven words do not fit the panel, so the word is for screen readers. */
.week-tone { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }

/* ---- Forms and buttons (as the birth form's) ---- */
.invite-form { display: grid; gap: 14px; }
.name-ask { display: grid; gap: 12px; justify-items: start; }
.name-ask .field { justify-self: stretch; }
.field { display: grid; gap: 7px; }
.field-label { line-height: 16px; font-size: 10.5px; letter-spacing: 0.24em; text-transform: uppercase; color: rgba(226, 214, 192, 0.66); }
.field input, .link {
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
  outline: none;
  transition: border-color 0.25s ease, background 0.25s ease, box-shadow 0.25s ease;
}
.field input:focus, .link:focus {
  border-color: rgba(240, 205, 138, 0.7);
  background: rgba(255, 240, 210, 0.06);
  box-shadow: 0 0 0 3px rgba(240, 205, 138, 0.12);
}
.link { font-size: 13px; color: rgba(246, 239, 226, 0.85); }
.actions { display: flex; align-items: center; gap: 16px; }
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
.gold-cta:hover:not(:disabled) { filter: brightness(1.05); }
.gold-cta:focus-visible { outline: 2px solid #ffe2a8; outline-offset: 3px; }
.gold-cta:disabled { opacity: 0.6; cursor: progress; }
.soft-button {
  justify-self: start;
  padding: 11px 20px;
  border-radius: 999px;
  border: 1px solid rgba(240, 205, 138, 0.5);
  background: rgba(240, 205, 138, 0.06);
  font: inherit;
  font-size: 14.5px;
  color: #f3dcae;
  cursor: pointer;
  transition: background 0.25s ease, border-color 0.25s ease;
}
.soft-button:hover:not(:disabled) { background: rgba(240, 205, 138, 0.12); border-color: rgba(240, 205, 138, 0.8); }
.soft-button:focus-visible { outline: 2px solid #ffe2a8; outline-offset: 3px; }
.soft-button:disabled { opacity: 0.6; cursor: progress; }
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
.quiet.danger:hover:not(:disabled) { color: #f2a48c; }

.link-box { display: grid; gap: 10px; }
.link-actions { display: flex; flex-wrap: wrap; align-items: center; gap: 14px; }

/* ---- One pair (the forecast's chips and unlock) ---- */
.chips { display: grid; gap: 6px; margin: 0; padding: 0; list-style: none; }
.chip {
  display: grid;
  grid-template-columns: auto 1fr;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px 12px;
  border-radius: 14px;
  border: 1px solid rgba(240, 210, 150, 0.14);
  background: rgba(255, 240, 210, 0.02);
  font: inherit;
  text-align: left;
  color: #efe7d8;
  cursor: default;
  transition: border-color 0.25s ease, background 0.25s ease;
}
.chip:hover, .chip.is-on { border-color: rgba(240, 205, 138, 0.5); background: rgba(240, 205, 138, 0.06); }
.chip:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 2px; }
.chip-glyphs { display: inline-flex; gap: 5px; font-family: 'Segoe UI Symbol', 'Noto Sans Symbols', sans-serif; font-size: 16px; }
.glyph-mine { color: #f0cd8a; }
.glyph-theirs { color: #f6cbbd; }
.chip-glyphs .tone-easy, .chip-glyphs .tone-joint { color: #f0cd8a; }
.chip-glyphs .tone-tense { color: #d98b7a; }
.chip-text { font-family: var(--book); font-size: 14px; line-height: 1.4; }
.chip-desc { grid-column: 2 / -1; font-family: var(--book); font-size: 13.5px; line-height: 1.5; color: rgba(226, 220, 210, 0.7); }
.chip.has-text { grid-template-columns: auto 1fr auto; cursor: pointer; }
.chip-fold { width: 12px; height: 12px; fill: none; stroke: rgba(240, 205, 138, 0.7); stroke-width: 1.5; stroke-linecap: round; transition: transform 0.25s ease; }
.chip.is-open .chip-fold { transform: rotate(180deg); }
.aspects-hint { margin: -6px 0 0; font-family: var(--serif); font-style: italic; font-size: 14.5px; color: rgba(226, 220, 210, 0.55); }

.unlock { display: grid; gap: 12px; justify-items: start; margin-top: -8px; }
.unlock.in-stories { margin-top: 4px; }
.pair-prices { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; width: 100%; margin: 0; }
.pair-prices div { display: grid; gap: 2px; justify-items: center; padding: 10px 8px; border-radius: 14px; border: 1px solid rgba(240, 210, 150, 0.14); }
.pair-prices .with-sky { border-color: rgba(240, 205, 138, 0.4); background: linear-gradient(180deg, rgba(240, 205, 138, 0.07), transparent); }
.pair-prices .is-mine { box-shadow: 0 0 0 3px rgba(240, 205, 138, 0.1); }
.pair-prices dt { font-family: var(--caps); font-weight: 600; font-size: 14px; letter-spacing: 0.08em; color: rgba(226, 220, 210, 0.62); }
.pair-prices .with-sky dt { color: #f0cd8a; }
.pair-prices dd { margin: 0; font-family: var(--serif); font-size: 21px; color: #f6efe2; }
.sky-link { font-size: 13px; color: #f0cd8a; text-decoration: underline; text-decoration-color: rgba(240, 205, 138, 0.35); text-underline-offset: 3px; }
.sky-link:hover { text-decoration-color: currentColor; }
.sky-link:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 2px; border-radius: 4px; }
.unlock-note { margin: 0; font-size: 13.5px; line-height: 1.5; color: rgba(233, 194, 124, 0.8); }
.unlock-cta {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 11px 20px;
  border-radius: 999px;
  background: linear-gradient(180deg, #f4dba6, #dcb36c);
  color: #2b1d0b;
  font-size: 14.5px;
  font-weight: 600;
  text-decoration: none;
  box-shadow: 0 8px 26px rgba(230, 170, 80, 0.22);
  transition: box-shadow 0.25s ease, transform 0.25s ease;
}
.unlock-cta { border: 0; font-family: inherit; cursor: pointer; }
.unlock-cta:disabled { opacity: 0.5; cursor: default; box-shadow: none; transform: none; }
.unlock-cta svg { width: 10px; height: 10px; fill: #5a3d12; }
.pay-error { margin: 0; font-size: 13px; color: #f2a48c; }
.unlock-cta:hover:not(:disabled) { box-shadow: 0 10px 34px rgba(230, 170, 80, 0.38); transform: translateY(-1px); }
.unlock-cta:focus-visible { outline: 2px solid #ffe2a8; outline-offset: 3px; }

.add-birth {
  justify-self: start;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 11px 20px;
  border-radius: 999px;
  border: 1px solid rgba(240, 205, 138, 0.5);
  background: rgba(240, 205, 138, 0.06);
  font-size: 14.5px;
  color: #f3dcae;
  text-decoration: none;
}
.add-birth svg { width: 10px; height: 10px; fill: #f0cd8a; filter: drop-shadow(0 0 5px rgba(255, 200, 110, 0.8)); }
.add-birth:hover { background: rgba(240, 205, 138, 0.12); }

.pair-foot {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding-top: 12px;
  border-top: 1px solid rgba(240, 210, 150, 0.12);
}
.confirm { display: inline-flex; align-items: center; gap: 6px; font-size: 13.5px; color: rgba(226, 220, 210, 0.8); }

@media (max-width: 760px) {
  .field input, .link { font-size: 16px; }
  .chip, .unlock-cta, .add-birth, .soft-button, .quiet, .pair-row { min-height: 44px; }
  /* A narrow card: the signs go under the line about the pair. */
  .pair-row {
    grid-template-areas:
      'mini name badge'
      'mini status status'
      'mini signs signs';
  }
  .pair-signs { justify-self: start; margin-top: 2px; }
}
@media (prefers-reduced-motion: reduce) {
  .unlock-cta, .pair-row, .chip-fold { transition: none; }
  .news.is-opening, .news.is-opening svg { animation: none; }
  .news.is-opening::after { display: none; }
  .reading-open.is-revealing { -webkit-mask-image: none; mask-image: none; animation: reveal-fade 1.2s ease both; }
}
</style>
