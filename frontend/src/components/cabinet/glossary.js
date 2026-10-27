import { reactive } from 'vue'
import { SIGNS } from '../../utils/skyToday.js'
import { ROMAN } from './astro.js'

/**
 * The words of astrology in a text, found for LiveText: the planets and points («Меркурий
 * в Рыбах», «Луна в VII доме») become links that light the point on the wheel, the terms
 * («квадрат», «управитель», «IV дом») explain themselves on hover, the dates turn gold.
 *
 * `\b` knows no Cyrillic, so the words are fenced with lookarounds on letters instead.
 */

const L = 'A-Za-zА-Яа-яЁё'
const fence = (source) => `(?<![${L}])(?:${source})(?![${L}])`

/** What each house of the chart speaks of, after «… дом —». */
export const HOUSE_THEMES = [
  'вы сами: облик, характер, начало дел',
  'деньги, ценности и то, что вас кормит',
  'общение, учёба, братья и сёстры, ближний круг',
  'дом, семья и корни',
  'радость, творчество, любовь и дети',
  'работа, здоровье и повседневный ритм',
  'партнёрство, брак и близкие союзы',
  'глубина, общие ресурсы и перемены',
  'дальние дороги, смыслы и учителя',
  'призвание, карьера и место в мире',
  'друзья, единомышленники и мечты',
  'тишина, внутренний мир и отдых',
]

const POINT_TIPS = {
  sun: ['Солнце', 'ваша воля и то, ради чего вы живёте.'],
  moon: ['Луна', 'чувства, привычки и то, что дарит покой.'],
  mercury: ['Меркурий', 'ум, речь и то, как вы учитесь.'],
  venus: ['Венера', 'любовь, вкус и то, что вам дорого.'],
  mars: ['Марс', 'энергия, напор и то, как вы действуете.'],
  jupiter: ['Юпитер', 'вера, рост и щедрость судьбы.'],
  saturn: ['Сатурн', 'опора, дисциплина и зрелость.'],
  uranus: ['Уран', 'свобода, перемены и озарения.'],
  neptune: ['Нептун', 'мечта, вдохновение и интуиция.'],
  pluto: ['Плутон', 'глубина и сила обновления.'],
  node: ['Северный узел', 'направление роста, к которому зовёт жизнь.'],
  chiron: ['Хирон', 'место, где ваш опыт становится даром помогать другим.'],
  lilith: ['Лилит', 'ваша свободная, неприручённая сторона.'],
  asc: ['Асцендент', 'знак, что восходил на востоке в минуту рождения: ваш облик и первое впечатление.'],
  mc: ['Середина неба', 'высшая точка карты: призвание и путь в мире.'],
}

/** Every form a point takes in a sentence. The names are capitalised, so they are matched as written. */
const POINT_FORMS = {
  sun: 'Солнц(?:е|а|у|ем)',
  moon: 'Лун(?:а|ы|е|у|ой|ою)',
  mercury: 'Меркури(?:й|я|ю|ем|и)',
  venus: 'Венер(?:а|ы|е|у|ой)',
  mars: 'Марс(?:а|у|ом|е)?',
  jupiter: 'Юпитер(?:а|у|ом|е)?',
  saturn: 'Сатурн(?:а|у|ом|е)?',
  uranus: 'Уран(?:а|у|ом|е)?',
  neptune: 'Нептун(?:а|у|ом|е)?',
  pluto: 'Плутон(?:а|у|ом|е)?',
  chiron: 'Хирон(?:а|у|ом|е)?',
  lilith: 'Лилит',
  node: '(?:[Сс]еверн|[Лл]унн)(?:ый|ого|ому|ым|ом) узе?л(?:а|у|ом|е)?',
  asc: 'Асцендент(?:а|у|ом|е)?',
  mc: 'Середин(?:а|ы|е|у|ой) неба',
}

const SIGN_IN = SIGNS.map((sign) => sign.in.replace(/^во? /, '')).join('|')
/** The place that may follow a point: «в Рыбах», «во Льве, в VII доме», «в 7-м доме». */
const PLACE = `(?:\\s(?:в|во)\\s(?:${SIGN_IN}))?(?:,?\\s(?:в\\s)?([IVX]{1,4}|\\d{1,2})(?:-?м)?\\sдоме)?`

