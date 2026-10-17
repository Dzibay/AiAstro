import { request } from './http.js'

export const siteApi = {
  config: () => request('/api/site/config'),
  legal: (page) => request(`/api/site/legal/${encodeURIComponent(page)}`),
}
