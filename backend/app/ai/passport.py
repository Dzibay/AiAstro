"""The person's sky as the model reads it: a short Russian text of facts, computed by the site, not guessed.

The model is told to speak only of what stands here. So the chart, today's sky over it, the good
days of the month, the pairs and what the person has said before are all written out plainly.
"""

import re
from datetime import date

from app.astro import forecast_texts as F
from app.astro import pair_texts as PT
from app.astro.texts import HOUSES, POINTS, ROMAN, SIGNS, _event_line, transit_phrase

WEEKDAYS = ("понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье")
ASPECTS = {"conjunction": "соединение", "sextile": "секстиль", "square": "квадрат", "trine": "трин", "opposition": "оппозиция"}
ELEMENTS = {"fire": "огонь", "earth": "земля", "air": "воздух", "water": "вода"}
MODES = {"cardinal": "кардинальный", "fixed": "фиксированный", "mutable": "мутабельный"}
DAY_TONE = {"easy": "лёгкий, поддерживающий", "tense": "насыщенный, день роста", "calm": "ровный, спокойный"}
PAIR_TONE = {"easy": "лёгкая", "tense": "яркая, с искрой", "mixed": "тепло и огонь вместе", "calm": "тихая, растущая со временем"}
# How many natal aspects and month days go in: enough to answer, not so many that the prompt swells.
ASPECTS_SHOWN = 12
DAYS_SHOWN = 4

_NAME = re.compile(r"[^\w-]+")


def _date(iso: str, year: int) -> str:
    day = date.fromisoformat(iso)
    text = f"{day.day} {F.MONTHS[day.month - 1]}"
    return text if day.year == year else f"{text} {day.year}"


def _name(text: str) -> str:
    """A partner's name as the person typed it: letters only, short, never an instruction."""
    return " ".join(_NAME.sub(" ", text).replace("_", " ").split()[:2])[:30] or "партнёр"


def _point(point: dict, time_known: bool) -> str:
    name = POINTS[point["id"]][0]
    line = f"{name} {SIGNS[point['sign']][0]}, {int(point['deg'])}°"
    if point.get("house"):
        line += f", в {ROMAN[point['house'] - 1]} доме ({HOUSES[point['house'] - 1]})"
    if point.get("retro") and point["id"] not in ("node", "lilith"):
        line += ", ретроградн."
    if point.get("approx") or (point["id"] == "moon" and not time_known):
        line += " — приблизительно: время рождения неизвестно"
    return line


def _chart(chart: dict) -> list[str]:
    time_known = chart.get("time_known")
    lines = ["НАТАЛЬНАЯ КАРТА"]
    if time_known and chart.get("angles"):
        lines.append("Время рождения известно: дома и Асцендент точны.")
    else:
        lines.append("Время рождения неизвестно: домов и Асцендента нет, Луна приблизительна. "
                     "Не говорите о домах; предложите указать время рождения в данных, чтобы ответы стали точнее.")
    lines += [f"- {_point(point, time_known)}" for point in chart["points"]]
    if chart.get("angles"):
        for angle in ("asc", "mc"):
            spot = chart["angles"][angle]
            lines.append(f"- {POINTS[angle][0]} {SIGNS[spot['sign']][0]}, {int(spot['deg'])}°")
    found = chart.get("aspects") or []
    if found:
        lines.append("Аспекты карты (самые точные первыми): " + "; ".join(
            f"{POINTS[aspect['a']][0]} — {ASPECTS[aspect['type']]} — {POINTS[aspect['b']][0]}"
            for aspect in found[:ASPECTS_SHOWN] if aspect["type"] in ASPECTS
        ) + ".")
    balance = chart.get("balance")
    if balance:
        lines.append("Стихии: " + ", ".join(f"{ELEMENTS[key]} {value}" for key, value in balance["elements"].items())
                     + ". Кресты: " + ", ".join(f"{MODES[key]} {value}" for key, value in balance["modes"].items()) + ".")
    return lines


