const KEY = 'aiastro_cookie_ok'

export function hasConsent() {
  return localStorage.getItem(KEY) === '1'
}

export function acceptConsent() {
  localStorage.setItem(KEY, '1')
}
