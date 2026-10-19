"""Readings: the words that go with the chart.

Every text the site shows about a chart comes through an `Interpreter`. For now it is the
`StubInterpreter`: hand-written templates in the site's voice, formal «вы», no promises. An AI
provider later replaces this one class; the API, the cache and the pages stay as they are.
"""

from datetime import date

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


class Interpreter:
    """What the site asks of whoever writes the readings. Each method returns plain text."""

    # Raised whenever the texts change, so the cached readings are written again.
    version = 0

    def natal_item(self, point: str, sign: str, house: int | None, retro: bool = False) -> str:
        raise NotImplementedError

    def forecast(self, forecast: dict) -> str:
        """The text of a day or a week (app.astro.forecast.build); paragraphs are split by blank lines."""
        raise NotImplementedError

    def synastry(self, pair: dict) -> str:
        """The full reading of a pair (app.astro.synastry.build); paragraphs are split by blank lines."""
        raise NotImplementedError

    def chat(self, history: list[dict], chart: dict) -> str:
        raise NotImplementedError


class StubInterpreter(Interpreter):
    """Templates until the AI is connected. The chat comes with its section."""

    version = 1

    def natal_item(self, point: str, sign: str, house: int | None, retro: bool = False) -> str:
        name, pronoun, theme = POINTS[point]
        where, manner = SIGNS[sign]
        parts = [
            f"{name} — {theme}.",
            f"{where[0].upper()}{where[1:]} {pronoun} звучит {manner}.",
        ]
        if house:
            parts.append(f"{ROMAN[house - 1]} дом — {HOUSES[house - 1]}: здесь эта сила проявляется ярче всего.")
        # The mean node always moves backwards: for it this says nothing.
        if retro and point != "node":
            parts.append(f"{_RETRO[pronoun]}: эта сила обращена внутрь и раскрывается не сразу, через пересмотр и возвращение.")
        return " ".join(parts)

    def forecast(self, forecast: dict) -> str:
        period, tone = forecast["period"], forecast["tone"]
        first = []
        if period == "day":
            moon = forecast["moon"]
            line = f"Сегодня Луна {SIGNS[moon['sign']][0]}"
            if moon["house"]:
                line += f" и проходит ваш {ROMAN[moon['house'] - 1]} дом: {HOUSES[moon['house'] - 1]}"
            first += [f"{line}.", f"День звучит {SIGNS[moon['sign']][1]}.", _OPEN["day"][tone]]
        else:
            first.append(_OPEN["week"][tone])
            names: dict[str, list[str]] = {}
            for day in forecast["days"]:
                names.setdefault(day["tone"], []).append(WEEKDAYS[date.fromisoformat(day["date"]).weekday()])
            # A list of five days or more says nothing a tone of the week does not.
            if 0 < len(names.get("easy", [])) <= 4:
                verb = "пройдёт" if len(names["easy"]) == 1 else "пройдут"
                first.append(f"Легче всего {verb} {_joined(names['easy'])}.")
            if 0 < len(names.get("tense", [])) <= 4:
                verb = "потребует" if len(names["tense"]) == 1 else "потребуют"
                first.append(f"Больше бережности {verb} {_joined(names['tense'])}.")
        paragraphs = [" ".join(first)]

        for index, transit in enumerate(forecast["transits"][:2]):
            when = ""
            if transit.get("date"):
                when = f", точнее всего {_ON_WEEKDAY[date.fromisoformat(transit['date']).weekday()]}"
            paragraphs.append(" ".join([
                f"{'Главный транзит' if index == 0 else 'И ещё'}: {transit_phrase(transit)}{when}.",
                f"Этот транзит трогает {_TOUCHES[transit['b']]}.",
                _ADVICE[transit["a"]][0 if transit["lean"] > 0 else 1],
            ]))
        if not forecast["transits"]:
            paragraphs.append("Тесных транзитов к вашей карте нет: небо оставляет вам свободу, распорядитесь ею по-своему.")

        paragraphs.append(_CLOSE[tone])
        return "\n\n".join(paragraphs)

    def synastry(self, pair: dict) -> str:
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
        paragraphs = [f"{_PAIR_OPEN[tone]} {elements}"]
        for aspect in pair["key"][:3]:
            paragraphs.append(" ".join([
                f"{pair_aspect_title(aspect)}.",
                f"С вашей стороны здесь {_PAIR_THEMES[aspect['a']]}, со стороны партнёра — {_PAIR_THEMES[aspect['b']]}.",
                _PAIR_ASPECT[aspect["type"]],
            ]))
        paragraphs.append(_PAIR_CLOSE[tone])
        return "\n\n".join(paragraphs)


interpreter: Interpreter = StubInterpreter()
