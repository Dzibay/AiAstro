"""Readings: the words that go with the chart.

Every text the site shows about a chart comes through an `Interpreter`. For now it is the
`StubInterpreter`: hand-written templates in the site's voice, formal «вы», no promises. An AI
provider later replaces this one class; the API, the cache and the pages stay as they are.
"""

import json
import re
from datetime import date

from app.astro import forecast_texts as F
from app.astro import natal_texts as N
from app.astro import pair_texts as P
from app.astro.portrait import element_of

# Roman numerals for the houses, as astrologers write them.
ROMAN = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII")

# name, the pronoun it takes, and what it stands for in a person's chart.
POINTS = {
    "sun": ("Солнце", "оно", "ваша сердцевина: воля, жизненная сила и то, ради чего вы светите"),
    "moon": ("Луна", "она", "ваши чувства и привычки, то, что успокаивает и даёт ощущение дома"),
    "mercury": ("Меркурий", "он", "ваш ум и речь: как вы думаете, учитесь и объясняете"),
    "venus": ("Венера", "она", "ваша любовь и вкус: что вы находите красивым и как привязываетесь"),
    "mars": ("Марс", "он", "ваша энергия и смелость: как вы добиваетесь и как защищаетесь"),
    "jupiter": ("Юпитер", "он", "ваша вера и щедрость: где жизнь расширяется и дарит удачу"),
    "saturn": ("Сатурн", "он", "ваша опора и ответственность: где нужно время, труд и терпение"),
    "uranus": ("Уран", "он", "ваша свобода: где вы ищете своё и меняете правила"),
    "neptune": ("Нептун", "он", "ваши мечты и чуткость: где граница между вами и миром тоньше"),
    "pluto": ("Плутон", "он", "ваша глубинная сила: где вы проходите перемены и выходите другим"),
    "node": ("Лунный узел", "он", "направление роста: то, к чему вы учитесь идти в этой жизни"),
    "asc": ("Асцендент", "он", "ваш восход: каким вас видят прежде слов и как вы входите в новое"),
    "mc": ("Середина неба", "она", "вершина карты: призвание и то, к чему вы идёте на виду у всех"),
}

# The sign in the prepositional case, and the manner it lends to whatever stands in it.
SIGNS = {
    "aries": ("в Овне", "смело и прямо, с первого шага"),
    "taurus": ("в Тельце", "неторопливо и прочно, с любовью к осязаемому"),
    "gemini": ("в Близнецах", "легко и любопытно, сразу на нескольких языках"),
    "cancer": ("в Раке", "бережно, через заботу и память"),
    "leo": ("во Льве", "щедро и открыто, как полдень"),
    "virgo": ("в Деве", "точно и внимательно, с любовью к мелочам"),
    "libra": ("в Весах", "мягко, в поисках равновесия и красоты"),
    "scorpio": ("в Скорпионе", "глубоко и сосредоточенно, без полутонов"),
    "sagittarius": ("в Стрельце", "широко, с верой в дальнюю дорогу"),
    "capricorn": ("в Козероге", "сдержанно и надёжно, с расчётом на годы"),
    "aquarius": ("в Водолее", "свободно и по-своему, на шаг впереди"),
    "pisces": ("в Рыбах", "тонко, на грани сна и сочувствия"),
}

# What a sign is like, whatever stands in it: the «как звучит» of a reading.
_SIGN_VOICE = {
    "aries": "Овен — знак начала: сила здесь не ждёт разрешения, загорается от одной искры и любит первый шаг больше последнего.",
    "taurus": "Телец — знак земли и тела: сила здесь копится медленно, держится долго и верит тому, что можно потрогать.",
    "gemini": "Близнецы — знак воздуха и слова: сила здесь живёт в разговоре, вопросах и переменах, ей тесно в одном русле.",
    "cancer": "Рак — знак воды и памяти: сила здесь бережёт своих, помнит пережитое и раскрывается там, где безопасно.",
    "leo": "Лев — знак солнца и сцены: сила здесь хочет быть увиденной, греет щедро и ждёт ответного тепла.",
    "virgo": "Дева — знак ремесла: сила здесь проявляется в точности, пользе и заботе о том, чего другие не замечают.",
    "libra": "Весы — знак меры: сила здесь ищет согласия, красоты и честного равновесия между «я» и «мы».",
    "scorpio": "Скорпион — знак глубины: сила здесь не терпит поверхностного, проходит через перемены и выходит обновлённой.",
    "sagittarius": "Стрелец — знак дальней дороги: сила здесь ищет смысл, горизонт и веру, ради которой стоит идти.",
    "capricorn": "Козерог — знак вершины: сила здесь строит медленно и надёжно, ей важны ответственность и плоды на годы.",
    "aquarius": "Водолей — знак свободы: сила здесь идёт своим путём, дружит с идеями и не боится быть непохожей.",
    "pisces": "Рыбы — знак океана: сила здесь тонко чувствует, сострадает и легко уходит в мечту и музыку.",
}

HOUSES = (
    "ваш облик и первое впечатление",
    "деньги, вещи и чувство опоры",
    "речь, учёба, близкие люди и короткие дороги",
    "дом, корни и семья",
    "радость, творчество, влюблённость и дети",
    "работа изо дня в день, режим и здоровье",
    "партнёрство и брак, все, кто стоит напротив вас",
    "близость, общие ресурсы и перемены",
    "смыслы, дальние страны и учителя",
    "призвание, карьера и место в мире",
    "друзья, единомышленники и надежды",
    "уединение, тайное и то, что лежит за кулисами",
)

# The past tense agrees with the pronoun: «он шёл», «она шла».
_RETRO = {
    "он": "В момент вашего рождения он шёл попятно",
    "она": "В момент вашего рождения она шла попятно",
    "оно": "В момент вашего рождения оно шло попятно",
}


