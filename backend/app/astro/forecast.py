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
from app.astro.ephemeris import PLANETS, delta, sky_at, wrap

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
# The spheres of a day, each read from the transits that touch its points on either side.
SPHERES = (
    ("love", {"venus", "moon"}),
    ("work", {"saturn", "jupiter", "mc", "sun"}),
    ("talk", {"mercury"}),
    ("energy", {"mars", "sun", "asc"}),
)
_SPHERE_LIMIT = 0.35
# The slow planets: their transits stand for months, and the forecast says from when to when.
SLOW = ("jupiter", "saturn", "uranus", "neptune", "pluto")
_SPAN_STEP = 5
_SPAN_REACH = 400
# The planets whose standing still and turning back the calendar marks.
STATIONS = ("mercury", "venus", "mars", "jupiter", "saturn")
# The planets whose passing into a new sign the calendar marks.
INGRESSES = ("sun", "mercury", "venus", "mars", "jupiter", "saturn")
MOON_PHASES = ("new", "crescent", "first_quarter", "gibbous", "full", "disseminating", "last_quarter", "balsamic")


@lru_cache(maxsize=512)
def _sky_at_noon(day: date, tz: str) -> dict:
    moment = datetime.combine(day, time(12, 0), tzinfo=ZoneInfo(tz)).astimezone(timezone.utc)
    return sky_at(moment)["points"]


def _targets(chart: dict) -> list[dict]:
    """The natal points a transit can touch; a Moon guessed without the time cannot be one."""
    found = [{"id": point["id"], "lon": point["lon"], "speed": 0.0} for point in chart["points"]
             if not point.get("approx")]
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
    spheres = _spheres(transits)
    score = sum(t["lean"] * t.pop("pressure") for t in transits)
    return {"date": day, "sky": sky, "transits": transits, "score": score, "spheres": spheres}


def _spheres(transits: list[dict]) -> dict:
    """The tone of each sphere of the day: easy, tense or calm, with the score it came from."""
    result = {}
    for sphere, points in SPHERES:
        score = sum(t["lean"] * t["pressure"] for t in transits if t["a"] in points or t["b"] in points)
        tone = "easy" if score > _SPHERE_LIMIT else "tense" if score < -_SPHERE_LIMIT else "calm"
        result[sphere] = {"tone": tone, "score": round(score, 2)}
    return result


def _sphere_tones(day: dict) -> dict:
    return {key: value["tone"] for key, value in day["spheres"].items()}


@lru_cache(maxsize=4096)
def _sky_at_utc_noon(day: date) -> dict:
    """The sky for the slow planets and the sky's own events: a few hours of time zone do not matter there."""
    return sky_at(datetime.combine(day, time(12, 0), tzinfo=timezone.utc))["points"]


def _within(planet: str, target: dict, kind: str, day: date) -> bool:
    lon = _sky_at_utc_noon(day)[planet]["lon"]
    angle = next(angle for name, angle, _ in aspects.ASPECTS if name == kind)
    return abs(abs(delta(lon, target["lon"])) - angle) <= aspects.limit(kind, planet, target["id"], ORB_SCALE)


def span(transit: dict, targets: list[dict], day: date) -> dict | None:
    """From when to when a slow transit holds, its retrograde loops included: {from, to}; None for a fast one.

    Read in steps of a few days, which is exact enough for «с середины августа по декабрь».
    """
    if transit["a"] not in SLOW:
        return None
    target = next((point for point in targets if point["id"] == transit["b"]), None)
    if target is None:
        return None
    ends = []
    for direction in (-1, 1):
        last = day
        for step in range(_SPAN_STEP, _SPAN_REACH, _SPAN_STEP):
            probe = day + timedelta(days=direction * step)
            if _within(transit["a"], target, transit["type"], probe):
                last = probe
                continue
            # A retrograde loop leaves the orb for some weeks and comes back: look a little further.
            if not any(_within(transit["a"], target, transit["type"], probe + timedelta(days=direction * extra))
                       for extra in (20, 40, 60)):
                break
        ends.append(last)
    return {"from": ends[0].isoformat(), "to": ends[1].isoformat()}


def _with_spans(transits: list[dict], targets: list[dict], start: date) -> list[dict]:
    return [{**t, "span": span(t, targets, date.fromisoformat(t["date"]) if t.get("date") else start)} for t in transits]


def _elongation(day: date) -> float:
    sky = _sky_at_utc_noon(day)
    return (sky["moon"]["lon"] - sky["sun"]["lon"]) % 360


