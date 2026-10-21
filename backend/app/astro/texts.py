"""Readings: the words that go with the chart.

Every text the site shows about a chart comes through an `Interpreter`. For now it is the
`StubInterpreter`: hand-written templates in the site's voice, formal «вы», no promises. An AI
provider later replaces this one class; the API, the cache and the pages stay as they are.
"""

import json
import re
from datetime import date

from app.astro import forecast_texts as F
from app.astro import natal_aspects as NA
from app.astro import natal_houses as H
from app.astro import natal_point_aspects as NPA
from app.astro import natal_points as NP
from app.astro import natal_signs as S
from app.astro import natal_texts as N
from app.astro import pair_aspects as PA
from app.astro import pair_overlays as PO
from app.astro import pair_texts as P
from app.astro import synastry
from app.astro import transit_fast as TF
from app.astro import transit_slow as TS
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
    "chiron": ("Хирон", "он", "ваша давняя рана и дар целителя: где болит и где вы умеете помогать другим"),
    "lilith": ("Лилит", "она", "ваша Чёрная Луна: непокорное желание и то, в чём вы не согласны подчиняться"),
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
    "neptune": "вашему Нептуну", "pluto": "вашему Плутону", "node": "вашему Лунному узлу", "chiron": "вашему Хирону", "lilith": "вашей Лилит",
    "asc": "вашему Асценденту", "mc": "вашей Середине неба",
}
_INSTRUMENTAL = {
    "sun": "вашим Солнцем", "moon": "вашей Луной", "mercury": "вашим Меркурием", "venus": "вашей Венерой",
    "mars": "вашим Марсом", "jupiter": "вашим Юпитером", "saturn": "вашим Сатурном", "uranus": "вашим Ураном",
    "neptune": "вашим Нептуном", "pluto": "вашим Плутоном", "node": "вашим Лунным узлом", "chiron": "вашим Хироном", "lilith": "вашей Лилит",
    "asc": "вашим Асцендентом", "mc": "вашей Серединой неба",
}
_ASPECT_PHRASE = {
    "conjunction": "соединяется с {instrumental}",
    "sextile": "в секстиле к {dative}",
    "square": "в квадрате к {dative}",
    "trine": "в трине к {dative}",
    "opposition": "в оппозиции к {dative}",
}
# A transit read by its pair: the fast planets in app.astro.transit_fast, the slow ones in transit_slow.
_TRANSIT = {**TF.FAST, **TS.SLOW}
# conjunction, trine and sextile, square and opposition.
_TRANSIT_GROUP = {"conjunction": 0, "trine": 1, "sextile": 1, "square": 2, "opposition": 2}


def transit_reading(transit: dict) -> str:
    """What this planet does to this point of the chart in this aspect."""
    return _TRANSIT[(transit["a"], transit["b"])][_TRANSIT_GROUP[transit["type"]]]


