import { request } from './http.js'

const get = (path) => request(path, { audience: 'admin', auth: true })
const send = (path, method, body) => request(path, { method, body, audience: 'admin', auth: true })
const id = encodeURIComponent
const query = (params) => new URLSearchParams(Object.entries(params).filter(([, value]) => value !== '' && value != null))

export const adminApi = {
  login: (body) => request('/api/admin/login', { method: 'POST', body, audience: 'admin' }),
  me: () => get('/api/admin/me'),
  settings: () => get('/api/admin/settings'),
  saveSetting: (body) => send('/api/admin/settings', 'PUT', body),
  /** A letter sent at once, to check the SMTP settings: { ok, error }. */
  testMail: (email) => send('/api/admin/mail/test', 'POST', { email }),
  /** Money and new accounts by day for 7, 30, 90 or 365 days, the products and the totals. */
  stats: (days) => get(`/api/admin/stats?${query({ days })}`),
  /** The payments through ЮKassa, a page at a time, and the address for its notifications. */
  payments: ({ q = '', status = '', offset = 0, user = '' } = {}) => get(`/api/admin/payments?${query({ q, status, offset, user })}`),
  /** state: '' | sky | nobirth | paid. */
  users: ({ q = '', state = '', offset = 0 } = {}) => get(`/api/admin/users?${query({ q, state, offset })}`),
  user: (userId) => get(`/api/admin/users/${id(userId)}`),
  /** Deletes the account for good; the email typed again is the confirmation. */
  deleteUser: (userId, email) => send(`/api/admin/users/${id(userId)}/delete`, 'POST', { email }),
  /** { days } extends «Небосвод» (0 closes it), { until: 'YYYY-MM-DD' } sets its last day. */
  setSky: (userId, body) => send(`/api/admin/users/${id(userId)}/sky`, 'PUT', body),
  /** The support's correction of the birth data, past the person's own one. */
  setBirth: (userId, birth) => send(`/api/admin/users/${id(userId)}/birth`, 'PUT', birth),
  /** Every pair with both its sides; state: '' | bought | linked | waiting. */
  pairs: ({ q = '', state = '', offset = 0 } = {}) => get(`/api/admin/pairs?${query({ q, state, offset })}`),
  setPairBought: (pairId, bought) => send(`/api/admin/pairs/${id(pairId)}/purchase`, 'PUT', { bought }),
  partners: (userId) => get(`/api/admin/users/${id(userId)}/partners`),
  setBought: (userId, partnerId, bought) =>
    send(`/api/admin/users/${id(userId)}/partners/${id(partnerId)}/purchase`, 'PUT', { bought }),
}
