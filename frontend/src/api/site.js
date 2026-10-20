import { request } from './http.js'

export const siteApi = {
  config: () => request('/api/site/config'),
  sky: () => request('/api/site/sky'),
  legal: (page) => request(`/api/site/legal/${encodeURIComponent(page)}`),
}
