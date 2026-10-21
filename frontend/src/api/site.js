import { request } from './http.js'

export const siteApi = {
  config: () => request('/api/site/config'),
  sky: () => request('/api/site/sky'),
  legal: (page) => request(`/api/site/legal/${encodeURIComponent(page)}`),
  // The landing pages' taste of a calculation, before any account (backend app/landing.py).
  previewNatal: (body) => request('/api/site/preview/natal', { method: 'POST', body }),
  previewPair: (body) => request('/api/site/preview/pair', { method: 'POST', body }),
  previewForecast: (body) => request('/api/site/preview/forecast', { method: 'POST', body }),
}