def item_title(point: str, sign: str, house: int | None) -> str:
    """«Венера в Скорпионе, в VIII доме»."""
    title = f"{POINTS[point][0]} {SIGNS[sign][0]}"
    return f"{title}, в {ROMAN[house - 1]} доме" if house else title


# ---- Forecast ----

# «в квадрате к вашей Венере», «соединяется с вашей Венерой».
_DATIVE = {
    "sun": "вашему Солнцу", "moon": "вашей Луне", "mercury": "вашему Меркурию", "venus": "вашей Венере",
    "mars": "вашему Марсу", "jupiter": "вашему Юпитеру", "saturn": "вашему Сатурну", "uranus": "вашему Урану",
    "neptune": "вашему Нептуну", "pluto": "вашему Плутону", "node": "вашему Лунному узлу",
    "asc": "вашему Асценденту", "mc": "вашей Середине неба",
}
_INSTRUMENTAL = {
    "sun": "вашим Солнцем", "moon": "вашей Луной", "mercury": "вашим Меркурием", "venus": "вашей Венерой",
    "mars": "вашим Марсом", "jupiter": "вашим Юпитером", "saturn": "вашим Сатурном", "uranus": "вашим Ураном",
    "neptune": "вашим Нептуном", "pluto": "вашим Плутоном", "node": "вашим Лунным узлом",
    "asc": "вашим Асцендентом", "mc": "вашей Серединой неба",
}
_ASPECT_PHRASE = {
    "conjunction": "соединяется с {instrumental}",
    "sextile": "в секстиле к {dative}",
    "square": "в квадрате к {dative}",
    "trine": "в трине к {dative}",
    "opposition": "в оппозиции к {dative}",
}
# What a transit to this natal point stirs, in the accusative: «трогает любовь, вкус и деньги».
_TOUCHES = {
    "sun": "вашу волю и жизненную силу", "moon": "чувства и ощущение дома", "mercury": "мысли, слова и переписку",
    "venus": "любовь, вкус и деньги", "mars": "энергию и решимость", "jupiter": "веру и планы на рост",
    "saturn": "обязательства и границы", "uranus": "тягу к свободе и переменам", "neptune": "мечты и интуицию",
    "pluto": "глубинные перемены", "node": "ваш путь роста", "asc": "то, каким вас видят",
    "mc": "работу и репутацию",
}
# The advice of a transiting planet: (when it comes easy, when it comes hard).
_ADVICE = {
    "moon": ("Доверьтесь настроению: сегодня оно подсказывает верно.",
             "Настроение может качнуться, не принимайте его за окончательный ответ."),
    "sun": ("Хороший час, чтобы показаться и заявить о своём.",
            "Не тратьте силы на доказательства, сохраните их для главного."),
    "mercury": ("Слова найдутся сами: пишите, договаривайтесь, спрашивайте.",
                "Перечитайте написанное дважды и переспросите, если что-то неясно."),
    "venus": ("Позвольте себе красоту и тепло, они сейчас к месту.",
              "Не покупайте утешение: желание может оказаться сильнее нужды."),
    "mars": ("Сил хватит на то, что давно откладывалось.",
             "Спешка обернётся спором: сосчитайте до десяти, прежде чем ответить."),
    "jupiter": ("Дверь приоткрыта: смело просите и предлагайте.",
                "Обещания опережают силы, берите ровно столько, сколько унесёте."),
    "saturn": ("Труд, вложенный сейчас, останется надолго.",
               "Медленно не значит плохо: проверка временем только укрепляет."),
    "uranus": ("Неожиданный поворот окажется к лучшему.",
               "Перемены торопят, оставьте себе запасной выход."),
    "neptune": ("Слушайте интуицию: она сейчас тоньше логики.",
                "В тумане не подписывают: сначала проверьте факты."),
    "pluto": ("Глубокий разговор может многое расставить по местам.",
              "Не держитесь за то, что отжило: отпустить тоже сила."),
}
_OPEN = {
    "day": {
        "easy": "Небо к вам расположено: многое сложится без нажима.",
        "tense": "Небо сегодня проверяет на прочность. Двигайтесь бережно, и напряжение станет опорой.",
        "calm": "Крупных событий небо не обещает: хороший день, чтобы делать своё в своём ритме.",
    },
    "week": {
        "easy": "Неделя идёт с попутным ветром: начатое в эти дни легко набирает ход.",
        "tense": "Неделя просит собранности: не всё пойдёт по плану, зато станет ясно, что действительно важно.",
        "calm": "Неделя ровная, без резких поворотов: удобное время довести начатое до конца.",
    },
}
_CLOSE = {
    "easy": "Вечером оглянитесь: то, что далось легко, стоит запомнить, это ваша сильная сторона.",
    "tense": "Оставьте себе тихий час: после напряжения небо всегда возвращает равновесие.",
    "calm": "Сделайте что-нибудь для себя: в ровные дни это особенно ценно.",
}
_TITLES = {
    "day": {
        "easy": ("Попутный ветер", "День открытых дверей", "Мягкий свет"),
        "tense": ("День на прочность", "Ветер навстречу", "Время собраться"),
        "calm": ("Ровное небо", "Тихий ход", "День без спешки"),
    },
    "week": {
        "easy": ("Неделя попутного ветра", "Неделя открытых дверей", "Светлая неделя"),
        "tense": ("Неделя на прочность", "Неделя встречного ветра", "Неделя, чтобы собраться"),
        "calm": ("Ровная неделя", "Неделя тихого хода", "Неделя без спешки"),
    },
}
WEEKDAYS = ("понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье")
# «точнее всего во вторник».
_ON_WEEKDAY = ("в понедельник", "во вторник", "в среду", "в четверг", "в пятницу", "в субботу", "в воскресенье")


