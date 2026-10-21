/**
 * After `vite build`: a ready HTML file for every landing page and the sitemap with them.
 *
 * Each dist/<slug>.html is dist/index.html with the page's own title, description, canonical,
 * Open Graph and JSON-LD (WebApplication, FAQPage, BreadcrumbList), and with its words already
 * inside #app — so search reads the page without running JS, and Vue takes it over for people.
 * nginx serves /<slug> from <slug>.html (try_files $uri.html) and puts the site's address in
 * place of __ORIGIN__, as for the home page.
 */

import { readFileSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'
import { LANDINGS, plain } from '../src/landing/pages.js'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const dist = join(root, 'dist')
const signs = JSON.parse(readFileSync(join(root, 'src/landing/signs.json'), 'utf8'))
const template = readFileSync(join(dist, 'index.html'), 'utf8')
const SITE = 'Астра'
const ORIGIN = '__ORIGIN__'

const escape = (text) => String(text)
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;')
/** The headings keep their <em>, everything else is escaped. */
const heading = (text) => escape(text).replace(/&lt;(\/?)em&gt;/g, '<$1em>')

/** Replaces the content of one tag found by its opening; fails loudly if index.html changed. */
function swap(html, pattern, replacement) {
  if (!pattern.test(html)) throw new Error(`prerender: no ${pattern} in index.html`)
  return html.replace(pattern, replacement)
}

function jsonLd(page, url) {
  const graph = [
    {
      '@type': 'WebApplication',
      name: `${SITE} — ${page.crumb}`,
      url,
      description: page.description,
      applicationCategory: 'LifestyleApplication',
      operatingSystem: 'Any',
      inLanguage: 'ru',
      offers: { '@type': 'Offer', price: '0', priceCurrency: 'RUB' },
    },
    {
      '@type': 'FAQPage',
      mainEntity: page.faq.map((item) => ({ '@type': 'Question', name: item.q, acceptedAnswer: { '@type': 'Answer', text: item.a } })),
    },
    {
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Главная', item: `${ORIGIN}/` },
        { '@type': 'ListItem', position: 2, name: page.crumb, item: url },
      ],
    },
  ]
  // «<» never appears inside the script, so no text can close it early.
  return JSON.stringify({ '@context': 'https://schema.org', '@graph': graph }, null, 1).replace(/</g, '\\u003c')
}

/** The page's words as plain HTML; the same order as LandingView, without the form. */
function body(page) {
  const out = []
  out.push('<main class="prerender" style="max-width:760px;margin:0 auto;padding:110px 20px 80px;color:#e8e2d8">')
  out.push(`<nav aria-label="Навигация"><a href="/">Главная</a> · <span>${escape(page.crumb)}</span></nav>`)
  out.push(`<p>${escape(page.kicker)}</p>`)
  out.push(`<h1>${heading(page.h1)}</h1>`)
  out.push(`<p>${escape(page.lead)}</p>`)
  for (const section of page.sections) {
    out.push(`<section><h2>${escape(section.h2)}</h2>${section.text.map((text) => `<p>${escape(text)}</p>`).join('')}</section>`)
  }
  if (page.signs) {
    out.push(`<section><h2>${escape(page.signsTitle)}</h2>`)
    for (const sign of signs[page.signs]) {
      out.push(`<section id="${sign.sign}"><h3>${escape(sign.title)}</h3><p>${escape(sign.essence)}</p><p>${escape(sign.text)}</p></section>`)
    }
    out.push('</section>')
  }
  out.push(`<section><h2>Вопросы</h2>${page.faq.map((item) => `<h3>${escape(item.q)}</h3><p>${escape(item.a)}</p>`).join('')}</section>`)
  out.push('<nav aria-label="Другие расчёты"><h2>Другие расчёты</h2><ul>')
  for (const other of LANDINGS.filter((item) => item.name !== page.name)) {
    out.push(`<li><a href="/${other.slug}">${escape(other.crumb)}</a></li>`)
  }
  out.push('</ul></nav></main>')
  return out.join('\n')
}

function render(page) {
  const url = `${ORIGIN}/${page.slug}`
  const title = escape(page.title)
  const description = escape(page.description)
  let html = template
  html = swap(html, /<title>[^<]*<\/title>/, `<title>${title}</title>`)
  html = swap(html, /<meta name="description" content="[^"]*" \/>/, `<meta name="description" content="${description}" />`)
  html = swap(html, /<link rel="canonical" href="[^"]*" \/>/, `<link rel="canonical" href="${url}" />`)
  html = swap(html, /<meta property="og:title" content="[^"]*" \/>/, `<meta property="og:title" content="${title}" />`)
  html = swap(html, /<meta property="og:description" content="[^"]*" \/>/, `<meta property="og:description" content="${description}" />`)
  html = swap(html, /<meta property="og:url" content="[^"]*" \/>/, `<meta property="og:url" content="${url}" />`)
  html = swap(html, /<meta name="twitter:title" content="[^"]*" \/>/, `<meta name="twitter:title" content="${title}" />`)
  html = swap(html, /<meta name="twitter:description" content="[^"]*" \/>/, `<meta name="twitter:description" content="${description}" />`)
  html = swap(html, /<script type="application\/ld\+json">[\s\S]*?<\/script>/, () => `<script type="application/ld+json">\n${jsonLd(page, url)}\n</script>`)
  html = swap(html, /<div id="app"><\/div>/, () => `<div id="app">\n${body(page)}\n</div>`)
  return html
}

for (const page of LANDINGS) {
  writeFileSync(join(dist, `${page.slug}.html`), render(page))
}

// The sitemap of the build replaces the one copied from public/: the home page and the landings.
const today = new Date().toISOString().slice(0, 10)
const entry = (path, priority) => `  <url>\n    <loc>${ORIGIN}${path}</loc>\n    <lastmod>${today}</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>${priority}</priority>\n  </url>`
writeFileSync(join(dist, 'sitemap.xml'), [
  '<?xml version="1.0" encoding="UTF-8"?>',
  '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
  entry('/', '1.0'),
  ...LANDINGS.map((page) => entry(`/${page.slug}`, '0.9')),
  '</urlset>',
  '',
].join('\n'))

console.log(`prerender: ${LANDINGS.length} landing pages and the sitemap`)
