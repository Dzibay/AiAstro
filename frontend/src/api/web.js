import { request } from './http.js'

export const webApi = {
  register: (body) => request('/api/web/register', { method: 'POST', body, audience: 'web' }),
  login: (body) => request('/api/web/login', { method: 'POST', body, audience: 'web' }),
  me: () => request('/api/web/me', { audience: 'web', auth: true }),
  setBirth: (body) => request('/api/web/me/birth', { method: 'PUT', body, audience: 'web', auth: true }),
}