def _today(today: dict) -> list[str]:
    year = date.fromisoformat(today["start"]).year
    lines = ["НЕБО СЕГОДНЯ", f"Тон дня: {DAY_TONE.get(today.get('tone'), 'ровный')}."]
    moon = today.get("moon")
    if moon:
        line = f"Луна {SIGNS[moon['sign']][0]}"
        if moon.get("house"):
            line += f", проходит ваш {ROMAN[moon['house'] - 1]} дом"
        name, meaning = F.PHASE[moon["phase"]]
        line += f"; фаза — {name}: {meaning}"
        if moon.get("next"):
            line += f" {F.LUNATION[moon['next']['kind']]} — {_date(moon['next']['date'], year)}."
        lines.append(line)
    for transit in today.get("transits") or []:
        line = f"- Транзит: {transit_phrase(transit)} ({'поддерживает' if transit['lean'] >= 0 else 'зовёт расти'})"
        span = transit.get("span")
        if span:
            line += f", с {_date(span['from'], year)} по {_date(span['to'], year)}"
        lines.append(line + ".")
    if today.get("retro"):
        lines.append("Ретроградны: " + ", ".join(POINTS[key][0] for key in today["retro"]) + ".")
    for sphere, tone in (today.get("spheres") or {}).items():
        lines.append(f"- {F.SPHERE_NAMES[sphere]}: {F.SPHERE_TONE[sphere][tone]}.")
    events = today.get("events") or []
    if events:
        lines.append("События неба: " + "; ".join(_event_line(event) for event in events) + ".")
    return lines


def _month(month: list[dict]) -> list[str]:
    if not month:
        return []
    year = date.fromisoformat(month[0]["date"]).year
    lines = ["БЛИЖАЙШИЕ 30 ДНЕЙ: дни, когда небо поддерживает сферу"]
    for sphere, name in F.SPHERE_NAMES.items():
        days = [day for day in month if (day.get("spheres") or {}).get(sphere) == "easy"][:DAYS_SHOWN]
        if days:
            lines.append(f"- {name}: " + ", ".join(
                f"{_date(day['date'], year)} ({WEEKDAYS[date.fromisoformat(day['date']).weekday()]})" for day in days
            ) + ".")
    best = sorted((day for day in month if day["tone"] == "easy"), key=lambda day: -day["score"])[:DAYS_SHOWN]
    if best:
        lines.append("Самые лёгкие дни в целом: " + ", ".join(_date(day["date"], year) for day in sorted(best, key=lambda day: day["date"])) + ".")
    events = [(day["date"], event) for day in month for event in day.get("events") or [] if event["kind"] != "ingress"]
    if events:
        lines.append("События месяца: " + "; ".join(f"{_date(when, year)} — {_event_line(event)}" for when, event in events[:6]) + ".")
    return lines


def _pairs(partners: list[dict]) -> list[str]:
    if not partners:
        return ["ПАРЫ: человек пока не добавил партнёров. Совместимость — в разделе «Пары»."]
    lines = ["ПАРЫ ЧЕЛОВЕКА (оценка сфер от 1 до 5; имена — как их ввёл человек)"]
    for partner in partners:
        spheres = ", ".join(f"{PT.SPHERES[sphere['id']][0]} {sphere['score']}" for sphere in partner.get("spheres") or []
                            if sphere["id"] in PT.SPHERES)
        lines.append(f"- «{_name(partner['name'])}»: связь {PAIR_TONE.get(partner['tone'], 'живая')}; {spheres}.")
    return lines


def build(chart: dict, context: dict, memory: list[str], today: date) -> str:
    """The whole passport; `context` is chat._context: {today, month, partners}."""
    lines = [f"Сегодня {today.day} {F.MONTHS[today.month - 1]} {today.year}, {WEEKDAYS[today.weekday()]}.", ""]
    lines += _chart(chart) + [""]
    if context.get("today"):
        lines += _today(context["today"]) + [""]
    month = _month(context.get("month") or [])
    if month:
        lines += month + [""]
    lines += _pairs(context.get("partners") or [])
    if memory:
        lines += ["", "ЧТО ЧЕЛОВЕК РАССКАЗЫВАЛ О СЕБЕ РАНЬШЕ"] + [f"- {fact}" for fact in memory]
    return "\n".join(lines)
