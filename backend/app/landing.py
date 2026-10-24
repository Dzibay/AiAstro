"""The landing pages' taste of the sky, before any account: a few points of the chart with their
readings, the tone of a pair, the main transit of the day.

Nothing is stored and nobody is named: the birth data come in, the words go out. What is shown is
what the cabinet shows for free — a point's reading, the opening of a pair or of a day — so the
landing never gives away more than an account would, and never less.
"""

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from app.astro import forecast, synastry
from app.astro.chart import natal
from app.astro.texts import POINTS, interpreter, item_title, pair_aspect_title, pair_phrase, transit_phrase
from app.errors import DomainError
from app.places import timezone_at
from app.throttle import Window

# The points a landing may show, in the order of the card.
SHOWN = ("sun", "moon", "asc", "lilith", "chiron", "node")
FOCUS = set(SHOWN)

# Each calculation is cheap, but the page is open to anyone: a one-minute budget per address.
allow = Window(30, 60).take


def _chart(birth_date: date, birth_time: time | None, lat: float | None, lon: float | None) -> dict:
    if not date(1900, 1, 1) <= birth_date <= date.today():
        raise DomainError("birth", 422)
    tz = timezone_at(lat, lon) if lat is not None and lon is not None else ""
    return natal(birth_date, birth_time, lat, lon, tz) | {"tz": tz or "UTC"}


def _point(found: dict) -> dict:
    house = found.get("house")
    reading = interpreter.natal_item(found["id"], found["sign"], house, bool(found.get("retro")))
    return {
        "id": found["id"],
        "name": POINTS[found["id"]][0],
        "sign": found["sign"],
        "house": house,
        "approx": bool(found.get("approx")),
        "title": item_title(found["id"], found["sign"], house),
        "essence": reading["essence"],
        "parts": reading["parts"],
    }


def natal_preview(birth_date: date, birth_time: time | None, lat: float | None, lon: float | None, focus: str = "") -> dict:
    """Sun, Moon, Ascendant and the three points beyond the planets; `focus` goes first."""
    chart = _chart(birth_date, birth_time, lat, lon)
    found = {point["id"]: point for point in chart["points"]}
    if chart["angles"]:
        found["asc"] = {"id": "asc", **chart["angles"]["asc"]}
    order = [focus] + [key for key in SHOWN if key != focus] if focus in FOCUS else list(SHOWN)
    return {
        "time_known": chart["time_known"],
        "place_known": chart["place_known"],
        "points": [_point(found[key]) for key in order if key in found],
        "balance": chart["balance"],
    }


def pair_preview(mine: dict, theirs: dict) -> dict:
    """The tone of two charts, the five spheres by score, the reading's opening — as an unbought pair."""
    pair = synastry.build(_chart(**mine), _chart(**theirs))
    reading = interpreter.synastry(pair)
    return {
        "tone": pair["tone"],
        "phrase": pair_phrase(pair),
        "spheres": pair["spheres"],
        "key": [{"type": aspect["type"], "lean": aspect["lean"], "title": pair_aspect_title(aspect)} for aspect in pair["key"][:3]],
        "reading": {"essence": reading["essence"], "parts": reading["parts"][:1]},
        "total": len(reading["parts"]),
    }


def forecast_preview(birth_date: date, birth_time: time | None, lat: float | None, lon: float | None) -> dict:
    """Today against the birth chart, in the Moscow day: the tone, the main transits, the reading's opening."""
    chart = _chart(birth_date, birth_time, lat, lon)
    zone = "Europe/Moscow"
    today = datetime.now(ZoneInfo(zone)).date()
    data = forecast.build(chart, today, "day", zone)
    reading = interpreter.forecast(data)
    return {
        "start": data["start"],
        "tone": data["tone"],
        "spheres": data["spheres"],
        "transits": [{"phrase": transit_phrase(transit), "lean": transit["lean"]} for transit in data["transits"][:3]],
        "reading": {"essence": reading["essence"], "parts": reading["parts"][:1]},
        "total": len(reading["parts"]),
    }
