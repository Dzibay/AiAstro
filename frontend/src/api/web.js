import { request } from './http.js'

export const webApi = {
  register: (body) => request('/api/web/register', { method: 'POST', body, audience: 'web' }),
  login: (body) => request('/api/web/login', { method: 'POST', body, audience: 'web' }),
  me: () => request('/api/web/me', { audience: 'web', auth: true }),
  setBirth: (body) => request('/api/web/me/birth', { method: 'PUT', body, audience: 'web', auth: true }),
  chart: () => request('/api/web/me/chart', { audience: 'web', auth: true }),
  chartItem: (id) => request(`/api/web/me/chart/items/${encodeURIComponent(id)}`, { audience: 'web', auth: true }),
  forecast: (period, tz) =>
    request(`/api/web/me/forecast?${new URLSearchParams({ period, tz })}`, { audience: 'web', auth: true }),
  month: (tz) => request(`/api/web/me/forecast/month?${new URLSearchParams({ tz })}`, { audience: 'web', auth: true }),
  setName: (name) => request('/api/web/me/name', { method: 'PUT', body: { name }, audience: 'web', auth: true }),
  setEmail: (body) => request('/api/web/me/email', { method: 'PUT', body, audience: 'web', auth: true }),
  setPassword: (body) => request('/api/web/me/password', { method: 'PUT', body, audience: 'web', auth: true }),
  deleteAccount: (password) =>
    request('/api/web/me/delete', { method: 'POST', body: { password }, audience: 'web', auth: true }),
  partners: () => request('/api/web/me/partners', { audience: 'web', auth: true }),
  addPartner: (body) => request('/api/web/me/partners', { method: 'POST', body, audience: 'web', auth: true }),
  removePartner: (id) =>
    request(`/api/web/me/partners/${encodeURIComponent(id)}`, { method: 'DELETE', audience: 'web', auth: true }),
  invitePartner: (id) =>
    request(`/api/web/me/partners/${encodeURIComponent(id)}/invite`, { method: 'POST', audience: 'web', auth: true }),
  synastry: (id) => request(`/api/web/me/partners/${encodeURIComponent(id)}/synastry`, { audience: 'web', auth: true }),
  chat: () => request('/api/web/me/chat', { audience: 'web', auth: true }),
  ask: (text) => request('/api/web/me/chat', { method: 'POST', body: { text }, audience: 'web', auth: true }),
  /** The partner's side of an invitation: open, no account. */
  invitation: (token) => request(`/api/web/invite/${encodeURIComponent(token)}`, { audience: 'web' }),
  answerInvitation: (token, body) =>
    request(`/api/web/invite/${encodeURIComponent(token)}`, { method: 'POST', body, audience: 'web' }),
  places: (q) => request(`/api/web/places?${new URLSearchParams({ q })}`, { audience: 'web' }),
}
