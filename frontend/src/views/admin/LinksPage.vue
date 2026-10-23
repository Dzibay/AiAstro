<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import ColumnChart from '../../components/admin/ColumnChart.vue'
import ConfirmDialog from '../../components/admin/ConfirmDialog.vue'
import { adminApi } from '../../api/admin.js'
import { useToast } from '../../composables/useToast.js'
import { PERIODS, PRODUCTS, buckets, failed, fmt, pageName, pct, stepOf } from './shared.js'

/**
 * Campaign links: an address with ?ref=<token> for each placement, and everything that came by
 * it — clicks, accounts, payments, money. A browser keeps the first link it came by, for good.
 */

const { push } = useToast()
const LINK_PERIODS = [{ days: 0, label: 'Всё время' }, ...PERIODS]
const days = ref(0)
const data = ref(null)
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  const asked = days.value
  try {
    const answer = await adminApi.links(asked)
    if (asked === days.value) data.value = answer
  } catch (caught) {
    error.value = failed(caught)
  } finally {
    loading.value = false
  }
}
watch(days, () => {
  load()
  if (open.value) loadDetail(open.value)
})
onMounted(load)

const items = computed(() => data.value?.items || [])
const totals = computed(() => data.value?.totals || {})
const tiles = computed(() => {
  const x = totals.value
  return [
    { label: 'Переходы', value: fmt.count(x.clicks), hint: `${fmt.count(x.visitors)} разных браузеров` },
    { label: 'Регистрации', value: fmt.count(x.signups), hint: `${pct(x.signups, x.visitors)} от посетителей` },
    { label: 'Платящие', value: fmt.count(x.paying), hint: `${pct(x.paying, x.signups)} от регистраций` },
    { label: 'Выручка', value: fmt.rub(x.revenue), hint: `«Небосвод» ${fmt.count(x.sky)} · пары ${fmt.count(x.pairs)}` },
  ]
})

/* ---- Copying ---- */

const copied = ref(0)
async function copy(link) {
  try {
    await navigator.clipboard.writeText(link.url)
  } catch {
    // No clipboard (an insecure address): the field is selected for a manual copy.
    window.prompt('Скопируйте ссылку', link.url)
    return
  }
  copied.value = link.id
  setTimeout(() => {
    if (copied.value === link.id) copied.value = 0
  }, 1600)
}

/* ---- A new link ---- */

const form = reactive({ name: '', token: '', note: '' })
const creating = ref(false)
const formError = ref('')
const base = computed(() => data.value?.base || `${window.location.origin}/?ref=`)

async function create() {
  formError.value = ''
  creating.value = true
  try {
    const made = await adminApi.createLink({ name: form.name.trim(), token: form.token.trim().toLowerCase(), note: form.note.trim() })
    Object.assign(form, { name: '', token: '', note: '' })
    await load()
    try {
      await navigator.clipboard.writeText(made.url)
      push('Ссылка создана и скопирована')
    } catch {
      push('Ссылка создана')
    }
    copied.value = made.id
    setTimeout(() => {
      if (copied.value === made.id) copied.value = 0
    }, 1600)
  } catch (caught) {
    formError.value = failed(caught)
  } finally {
    creating.value = false
  }
}

/* ---- One link opened ---- */

const open = ref(0)
const detail = ref(null)
const detailLoading = ref(false)
const edit = reactive({ name: '', note: '', busy: false })

async function loadDetail(id) {
  detailLoading.value = true
  try {
    const answer = await adminApi.link(id, days.value)
    if (open.value === id) detail.value = answer
  } catch (caught) {
    push(failed(caught))
  } finally {
    detailLoading.value = false
  }
}

function toggle(link) {
  if (open.value === link.id) {
    open.value = 0
    return
  }
  open.value = link.id
  detail.value = null
  Object.assign(edit, { name: link.name, note: link.note })
  loadDetail(link.id)
}

const opened = computed(() => items.value.find((item) => item.id === open.value) || null)
const changed = computed(() => opened.value && (edit.name.trim() !== opened.value.name || edit.note.trim() !== opened.value.note))
async function save() {
  edit.busy = true
  try {
    await adminApi.updateLink(open.value, { name: edit.name.trim(), note: edit.note.trim() })
    await load()
    push('Сохранено')
  } catch (caught) {
    push(failed(caught))
  } finally {
    edit.busy = false
  }
}

const span = computed(() => days.value || detail.value?.series.length || 30)
const clickPoints = computed(() => buckets(detail.value?.series || [], 'clicks', span.value))
const signupPoints = computed(() => buckets(detail.value?.series || [], 'signups', span.value))

