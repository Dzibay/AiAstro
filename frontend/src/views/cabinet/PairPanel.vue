<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import PanelHead from '../../components/cabinet/PanelHead.vue'
import ReadingText from '../../components/cabinet/ReadingText.vue'
import BirthForm from '../../components/cabinet/BirthForm.vue'
import { ASPECTS, POINTS } from '../../components/cabinet/astro.js'
import { errorText } from '../../api/http.js'
import { inviteLink, usePartners } from '../../composables/usePartners.js'
import { useToast } from '../../composables/useToast.js'
import { formatDate } from '../../utils/format.js'

/**
 * «Пара»: the list of pairs, the two ways to a partner and the pair itself.
 *
 * ?add — the partner's data typed in by hand, ?invite — a link for the partner to fill in,
 * ?partner=<id> — one pair: the stars, the tone in a phrase and the key aspects for free,
 * the full reading once it is bought. The sky (CabinetView → PairSky) follows the same query.
 */

const props = defineProps({
  user: { type: Object, required: true },
})

const route = useRoute()
const router = useRouter()
const { push } = useToast()
const {
  partners, status, message, draft, hot, hotAspect, lit, syntheses,
  load, add, invite, remove, synastry, clearDraft,
} = usePartners()

const mode = computed(() => {
  if (route.query.add !== undefined) return 'add'
  if (route.query.invite !== undefined) return 'invite'
  return route.query.partner ? 'pair' : 'list'
})
const partnerId = computed(() => Number(route.query.partner) || 0)
const partner = computed(() => partners.value.find((item) => item.id === partnerId.value) || null)
const pair = computed(() => (partner.value?.birth ? syntheses[partner.value.id] || null : null))

function go(query) {
  router.push({ name: 'cabinet-pair', query })
}

onMounted(() => load())
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

/* ---- Waiting for invitations: the list is asked again, and a star that lit up flashes ---- */

const waiting = computed(() => partners.value.some((item) => !item.birth && item.invite))
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

