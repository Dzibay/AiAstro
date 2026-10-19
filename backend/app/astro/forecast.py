"""Transits: the sky of a given day laid over the natal chart, for a day or for a week.

Each day is read at local noon. A transit counts only while it is close (a third of the natal
orbs): a wide one says little about one particular day. Every transit leans the day one way or
the other, the slow planets more than the fast ones, the tight ones more than the loose; the sum
gives the day its tone: easy, tense or calm.
"""

from datetime import date, datetime, time, timedelta, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo

from app.astro import aspects, houses
from app.astro.chart import SIGNS
from app.astro.ephemeris import PLANETS, sky_at, wrap

PERIODS = ("day", "week")
ORB_SCALE = 0.35
WEEK_DAYS = 7
MONTH_DAYS = 30
# The key transits shown as chips under the text.
KEY_TRANSITS = 4

# How much a transit matters, for picking the key ones: the slow planets press longer and harder.
WEIGHT = {
    "moon": 0.8, "sun": 1.0, "mercury": 0.9, "venus": 1.0, "mars": 1.1,
    "jupiter": 1.3, "saturn": 1.4, "uranus": 1.2, "neptune": 1.1, "pluto": 1.2,
}
# How much it sways one particular day: the slow ones stand for weeks, so they are the background
# and the fast ones make the difference between Tuesday and Wednesday.
PRESSURE = {
    "moon": 1.0, "sun": 0.9, "mercury": 0.8, "venus": 0.9, "mars": 1.0,
    "jupiter": 0.5, "saturn": 0.6, "uranus": 0.4, "neptune": 0.4, "pluto": 0.4,
}
# A conjunction takes the colour of whoever is in it.
HARD = {"mars", "saturn", "pluto"}
SOFT = {"venus", "jupiter"}
_TONE_LIMIT = 0.8


@lru_cache(maxsize=512)
def _sky_at_noon(day: date, tz: str) -> dict:
    moment = datetime.combine(day, time(12, 0), tzinfo=ZoneInfo(tz)).astimezone(timezone.utc)
    return sky_at(moment)["points"]


def _targets(chart: dict) -> list[dict]:
    """The natal points a transit can touch; a Moon guessed without the time cannot be one."""
    found = [{"id": point["id"], "lon": point["lon"], "speed": 0.0} for point in chart["points"] if not point.get("approx")]
    if chart["angles"]:
        found += [{"id": key, "lon": angle["lon"], "speed": 0.0} for key, angle in chart["angles"].items()]
    return found


def valence(aspect: dict) -> float:
    """+1 for the easy aspects, -1 for the tense ones; a conjunction leans with its planets."""
    if aspect["type"] in ("sextile", "trine"):
        return 1.0
    if aspect["type"] in ("square", "opposition"):
        return -1.0
    pair = {aspect["a"], aspect["b"]}
    if pair & HARD:
        return -0.6
    return 1.0 if pair & SOFT else 0.4


def _closeness(aspect: dict) -> float:
    return 0.4 + 0.6 * max(0.0, 1 - aspect["orb"] / aspects.limit(aspect["type"], aspect["a"], aspect["b"], ORB_SCALE))


def _tone(score: float) -> str:
    if score > _TONE_LIMIT:
        return "easy"
    return "tense" if score < -_TONE_LIMIT else "calm"


def _day(chart: dict, targets: list[dict], day: date, tz: str) -> dict:
    sky = _sky_at_noon(day, tz)
    moving = [{"id": key, "lon": sky[key]["lon"], "speed": sky[key]["speed"]} for key in PLANETS]
    transits = []
    for aspect in aspects.find(moving, targets, ORB_SCALE):
        closeness = _closeness(aspect)
        transits.append({
            **aspect,
            "strength": round(WEIGHT[aspect["a"]] * closeness, 3),
            "lean": valence(aspect),
            "pressure": PRESSURE[aspect["a"]] * closeness,
        })
    score = sum(t["lean"] * t.pop("pressure") for t in transits)
    return {"date": day, "sky": sky, "transits": transits, "score": score}