def forecast_title(forecast: dict) -> str:
    """The heading of the day or the week: by its tone, varied from day to day."""
    variants = _TITLES[forecast["period"]][forecast["tone"]]
    return variants[date.fromisoformat(forecast["start"]).toordinal() % len(variants)]


def _day_month(iso: str, year: int | None = None) -> str:
    """«26 октября», with the year when it is not `year`."""
    day = date.fromisoformat(iso)
    text = f"{day.day} {F.MONTHS[day.month - 1]}"
    return text if year in (None, day.year) else f"{text} {day.year} года"


def _in_days(count: int) -> str:
    if count == 1:
        return "завтра"
    if count % 10 == 1 and count % 100 != 11:
        word = "день"
    elif count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        word = "дня"
    else:
        word = "дней"
    return f"через {count} {word}"


def _span_line(span: dict, start: date) -> str:
    """«Это надолго: с 5 октября по 22 февраля 2027 года» — a slow transit stands for months."""
    begun, ends = date.fromisoformat(span["from"]), date.fromisoformat(span["to"])
    if (ends - begun).days < 21:
        return f"Он продлится примерно до {_day_month(span['to'], start.year)}."
    head = "Это надолго" if (ends - begun).days >= 60 else "Это на несколько недель"
    if begun >= start:
        return f"{head}: с {_day_month(span['from'], start.year)} по {_day_month(span['to'], start.year)}."
    return f"{head}: транзит идёт с {_day_month(span['from'], start.year)} и продлится до {_day_month(span['to'], start.year)}."


def _event_line(event: dict) -> str:
    """«полнолуние в Тельце: кульминация и ясность»."""
    sign = SIGNS[event["sign"]][0]
    name = POINTS[event["planet"]][0]
    line = F.EVENT[event["kind"]].format(sign=sign, name=name, into=F.SIGN_GENITIVE[event["sign"]])
    if event["kind"] == "ingress":
        line += f": {F.INGRESS_THEME[event['planet']]}"
    return line


def transit_phrase(transit: dict) -> str:
    """«Марс в квадрате к вашей Венере»."""
    phrase = _ASPECT_PHRASE[transit["type"]].format(dative=_DATIVE[transit["b"]], instrumental=_INSTRUMENTAL[transit["b"]])
    return f"{POINTS[transit['a']][0]} {phrase}"


# ---- Synastry ----

# What a point brings into a pair: «с вашей стороны здесь нежность и вкус, со стороны партнёра — желание».
_PAIR_THEMES = {
    "sun": "воля и самоощущение", "moon": "чувства и быт", "mercury": "разговоры и понимание",
    "venus": "нежность и вкус", "mars": "желание и решимость", "jupiter": "щедрость и вера",
    "saturn": "верность и границы", "uranus": "свобода и перемены", "neptune": "мечты и чуткость",
    "pluto": "глубина и сила", "asc": "первое впечатление", "mc": "цели и призвание",
}
# «Марс партнёра».
_GENITIVE_PARTNER = "партнёра"
_OWN = {"он": "Ваш", "она": "Ваша", "оно": "Ваше"}
_PAIR_ASPECT = {
    "conjunction": "Соединение сплавляет их в одно: в этой точке вы чувствуете друг друга сильнее всего.",
    "trine": "Трин даёт им течь легко: здесь вам не нужно стараться, чтобы понимать друг друга.",
    "sextile": "Секстиль приоткрывает дверь: стоит сделать шаг навстречу, и всё сложится.",
    "square": "Квадрат сталкивает их: отсюда искры и споры, но и рост, если вы готовы слушать.",
    "opposition": "Оппозиция ставит их друг напротив друга: вы притягиваетесь, как противоположности, и учитесь равновесию.",
}
# The tone of the pair in one phrase: the free part of the reading.
PAIR_PHRASES = {
    "easy": "Вам легко рядом: ваши небеса говорят на одном языке.",
    "tense": "Между вами искра: притяжение и споры здесь идут рука об руку.",
    "mixed": "Союз двух сил: тепло и напряжение здесь рядом, и оба делают вас сильнее.",
    "calm": "Тихая связь: небо не торопит, и близость растёт исподволь.",
}
_PAIR_OPEN = {
    "easy": "Ваши карты отзываются друг другу мягко: большинство связей между ними лёгкие, и рядом друг с другом вам спокойно.",
    "tense": "Ваши карты сцеплены крепко и с напряжением: этот союз будит, испытывает и не даёт заскучать.",
    "mixed": "В ваших картах есть и лёгкие связи, и напряжённые: здесь хватает и тепла, и вызова, и оба вам нужны.",
    "calm": "Тесных связей между вашими картами немного: этот союз не вспыхивает сразу, он складывается из времени и выбора.",
}
_PAIR_CLOSE = {
    "easy": "Берегите эту лёгкость: ей нужно внимание, иначе она становится привычкой.",
    "tense": "Договаривайтесь о правилах спора заранее: тогда напряжение будет работать на вас, а не против.",
    "mixed": "Опирайтесь на лёгкие связи, когда напряжённые дают о себе знать: в вашей паре есть и то и другое.",
    "calm": "Дайте союзу время и общие дела: так тихие связи становятся прочными.",
}
_ELEMENT_NAMES = {"fire": "огонь", "earth": "земля", "air": "воздух", "water": "вода"}
_KINDRED = ({"fire", "air"}, {"earth", "water"})


