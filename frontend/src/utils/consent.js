const KEY = 'aiastro_cookie_ok'
// Raised when the note says something new (Яндекс Метрика), so it is accepted anew.
const VERSION = '2'

export function hasConsent() {
  return localStorage.getItem(KEY) === VERSION
}

export function acceptConsent() {
  localStorage.setItem(KEY, VERSION)
}
