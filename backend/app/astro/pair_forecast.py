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
    "tense": "Вы и {name} сегодня под глубоким небом: день зовёт к бережности друг к другу. Говорите мягко, дайте главному созреть — и вечер принесёт тепло.",
    "calm": "Вы и {name} сегодня под тихим небом: день спокойный и ровный — хорошо просто побыть рядом.",
}
_APART = {
    ("easy", "tense"): "У вас день лёгкий, а партнёру сегодня нужна мягкость: ваше спокойствие — лучшая опора для пары.",
    ("tense", "easy"): "У партнёра день лёгкий, а вам сегодня нужна мягкость: обопритесь на партнёра и поделитесь тем, что на душе.",
    ("calm", "tense"): "Партнёру сегодня особенно нужна теплота: просто будьте рядом — этого достаточно.",
    ("tense", "calm"): "Вам сегодня особенно нужна теплота: расскажите партнёру, что у вас на душе, — и получите поддержку.",
}
_LOVE = {
    "easy": "В чувствах у обоих мягкий день: хороший вечер для нежности и долгого разговора.",
    "tense": "Чувства сегодня тоньше обычного: самое время для простого тепла и добрых слов.",
}


# What a planet of the day brings to a link it lights: (when the link sounds warmer, when it is strained).
_LIT_PLANET = {
    "moon": ("настроения совпадают, хорошо провести вечер вместе",
             "настроения у каждого свои — ключ в том, чтобы мягко поинтересоваться, как прошёл день у партнёра"),
    "sun": ("вы замечаете друг друга, хорошо сказать о важном",
            "каждому хочется быть услышанным — ключ в том, чтобы щедро уступить в мелочи"),
    "mercury": ("разговор клеится, удачно обсуждать планы",
                "словам нужна точность — ключ в том, чтобы переспрашивать и слушать до конца"),
    "venus": ("много нежности, хорошо для свидания и подарка",
              "обоим хочется больше тепла — ключ в том, чтобы подарить его первыми"),
    "mars": ("много желания и общей энергии, хорошо сделать что-то вместе",
             "между вами много огня — ключ в том, чтобы направить его в общее дело"),
    "jupiter": ("щедрый день для пары, хорошо мечтать и планировать",
                "мечты летят высоко — ключ в том, чтобы выбрать из них одну и договориться о шагах"),
    "saturn": ("день для серьёзного разговора и общих обязательств",
               "паре нужна надёжность — ключ в том, чтобы проявить заботу делом и сказать тёплое слово"),
    "uranus": ("неожиданный, живой день, хорошо попробовать новое вдвоём",
               "каждому хочется простора — ключ в том, чтобы подарить его друг другу"),
    "neptune": ("тонкое понимание без слов, хорошо для романтики",
                "чувства тонкие и мечтательные — ключ в том, чтобы проговаривать простое"),
    "pluto": ("глубокая близость, хорошо для откровенного разговора",
              "чувства глубоки и сильны — ключ в том, чтобы доверять и давать свободу"),
}


def _lit_line(item: dict) -> str:
    warm, strained = _LIT_PLANET[item["planet"]]
    if item["lean"] > 0:
        return f"{item['planet_name']} сегодня касается обоих концов связи «{item['title']}»: она звучит ярче — {warm}."
    return f"{item['planet_name']} сегодня касается обоих концов связи «{item['title']}»: ей сегодня нужна забота — {strained}."


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
