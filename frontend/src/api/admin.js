import { request } from './http.js'

export const adminApi = {
  login: (body) => request('/api/admin/login', { method: 'POST', body, audience: 'admin' }),
  me: () => request('/api/admin/me', { audience: 'admin', auth: true }),
  settings: () => request('/api/admin/settings', { audience: 'admin', auth: true }),
  saveSetting: (body) =>
    request('/api/admin/settings', { method: 'PUT', body, audience: 'admin', auth: true }),
}
