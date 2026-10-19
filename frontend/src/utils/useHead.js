function setTag(selector, create, attrs, value) {
  let node = document.head.querySelector(selector)
  if (!value) {
    node?.remove()
    return
  }
  if (!node) {
    node = document.createElement(create)
    Object.entries(attrs).forEach(([key, val]) => node.setAttribute(key, val))
    document.head.appendChild(node)
  }
  node.setAttribute(attrs.rel ? 'href' : 'content', value)
}

const meta = (name, value) => setTag(`meta[name="${name}"]`, 'meta', { name }, value)
const og = (property, value) => setTag(`meta[property="${property}"]`, 'meta', { property }, value)

export function useHead({ title, description = '', noindex = false }) {
  document.title = title
  meta('description', description)
  meta('robots', noindex ? 'noindex, nofollow' : 'index, follow')

  // Canonical and social tags follow the current page; query and hash are not part of the address.
  const url = `${window.location.origin}${window.location.pathname}`
  setTag('link[rel="canonical"]', 'link', { rel: 'canonical' }, noindex ? '' : url)
  og('og:title', title)
  og('og:description', description)
  og('og:url', url)
  meta('twitter:title', title)
  meta('twitter:description', description)
}