_OPEN = {
    "day": {
        "easy": (
            "Небо к вам расположено: многое сложится без нажима.",
            "Сегодня небо на вашей стороне: просьбы слышат, двери открываются, начатое идёт легко.",
            "Мягкий день: связи с вашей картой лёгкие, и то, что вы сделаете от души, получится.",
        ),
        "tense": (
            "Небо сегодня проверяет на прочность. Двигайтесь бережно, и напряжение станет опорой.",
            "День с характером: что-то пойдёт наперекор. Это не наказание, а подсказка, где нужна сила.",
            "Сегодня небо задаёт трудные вопросы. Не спешите с ответами — к вечеру многое прояснится.",
        ),
        "calm": (
            "Крупных событий небо не обещает: хороший день, чтобы делать своё в своём ритме.",
            "Тихий день: небо не вмешивается, и всё зависит от вашего выбора.",
            "Ровный фон без сильных влияний: удобно разобрать дела и отдохнуть.",
        ),
    },
    "week": {
        "easy": (
            "Неделя идёт с попутным ветром: начатое в эти дни легко набирает ход.",
            "Удачная неделя: небо поддерживает ваши планы, смело предлагайте и просите.",
            "Светлая неделя: связи с вашей картой лёгкие, хорошо для встреч, начинаний и радости.",
        ),
        "tense": (
            "Неделя просит собранности: не всё пойдёт по плану, зато станет ясно, что действительно важно.",
            "Неделя на прочность: будут споры и задержки. Держитесь главного, и неделя закалит, а не измотает.",
            "Непростая неделя: небо давит на чувствительные точки. Берегите силы и не решайте сгоряча.",
        ),
        "calm": (
            "Неделя ровная, без резких поворотов: удобное время довести начатое до конца.",
            "Спокойная неделя: небо не торопит, и можно идти своим темпом.",
            "Тихая неделя: хорошее время навести порядок в делах и в мыслях.",
        ),
    },
}
_CLOSE = {
    "easy": (
        "Вечером оглянитесь: то, что далось легко, стоит запомнить, это ваша сильная сторона.",
        "Поделитесь удачей: доброе слово или помощь сегодня вернутся вдвойне.",
        "Не растратьте лёгкость на мелочи: вложите её в то, что для вас по-настоящему важно.",
    ),
    "tense": (
        "Оставьте себе тихий час: после напряжения небо всегда возвращает равновесие.",
        "Будьте к себе мягче, чем обычно: трудный день не говорит о вас ничего плохого.",
        "Перед важным ответом сделайте паузу: то, что кажется срочным, часто может подождать.",
    ),
    "calm": (
        "Сделайте что-нибудь для себя: в ровные дни это особенно ценно.",
        "Используйте тишину: запишите планы или просто отдохните без чувства вины.",
        "Хороший момент для маленького доброго дела — себе или близким.",
    ),
}


def _varied(variants: tuple, start: str, shift: int = 0) -> str:
    """One of the variants, changing from day to day; a shift keeps the week from repeating the day."""
    return variants[(date.fromisoformat(start).toordinal() + shift) % len(variants)]


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

# «Марс партнёра».
_GENITIVE_PARTNER = "партнёра"
_OWN = {"он": "Ваш", "она": "Ваша", "оно": "Ваше"}
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
# The Sun and the Moon of the union by element: whether what the pair strives for and what it needs agree.
_UNION_ELEMENTS = {
    "same": "Солнце и Луна союза в одной стихии: то, к чему ваша пара стремится, и то, что ей нужно, совпадают.",
    "kindred": "Солнце и Луна союза в родственных стихиях: цели пары и её потребности поддерживают друг друга.",
    "apart": ("Солнце и Луна союза в разных стихиях: то, к чему пара стремится, и то, что ей нужно для покоя, "
              "порой спорят. Выход — не жертвовать одним ради другого, а давать место обоим."),
}