/** «VII» or «7» → 7; anything else → 0. */
function houseNumber(value) {
  if (!value) return 0
  const number = /^\d+$/.test(value) ? Number(value) : ROMAN.indexOf(value) + 1
  return number >= 1 && number <= 12 ? number : 0
}

const houseTip = (number) => [`${ROMAN[number - 1]} дом`, `${HOUSE_THEMES[number - 1]}.`]

const ASPECT = 'Аспект — угол между двумя планетами: так они «разговаривают» друг с другом.'
const CROSS = {
  кардинальн: ['Кардинальный крест', 'ритм зачинателя: вы оживаете, когда начинаете новое.'],
  фиксированн: ['Фиксированный крест', 'ритм хранителя: ваша сила в постоянстве и в делах, доведённых до конца.'],
  мутабельн: ['Мутабельный крест', 'ритм гибкого путника: вы легко подстраиваетесь и меняетесь.'],
}

/**
 * The rules, in the order they win when two start at the same letter: the longer phrases first
 * («Фаза Луны» before «Луны», «кардинальный крест» before «крест»).
 */
const TERM_RULES = [
  ['[Фф]аз(?:а|ы|е|у|ой) Луны', () => ['Фаза Луны', 'как Солнце освещало Луну в день вашего рождения: ритм, в котором вы растёте.']],
  ['(?:под|над) горизонтом', () => ['Горизонт карты', 'линия Асцендента. Планеты под ним обращены к личному, над ним — к миру.']],
  ['(кардинальн|фиксированн|мутабельн)\\p{L}* крест\\p{L}*', (match) => CROSS[match[1].toLowerCase()]],
  ['крест(?:а|у|ом|е|ы)?', () => ['Крест', 'ритм, в котором вы действуете: кардинальный начинает, фиксированный удерживает, мутабельный меняется.']],
  ['стихи(?:я|и|ю|ей|й|ям|ями|ях)', () => ['Стихии', 'огонь, земля, воздух и вода: из чего «сделан» характер. Считаются по знакам десяти планет.']],
  ['стеллиум\\p{L}*', () => ['Стеллиум', 'три и больше планет в одном знаке или доме: здесь собрана главная сила карты.']],
  ['(?:управител\\p{L}*|планет\\p{L}*-хозяи?\\p{L}*)', () => ['Управитель', 'планета-хозяин знака. Хозяин восходящего знака ведёт всю карту.']],
  ['квадрат(?:а|у|ом|е|ы|ов|ами|ах)?', () => ['Квадрат', 'угол 90° между планетами: напряжение, из которого рождается рост.']],
  ['оппозици(?:я|и|ю|ей|ям|ями|ях)', () => ['Оппозиция', 'планеты друг напротив друга: две силы, которые учатся договариваться.']],
  ['трин(?:а|у|ом|е|ы|ов|ами|ах)?', () => ['Трин', 'угол 120°: лёгкая, природная гармония двух планет.']],
  ['секстил(?:ь|я|ю|ем|е|и|ей|ями|ях)', () => ['Секстиль', 'угол 60°: возможность, которая раскрывается от небольшого усилия.']],
  ['соединени(?:е|я|ю|ем|и|й|ями|ях)', () => ['Соединение', 'планеты стоят рядом, и их силы звучат как одна.']],
  ['аспект(?:а|у|ом|е|ы|ов|ами|ах)?', () => ASPECT.split(' — ')],
  ['(?:попятн|ретроградн)\\p{L}*', () => ['Попятная планета', 'с Земли она кажется идущей назад: её сила обращена внутрь, к пересмотру и глубине.']],
  ['транзит\\p{L}*', () => ['Транзит', 'планета сегодняшнего неба, которая касается точки вашей карты.']],
  ['Десцендент\\p{L}*', () => ['Десцендент', 'точка напротив Асцендента, начало VII дома: каких людей вы ищете рядом.']],
  ['([IVX]{1,4}) дом(?:а|у|ом|е)?', (match) => houseNumber(match[1]) && houseTip(houseNumber(match[1]))],
  ['(\\d{1,2})-?(?:й|м|го|му|ом)?\\sдом(?:а|у|ом|е)?', (match) => houseNumber(match[1]) && houseTip(houseNumber(match[1]))],
]

