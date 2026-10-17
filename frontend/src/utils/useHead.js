function setMeta(name, content) {
  let meta = document.querySelector(`meta[name="${name}"]`)
  if (!content) {
    if (meta) meta.remove()
    return
  }
  if (!meta) {
    meta = document.createElement('meta')
    meta.setAttribute('name', name)
    document.head.appendChild(meta)
  }
  meta.setAttribute('content', content)
}

export function useHead({ title, description = '', noindex = false }) {
  document.title = title
  setMeta('description', description)
  setMeta('robots', noindex ? 'noindex, nofollow' : 'index, follow')
}