def _overlay_text(planets: list[dict], theirs: bool) -> str:
    """«Венера партнёра — в вашем V доме: одна из самых романтических связей…» for each planet."""
    lines = []
    for planet in planets:
        key, house = planet["id"], planet["house"]
        name = POINTS[key][0]
        if theirs:
            head = f"{name} {_GENITIVE_PARTNER} — в вашем {ROMAN[house - 1]} доме"
        else:
            head = f"{_OWN[POINTS[key][1]]} {name} — в {ROMAN[house - 1]} доме {_GENITIVE_PARTNER}"
        lines.append(f"{head}: {PO.OVERLAY[key][house - 1]}.")
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
    ("pluto", ("плутон",)), ("chiron", ("хирон",)), ("lilith", ("лилит", "чёрная луна", "черная луна", "чёрной лун", "черной лун")), ("asc", ("асцендент", "восходящ")),
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
                   and not {item["a"], item["b"]} & {"node", "chiron", "lilith"}), None)
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
        lines = [f"Сейчас {transit_phrase(transit)}.", transit_reading(transit)]
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

    version = 18

    def natal_item(self, point: str, sign: str, house: int | None, retro: bool = False) -> dict:
        name, pronoun, theme = POINTS[point]
        where, manner = SIGNS[sign]
        own = S.PLANET_SIGN.get(point, NP.POINT_SIGN.get(point, {})).get(sign)
        if own:
            essence, reading = own
        else:
            # The angles: their own words live in the portrait; here the sign's manner speaks.
            # «ваш восход: каким вас видят…» gives «Ваш восход — смело и прямо, с первого шага».
            essence = f"{_cap(re.split(r'[:,]', theme, maxsplit=1)[0])} — {manner}"
            reading = N.RISING[sign] if point == "asc" else f"{_cap(where)} {pronoun} звучит {manner}."
            reading += f" {_SIGN_VOICE[sign]}"
        parts = [_part("Тема", f"{name} — {theme}."), _part(f"{name} {where}", reading)]
        if house:
            own = H.PLANET_HOUSE.get(point)
            text = own[house - 1] if own else f"{_cap(HOUSES[house - 1])}: здесь эта сила проявляется ярче всего."
            parts.append(_part(f"Где проявляется · {ROMAN[house - 1]} дом", text))
        # The mean node always moves backwards: for it this says nothing.
        if retro and point != "node":
            parts.append(_part("Попятность", f"{_RETRO[pronoun]}: эта сила обращена внутрь и раскрывается не сразу, "
                                             "через пересмотр и возвращение."))
        return {"essence": f"{essence}.", "parts": parts}

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
        pair = frozenset({a, b})
        if own := NPA.POINT_ASPECT.get(pair):
            text = own[NPA.INDEX[len(own)][kind]]
            # The opposite end (the south node, the Descendant, the IC) is already named.
            return text if kind == "opposition" and len(own) == 4 else f"{text} {NA.KIND_NOTE[kind]}"
        own = NA.PAIR_ASPECT[pair]
        return f"{own[NA.GROUP[kind]]} {NA.KIND_NOTE[kind]}"

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
        for index, transit in enumerate(forecast["transits"][:3]):
            when = ""
            if transit.get("date"):
                when = f", точнее всего {_ON_WEEKDAY[date.fromisoformat(transit['date']).weekday()]}"
            lines = [f"{transit_phrase(transit)}{when}.", transit_reading(transit)]
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

        parts.append(_part("Совет", _varied(_CLOSE[tone], forecast["start"], period == "week")))
        return {"essence": _varied(_OPEN[period][tone], forecast["start"]), "parts": parts}

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

        points, named = dict(synastry.SPHERES), set()
        for sphere in pair["spheres"]:
            label, readings = P.SPHERES[sphere["id"]]
            text = readings[sphere["score"] - 1]
            # The strongest link of the sphere, so the reader sees where the score comes from: one with
            # both ends in it first, and never the one another sphere has already named.
            own = points[sphere["id"]]
            fresh = [aspect for aspect in pair.get("aspects", []) if pair_aspect_title(aspect) not in named]
            both = [aspect for aspect in fresh if aspect["a"] in own and aspect["b"] in own]
            either = [aspect for aspect in fresh if aspect["a"] in own or aspect["b"] in own]
            if main := (both or either or [None])[0]:
                title = pair_aspect_title(main)
                named.add(title)
                text += f" Сильнее всего эту сферу задаёт связь «{title}»."
            parts.append(_part(label, text))

        for aspect in pair["key"][:3]:
            parts.append(_part(pair_aspect_title(aspect), self.pair_aspect(aspect["a"], aspect["b"], aspect["type"])))

        overlays = pair["overlays"]
        if overlays["theirs_in_mine"]:
            parts.append(_part("Партнёр в ваших домах", _overlay_text(overlays["theirs_in_mine"], theirs=True)))
        if overlays["mine_in_theirs"]:
            parts.append(_part("Вы в домах партнёра", _overlay_text(overlays["mine_in_theirs"], theirs=False)))

        composite = pair.get("composite")
        if composite:
            text = P.COMPOSITE_SUN[composite["sun"]]
            if composite["moon"]:
                text += " " + P.COMPOSITE_MOON[composite["moon"]]
                sun, moon = element_of(composite["sun"]), element_of(composite["moon"])
                if sun == moon:
                    text += " " + _UNION_ELEMENTS["same"]
                elif {sun, moon} in _KINDRED:
                    text += " " + _UNION_ELEMENTS["kindred"]
                else:
                    text += " " + _UNION_ELEMENTS["apart"]
            parts.append(_part("Союз как целое", text))

        parts.append(_part("Совет", _PAIR_CLOSE[tone]))
        return {"essence": _PAIR_OPEN[tone], "parts": parts}

    def pair_aspect(self, a: str, b: str, kind: str) -> str:
        own = PA.PAIR_ASPECT[frozenset({a, b})]
        return f"{own[PA.GROUP[kind]]} {PA.KIND_NOTE[kind]}"

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
