"""The pair's day: the same sky over two charts.

Each chart gets its own day (forecast._day): its tone and its spheres. What belongs to the pair
are the lit links: a planet of the day touching both ends of a key link between the charts
(the partner's Mars and your Venus in a trine, and today's Moon on both) sets that link sounding.
The pair's tone is the two days together, with the lit links leaning it their way.
"""

from datetime import date, timedelta

from app.astro import forecast, synastry
from app.astro.texts import POINTS, WEEKDAYS, _ON_WEEKDAY, pair_aspect_title, transit_phrase

WEEK = 7
# How much a lit link sways the pair's day, against an ordinary transit of one of the two.
LIT_WEIGHT = 0.6
KEY_TRANSITS = 2


def _lit(links: list[dict], mine: dict, theirs: dict) -> list[dict]:
    """The key links of the pair that a planet of the day touches at both ends."""
    lit = []
    for link in links:
        for one in mine["transits"]:
            if one["b"] != link["a"]:
                continue
            other = next((t for t in theirs["transits"] if t["a"] == one["a"] and t["b"] == link["b"]), None)
            if other is None:
                continue
            lit.append({
                "planet": one["a"],
                "link": {key: link[key] for key in ("a", "b", "type")},
                "title": pair_aspect_title(link),
                "lean": round((one["lean"] + other["lean"]) / 2, 2),
                "strength": round(one["strength"] + other["strength"], 3),
            })
    lit.sort(key=lambda item: -item["strength"])
    return lit


def _pair_day(links: list[dict], mine_chart: dict, theirs_chart: dict, targets: tuple, day: date, tz: str) -> dict:
    mine = forecast._day(mine_chart, targets[0], day, tz)
    theirs = forecast._day(theirs_chart, targets[1], day, tz)
    lit = _lit(links, mine, theirs)
    score = (mine["score"] + theirs["score"]) / 2 + LIT_WEIGHT * sum(item["lean"] for item in lit)
    return {"date": day, "mine": mine, "theirs": theirs, "lit": lit, "score": score, "tone": forecast._tone(score)}


def build(mine_chart: dict, theirs_chart: dict, today: date, tz: str) -> dict:
    """Today in full and the week ahead in tones: {date, tone, mine, theirs, lit, transits, week}."""
    links = synastry.build(mine_chart, theirs_chart)["key"]
    targets = (forecast._targets(mine_chart), forecast._targets(theirs_chart))
    days = [_pair_day(links, mine_chart, theirs_chart, targets, today + timedelta(days=step), tz) for step in range(WEEK)]
    first = days[0]

    def side(day: dict) -> dict:
        return {"tone": forecast._tone(day["score"]), "love": day["spheres"]["love"]["tone"]}

    top = sorted(first["mine"]["transits"], key=lambda t: -t["strength"])[:KEY_TRANSITS]
    return {
        "date": today.isoformat(),
        "tone": first["tone"],
        "mine": side(first["mine"]),
        "theirs": side(first["theirs"]),
        "lit": [{**item, "planet_name": POINTS[item["planet"]][0]} for item in first["lit"][:3]],
        "transits": [{"a": t["a"], "b": t["b"], "type": t["type"], "title": transit_phrase(t)} for t in top],
        "week": [
            {"date": day["date"].isoformat(), "weekday": WEEKDAYS[day["date"].weekday()], "tone": day["tone"]}
            for day in days
        ],
    }


# ---- The words ----

_OPEN = {
    "easy": "Вы и {name} сегодня под лёгким небом: день сам подталкивает друг к другу — хорошо говорить о важном и строить общие планы.",
    "tense": "Вы и {name} сегодня под напряжённым небом: чужую усталость легко принять на свой счёт. Говорите мягче и не решайте главное наспех.",
    "calm": "Вы и {name} сегодня под тихим небом: день не толкает ни к спорам, ни к признаниям — хорошо просто побыть рядом.",
}
_APART = {
    ("easy", "tense"): "У вас день лёгкий, у партнёра — напряжённый: ваше спокойствие сегодня — лучшая опора для пары.",
    ("tense", "easy"): "У партнёра день лёгкий, у вас — напряжённый: можно опереться на партнёра и не держать всё в себе.",
}
_LOVE = {
    "easy": "В чувствах у обоих мягкий день: хороший вечер для нежности и долгого разговора.",
    "tense": "Чувства сегодня ранимее обычного: меньше упрёков, больше простого тепла.",
}


def _lit_line(item: dict) -> str:
    sound = "звучит ярче и теплее" if item["lean"] > 0 else "натянута — берегите её и не тяните за неё"
    return f"{item['planet_name']} сегодня касается обоих концов связи «{item['title']}»: эта связь {sound}."


def text(data: dict, name: str) -> str:
    """The pair's day in a few sentences, to «вы», with the partner named as the person calls them."""
    lines = [_OPEN[data["tone"]].format(name=name)]
    apart = _APART.get((data["mine"]["tone"], data["theirs"]["tone"]))
    if apart:
        lines.append(apart)
    lines += [_lit_line(item) for item in data["lit"][:2]]
    loves = {data["mine"]["love"], data["theirs"]["love"]}
    if "tense" in loves:
        lines.append(_LOVE["tense"])
    elif loves == {"easy"}:
        lines.append(_LOVE["easy"])
    ahead = data["week"][1:]
    best = next((day for day in ahead if day["tone"] == "easy"), None)
    if best is not None and data["tone"] != "easy":
        lines.append(f"Самый лёгкий день впереди для вас двоих — {_ON_WEEKDAY[WEEKDAYS.index(best['weekday'])]}.")
    return " ".join(lines)
