import { computed, reactive, watch } from 'vue'
import { webApi } from '../api/web.js'
import { webToken } from './useSession.js'
import { usePrices } from '../utils/prices.js'

/**
 * What «Небосвод» holds for this person (GET /me/sky), said in words: one line per feature for
 * the panel and a short one for the dome (SkyDome), in the person's own numbers — the chapters of
 * the portrait still closed, the light days of the month ahead, the questions already asked.
 * With the subscription the same lines tell what burns today and where to find it.
 *
 * Asked afresh each time the page opens: the questions and the pairs change between visits.
 */

const state = reactive({ data: null, loading: false })
// A request still in flight when the session changes must not write its stale answer back.
let generation = 0

function zone() {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || ''
  } catch {
    return ''
  }
}

function load() {
  const asked = ++generation
  state.loading = true
  return webApi
    .skyTeasers(zone())
    .then((data) => {
      if (asked === generation) state.data = data
    })
    .catch(() => {
      // Without the numbers the page still tells what each feature gives, in general words.
    })
    .finally(() => {
      if (asked === generation) state.loading = false
    })
}

watch(webToken, () => {
  generation += 1
  state.data = null
  state.loading = false
}, { flush: 'sync' })

/* ---- Words ---- */

function plural(count, one, few, many) {
  const tens = count % 100
  const units = count % 10
  if (tens > 10 && tens < 20) return many
  if (units === 1) return one
  if (units > 1 && units < 5) return few
  return many
}

const MONTHS_IN = ['январе', 'феврале', 'марте', 'апреле', 'мае', 'июне', 'июле', 'августе', 'сентябре', 'октябре', 'ноябре', 'декабре']
const dayMonth = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long' })
const asDay = (iso) => {
  const [year, month, day] = iso.split('-').map(Number)
  return new Date(year, month - 1, day)
}
/** «29 октября», from the server's ISO date, read as a calendar day (no zone shift); «сегодня», «завтра» near `today`. */
function onDay(iso, today) {
  const ahead = today ? Math.round((asDay(iso) - asDay(today)) / 86400000) : -1
  return ahead === 0 ? 'сегодня' : ahead === 1 ? 'завтра' : dayMonth.format(asDay(iso))
}
function inMonth(key) {
  return `в ${MONTHS_IN[Number(key.slice(5, 7)) - 1]}`
}

/** The spheres of the week's best days, as «лучший день для …». */
const FOR_SPHERE = { love: 'для близких', work: 'для дел', talk: 'для разговоров', energy: 'для сил' }
function bestDay(best, today) {
  const sphere = Object.keys(FOR_SPHERE).find((id) => best?.[id])
  return sphere ? { what: FOR_SPHERE[sphere], when: onDay(best[sphere], today) } : null
}

const quoted = (titles, count) => titles.slice(0, count).map((title) => `«${title}»`).join(', ')
const screens = (count) => `${count} ${plural(count, 'экран', 'экрана', 'экранов')}`

/**
 * `notes[feature]`: { short, line, to } — `short` for the dome (a few words), `line` for the panel,
 * `to` where it burns (with «Небосвод»). A feature without numbers yet is left out.
 */
