/** What the ИИ-астролог's pages call things: the topics of a message, who answered, the kinds of calls, the money. */

export const CATEGORIES = {
  astro: 'об астрологии',
  smalltalk: 'беседа',
  offtopic: 'не по теме',
  injection: 'попытка сменить роль',
  abuse: 'грубость',
  crisis: 'кризис',
  pending: 'ждёт ответа',
  '': 'до разметки',
}
/** The badge of a topic: the conversation itself is calm, the turns away are gold, the hard ones red. */
export const CATEGORY_TONE = {
  astro: 'is-ok',
  smalltalk: 'is-plain',
  offtopic: 'is-warn',
  injection: 'is-bad',
  abuse: 'is-bad',
  crisis: 'is-bad',
  pending: 'is-plain',
  '': 'is-plain',
}
export const categoryName = (category) => CATEGORIES[category ?? ''] || category

/** Who wrote the answer: the model, a template of the site (the model off, out of budget or failed), the service's own reply. */
export const SOURCES = { ai: 'модель', stub: 'шаблон', guard: 'ответ сервиса', '': 'шаблон' }
export const SOURCE_NOTES = {
  ai: 'ответ написала модель и он прошёл проверку',
  stub: 'модель выключена, бюджет исчерпан или ответ не прошёл проверку — ответил шаблон сайта',
  guard: 'код распознал кризис, попытку сменить роль или брань — модель не вызывалась',
}
export const sourceName = (source) => SOURCES[source ?? ''] || source

export const KINDS = { chat: 'чат', check: 'проверка связи', playground: 'песочница', redteam: 'провокации' }

export const MODES = [
  { id: 'off', label: 'Выключен', note: 'Отвечают шаблоны сайта, как раньше. Модель не вызывается и денег не тратит.' },
  { id: 'test', label: 'Тест', note: 'Модель отвечает только почтам из списка тестировщиков, остальным — шаблоны.' },
  { id: 'on', label: 'Включён', note: 'Модель отвечает всем, в пределах дневного лимита и бюджета месяца.' },
]

/**
 * Roubles of the provider: a call costs kopecks, so small sums keep up to four decimals.
 * 0.0123 → «0,0123 ₽», 12.5 → «12,50 ₽», 1234 → «1 234 ₽».
 */
export function money(value) {
  const number = Number(value || 0)
  if (!number) return '0 ₽'
  const digits = number >= 1000 ? 0 : number >= 1 ? 2 : 4
  return `${number.toLocaleString('ru-RU', { minimumFractionDigits: number >= 1000 ? 0 : Math.min(digits, 2), maximumFractionDigits: digits })} ₽`
}

/** Milliseconds as seconds: 1240 → «1,2 с». */
export const seconds = (ms) => (ms ? `${(ms / 1000).toLocaleString('ru-RU', { maximumFractionDigits: 1 })} с` : '—')

export const tokens = (value) => Number(value || 0).toLocaleString('ru-RU')

/**
 * What an ordinary answer costs on a model: the rules and the person's sky (~3 500 tokens, ~1 500 of
 * them read again from the provider's cache), ~400 tokens of answer. An estimate for choosing, not a bill.
 */
export function answerCost(model) {
  if (!model) return 0
  return (2000 * model.input + 1500 * model.cached + 400 * model.output) / 1000
}

export const modelName = (models, id) => models.find((model) => model.id === id)?.label || id || '—'
