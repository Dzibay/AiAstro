import { ApiError } from '../api/http.js'
import { webApi } from '../api/web.js'

/**
 * Every form that asks for the address — the hero, the end of the home page, the login page, a
 * landing, an invitation — goes through here: the letter with the link and six digits leaves, and
 * the login page's letter screen (/login?mode=sent) takes over. The address is kept for this tab
 * only, so a reload of that screen still knows where the letter went.
 */

const LETTER_KEY = 'astra-letter'
/** The birth data typed on the home page or a landing before the address (HomeView, LandingView). */
export const BIRTH_KEY = 'astra-birth'
/** Where the address was given: the funnel's start places (the `signup` event and the act `start:*`). */
export const START_PLACES = ['hero', 'how', 'final', 'compat', 'header', 'sky', 'login', 'landing', 'invite']

function read(key) {
  try {
    const value = JSON.parse(sessionStorage.getItem(key) || 'null')
    return value && typeof value === 'object' ? value : null
  } catch {
    return null
  }
}

/** The letter just sent: { email, wait } (seconds before another may go, sent — whether this one went). */
export function keptLetter() {
  const kept = read(LETTER_KEY)
  if (!kept || typeof kept.email !== 'string' || !kept.email) return null
  const wait = Math.max(0, Math.ceil(((Number(kept.until) || 0) - Date.now()) / 1000))
  return { email: kept.email, wait, sent: kept.sent !== false }
}

function keepLetter(email, wait, sent) {
  try {
    sessionStorage.setItem(LETTER_KEY, JSON.stringify({ email, until: Date.now() + wait * 1000, sent }))
  } catch {
    /* private mode: the screen still shows, only a reload forgets it */
  }
}

/** The birth data waiting from the home page, in the shape the API takes them; null without a date. */
export function savedBirth() {
  const saved = read(BIRTH_KEY)
  if (!saved || typeof saved.date !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(saved.date)) return null
  const time = !saved.noTime && typeof saved.time === 'string' && /^\d{2}:\d{2}$/.test(saved.time) ? saved.time : null
  const city = typeof saved.city === 'string' ? saved.city.trim() : ''
  const birth = { date: saved.date, time, place: city || null }
  const place = saved.place
  if (place && place.label === city && Number.isFinite(place.lat) && Number.isFinite(place.lon)) {
    Object.assign(birth, { lat: place.lat, lon: place.lon })
  }
  return birth
}

/** In the cabinet at last: what waited for it here is spent. */
export function forgetSignIn() {
  try {
    sessionStorage.removeItem(LETTER_KEY)
    sessionStorage.removeItem(BIRTH_KEY)
  } catch {
    /* private mode */
  }
}

/**
 * The letter to the address ({ email, consent, next, place }); the birth data from the home page go
 * along, kept by a new cabinet. Gives { token, user } when the cabinet opened at once (the site's
 * mail is not set up), else { sent, wait }: sent — the letter has just gone, wait — the seconds
 * before another may. Errors are the API's: consent (a new address without the tick), mail_off…
 */
export async function startSignIn({ email, consent = false, next = '/cabinet', place = '' }) {
  const address = email.trim()
  let answer
  try {
    answer = await webApi.start({
      email: address,
      consent,
      next,
      place: START_PLACES.includes(place) ? place : '',
      birth: savedBirth(),
    })
  } catch (error) {
    // Two letters asked at the same instant: the other one is on its way.
    if (!(error instanceof ApiError && error.code === 'confirm_wait')) throw error
    answer = { wait: 60 }
  }
  if (answer.token) return { token: answer.token, user: answer.user }
  // wait > 0: the previous letter is still fresh, and no new one went.
  const sent = !answer.wait
  const wait = answer.wait || answer.pause || 60
  keepLetter(address, wait, sent)
  return { sent, wait }
}

/** The login page's letter screen, after a letter sent from elsewhere (the address stays in this tab). */
export function letterRoute(place, next = '/cabinet') {
  const query = { mode: 'sent', from: START_PLACES.includes(place) ? place : undefined }
  if (next && next !== '/cabinet') query.next = next
  return { name: 'login', query }
}