def _sky_points(sky: dict) -> list[dict]:
    points = []
    for key in PLANETS:
        lon = wrap(sky[key]["lon"])
        index = int(lon // 30) % 12
        points.append({
            "id": key,
            "lon": round(lon, 4),
            "sign": SIGNS[index],
            "deg": round(lon - index * 30, 2),
            "retro": sky[key]["speed"] < 0,
        })
    return points


def _strongest(transits: list[dict]) -> list[dict]:
    return sorted(transits, key=lambda t: t["strength"], reverse=True)[:KEY_TRANSITS]


def build(chart: dict, start: date, period: str, tz: str) -> dict:
    """Transits for a day or for the week from `start`: the sky, the key transits, the tones."""
    targets = _targets(chart)

    if period == "day":
        day = _day(chart, targets, start, tz)
        moon = _sky_points(day["sky"])[1]
        house = houses.house_of(moon["lon"], [cusp["lon"] for cusp in chart["houses"]]) if chart["houses"] else None
        return {
            "period": "day",
            "start": start.isoformat(),
            "end": start.isoformat(),
            "tone": _tone(day["score"]),
            "moon": {"sign": moon["sign"], "house": house},
            "sky": _sky_points(day["sky"]),
            "transits": _strongest(day["transits"]),
            "days": None,
        }

    days = [_day(chart, targets, start + timedelta(days=offset), tz) for offset in range(WEEK_DAYS)]
    # Over a week the Moon touches everything; the key transits are the slower ones, each at its closest day.
    closest: dict[tuple, dict] = {}
    for day in days:
        for transit in day["transits"]:
            if transit["a"] == "moon":
                continue
            key = (transit["a"], transit["b"], transit["type"])
            if key not in closest or transit["orb"] < closest[key]["orb"]:
                closest[key] = {**transit, "date": day["date"].isoformat()}
    score = sum(day["score"] for day in days) / WEEK_DAYS
    return {
        "period": "week",
        "start": start.isoformat(),
        "end": days[-1]["date"].isoformat(),
        "tone": _tone(score),
        "moon": None,
        # The sky of the middle of the week: the slow planets barely move in three days.
        "sky": _sky_points(days[WEEK_DAYS // 2]["sky"]),
        "transits": _strongest(list(closest.values())),
        "days": [{"date": day["date"].isoformat(), "tone": _tone(day["score"]), "score": round(day["score"], 2)} for day in days],
    }


def month(chart: dict, start: date, tz: str) -> list[dict]:
    """Thirty days from `start`: each day's tone and its strongest transit, for the star calendar.

    Slow planets hold the same aspects for months and would colour every day alike, so a day's
    tone is read against the month's median and its main transit is one the month does not hold
    throughout, when there is such."""
    targets = _targets(chart)
    raw = [_day(chart, targets, start + timedelta(days=offset), tz) for offset in range(MONTH_DAYS)]
    scores = sorted(day["score"] for day in raw)
    middle = len(scores) // 2
    median = scores[middle] if len(scores) % 2 else (scores[middle - 1] + scores[middle]) / 2
    keys = [{(t["a"], t["b"], t["type"]) for t in day["transits"]} for day in raw]
    constant = set.intersection(*keys) if keys else set()
    days = []
    for day in raw:
        ranked = sorted(day["transits"], key=lambda t: t["strength"], reverse=True)
        passing = [t for t in ranked if (t["a"], t["b"], t["type"]) not in constant]
        top = (passing or ranked)[:1]
        days.append({
            "date": day["date"].isoformat(),
            "tone": _tone(day["score"] - median),
            "score": round(day["score"] - median, 2),
            "top": {key: top[0][key] for key in ("a", "b", "type", "lean")} if top else None,
        })
    return days