const FUNNEL = [
  ['signup', 'Регистрация'],
  ['confirm', 'Подтвердил почту'],
  ['birth', 'Дата рождения'],
  ['section', 'Открыл раздел'],
  ['pair', 'Добавил пару'],
  ['chat', 'Спросил астролога'],
  ['checkout', 'Начал оплату'],
  ['paid', 'Оплатил'],
  ['sky', '«Небосвод»'],
  ['pair_bought', 'Разбор пары'],
]
const funnel = computed(() => {
  const d = detail.value
  if (!d) return []
  const top = Math.max(d.visitors, d.funnel.signup, 1)
  return [
    { key: 'visitors', label: 'Перешли', value: d.visitors, share: '' },
    ...FUNNEL.map(([key, label]) => ({ key, label, value: d.funnel[key], share: key === 'signup' ? pct(d.funnel.signup, d.visitors) : pct(d.funnel[key], d.funnel.signup) })),
  ].map((row) => ({ ...row, width: (row.value / top) * 100, paid: ['checkout', 'paid', 'sky', 'pair_bought'].includes(row.key) }))
})
const DEVICES = { phone: 'Телефон', desktop: 'Компьютер', unknown: 'Не определено' }
const hours = (value) => (!value ? '—' : value < 1 ? `${Math.max(1, Math.round(value * 60))} мин` : value < 48 ? `${Math.round(value)} ч` : `${Math.round(value / 24)} дн`)

/* ---- Deleting ---- */

const ask = reactive({ open: false, link: null, error: '', busy: false })
function askDelete(link) {
  Object.assign(ask, { open: true, link, error: '', busy: false })
}
async function confirmed() {
  ask.busy = true
  try {
    await adminApi.deleteLink(ask.link.id)
    if (open.value === ask.link.id) open.value = 0
    ask.open = false
    await load()
    push('Ссылка удалена')
  } catch (caught) {
    ask.error = failed(caught)
  } finally {
    ask.busy = false
  }
}
</script>