function words(data, price) {
  if (!data) return {}
  const notes = {}
  const lit = data.lit
  const { chart, day, week, calendar, chat, pair } = data

  if (chart) {
    const closed = chart.titles.length
    notes.chart = lit
      ? {
          short: `${chart.chapters} ${plural(chart.chapters, 'глава', 'главы', 'глав')} портрета`,
          line: `Портрет карты — ${chart.chapters} ${plural(chart.chapters, 'глава', 'главы', 'глав')} прогулкой по колесу, и смысл каждого из ${chart.aspects} ${plural(chart.aspects, 'аспекта', 'аспектов', 'аспектов')}.`,
          to: { name: 'cabinet-chart' },
        }
      : {
          short: `ещё ${closed} ${plural(closed, 'глава', 'главы', 'глав')} портрета`,
          line: closed
            ? `Портрет открыт на первой главе. Ещё ${closed} ${plural(closed, 'глава ждёт', 'главы ждут', 'глав ждут')}: ${quoted(chart.titles, 2)}${closed > 2 ? ' и другие' : ''}.`
            : 'Портрет карты целиком и смысл каждого аспекта.',
        }
  }

  if (day) {
    const closed = Math.max(0, day.screens - 1)
    notes.day = lit
      ? {
          short: `«${day.title}»`,
          line: `Сегодня — «${day.title}»${day.tasks ? `, отмечено ${day.done} из ${day.tasks} ${plural(day.tasks, 'дела', 'дел', 'дел')}` : ''}.`,
          to: { name: 'cabinet-forecast' },
        }
      : {
          short: `«${day.title}»`,
          line: closed
            ? `Сегодня — «${day.title}». Открыт первый экран, ещё ${screens(closed)} ждут: ${quoted(day.titles, 2)}.`
            : `Сегодня — «${day.title}». Полный текст — каждое утро.`,
        }
  }

  if (week) {
    const best = bestDay(week.best, calendar?.start)
    const closed = Math.max(0, week.screens - 1)
    const bestLine = best ? `лучший день ${best.what} — ${best.when}` : ''
    notes.week = lit
      ? {
          short: best ? `${best.when} — ${best.what}` : `«${week.title}»`,
          line: `«${week.title}»${bestLine ? `: ${bestLine}` : ''}.`,
          to: { name: 'cabinet-forecast', query: { period: 'week' } },
        }
      : {
          short: best ? `${best.when} — ${best.what}` : `«${week.title}»`,
          line: `«${week.title}»${bestLine ? `: ${bestLine}` : ''}.${closed ? ` Ещё ${screens(closed)} о том, как прожить её легко.` : ''}`,
        }
  }

  if (calendar) {
    const month = inMonth(calendar.month)
    const easy = calendar.easy
    const easyWords = `${easy} ${plural(easy, 'лёгкий день', 'лёгких дня', 'лёгких дней')}`
    const nearest = calendar.nearest ? `Ближайший лёгкий день — ${onDay(calendar.nearest, calendar.start)}.` : ''
    notes.calendar = lit
      ? {
          short: easy ? `${easyWords} ${month}` : 'месяц на одном листе',
          line: [nearest, easy ? `${month[0].toUpperCase()}${month.slice(1)} их ${easy}.` : 'Тридцать дней на одном листе.'].filter(Boolean).join(' '),
          to: { name: 'cabinet-forecast', query: { period: 'month' } },
        }
      : {
          short: easy ? `${easyWords} ${month}` : 'весь месяц вперёд',
          line: [nearest, easy
            ? `${month[0].toUpperCase()}${month.slice(1)} ждут ещё ${easyWords} — календарь покажет весь месяц.`
            : 'Календарь покажет весь месяц и главный транзит каждого дня.'].filter(Boolean).join(' '),
        }
  }

  if (chat) {
    const { asked, left, daily, today_left: todayLeft } = chat
    notes.chat = lit
      ? {
          short: `${daily} ${plural(daily, 'вопрос', 'вопроса', 'вопросов')} в день`,
          line: `Сегодня ещё ${todayLeft} ${plural(todayLeft, 'вопрос', 'вопроса', 'вопросов')} из ${daily}.`,
          to: { name: 'cabinet-chat' },
        }
      : {
          short: `${daily} ${plural(daily, 'вопрос', 'вопроса', 'вопросов')} в день`,
          line: !asked
            ? `${left} ${plural(left, 'вопрос', 'вопроса', 'вопросов')} на пробу уже ваши, с «Небосводом» — ${daily} каждый день.`
            : left
              ? `${asked} ${plural(asked, 'вопрос', 'вопроса', 'вопросов')} позади, ещё ${left} на пробу → с «Небосводом» ${daily} в день.`
              : `${asked} ${plural(asked, 'вопрос', 'вопроса', 'вопросов')} позади → с «Небосводом» ${daily} каждый день.`,
        }
  }

  if (pair) {
    const cheaper = `${price.synastrySky} вместо ${price.synastry}`
    if (!pair.name) {
      notes.pair = {
        short: 'разбор дешевле',
        line: lit ? `Разбор пары для вас — ${price.synastrySky}. Добавьте близкого человека.` : `Добавьте близкого человека — с «Небосводом» разбор пары ${cheaper}.`,
        to: lit ? { name: 'cabinet-pair', query: { add: null } } : undefined,
      }
    } else if (pair.named_open) {
      notes.pair = {
        short: `вы и ${pair.name}`,
        line: lit ? `Вы и ${pair.name}: как сегодняшнее небо проходит по связям ваших карт.` : `Вы и ${pair.name} — пара открыта, с «Небосводом» у неё появится свой день.`,
        to: lit ? { name: 'cabinet-pair', query: { partner: pair.id } } : undefined,
      }
    } else {
      notes.pair = {
        short: `вы и ${pair.name}`,
        line: lit ? `Вы и ${pair.name}: разбор пары для вас — ${price.synastrySky}.` : `Вы и ${pair.name}: разбор пары ${cheaper}, а потом — её день каждое утро.`,
        to: lit ? { name: 'cabinet-pair', query: { partner: pair.id } } : undefined,
      }
    }
  }

  return notes
}

export function useSkyTeasers() {
  const { synastry, synastrySky } = usePrices()
  const notes = computed(() => words(state.data, { synastry: synastry.value, synastrySky: synastrySky.value }))
  return { teasers: state, notes, load }
}