def _overlay_text(planets: list[dict], theirs: bool) -> str:
    """«Солнце и Луна партнёра — в вашем III доме: вам есть о чём говорить… Солнце освещает…»."""
    by_house: dict[int, list[str]] = {}
    for planet in planets:
        by_house.setdefault(planet["house"], []).append(planet["id"])
    lines = []
    for house, ids in by_house.items():
        names = _joined([POINTS[key][0] for key in ids])
        if theirs:
            head = f"{names} {_GENITIVE_PARTNER} — в вашем {ROMAN[house - 1]} доме"
        else:
            own = "Ваши" if len(ids) > 1 else _OWN[POINTS[ids[0]][1]]
            head = f"{own} {names} — в {ROMAN[house - 1]} доме {_GENITIVE_PARTNER}"
        lines.append(f"{head}: {P.OVERLAY_HOUSE[house - 1]}.")
        lines += [f"{POINTS[key][0]} {P.OVERLAY_PLANET[key]}." for key in ids]
    return " ".join(lines)


def pair_phrase(pair: dict) -> str:
    return PAIR_PHRASES[pair["tone"]]


def pair_aspect_title(aspect: dict) -> str:
    """«Ваша Венера и Марс партнёра в трине»."""
    mine, pronoun, _ = POINTS[aspect["a"]]
    theirs = POINTS[aspect["b"]][0]
    where = {"conjunction": "в соединении", "sextile": "в секстиле", "square": "в квадрате",
             "trine": "в трине", "opposition": "в оппозиции"}[aspect["type"]]
    return f"{_OWN[pronoun]} {mine} и {theirs} {_GENITIVE_PARTNER} {where}"


def _joined(words: list[str]) -> str:
    return words[0] if len(words) == 1 else f"{', '.join(words[:-1])} и {words[-1]}"


# ---- Chat ----

# What a question is about: the stems that give it away, the points of the chart that answer it,
# and the advice the answer ends with. The first topic whose stem is found wins.
_TOPICS = (
    ("love", ("любов", "любв", "люблю", "любит", "любим", "отношен", "партнёр", "партнер", "брак", "свидан", "влюб", "семейн"),
     ("venus", "moon", "mars"),
     "В любви ваша карта просит не угадывать, а говорить: то, что названо вслух, становится ближе."),
    ("money", ("деньг", "денег", "доход", "финанс", "заработ", "зарплат", "покупк", "трат"),
     ("venus", "jupiter", "saturn"),
     "С деньгами вам помогает то же, что и во всём остальном: ясное «зачем» прежде, чем «сколько»."),
    ("work", ("работ", "карьер", "призван", "професс", "начальн", "коллег", "бизнес", "должност", "дело", "дела "),
     ("saturn", "mc", "sun"),
     "В делах опирайтесь на то, что строится медленно: ваше небо вознаграждает терпение больше, чем рывок."),
    ("feelings", ("чувств", "настроен", "эмоци", "тревог", "грус", "устал", "спокой", "дом", "семь", "мам"),
     ("moon", "venus", "neptune"),
     "Берегите то, что вас успокаивает: в этой карте силы возвращаются через тишину и привычный ритм."),
    ("talk", ("разговор", "говор", "общен", "слов", "учёб", "учеб", "экзамен", "переговор", "письм"),
     ("mercury", "moon", "venus"),
     "Для важного разговора выбирайте час, когда вам самим спокойно: тогда слова находятся сами."),
    ("energy", ("энерг", " сил", "спорт", "злост", "злюсь", "ссор", "конфликт", "решимост", "смелост"),
     ("mars", "sun", "saturn"),
     "Давайте энергии выход раньше, чем она найдёт его сама: движение, честное «нет», законченное дело."),
    ("luck", ("удач", "везен", " рост", "путешеств", "переезд", "поездк", "мечт", "возможност"),
     ("jupiter", "sun", "node"),
     "Удача в вашей карте любит щедрость: делитесь тем, что умеете, и двери откроются сами."),
    ("change", ("перемен", "свобод", "уйти", "уход", "решени", "выбор", "кризис"),
     ("uranus", "pluto", "saturn"),
     "Перемены легче, когда у них есть опора: решите, что остаётся неизменным, и меняйте остальное."),
    ("path", ("смысл", "предназнач", "путь", "кто я", "судьб", "зачем", "цель", "цели"),
     ("node", "sun", "mc"),
     "Ваш путь виден не сразу, а по шагам: замечайте, где вам интересно, — там он и проходит."),
)
# A planet named in the question answers it whatever the topic; the node before the Moon,
# since «лунный узел» holds both.
_NAMED = (
    ("node", ("узел", "узл")), ("sun", ("солнц",)), ("moon", ("лун",)), ("mercury", ("меркури",)),
    ("venus", ("венер",)), ("mars", ("марс",)), ("jupiter", ("юпитер",)), ("saturn", ("сатурн",)),
    ("uranus", ("уран ", "урана", "урану", "ураном", "уране")), ("neptune", ("нептун",)),
    ("pluto", ("плутон",)), ("asc", ("асцендент", "восходящ")),
)
_WHEN = ("когда", "какой день", "в какой день", "день недели", "дни недели", "в какие дни")
_GREETING = ("привет", "здравств", "добрый день", "добрый вечер", "доброе утро")
# The planet that keeps each day of the week, Monday first: the Moon, Mars, Mercury, Jupiter, Venus, Saturn, the Sun.
_DAY_OF = {"moon": 0, "mars": 1, "mercury": 2, "jupiter": 3, "venus": 4, "saturn": 5, "sun": 6}
# «его хранит Марс» for a Tuesday, «её хранит Меркурий» for a Wednesday.
_DAY_PRONOUN = ("его", "его", "её", "его", "её", "её", "его")
# «Его поддерживает трин с вашей Луной».
_HIM = {"он": "Его", "она": "Её", "оно": "Его"}
_ASPECT_NAMES = {"sextile": "секстиль", "square": "квадрат", "trine": "трин", "opposition": "оппозиция"}
_MY = {"он": "мой", "она": "моя", "оно": "моё"}


_PUNCTUATION = re.compile(r"[^\w\s]")


def _words(text: str) -> str:
    """The question in lower case, its punctuation turned to spaces: « сатурн о работе »."""
    return " " + _PUNCTUATION.sub(" ", text.lower().replace("ё", "е")) + " "