<template>
  <header class="adm-head">
    <div>
      <h1>Ссылки</h1>
      <p>Метки для рекламы: каждой площадке — своя ссылка. Человек навсегда остаётся за первой ссылкой, по которой пришёл.</p>
    </div>
    <div class="adm-seg" role="group" aria-label="Период">
      <button v-for="p in LINK_PERIODS" :key="p.days" type="button" :aria-pressed="days === p.days" @click="days = p.days">{{ p.label }}</button>
    </div>
  </header>

  <p v-if="error" class="error">{{ error }}</p>

  <div class="ln" :class="{ 'adm-loading': loading }">
    <div v-if="data" class="ln-tiles">
      <div v-for="tile in tiles" :key="tile.label" class="adm-panel ln-tile">
        <span class="ln-tile-label">{{ tile.label }}</span>
        <strong class="ln-tile-value">{{ tile.value }}</strong>
        <span class="ln-tile-hint">{{ tile.hint }}</span>
      </div>
    </div>

    <form class="adm-panel ln-form" @submit.prevent="create">
      <div class="adm-panel-head">
        <h2>Новая ссылка</h2>
        <p>метку можно не придумывать — её сочинит сервер</p>
      </div>
      <div class="ln-form-row">
        <label class="adm-label ln-name">
          Название
          <input v-model="form.name" class="adm-input" maxlength="80" placeholder="Например, Telegram — канал о луне" required>
        </label>
        <label class="adm-label ln-token">
          Метка
          <span class="ln-token-field">
            <span class="ln-token-base">{{ base }}</span>
            <input v-model="form.token" class="adm-input" maxlength="40" placeholder="tg-moon" pattern="[a-zA-Z0-9][a-zA-Z0-9_\-]{1,39}" title="2–40 знаков: латиница, цифры, дефис или подчёркивание">
          </span>
        </label>
        <label class="adm-label ln-note">
          Заметка
          <input v-model="form.note" class="adm-input" maxlength="300" placeholder="Где размещена, сколько стоила, до какого дня">
        </label>
        <button type="submit" class="adm-btn is-gold ln-create" :disabled="creating || !form.name.trim()">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
          {{ creating ? 'Создаём…' : 'Создать' }}
        </button>
      </div>
      <p v-if="formError" class="error ln-form-error">{{ formError }}</p>
    </form>

    <section class="adm-panel ln-list">
      <div class="adm-panel-head">
        <h2>Все ссылки</h2>
        <p>{{ days ? `за ${LINK_PERIODS.find((p) => p.days === days)?.label}` : 'за всё время' }} · нажмите на строку — откроется подробно</p>
      </div>
      <table v-if="items.length" class="adm-table ln-table">
        <thead>
          <tr>
            <th>Ссылка</th>
            <th class="num">Переходы</th>
            <th class="num">Регистрации</th>
            <th class="num">Дата рожд.</th>
            <th class="num">Платят</th>
            <th class="num">«Небосвод»</th>
            <th class="num">Пары</th>
            <th class="num">Выручка</th>
            <th class="num">₽ / переход</th>
            <th aria-label="Действия" />
          </tr>
        </thead>
        <tbody>
          <template v-for="link in items" :key="link.id">
            <tr class="is-link" :class="{ 'is-on': open === link.id }" tabindex="0" @click="toggle(link)" @keydown.enter.self="toggle(link)">
              <td class="wide">
                <div class="ln-who">
                  <strong>{{ link.name || 'Без названия' }}</strong>
                  <span class="ln-token-line">
                    <code>?ref={{ link.token }}</code>
                    <button type="button" class="ln-icon" :class="{ 'is-done': copied === link.id }" :aria-label="`Скопировать ссылку ${link.token}`" :title="copied === link.id ? 'Скопировано' : 'Скопировать ссылку'" @click.stop="copy(link)">
                      <svg v-if="copied === link.id" viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12.5 4.5 4.5L19 7.5" /></svg>
                      <svg v-else viewBox="0 0 24 24" aria-hidden="true"><path d="M9 9h10v11H9zM5 15H4V4h11v1" /></svg>
                    </button>
                  </span>
                  <span v-if="link.note" class="adm-dim ln-note-line">{{ link.note }}</span>
                </div>
              </td>
              <td data-label="Переходы" class="num">
                {{ fmt.count(link.clicks) }}
                <span class="ln-sub">{{ fmt.count(link.visitors) }} браузеров</span>
              </td>
              <td data-label="Регистрации" class="num">
                {{ fmt.count(link.signups) }}
                <span class="ln-sub">{{ pct(link.signups, link.visitors) }}</span>
              </td>
              <td data-label="Дата рождения" class="num">{{ fmt.count(link.birth) }}</td>
              <td data-label="Платят" class="num">
                {{ fmt.count(link.paying) }}
                <span class="ln-sub">{{ pct(link.paying, link.signups) }}</span>
              </td>
              <td data-label="«Небосвод»" class="num">
                {{ fmt.count(link.sky) }}
                <span class="ln-sub">горит у {{ fmt.count(link.sky_now) }}</span>
              </td>
              <td data-label="Пары" class="num">{{ fmt.count(link.pairs) }}</td>
              <td data-label="Выручка" class="num"><strong class="ln-money">{{ fmt.rub(link.revenue) }}</strong></td>
              <td data-label="₽ / переход" class="num">{{ link.visitors ? fmt.rub(Math.round(link.revenue / link.visitors)) : '—' }}</td>
              <td class="ln-actions">
                <button type="button" class="ln-icon is-danger" :aria-label="`Удалить ссылку ${link.token}`" title="Удалить" @click.stop="askDelete(link)">
                  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M9 7V4h6v3M6.5 7l1 13h9l1-13M10 11v6M14 11v6" /></svg>
                </button>
                <svg class="ln-chevron" viewBox="0 0 24 24" aria-hidden="true"><path d="m6 9 6 6 6-6" /></svg>
              </td>
            </tr>
            <tr v-if="open === link.id" class="ln-detail-row">
              <td colspan="10" class="wide">
                <div class="ln-detail" :class="{ 'adm-loading': detailLoading }">
                  <template v-if="detail">
                    <div class="ln-detail-meta">
                      <span>Создана {{ fmt.day(link.created_at) }}</span>
                      <span>последний переход: {{ link.last_click ? fmt.moment(link.last_click) : 'ещё не было' }}</span>
                      <span>от регистрации до оплаты: {{ hours(detail.hours_to_pay) }}</span>
                      <a :href="link.url" target="_blank" rel="noopener" class="ln-url">{{ link.url }}</a>
                    </div>

                    <div class="ln-detail-grid">
                      <div>
                        <h3>Переходы {{ stepOf(span) }}</h3>
                        <ColumnChart :points="clickPoints" name="Переходы" color="#3987e5" :format="fmt.count" :axis-format="fmt.compact" :height="150" />
                      </div>
                      <div>
                        <h3>Регистрации {{ stepOf(span) }}</h3>
                        <ColumnChart :points="signupPoints" name="Регистрации" color="#b8882c" :format="fmt.count" :axis-format="fmt.compact" :height="150" />
                      </div>
                    </div>

                    <div class="ln-detail-grid">
                      <div>
                        <h3>Воронка</h3>
                        <ol class="ln-funnel">
                          <li v-for="row in funnel" :key="row.key" :class="{ 'is-paid': row.paid }">
                            <span>{{ row.label }}</span>
                            <span class="ln-funnel-track"><i :style="{ width: `${row.width}%` }" /></span>
                            <strong class="num">{{ fmt.count(row.value) }}</strong>
                            <span class="num adm-dim">{{ row.share }}</span>
                          </li>
                        </ol>
                      </div>
                      <div class="ln-side">
                        <h3>Куда попадают</h3>
                        <ul v-if="detail.landings.length" class="ln-mini">
                          <li v-for="row in detail.landings" :key="row.name"><span>{{ pageName(row.name) }}</span><strong class="num">{{ fmt.count(row.clicks) }}</strong></li>
                        </ul>
                        <p v-else class="adm-dim">Переходов не было.</p>
                        <h3>Устройства</h3>
                        <ul v-if="detail.devices.length" class="ln-mini">
                          <li v-for="row in detail.devices" :key="row.device"><span>{{ DEVICES[row.device] || row.device }}</span><strong class="num">{{ pct(row.visitors, detail.visitors) }}</strong></li>
                        </ul>
                        <p v-else class="adm-dim">—</p>
                        <h3>Покупки</h3>
                        <ul v-if="detail.products.length" class="ln-mini">
                          <li v-for="row in detail.products" :key="row.product"><span>{{ PRODUCTS[row.product] || row.product }} × {{ row.payments }}</span><strong class="num">{{ fmt.rub(row.revenue) }}</strong></li>
                        </ul>
                        <p v-else class="adm-dim">Оплат пока нет.</p>
                      </div>
                    </div>

                    <div>
                      <h3>Кто пришёл <span class="adm-dim">· последние {{ detail.people.length }}</span></h3>
                      <ul v-if="detail.people.length" class="ln-people">
                        <li v-for="person in detail.people" :key="person.id">
                          <RouterLink :to="{ name: 'admin-user', params: { id: person.id } }" class="ln-person">{{ person.email }}</RouterLink>
                          <span class="adm-dim">{{ fmt.day(person.created_at) }}</span>
                          <span class="ln-flags">
                            <span v-if="person.birth" class="adm-badge is-plain">дата</span>
                            <span v-if="person.sky" class="adm-badge is-warn">«Небосвод»</span>
                          </span>
                          <strong class="num">{{ person.paid ? fmt.rub(person.paid) : '—' }}</strong>
                        </li>
                      </ul>
                      <p v-else class="adm-dim">По этой ссылке ещё никто не зарегистрировался.</p>
                    </div>

                    <form class="ln-edit" @submit.prevent="save">
                      <label class="adm-label">Название<input v-model="edit.name" class="adm-input" maxlength="80"></label>
                      <label class="adm-label ln-edit-note">Заметка<input v-model="edit.note" class="adm-input" maxlength="300"></label>
                      <button type="submit" class="adm-btn" :disabled="!changed || edit.busy">Сохранить</button>
                    </form>
                  </template>
                  <p v-else class="adm-dim">Загружаем…</p>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
      <p v-else-if="data" class="adm-empty">Ссылок пока нет — создайте первую выше.</p>
    </section>
  </div>

  <ConfirmDialog
    :open="ask.open"
    title="Удалить ссылку?"
    :text="ask.link ? `«${ask.link.name || ask.link.token}» перестанет считаться, её переходы пропадут. Люди и их оплаты останутся, но без метки.` : ''"
    label="Удалить"
    :busy="ask.busy"
    :error="ask.error"
    @confirm="confirmed"
    @cancel="ask.open = false"
  />
