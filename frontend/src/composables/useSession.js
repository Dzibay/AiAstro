import { ref } from 'vue'

const WEB_KEY = 'aiastro_session'
const ADMIN_KEY = 'aiastro_admin'

export const webToken = ref(localStorage.getItem(WEB_KEY) || '')
export const adminToken = ref(localStorage.getItem(ADMIN_KEY) || '')

export function readSession(audience) {
  if (audience === 'web') return webToken.value
  if (audience === 'admin') return adminToken.value
  return ''
}

export function writeSession(audience, value) {
  const next = value || ''
  if (audience === 'web') {
    webToken.value = next
    if (next) localStorage.setItem(WEB_KEY, next)
    else localStorage.removeItem(WEB_KEY)
  }
  if (audience === 'admin') {
    adminToken.value = next
    if (next) localStorage.setItem(ADMIN_KEY, next)
    else localStorage.removeItem(ADMIN_KEY)
  }
}

export function clearSession(audience) {
  writeSession(audience, '')
}

// The letter's link opened in another tab signs this one in too; a sign-out there signs it out here.
window.addEventListener('storage', (event) => {
  if (event.key === WEB_KEY) webToken.value = event.newValue || ''
  if (event.key === ADMIN_KEY) adminToken.value = event.newValue || ''
})

export function useSession() {
  return { webToken, adminToken, readSession, writeSession, clearSession }
}
