import { reactive, ref } from 'vue'
import { webApi } from '../api/web.js'
import { ApiError, errorText } from '../api/http.js'

/**
 * The person's pairs (GET /me/partners), shared by the «Пара» panel and the stars on the sky.
 * The list is asked once per visit; the synastry of each pair once, until the pair changes.
 * While someone is still to answer an invitation the list is asked again now and then, so their
 * star lights up without a reload.
 */

const partners = ref([])
/** idle → loading → ready | error */
const status = ref('idle')
const message = ref('')
/** The partner being typed in the form: { name, date, time } — the sky draws it as it comes. */
const draft = reactive({ name: '', date: '', time: '' })
/** The pair under the pointer in the list, and the aspect under it in the panel: the sky answers. */
const hot = ref(null)
const hotAspect = ref(null)
/** Partners whose star has just lit up: the sky flashes them once. */
const lit = ref(new Set())
const syntheses = reactive({})

let pending = null
let generation = 0

function apply(items) {
  const before = new Map(partners.value.map((partner) => [partner.id, partner]))
  const fresh = new Set()
  for (const partner of items) {
    const was = before.get(partner.id)
    if (was && !was.birth && partner.birth) fresh.add(partner.id)
  }
  if (fresh.size) lit.value = new Set([...lit.value, ...fresh])
  partners.value = items
  return fresh
}

function load(force = false) {
  if (!force && (status.value === 'ready' || pending)) return pending || Promise.resolve([])
  if (!force || status.value !== 'ready') status.value = 'loading'
  const asked = generation
  pending = webApi
    .partners()
    .then((data) => {
      if (asked !== generation) return []
      const fresh = apply(data.items)
      status.value = 'ready'
      return [...fresh]
    })
    .catch((error) => {
      if (asked !== generation) return []
      // A failed refresh keeps the list it has; only the first load shows the error.
      if (status.value !== 'ready') {
        message.value = errorText(error)
        status.value = 'error'
      }
      return []
    })
    .finally(() => {
      pending = null
    })
  return pending
}

function replace(partner) {
  const index = partners.value.findIndex((item) => item.id === partner.id)
  partners.value = index < 0
    ? [...partners.value, partner]
    : partners.value.map((item) => (item.id === partner.id ? partner : item))
  return partner
}

async function add(body) {
  return replace(await webApi.addPartner(body))
}

async function invite(id) {
  return replace(await webApi.invitePartner(id))
}

async function remove(id) {
  await webApi.removePartner(id)
  partners.value = partners.value.filter((item) => item.id !== id)
  delete syntheses[id]
}

/** Asks for the synastry of one pair once; read it from `syntheses[id]`: { status, data, message }. */
function synastry(id, again = false) {
  if (again && syntheses[id]?.status === 'error') delete syntheses[id]
  if (!syntheses[id]) {
    syntheses[id] = { status: 'loading', data: null, message: '' }
    const entry = syntheses[id]
    webApi
      .synastry(id)
      .then((data) => {
        entry.data = data
        entry.status = 'ready'
      })
      .catch((error) => {
        entry.status = error instanceof ApiError && error.code === 'no_birth' ? 'empty' : 'error'
        entry.message = errorText(error)
      })
  }
  return syntheses[id]
}

function clearDraft() {
  Object.assign(draft, { name: '', date: '', time: '' })
}

/** After the person's own birth data change, every synastry is read again. */
function forgetSyntheses() {
  for (const id of Object.keys(syntheses)) delete syntheses[id]
}

function forget() {
  generation += 1
  partners.value = []
  status.value = 'idle'
  pending = null
  lit.value = new Set()
  forgetSyntheses()
  clearDraft()
}

export function usePartners() {
  return {
    partners, status, message, draft, hot, hotAspect, lit, syntheses,
    load, add, invite, remove, synastry, clearDraft, forgetSyntheses, forget,
  }
}

/** The link the partner opens: /invite/<token> on this site. */
export function inviteLink(token) {
  return `${window.location.origin}/invite/${token}`
}