</template>

<style scoped>
.ln { display: grid; gap: 18px; }
.num { font-variant-numeric: tabular-nums; text-align: right; }

.ln-tiles { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.ln-tile { display: grid; align-content: start; gap: 4px; padding: 16px 18px; }
.ln-tile-label { color: var(--muted); font-size: 14px; }
.ln-tile-value { font-size: 26px; font-weight: 600; line-height: 1.15; }
.ln-tile-hint { color: var(--soft); font-size: 13px; }

.ln-form-row { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(0, 1.3fr) minmax(0, 1.2fr) auto; align-items: end; gap: 12px; }
.ln-form .adm-input { width: 100%; box-sizing: border-box; }
.ln-token-field { display: flex; align-items: center; border: 1px solid var(--panel-line); border-radius: 10px; overflow: hidden; background: rgba(0, 0, 0, 0.2); }
.ln-token-field .adm-input { border: 0; border-radius: 0; background: transparent; min-width: 6em; }
.ln-token-base { padding: 0 2px 0 12px; color: var(--soft); font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 55%; direction: rtl; }
.ln-create svg, .ln-icon svg, .ln-chevron { width: 16px; height: 16px; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
.ln-form-error { margin: 10px 0 0; }

.ln-table td { vertical-align: top; }
.ln-who { display: grid; gap: 3px; min-width: 14em; }
.ln-who strong { font-weight: 500; }
.ln-token-line { display: inline-flex; align-items: center; gap: 6px; }
.ln-token-line code { color: var(--gold); font-size: 13px; }
.ln-note-line { font-size: 13px; max-width: 26em; }
.ln-sub { display: block; color: var(--soft); font-size: 12px; }
.ln-money { color: var(--gold); font-weight: 600; }

/* Small round icon buttons: glass, as every control. */
.ln-icon {
  display: inline-grid;
  place-items: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border: 1px solid var(--panel-line);
  border-radius: 50%;
  background: rgba(255, 236, 200, 0.04);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  color: var(--soft);
  cursor: pointer;
  transition: color 0.2s ease, border-color 0.2s ease, background 0.2s ease;
}
.ln-icon svg { width: 14px; height: 14px; }
.ln-icon:hover { color: var(--gold); border-color: rgba(224, 193, 122, 0.4); }
.ln-icon.is-done { color: var(--ok); border-color: rgba(159, 211, 168, 0.4); }
.ln-icon.is-danger:hover { color: var(--danger); border-color: rgba(231, 160, 144, 0.4); }
.ln-actions { white-space: nowrap; text-align: right; }
.ln-chevron { margin-left: 8px; vertical-align: middle; color: var(--soft); transition: transform 0.2s ease; }
tr.is-on .ln-chevron { transform: rotate(180deg); }

.ln-detail-row > td { padding-top: 0; }
.ln-detail { display: grid; gap: 22px; padding: 18px 18px 20px; border: 1px solid var(--panel-line); border-radius: 14px; background: rgba(0, 0, 0, 0.18); cursor: default; }
.ln-detail h3 { margin: 0 0 10px; font-size: 14px; font-weight: 500; color: var(--muted); }
.ln-detail-meta { display: flex; flex-wrap: wrap; gap: 6px 20px; color: var(--soft); font-size: 13px; }
.ln-url { color: var(--gold); text-decoration: none; overflow-wrap: anywhere; }
.ln-url:hover { text-decoration: underline; }
.ln-detail-grid { display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr); gap: 26px; }

.ln-funnel { display: grid; gap: 6px; margin: 0; padding: 0; list-style: none; font-size: 14px; }
.ln-funnel li { display: grid; grid-template-columns: 9.5em minmax(0, 1fr) 3.5em 3.5em; align-items: center; gap: 10px; }
.ln-funnel-track { display: block; height: 9px; border-radius: 3px; background: rgba(244, 239, 230, 0.04); overflow: hidden; }
.ln-funnel-track i { display: block; height: 100%; border-radius: 3px; background: var(--people); }
.ln-funnel li.is-paid .ln-funnel-track i { background: var(--money); }

.ln-side h3:not(:first-child) { margin-top: 16px; }
.ln-mini { display: grid; gap: 5px; margin: 0; padding: 0; list-style: none; font-size: 14px; }
.ln-mini li { display: flex; justify-content: space-between; gap: 12px; }

.ln-people { display: grid; margin: 0; padding: 0; list-style: none; font-size: 14px; }
.ln-people li { display: grid; grid-template-columns: minmax(0, 1fr) 8em 12em 6em; align-items: center; gap: 10px; padding: 7px 0; border-top: 1px solid var(--panel-line); }
.ln-people li:first-child { border-top: 0; }
.ln-person { color: var(--ink); text-decoration: none; overflow-wrap: anywhere; }
.ln-person:hover { text-decoration: underline; }
.ln-flags { display: flex; gap: 6px; }

.ln-edit { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.6fr) auto; align-items: end; gap: 12px; padding-top: 16px; border-top: 1px solid var(--panel-line); }
.ln-edit .adm-input { width: 100%; box-sizing: border-box; }

@media (max-width: 1200px) {
  .ln-form-row { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
  .ln-detail-grid { grid-template-columns: minmax(0, 1fr); }
}
@media (max-width: 760px) {
  .ln-tiles { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .ln-form-row, .ln-edit { grid-template-columns: minmax(0, 1fr); }
  .ln-sub { display: inline; margin-left: 6px; }
  .ln-people li { grid-template-columns: minmax(0, 1fr) auto; }
  .ln-flags { display: none; }
}
</style>
