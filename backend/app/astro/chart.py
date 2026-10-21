"""The natal chart: where everything stood at the moment of birth, as seen from the birth place.

What is not known is left out rather than guessed. Without the time the chart is drawn for
noon: the Sun and the planets barely move in half a day, the Moon may be six degrees off, so
her aspects are dropped, and there are no houses or Ascendant. Without the coordinates there
are no houses either, and the time is read as UTC.
"""

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from app.astro import aspects, houses
from app.astro.ephemeris import PLANETS, sky_at, wrap

# Beyond the planets: the true node, Chiron and Black Moon Lilith (the mean apogee).
EXTRA = ("node", "chiron", "lilith")

# Raised whenever the output changes, so the cached charts are recomputed.
VERSION = 2

SIGNS = (
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
)
ELEMENTS = ("fire", "earth", "air", "water")
MODES = ("cardinal", "fixed", "mutable")

# Near the pole the horizon formulas divide by nothing.
_POLAR_LIMIT = 89.9


def _place(lon: float) -> dict:
    lon = wrap(lon)
    index = int(lon // 30) % 12
    return {"lon": round(lon, 4), "sign": SIGNS[index], "deg": round(lon - index * 30, 2)}


def moment_of(birth_date: date, birth_time: time | None, tz: str) -> datetime:
    local = datetime.combine(birth_date, birth_time or time(12, 0), tzinfo=ZoneInfo(tz or "UTC"))
    return local.astimezone(timezone.utc)


def natal(birth_date: date, birth_time: time | None, lat: float | None, lon: float | None, tz: str = "") -> dict:
    time_known = birth_time is not None
    place_known = lat is not None and lon is not None
    moment = moment_of(birth_date, birth_time, tz if place_known else "UTC")
    sky = sky_at(moment)

    points = []
    for key in (*PLANETS, *EXTRA):
        body = sky["points"][key]
        point = {"id": key, **_place(body["lon"]), "speed": round(body["speed"], 4), "retro": body["speed"] < 0}
        if key == "moon" and not time_known:
            point["approx"] = True
        points.append(point)

    angles = cusps = system = None
    if time_known and place_known:
        latitude = max(-_POLAR_LIMIT, min(_POLAR_LIMIT, float(lat)))
        ramc = wrap(sky["gast"] + float(lon))
        asc, mc = houses.angles(ramc, sky["obliquity"], latitude)
        cusps = houses.placidus(ramc, sky["obliquity"], latitude)
        system = "placidus"
        if cusps is None:
            cusps, system = houses.porphyry(asc, mc), "porphyry"
        angles = {"asc": _place(asc), "mc": _place(mc)}
        for point in points:
            point["house"] = houses.house_of(point["lon"], cusps)

    # The aspects use the unrounded longitudes, the speeds tell applying from separating.
    raw = [{"id": point["id"], "lon": sky["points"][point["id"]]["lon"], "speed": sky["points"][point["id"]]["speed"]}
           for point in points if time_known or point["id"] != "moon"]
    if angles:
        raw += [{"id": "asc", "lon": asc, "speed": 0.0}, {"id": "mc", "lon": mc, "speed": 0.0}]

    return {
        "version": VERSION,
        "time_known": time_known,
        "place_known": place_known,
        "moment": moment.isoformat(),
        "house_system": system,
        "points": points,
        "angles": angles,
        "houses": [_place(cusp) for cusp in cusps] if cusps else None,
        "aspects": aspects.find(raw),
        "balance": _balance(points),
    }


def _balance(points: list[dict]) -> dict:
    """Elements and modes of the ten planets: the temperament of the chart in two lines."""
    elements = dict.fromkeys(ELEMENTS, 0)
    modes = dict.fromkeys(MODES, 0)
    for point in points:
        if point["id"] not in PLANETS:
            continue
        index = SIGNS.index(point["sign"])
        elements[ELEMENTS[index % 4]] += 1
        modes[MODES[index % 3]] += 1
    return {"elements": elements, "modes": modes}