const MONTHS = 'января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря'
const MONTHS_IN = 'январе|феврале|марте|апреле|мае|июне|июле|августе|сентябре|октябре|ноябре|декабре'
const DATE_RULES = [
  `\\d{1,2}(?:\\s?[–—-]\\s?\\d{1,2}|\\s(?:по|и)\\s\\d{1,2})?\\s(?:${MONTHS})(?:\\s\\d{4}(?:\\sг(?:ода|\\.)?)?)?`,
  '\\d{1,2}\\.(?:0[1-9]|1[0-2])(?:\\.\\d{2,4})?',
  `(?:в|во)\\s(?:${MONTHS_IN}|понедельник|вторник|среду|четверг|пятницу|субботу|воскресенье)`,
]

const make = (source, flags = 'gu') => new RegExp(fence(source), flags)

const RULES = [
  ...TERM_RULES.slice(0, 1).map(([source, tip]) => ({ re: make(source), term: tip })),
  ...Object.entries(POINT_FORMS).map(([id, forms]) => ({ re: make(`${forms}${PLACE}`), point: id })),
  ...TERM_RULES.slice(1).map(([source, tip]) => ({ re: make(source, 'giu'), term: tip })),
]
const DATES = DATE_RULES.map((source) => ({ re: make(source, 'giu'), date: true }))

function token(rule, match) {
  const text = match[0]
  if (rule.date) return { kind: 'date', text }
  if (rule.point) {
    const [head, body] = POINT_TIPS[rule.point]
    const house = houseNumber(match[1])
    return {
      kind: 'point',
      text,
      id: rule.point,
      tip: { head, text: body, more: house ? houseTip(house).join(' — ') : '' },
    }
  }
  const tip = rule.term(match)
  if (!tip) return { kind: 'text', text }
  return { kind: 'term', text, tip: { head: tip[0], text: tip[1] } }
}

/**
 * The text cut into pieces: { kind: 'text' | 'point' | 'term' | 'date', text, id?, tip? }.
 * Each rule keeps its next match, so a long answer is read once per rule, not once per word.
 */
export function tokenize(text, { dates = false } = {}) {
  if (!text) return []
  const rules = dates ? [...RULES, ...DATES] : RULES
  const next = rules.map(() => undefined)
  const out = []
  let at = 0
  while (at < text.length) {
    let best = -1
    for (let index = 0; index < rules.length; index += 1) {
      let found = next[index]
      if (found === null) continue
      if (found === undefined || found.index < at) {
        rules[index].re.lastIndex = at
        found = rules[index].re.exec(text)
        next[index] = found
        if (!found) continue
      }
      if (best < 0 || found.index < next[best].index) best = index
    }
    if (best < 0) break
    const match = next[best]
    if (match.index > at) out.push({ kind: 'text', text: text.slice(at, match.index) })
    out.push(token(rules[best], match))
    at = match.index + match[0].length
  }
  if (at < text.length) out.push({ kind: 'text', text: text.slice(at) })
  return out
}

/** The one hint on the screen: whose it is, what it says and where it stands (viewport px). */
export const tip = reactive({ owner: 0, head: '', text: '', more: '', x: 0, y: 0, below: false })

let listening = false
let owners = 0
/** Each LiveText's own number, to tell whose hint is open. */
export const nextOwner = () => {
  owners += 1
  return owners
}
function hideAll() {
  tip.owner = 0
}

/** The hint beside a word: above it, or below when the word is near the top of the screen. */
export function showTip(owner, element, content) {
  const rect = element.getBoundingClientRect()
  const half = Math.min(150, window.innerWidth / 2 - 12)
  Object.assign(tip, {
    owner,
    head: content.head,
    text: content.text,
    more: content.more || '',
    x: Math.min(Math.max(rect.left + rect.width / 2, half + 12), window.innerWidth - half - 12),
    below: rect.top < 150,
  })
  tip.y = tip.below ? rect.bottom + 8 : rect.top - 8
  if (!listening) {
    listening = true
    // The page moved under the word: the hint would point at nothing.
    window.addEventListener('scroll', hideAll, { capture: true, passive: true })
    window.addEventListener('resize', hideAll, { passive: true })
  }
}

export function hideTip(owner) {
  if (tip.owner === owner) tip.owner = 0
}