def _find(chart: dict, point: str) -> dict | None:
    if point in ("asc", "mc"):
        return {"id": point, **chart["angles"][point]} if chart.get("angles") else None
    return next((item for item in chart["points"] if item["id"] == point), None)


def _subject(question: str, chart: dict) -> tuple[str | None, list[str], bool]:
    """The topic of a question, the points that answer it (the named planet first), and whether one was named."""
    text = _words(question)
    named = [point for point, stems in _NAMED if any(stem in text for stem in stems)]
    topic = next((entry for entry in _TOPICS if any(stem in text for stem in entry[1])), None)
    points = [*named, *(topic[2] if topic else ("sun", "moon", "asc"))]
    seen = []
    for point in points:
        if point not in seen and _find(chart, point):
            seen.append(point)
    return (topic[0] if topic else None), seen, bool(named)


def _aspect_line(chart: dict, point: str) -> str | None:
    """The tightest aspect of the point inside the chart, in one sentence."""
    _, pronoun, _ = POINTS[point]
    aspect = next((item for item in chart.get("aspects", []) if point in (item["a"], item["b"])
                   and "node" not in (item["a"], item["b"])), None)
    if aspect is None:
        return None
    other = aspect["b"] if aspect["a"] == point else aspect["a"]
    with_other = _INSTRUMENTAL[other]
    if aspect["type"] == "conjunction":
        return f"{pronoun.capitalize()} в соединении с {with_other}: эти две силы действуют в вас заодно."
    name = _ASPECT_NAMES[aspect["type"]]
    if aspect["type"] in ("trine", "sextile"):
        return f"{_HIM[pronoun]} поддерживает {name} с {with_other}: здесь силы помогают друг другу."
    return (f"{_HIM[pronoun]} испытывает {name} с {with_other}: отсюда внутреннее напряжение, "
            "которое становится ростом, если его не прятать.")


# The sphere of the day (app.astro.forecast.SPHERES) a topic of the chat belongs to.
_CHAT_SPHERE = {"love": "love", "feelings": "love", "money": "work", "work": "work", "talk": "talk", "energy": "energy",
                "luck": "work"}


def _now_line(today: dict | None, points: list[str], sphere: str | None) -> str | None:
    """Today's transit to the asked point, else how the day sounds for the asked sphere."""
    if not today:
        return None
    transit = next((t for t in today["transits"] if t["b"] in points), None)
    if transit:
        lines = [f"Сейчас {transit_phrase(transit)}.", _ADVICE[transit["a"]][0 if transit["lean"] > 0 else 1]]
        if transit.get("span"):
            lines.append(_span_line(transit["span"], date.fromisoformat(today["start"])))
        return " ".join(lines)
    if sphere and today.get("spheres"):
        return f"Сегодня в сфере «{F.SPHERE_NAMES[sphere]}» {F.SPHERE_TONE[sphere][today['spheres'][sphere]]}."
    return None


def chat_suggestions(chart: dict) -> list[str]:
    """Three or four questions the person might ask first, in their own voice, about their own chart."""
    suggestions = []
    saturn = _find(chart, "saturn")
    if saturn:
        suggestions.append("Что говорит мой Сатурн о работе?")
    venus = _find(chart, "venus")
    if venus:
        suggestions.append(f"Как моя Венера {SIGNS[venus['sign']][0]} влияет на любовь?")
    moon = _find(chart, "moon")
    if moon:
        suggestions.append(f"Что моя Луна {SIGNS[moon['sign']][0]} говорит о чувствах?")
    suggestions.append("Какой день недели лучше для важного разговора?")
    return suggestions


# ---- Reading ----

def _part(label: str, text: str) -> dict:
    return {"label": label, "text": text}


def _cap(text: str) -> str:
    return text[0].upper() + text[1:]


def reading_text(reading: dict) -> str:
    """A reading as plain paragraphs: for whoever reads the conversation as text (an AI provider)."""
    lines = [reading["essence"]] if reading["essence"] else []
    lines += [f"{part['label']}. {part['text']}" if part["label"] else part["text"] for part in reading["parts"]]
    return "\n\n".join(lines)


def as_reading(text: str) -> dict:
    """A stored reading back from its JSON; a plain text of before becomes paragraphs without labels."""
    try:
        reading = json.loads(text)
    except ValueError:
        reading = None
    if isinstance(reading, dict) and "parts" in reading:
        return reading
    return {"essence": "", "parts": [_part("", paragraph) for paragraph in text.split("\n\n") if paragraph]}


class Interpreter:
    """What the site asks of whoever writes the readings.

    Each method returns a reading: {essence, parts: [{label, text}]}. The essence is one line, the
    heart of it; the parts are short theses under small labels («Тема», «Как звучит», «Совет»).
    """

    # Raised whenever the texts change, so the cached readings are written again.
    version = 0

    def natal_item(self, point: str, sign: str, house: int | None, retro: bool = False) -> dict:
        raise NotImplementedError

    def portrait(self, facts: dict) -> dict:
        """The chart read as a whole (app.astro.portrait.facts); without «Небосвод» only its first part is shown."""
        raise NotImplementedError

    def natal_aspect(self, a: str, b: str, kind: str) -> str:
        """One aspect inside the person's chart, in a short paragraph."""
        raise NotImplementedError

    def forecast(self, forecast: dict) -> dict:
        """The reading of a day or a week (app.astro.forecast.build); without «Небосвод» only its first part is shown."""
        raise NotImplementedError

    def synastry(self, pair: dict) -> dict:
        """The full reading of a pair (app.astro.synastry.build); before the purchase only its first part is shown."""
        raise NotImplementedError

    def pair_aspect(self, a: str, b: str, kind: str) -> str:
        """One aspect between two charts (`a` is the person's, `b` the partner's), in a short paragraph."""
        raise NotImplementedError

    def chat(self, history: list[dict], chart: dict, context: dict | None = None) -> dict:
        """The answer to the last message of `history` ({role: user | astrologer, text}, oldest first).

        `context` is what is known besides the chart: {today: forecast.build of the day, month:
        forecast.month, partners: [{name, tone, spheres}]}; any of it may be missing.
        """
        raise NotImplementedError