def moon_phase(day: date) -> str:
    """Eight phases by the Moon's distance from the Sun, 45° each, from the new Moon on."""
    return MOON_PHASES[int(_elongation(day) // 45) % 8]


def _crossing(day: date) -> tuple[str | None, float]:
    """A new or full Moon between this noon and the next, and how far into those hours it falls (0…1)."""
    before, after = _elongation(day), _elongation(day + timedelta(days=1))
    if after < before:
        return "new", (360 - before) / (360 - before + after)
    if before < 180 <= after:
        return "full", (180 - before) / (after - before)
    return None, 0.0


def _lunation(day: date) -> str | None:
    """«new» or «full» when that Moon falls within half a day of this noon."""
    kind, share = _crossing(day)
    if kind and share < 0.5:
        return kind
    kind, share = _crossing(day - timedelta(days=1))
    return kind if kind and share >= 0.5 else None


def next_lunation(start: date) -> dict | None:
    """The nearest new or full Moon from `start` on: {kind, date}."""
    for offset in range(31):
        day = start + timedelta(days=offset)
        kind = _lunation(day)
        if kind:
            return {"kind": kind, "date": day.isoformat(), "in": offset}
    return None


def _sign(lon: float) -> str:
    return SIGNS[int(wrap(lon) // 30) % 12]


def events(day: date) -> list[dict]:
    """What happens in the sky itself between this noon and the next: lunations, stations, ingresses."""
    today, tomorrow = _sky_at_utc_noon(day), _sky_at_utc_noon(day + timedelta(days=1))
    found = []
    kind = _lunation(day)
    if kind:
        found.append({"kind": f"{kind}_moon", "planet": "moon", "sign": _sign(today["moon"]["lon"])})
    for planet in STATIONS:
        if today[planet]["speed"] >= 0 > tomorrow[planet]["speed"]:
            found.append({"kind": "retro", "planet": planet, "sign": _sign(tomorrow[planet]["lon"])})
        elif today[planet]["speed"] < 0 <= tomorrow[planet]["speed"]:
            found.append({"kind": "direct", "planet": planet, "sign": _sign(tomorrow[planet]["lon"])})
    for planet in INGRESSES:
        if _sign(today[planet]["lon"]) != _sign(tomorrow[planet]["lon"]):
            found.append({"kind": "ingress", "planet": planet, "sign": _sign(tomorrow[planet]["lon"])})
    return found


def retrograde(sky: dict) -> list[str]:
    """The planets going backwards that day; the Sun and the Moon never do."""
    return [key for key in PLANETS if key not in ("sun", "moon") and sky[key]["speed"] < 0]


def _best(days: list[dict]) -> dict:
    """The kindest day of the week for each sphere, when one stands out: {sphere: date}."""
    best = {}
    for sphere, _ in SPHERES:
        top = max(days, key=lambda day: day["spheres"][sphere]["score"])
        if top["spheres"][sphere]["tone"] == "easy":
            best[sphere] = top["date"].isoformat()
    return best


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
            "moon": {"sign": moon["sign"], "house": house, "phase": moon_phase(start), "next": next_lunation(start)},
            "sky": _sky_points(day["sky"]),
            "transits": _with_spans(_strongest(day["transits"]), targets, start),
            "spheres": _sphere_tones(day),
            "retro": retrograde(day["sky"]),
            "events": events(start),
            "best": None,
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
        "transits": _with_spans(_strongest(list(closest.values())), targets, start),
        "spheres": None,
        # Every planet that goes backwards on any day of the week: a station mid-week counts.
        "retro": [key for key in PLANETS if any(key in retrograde(day["sky"]) for day in days)],
        "events": [{**event, "date": day["date"].isoformat()} for day in days for event in events(day["date"])],
        "best": _best(days),
        "days": [{"date": day["date"].isoformat(), "tone": _tone(day["score"]), "score": round(day["score"], 2),
                  "spheres": _sphere_tones(day)} for day in days],
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
            "spheres": _sphere_tones(day),
            "events": events(day["date"]),
        })
    return days


@lru_cache(maxsize=8)
def public_sky(start: date) -> dict:
    """The sky of the week for everyone, without a chart: the Moon, the retrograde planets, the events."""
    sky = _sky_at_utc_noon(start)
    week = []
    for offset in range(7):
        day = start + timedelta(days=offset)
        week += [{**event, "date": day.isoformat()} for event in events(day)]
    return {
        "date": start.isoformat(),
        "moon": {"sign": _sign(sky["moon"]["lon"]), "phase": moon_phase(start)},
        "next": next_lunation(start),
        "retro": retrograde(sky),
        "events": week,
    }
