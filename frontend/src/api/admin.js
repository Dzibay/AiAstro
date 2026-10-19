import { request } from './http.js'

export const adminApi = {
  login: (body) => request('/api/admin/login', { method: 'POST', body, audience: 'admin' }),
  me: () => request('/api/admin/me', { audience: 'admin', auth: true }),
  settings: () => request('/api/admin/settings', { audience: 'admin', auth: true }),
  saveSetting: (body) =>
    request('/api/admin/settings', { method: 'PUT', body, audience: 'admin', auth: true }),
  users: (q) => request(`/api/admin/users?${new URLSearchParams({ q })}`, { audience: 'admin', auth: true }),
  setSky: (id, days) =>
    request(`/api/admin/users/${encodeURIComponent(id)}/sky`, {
      method: 'PUT',
      body: { days },
      audience: 'admin',
      auth: true,
    }),
  partners: (id) => request(`/api/admin/users/${encodeURIComponent(id)}/partners`, { audience: 'admin', auth: true }),
  setBought: (id, partnerId, bought) =>
    request(`/api/admin/users/${encodeURIComponent(id)}/partners/${encodeURIComponent(partnerId)}/purchase`, {
      method: 'PUT',
      body: { bought },
      audience: 'admin',
      auth: true,
    }),
}