async function addByHand({ name, birth }) {
  return add({ name, birth })
}
function onAdded(created) {
  clearDraft()
  router.replace({ name: 'cabinet-pair', query: { partner: created.id } })
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
  inviteMessage.value = ''
  inviting.value = true
  try {
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
function share() {
  navigator.share({ title: 'Астра', text: `${props.user.name} приглашает вас зажечь свою звезду рядом`, url: link.value }).catch(() => {})
}
const relinking = ref(false)
async function makeLink() {
  relinking.value = true
  try {
    await invite(partner.value.id)
  } catch (error) {
    push(errorText(error))
  } finally {
    relinking.value = false
  }
}

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

function status_of(item) {
  if (!item.birth) return item.invite ? 'ждём ответа' : 'без данных'
  return item.bought ? 'звезда горит · разбор открыт' : 'звезда горит'
}
</script>

<template>
  <div class="pair-panel">
    <!-- ---- By hand ---- -->
    <BirthForm
      v-if="mode === 'add'"
      with-name
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

    <!-- ---- By invitation ---- -->
    <form v-else-if="mode === 'invite'" class="invite-form" novalidate @submit.prevent="sendInvite">
      <PanelHead lead="Партнёр откроет ссылку, увидит ваше небо и сам укажет свои данные — без регистрации.">
        <em>Приглашение</em>
      </PanelHead>
      <label class="field">
        <span class="field-label">Как зовут партнёра</span>
        <input v-model="inviteName" type="text" maxlength="80" autocomplete="off" />
      </label>
      <p v-if="inviteMessage" class="error" role="alert">{{ inviteMessage }}</p>
      <div class="actions">
        <button class="gold-cta" type="submit" :disabled="inviting">{{ inviting ? 'Минуту…' : 'Отправить приглашение' }}</button>
        <button type="button" class="quiet" :disabled="inviting" @click="go({})">Отмена</button>
      </div>
    </form>

    <p v-else-if="status === 'error'" class="error">{{ message }}</p>
    <p v-else-if="status !== 'ready'" class="loading">Ищем ваши звёзды…</p>

    <!-- ---- One pair ---- -->
    <template v-else-if="mode === 'pair' && partner">
      <template v-if="!partner.birth">
        <PanelHead :lead="`Когда ${partner.name} откроет ссылку и укажет данные рождения, на небе зажжётся вторая звезда.`">
          Ждём <em>ответа</em>
        </PanelHead>
        <div v-if="link" class="link-box">
          <input class="link" :value="link" readonly aria-label="Ссылка-приглашение" @focus="$event.target.select()" />
          <div class="link-actions">
            <button type="button" class="soft-button" @click="copyLink">{{ copied ? 'Скопировано' : 'Скопировать ссылку' }}</button>
            <button v-if="canShare" type="button" class="quiet" @click="share">Поделиться</button>
          </div>
          <p class="hint">Ссылка ведёт только к этой паре: по ней видно лишь ваше имя, не ваши данные.</p>
        </div>
        <button v-else type="button" class="soft-button" :disabled="relinking" @click="makeLink">Получить ссылку</button>
      </template>

      <template v-else>
        <PanelHead :lead="pair?.data?.phrase || ''">Вы и <em>{{ partner.name }}</em></PanelHead>
        <p class="birth-line">{{ birthLine }}</p>

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
          <section class="block" aria-labelledby="aspects-title">
            <h3 id="aspects-title" class="block-title">Ключевые аспекты</h3>
            <ul v-if="aspects.length" class="chips">
              <li v-for="aspect in aspects" :key="aspect.key">
                <button
                  type="button"
                  class="chip"
                  :class="{ 'is-on': hotKey === aspect.key }"
                  :aria-label="aspect.title"
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
                </button>
              </li>
            </ul>
            <p v-else class="quiet-text">Тесных аспектов между картами нет: связь складывается из времени и выбора.</p>
          </section>

          <div v-if="pair.data.locked" class="unlock">
            <p class="unlock-note">Звёзды, тон и аспекты открыты всем. Полный разбор — как вы любите, спорите и растёте рядом — отдельно для этой пары.</p>
            <RouterLink class="unlock-cta" :to="{ name: 'checkout', params: { product: 'synastry' }, query: { partner: partner.id } }">
              <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 0Q11 9 20 10Q11 11 10 20Q9 11 0 10Q9 9 10 0Z" /></svg>
              Оформить разбор — от … ₽
            </RouterLink>
          </div>
          <section v-else class="block" aria-labelledby="reading-title">
            <h3 id="reading-title" class="block-title">Разбор пары</h3>
            <ReadingText :reading="pair.data.reading" />
          </section>
        </template>
      </template>

      <footer class="pair-foot">
        <button type="button" class="quiet" @click="go({})">← Все пары</button>
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
        <li v-for="item in partners" :key="item.id">
          <RouterLink
            class="pair-row"
            :class="{ 'is-waiting': !item.birth }"
            :to="{ name: 'cabinet-pair', query: { partner: item.id } }"
            @pointerenter="hot = item.id"
            @pointerleave="hot = null"
            @focus="hot = item.id"
            @blur="hot = null"
          >
            <span class="pair-star" aria-hidden="true" />
            <span class="pair-name">{{ item.name }}</span>
            <span class="pair-status">{{ status_of(item) }}</span>
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

/* ---- The list ---- */
.pairs { display: grid; gap: 6px; margin: 0; padding: 0; list-style: none; }
.pair-row {
  display: grid;
  grid-template-columns: auto 1fr;
  grid-template-rows: auto auto;
  column-gap: 12px;
  align-items: center;
  padding: 10px 14px;
  border-radius: 14px;
  border: 1px solid rgba(240, 210, 150, 0.14);
  background: rgba(255, 240, 210, 0.02);
  color: #efe7d8;
  text-decoration: none;
  transition: border-color 0.25s ease, background 0.25s ease;
}
.pair-row:hover { border-color: rgba(240, 205, 138, 0.5); background: rgba(240, 205, 138, 0.06); }
.pair-row:focus-visible { outline: 1px solid #f0cd8a; outline-offset: 2px; }
.pair-star {
  grid-row: span 2;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #fff4ee;
  box-shadow: 0 0 10px 2px rgba(255, 185, 164, 0.7);
}
.pair-row.is-waiting .pair-star { background: none; border: 1px dashed rgba(243, 220, 174, 0.7); box-shadow: none; }
.pair-name { font-family: var(--serif); font-size: 19px; line-height: 1.15; }
.pair-status { font-family: var(--serif); font-style: italic; font-size: 15px; color: rgba(226, 220, 210, 0.55); }

.ways { display: flex; flex-wrap: wrap; gap: 10px; }
.ways .gold-cta { flex: none; }

/* ---- Forms and buttons (as the birth form's) ---- */
.invite-form { display: grid; gap: 14px; }
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

.unlock { display: grid; gap: 12px; justify-items: start; }
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
.unlock-cta svg { width: 10px; height: 10px; fill: #5a3d12; }
.unlock-cta:hover { box-shadow: 0 10px 34px rgba(230, 170, 80, 0.38); transform: translateY(-1px); }
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
}
@media (prefers-reduced-motion: reduce) {
  .unlock-cta { transition: none; }
}
</style>
