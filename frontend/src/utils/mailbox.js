/**
 * The mail service behind an address: the «Открыть почту» button leads straight to its inbox,
 * and a slip in a well-known domain (gmial.com, yandex.ry) is noticed before the letter is lost.
 */

const SERVICES = [
  { label: 'Gmail', url: 'https://mail.google.com/mail/u/0/#inbox', domains: ['gmail.com', 'googlemail.com'] },
  { label: 'Яндекс Почту', url: 'https://mail.yandex.ru/', domains: ['yandex.ru', 'ya.ru', 'yandex.com', 'yandex.by', 'yandex.kz', 'yandex.ua', 'narod.ru'] },
  { label: 'Почту Mail', url: 'https://e.mail.ru/inbox/', domains: ['mail.ru', 'inbox.ru', 'list.ru', 'bk.ru', 'internet.ru', 'mail.ua'] },
  { label: 'Outlook', url: 'https://outlook.live.com/mail/0/', domains: ['outlook.com', 'hotmail.com', 'live.com', 'msn.com', 'outlook.ru'] },
  { label: 'iCloud Почту', url: 'https://www.icloud.com/mail/', domains: ['icloud.com', 'me.com', 'mac.com'] },
  { label: 'Рамблер Почту', url: 'https://mail.rambler.ru/', domains: ['rambler.ru', 'lenta.ru', 'autorambler.ru', 'myrambler.ru', 'ro.ru'] },
  { label: 'Yahoo Mail', url: 'https://mail.yahoo.com/', domains: ['yahoo.com', 'ymail.com'] },
  { label: 'Proton Mail', url: 'https://mail.proton.me/', domains: ['proton.me', 'protonmail.com', 'pm.me'] },
]

const KNOWN = SERVICES.flatMap((service) => service.domains)
/** Real services a letter or two away from the known ones: never taken for a slip. */
const REAL = new Set(['gmx.com', 'gmx.de', 'gmx.net', 'mail.com', 'mail.kz', 'aol.com', 'ukr.net', 'tut.by', 'i.ua', 'qip.ru', 'web.de', 'zoho.com', 'tuta.io'])

function domainOf(email) {
  const at = String(email || '').lastIndexOf('@')
  return at < 0 ? '' : String(email).slice(at + 1).trim().toLowerCase()
}

/** { label, url } of the service the address lives at, or null for a domain of its own. */
export function mailbox(email) {
  const domain = domainOf(email)
  return SERVICES.find((service) => service.domains.includes(domain)) || null
}

/** Letters to add, drop or change to turn one word into the other. */
function distance(a, b) {
  const row = Array.from({ length: b.length + 1 }, (_, i) => i)
  for (let i = 1; i <= a.length; i += 1) {
    let diagonal = row[0]
    row[0] = i
    for (let j = 1; j <= b.length; j += 1) {
      const above = row[j]
      row[j] = Math.min(row[j] + 1, row[j - 1] + 1, diagonal + (a[i - 1] === b[j - 1] ? 0 : 1))
      diagonal = above
    }
  }
  return row[b.length]
}

/** The address with a well-known domain in place of a near miss (gmial.com → gmail.com), or ''. */
export function likelyMeant(email) {
  const domain = domainOf(email)
  if (!domain || KNOWN.includes(domain) || REAL.has(domain)) return ''
  let best = ''
  let bestDistance = 3
  for (const known of KNOWN) {
    const gap = distance(domain, known)
    if (gap < bestDistance) {
      best = known
      bestDistance = gap
    }
  }
  // One slip in a short domain, two in a long one: ya.ru and yo.ru are both real enough.
  if (!best || bestDistance > (best.length > 7 ? 2 : 1)) return ''
  return `${String(email).slice(0, String(email).lastIndexOf('@'))}@${best}`
}