class StubInterpreter(Interpreter):
    """Templates until the AI is connected. The chat answers with facts of the chart, not with wit."""

    version = 7

    def natal_item(self, point: str, sign: str, house: int | None, retro: bool = False) -> dict:
        name, pronoun, theme = POINTS[point]
        where, manner = SIGNS[sign]
        # «ваша любовь и вкус: что вы находите красивым…» gives «Ваша любовь и вкус — глубоко и сосредоточенно».
        head = re.split(r"[:,]", theme, maxsplit=1)[0]
        parts = [
            _part("Тема", f"{name} — {theme}."),
            _part("Как звучит", f"{_cap(where)} {pronoun} звучит {manner}. {_SIGN_VOICE[sign]}"),
        ]
        if house:
            parts.append(_part(f"Где проявляется · {ROMAN[house - 1]} дом",
                               f"{_cap(HOUSES[house - 1])}: здесь эта сила проявляется ярче всего."))
        # The mean node always moves backwards: for it this says nothing.
        if retro and point != "node":
            parts.append(_part("Попятность", f"{_RETRO[pronoun]}: эта сила обращена внутрь и раскрывается не сразу, "
                                             "через пересмотр и возвращение."))
        return {"essence": f"{_cap(head)} — {manner}.", "parts": parts}

    def portrait(self, facts: dict) -> dict:
        sun, moon = facts["sun"], facts["moon"]
        core = [f"Солнце {SIGNS[sun][0]} — сердцевина вашей карты. {_SIGN_VOICE[sun]}"]
        if moon:
            sun_element, moon_element = element_of(sun), element_of(moon)
            if sun_element == moon_element:
                relation = "same"
            elif {sun_element, moon_element} in _KINDRED:
                relation = "kindred"
            else:
                relation = "foreign"
            core.append(N.SUN_MOON[relation].format(
                element=N.ELEMENT_NAMES[sun_element],
                sun_element=N.ELEMENT_NAMES[sun_element],
                moon_element=N.ELEMENT_NAMES[moon_element],
            ))
        parts = [_part("Ядро", " ".join(core))]

        ruler = facts["ruler"]
        if facts["asc"] and ruler:
            name, pronoun, _ = POINTS[ruler["id"]]
            template = {"он": N.RULER, "она": N.RULER_FEMININE, "оно": N.RULER_NEUTER}[pronoun]
            rising = [N.RISING[facts["asc"]], template.format(rising=SIGNS[facts["asc"]][0], ruler=name)]
            where = f"{_cap(pronoun)} стоит {SIGNS[ruler['sign']][0]}"
            if ruler["house"]:
                where += f", в {ROMAN[ruler['house'] - 1]} доме — {HOUSES[ruler['house'] - 1]}: туда и тянется ваша жизнь"
            rising.append(f"{where}.")
            parts.append(_part("Восход", " ".join(rising)))

        pair = facts.get("element_pair") or []
        if facts["element"]:
            temperament = [N.ELEMENT_LEAD[facts["element"]]]
        elif pair:
            temperament = [N.ELEMENTS_PAIR.format(a=N.ELEMENT_NAMES[pair[0]], b=N.ELEMENT_NAMES[pair[1]],
                                                  first=N.ELEMENT_GIFT[pair[0]], second=N.ELEMENT_GIFT[pair[1]])]
        else:
            temperament = [N.ELEMENTS_EVEN]
        temperament += [N.ELEMENT_MISSING[element] for element in facts["missing"]]
        temperament.append(N.MODE_LEAD[facts["mode"]] if facts["mode"] else N.MODES_EVEN)
        parts.append(_part("Темперамент", " ".join(temperament)))

        accents = []
        for group in facts["stellium_signs"]:
            sign = group["sign"]
            template = N.STELLIUM_SUN if sign == sun else N.STELLIUM_SIGN
            accents.append(template.format(
                names=_joined([POINTS[point][0] for point in group["points"]]), where=SIGNS[sign][0], voice=_SIGN_VOICE[sign],
            ))
        for index, group in enumerate(facts["stellium_houses"]):
            accents.append((N.STELLIUM_HOUSE_MORE if index else N.STELLIUM_HOUSE).format(
                names=_joined([POINTS[point][0] for point in group["points"]]),
                house=ROMAN[group["house"] - 1],
                theme=HOUSES[group["house"] - 1],
            ))
        for entry in facts["on_angles"]:
            name, _, theme = POINTS[entry["id"]]
            accents.append(N.ON_ANGLE[entry["angle"]].format(name=name, theme=re.split(r"[:,]", theme, maxsplit=1)[0]))
        for lean in (facts["hemispheres"] or {}).values():
            if lean:
                accents.append(N.HEMISPHERE[lean])
        if accents:
            parts.append(_part("Акценты", " ".join(accents)))

        if facts["tension"]:
            aspect = facts["tension"]
            parts.append(_part("Главное напряжение", self.natal_aspect(aspect["a"], aspect["b"], aspect["type"])))
        if facts["gift"]:
            aspect = facts["gift"]
            parts.append(_part("Главный дар", self.natal_aspect(aspect["a"], aspect["b"], aspect["type"])))
        if facts["phase"]:
            parts.append(_part("Луна при рождении", N.PHASE[facts["phase"]]))

        node = facts["node"]
        path = [N.NODE_SIGN[node["sign"]]]
        if node["house"]:
            path.append(f"Узел стоит в {ROMAN[node['house'] - 1]} доме: {HOUSES[node['house'] - 1]} — сфера, где этот рост случается.")
        parts.append(_part("Путь", " ".join(path)))
        if not facts["element"] and pair:
            essence = N.ESSENCE_PAIR.format(a=N.ELEMENT_NAMES[pair[0]], b=N.ELEMENT_NAMES[pair[1]])
        else:
            essence = N.ESSENCE[facts["element"]]
        return {"essence": f"{essence}.", "parts": parts}

    def natal_aspect(self, a: str, b: str, kind: str) -> str:
        angle = next((point for point in (a, b) if point in ("asc", "mc")), None)
        if angle:
            other = b if angle == a else a
            theme = N.ANGLE_PAIR[angle].format(name=POINTS[other][0])
        else:
            theme = N.NATAL_PAIRS.get(frozenset({a, b}))
            if theme is None:
                first, second = (re.split(r"[:,]", POINTS[point][2], maxsplit=1)[0] for point in (a, b))
                theme = f"{POINTS[a][0]} и {POINTS[b][0]}: {first} и {second}."
        return " ".join([theme, N.ASPECT_DYNAMIC[kind], N.ASPECT_ADVICE[kind]])

    def forecast(self, forecast: dict) -> dict:
        period, tone = forecast["period"], forecast["tone"]
        parts = []
        if period == "day":
            moon = forecast["moon"]
            line = f"Сегодня Луна {SIGNS[moon['sign']][0]}"
            if moon["house"]:
                line += f" и проходит ваш {ROMAN[moon['house'] - 1]} дом: {HOUSES[moon['house'] - 1]}"
            text = f"{line}. День звучит {SIGNS[moon['sign']][1]}."
            if moon.get("phase"):
                name, meaning = F.PHASE[moon["phase"]]
                text += f" Фаза — {name}. {meaning}"
            upcoming = moon.get("next")
            if upcoming and upcoming["in"] > 0:
                text += f" {F.LUNATION[upcoming['kind']]} — {_in_days(upcoming['in'])}, {_day_month(upcoming['date'])}."
            parts.append(_part("Луна", text))
            if forecast.get("spheres"):
                parts.append(_part("Сферы дня", " ".join(
                    f"{F.SPHERE_NAMES[key]}: {F.SPHERE_TONE[key][value]}." for key, value in forecast["spheres"].items())))
        else:
            names: dict[str, list[str]] = {}
            for day in forecast["days"]:
                names.setdefault(day["tone"], []).append(WEEKDAYS[date.fromisoformat(day["date"]).weekday()])
            days = []
            # A list of five days or more says nothing a tone of the week does not.
            if 0 < len(names.get("easy", [])) <= 4:
                verb = "пройдёт" if len(names["easy"]) == 1 else "пройдут"
                days.append(f"Легче всего {verb} {_joined(names['easy'])}.")
            if 0 < len(names.get("tense", [])) <= 4:
                verb = "потребует" if len(names["tense"]) == 1 else "потребуют"
                days.append(f"Больше бережности {verb} {_joined(names['tense'])}.")
            if days:
                parts.append(_part("Дни недели", " ".join(days)))
            best = forecast.get("best") or {}
            if best:
                parts.append(_part("Лучшие дни", " ".join(
                    f"{_cap(F.SPHERE_FOR[key])} — {WEEKDAYS[date.fromisoformat(day).weekday()]}."
                    for key, day in best.items())))

        start = date.fromisoformat(forecast["start"])
        advised = set()
        for index, transit in enumerate(forecast["transits"][:3]):
            when = ""
            if transit.get("date"):
                when = f", точнее всего {_ON_WEEKDAY[date.fromisoformat(transit['date']).weekday()]}"
            lines = [
                f"{transit_phrase(transit)}{when}.",
                f"Этот транзит трогает {_TOUCHES[transit['b']]}.",
            ]
            # One planet gives its advice once, however many points it touches.
            if transit["a"] not in advised:
                lines.append(_ADVICE[transit["a"]][0 if transit["lean"] > 0 else 1])
                advised.add(transit["a"])
            if transit.get("span"):
                lines.append(_span_line(transit["span"], start))
            parts.append(_part(("Главный транзит", "И ещё", "Фоном")[index], " ".join(lines)))
        if not forecast["transits"]:
            parts.append(_part("Транзиты", "Тесных транзитов к вашей карте нет: небо оставляет вам свободу, "
                                           "распорядитесь ею по-своему."))

        events = forecast.get("events") or []
        if events:
            lines = []
            for event in events:
                line = _event_line(event)
                if event.get("date") and period == "week":
                    line = f"{_cap(_ON_WEEKDAY[date.fromisoformat(event['date']).weekday()])} {line}"
                lines.append(_cap(line) + ".")
            parts.append(_part("Небо " + ("дня" if period == "day" else "недели"), " ".join(lines)))

        retro = forecast.get("retro") or []
        if retro:
            lines = [F.RETRO[key] for key in retro if key in F.RETRO]
            slow = [POINTS[key][0] for key in retro if key not in F.RETRO]
            if slow:
                template = F.RETRO_SLOW_ONE if len(slow) == 1 else F.RETRO_SLOW
                lines.append(template.format(names=_joined(slow), also=" тоже" if lines else ""))
            parts.append(_part("Попятные планеты", " ".join(lines)))

        parts.append(_part("Совет", _CLOSE[tone]))
        return {"essence": _OPEN[period][tone], "parts": parts}

    def synastry(self, pair: dict) -> dict:
        tone = pair["tone"]
        mine, theirs = pair["elements"]["mine"], pair["elements"]["theirs"]
        if mine == theirs:
            elements = f"У вас обоих преобладает {_ELEMENT_NAMES[mine]}: вы понимаете друг друга без перевода."
        elif {mine, theirs} in _KINDRED:
            elements = (f"У вас преобладает {_ELEMENT_NAMES[mine]}, у партнёра — {_ELEMENT_NAMES[theirs]}: "
                        "стихии, которые питают друг друга.")
        else:
            elements = (f"У вас преобладает {_ELEMENT_NAMES[mine]}, у партнёра — {_ELEMENT_NAMES[theirs]}: "
                        "разный темп, и в этом ваша возможность научиться друг у друга.")
        parts = [_part("Стихии", elements)]

        for sphere in pair["spheres"]:
            label, variants = P.SPHERES[sphere["id"]]
            band = 0 if sphere["score"] <= 2 else 1 if sphere["score"] == 3 else 2
            parts.append(_part(label, variants[band]))

        for aspect in pair["key"][:3]:
            parts.append(_part(pair_aspect_title(aspect), self.pair_aspect(aspect["a"], aspect["b"], aspect["type"])))

        overlays = pair["overlays"]
        if overlays["theirs_in_mine"]:
            parts.append(_part("Партнёр в ваших домах", _overlay_text(overlays["theirs_in_mine"], theirs=True)))
        if overlays["mine_in_theirs"]:
            parts.append(_part("Вы в домах партнёра", _overlay_text(overlays["mine_in_theirs"], theirs=False)))

        composite = pair.get("composite")
        if composite:
            sign, manner = SIGNS[composite["sun"]]
            text = P.COMPOSITE_SUN.format(sign=sign, manner=manner)
            if composite["moon"]:
                sign, manner = SIGNS[composite["moon"]]
                text += " " + P.COMPOSITE_MOON.format(sign=sign, manner=manner)
            parts.append(_part("Союз как целое", text))

        parts.append(_part("Совет", _PAIR_CLOSE[tone]))
        return {"essence": _PAIR_OPEN[tone], "parts": parts}

    def pair_aspect(self, a: str, b: str, kind: str) -> str:
        meaning = P.PAIRS.get(frozenset({a, b}))
        if meaning is None:
            meaning = f"С вашей стороны здесь {_PAIR_THEMES[a]}, со стороны партнёра — {_PAIR_THEMES[b]}."
        # The same pair of points always gets the same words: the choice rests on their names alone.
        variants = P.DYNAMIC[kind]
        return f"{meaning} {variants[sum(map(ord, a + b)) % len(variants)]}"

    def chat(self, history: list[dict], chart: dict, context: dict | None = None) -> dict:
        question = _words(history[-1]["text"])
        context = context or {}
        topic, points, named = _subject(question, chart)

        point = points[0]
        found = _find(chart, point)
        name, pronoun, theme = POINTS[point]
        where, manner = SIGNS[found["sign"]]
        fact = f"{_OWN[pronoun]} {name} стоит {where}"
        if found.get("house"):
            fact += f", в {ROMAN[found['house'] - 1]} доме"
        essence = f"{fact}."
        if any(word in question for word in _GREETING):
            essence = f"Здравствуйте. {essence}"

        meaning = [f"{name} — {theme}; здесь {pronoun} звучит {manner}."]
        if found.get("house"):
            meaning.append(f"Этот дом — {HOUSES[found['house'] - 1]}: туда и направлена эта сила.")
        parts = [_part("Что это значит", " ".join(meaning))]

        aspect = _aspect_line(chart, point)
        if aspect:
            parts.append(_part("Аспект", aspect))
        # Without a topic the answer reads the chart's core: the second point adds a line of its own.
        if topic is None and not named and len(points) > 1:
            other = _find(chart, points[1])
            other_name, other_pronoun, other_theme = POINTS[points[1]]
            parts.append(_part("И ещё", f"{_OWN[other_pronoun]} {other_name} {SIGNS[other['sign']][0]} — {other_theme}."))
        sphere = _CHAT_SPHERE.get(topic)
        now = _now_line(context.get("today"), points[:2], sphere)
        if now:
            parts.append(_part("Сейчас в небе", now))
        when = []
        days = [day for day in context.get("month") or [] if sphere and (day.get("spheres") or {}).get(sphere) == "easy"]
        if days and (sphere or any(word in question for word in _WHEN)):
            start = date.fromisoformat(context["month"][0]["date"]).year
            dates = [_day_month(day["date"], start) for day in days[:3]]
            when.append(f"Ближайшие дни, когда небо поддержит это: {_joined(dates)}.")
        if any(word in question for word in _WHEN):
            ruler = next((item for item in points if item in _DAY_OF), "sun")
            day = _DAY_OF[ruler]
            when.append(f"Из дней недели вам ближе всего {WEEKDAYS[day]}: "
                        f"{_DAY_PRONOUN[day]} хранит {POINTS[ruler][0]}, и {_ON_WEEKDAY[day]} "
                        "эта сила звучит в вас громче.")
        if when:
            parts.append(_part("Когда", " ".join(when)))
        partners = context.get("partners") or []
        if topic == "love" and partners:
            # Pairs of one tone share one phrase: «Мира и Лев — союз двух сил…».
            tones: dict[str, list[str]] = {}
            for partner in partners:
                tones.setdefault(partner["tone"], []).append(partner["name"])
            lines = [f"{_joined(names)} — {PAIR_PHRASES[tone][0].lower()}{PAIR_PHRASES[tone][1:]}"
                     for tone, names in tones.items()]
            parts.append(_part("Ваши пары", " ".join(lines) + " Подробно — в разборе каждой пары."))
        if topic:
            parts.append(_part("Совет", next(entry[3] for entry in _TOPICS if entry[0] == topic)))

        if not chart.get("time_known"):
            parts.append(_part("Время рождения", "Оно не указано, поэтому домов в ответе нет: "
                                                 "уточните его в данных рождения, и разговор станет точнее."))
        return {"essence": essence, "parts": parts}


interpreter: Interpreter = StubInterpreter()
