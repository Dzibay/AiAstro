import { request } from './http.js'
import { visitorId } from '../utils/track.js'

export const webApi = {
  register: (body) => request('/api/web/register', { method: 'POST', body: { ...body, visitor: visitorId() || null }, audience: 'web' }),
  login: (body) => request('/api/web/login', { method: 'POST', body: { ...body, visitor: visitorId() || null }, audience: 'web' }),
  me: () => request('/api/web/me', { audience: 'web', auth: true }),
  setBirth: (body) => request('/api/web/me/birth', { method: 'PUT', body, audience: 'web', auth: true }),
  chart: () => request('/api/web/me/chart', { audience: 'web', auth: true }),
  portrait: () => request('/api/web/me/chart/portrait', { audience: 'web', auth: true }),
  chartItem: (id) => request(`/api/web/me/chart/items/${encodeURIComponent(id)}`, { audience: 'web', auth: true }),
  forecast: (period, tz) =>
    request(`/api/web/me/forecast?${new URLSearchParams({ period, tz })}`, { audience: 'web', auth: true }),
  month: (tz) => request(`/api/web/me/forecast/month?${new URLSearchParams({ tz })}`, { audience: 'web', auth: true }),
  setName: (name) => request('/api/web/me/name', { method: 'PUT', body: { name }, audience: 'web', auth: true }),
  setEmail: (body) => request('/api/web/me/email', { method: 'PUT', body, audience: 'web', auth: true }),
  setMailNotes: (on) => request('/api/web/me/mail', { method: 'PUT', body: { on }, audience: 'web', auth: true }),
  addMarks: (marks) => request('/api/web/me/marks', { method: 'POST', body: { marks }, audience: 'web', auth: true }),
  forgotPassword: (email) => request('/api/web/password/forgot', { method: 'POST', body: { email }, audience: 'web' }),
  resetPassword: (body) => request('/api/web/password/reset', { method: 'POST', body, audience: 'web' }),
  setPassword: (body) => request('/api/web/me/password', { method: 'PUT', body, audience: 'web', auth: true }),
  deleteAccount: (password) =>
    request('/api/web/me/delete', { method: 'POST', body: { password }, audience: 'web', auth: true }),
  partners: () => request('/api/web/me/partners', { audience: 'web', auth: true }),
  addPartner: (body) => request('/api/web/me/partners', { method: 'POST', body, audience: 'web', auth: true }),
  removePartner: (id) =>
    request(`/api/web/me/partners/${encodeURIComponent(id)}`, { method: 'DELETE', audience: 'web', auth: true }),
  updatePartner: (id, body) =>
    request(`/api/web/me/partners/${encodeURIComponent(id)}`, { method: 'PUT', body, audience: 'web', auth: true }),
  /** The consent to show the joined partner one's own birth data. */
  sharePartner: (id) =>
    request(`/api/web/me/partners/${encodeURIComponent(id)}/share`, { method: 'POST', audience: 'web', auth: true }),
  seenPartner: (id) =>
    request(`/api/web/me/partners/${encodeURIComponent(id)}/seen`, { method: 'POST', audience: 'web', auth: true }),
  pairForecast: (id, tz) =>
    request(`/api/web/me/partners/${encodeURIComponent(id)}/forecast?${new URLSearchParams({ tz })}`, {
      audience: 'web',
      auth: true,
    }),
  invitePartner: (id) =>
    request(`/api/web/me/partners/${encodeURIComponent(id)}/invite`, { method: 'POST', audience: 'web', auth: true }),
  synastry: (id) => request(`/api/web/me/partners/${encodeURIComponent(id)}/synastry`, { audience: 'web', auth: true }),
  chat: () => request('/api/web/me/chat', { audience: 'web', auth: true }),
  ask: (text) => request('/api/web/me/chat', { method: 'POST', body: { text }, audience: 'web', auth: true }),
  /** The partner's side of an invitation: open, no account (a session, if any, says whose it is). */
  invitation: (token) => request(`/api/web/invite/${encodeURIComponent(token)}`, { audience: 'web', auth: true }),
  /** The invitation answered from a cabinet: its own birth data light the star. */
  acceptInvitation: (token, share) =>
    request(`/api/web/invite/${encodeURIComponent(token)}/accept`, { method: 'POST', body: { share }, audience: 'web', auth: true }),
  /** The pair joins the cabinet opened after the invitation was answered: the page's key proves it. */
  linkInvitation: (token, claim) =>
    request(`/api/web/invite/${encodeURIComponent(token)}/link`, { method: 'POST', body: { claim }, audience: 'web', auth: true }),
  answerInvitation: (token, body) =>
    request(`/api/web/invite/${encodeURIComponent(token)}`, { method: 'POST', body, audience: 'web' }),
  /** A payment at ЮKassa ({ product, partner }): { id, url } of its page; then its status after the return. */
  pay: (body) => request('/api/web/me/payments', { method: 'POST', body, audience: 'web', auth: true }),
  payment: (id) => request(`/api/web/me/payments/${encodeURIComponent(id)}`, { audience: 'web', auth: true }),
  places: (q) => request(`/api/web/places?${new URLSearchParams({ q })}`, { audience: 'web' }),
}
