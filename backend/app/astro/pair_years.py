"""The years ahead of a pair: when the slow planets pass over the points of the union.

The union is the composite chart: the midpoints of the two Suns, the two Moons and the two
Venuses. A slow planet in a close aspect to one of them marks a period the pair lives through
together — months for Jupiter and Saturn, a year or more for the outer planets. The sky is
sampled every two days; two passes of one retrograde loop make one period.
"""

from datetime import date, timedelta
from functools import lru_cache

import numpy as np
from skyfield.framelib import ecliptic_frame

from app.astro.ephemeris import PLANETS, _sky, delta, wrap
from app.astro.forecast import valence

YEARS = 5
# A period that began before today is still found whole, and one that begins near the end runs out.
_BEFORE = 2 * 365
_AFTER = 365
_STEP = 2
# Two stretches closer than this are one period: the planet turned back and came again.
_GAP = 150
# A period about to end says little about the years ahead.
_LEFT = 30

SLOW = ("jupiter", "saturn", "uranus", "neptune", "pluto")
TARGETS = ("sun", "moon", "venus")
ASPECTS = {"conjunction": 0, "trine": 120, "square": 90, "opposition": 180}
ORB = {"jupiter": 2.0, "saturn": 2.0, "uranus": 1.5, "neptune": 1.5, "pluto": 1.5}
# What a period weighs, for picking the ones the timeline shows.
WEIGHT = {"pluto": 1.3, "saturn": 1.25, "uranus": 1.15, "neptune": 1.05, "jupiter": 0.9}
TARGET_WEIGHT = {"sun": 1.0, "moon": 0.95, "venus": 0.95}
ASPECT_WEIGHT = {"conjunction": 1.0, "square": 0.9, "opposition": 0.9, "trine": 0.8}
SHOWN = 6
# Jupiter comes round often: without a limit it would fill the timeline with good news.
MAX_JUPITER = 3


@lru_cache(maxsize=4)
def _track(start: date) -> tuple[list[date], dict]:
    """The longitudes of the slow planets every two days around the five years from `start`."""
    ts, eph = _sky()
    first = start - timedelta(days=_BEFORE)
    count = (_BEFORE + YEARS * 365 + _AFTER) // _STEP + 1
    steps = np.arange(count) * _STEP
    times = ts.utc(first.year, first.month, first.day + steps, 12)
    earth = eph["earth"].at(times)
    longitudes = {}
    for key in SLOW:
        _, lon, _ = earth.observe(eph[PLANETS[key]]).apparent().frame_latlon(ecliptic_frame)
        longitudes[key] = lon.degrees % 360.0
    return [first + timedelta(days=int(step)) for step in steps], longitudes


def _union(mine: dict, theirs: dict) -> dict:
    """The points of the composite: a Moon guessed without the birth time is left out."""
    a = {point["id"]: point for point in mine["points"]}
    b = {point["id"]: point for point in theirs["points"]}
    return {key: wrap(b[key]["lon"] + delta(a[key]["lon"], b[key]["lon"]) / 2)
            for key in TARGETS if not a[key].get("approx") and not b[key].get("approx")}


def _runs(close: np.ndarray) -> list[tuple[int, int]]:
    found = np.flatnonzero(close)
    if not found.size:
        return []
    runs, first, last = [], found[0], found[0]
    for index in found[1:]:
        if (index - last) * _STEP > _GAP:
            runs.append((first, last))
            first = index
        last = index
    runs.append((first, last))
    return runs


def build(mine: dict, theirs: dict, start: date) -> list[dict]:
    """The periods of the next five years from `start`, by date: [{from, to, planet, target, type, tone, weight, now}]."""
    days, longitudes = _track(start)
    end = start + timedelta(days=YEARS * 365)
    found = []
    for target, point in _union(mine, theirs).items():
        for planet in SLOW:
            # How far the planet stands from the point, 0 to 180 degrees either way.
            apart = np.abs((longitudes[planet] - point + 180.0) % 360.0 - 180.0)
            for kind, angle in ASPECTS.items():
                for first, last in _runs(np.abs(apart - angle) <= ORB[planet]):
                    begun, ended = days[first], days[last]
                    if ended < start + timedelta(days=_LEFT) or begun > end:
                        continue
                    lean = valence({"a": planet, "b": target, "type": kind})
                    found.append({
                        "from": begun.isoformat(), "to": ended.isoformat(), "planet": planet, "target": target,
                        "type": kind, "now": begun <= start,
                        "tone": "easy" if lean > 0.5 else "tense" if lean < 0 else "calm",
                        "weight": round(WEIGHT[planet] * TARGET_WEIGHT[target] * ASPECT_WEIGHT[kind], 3),
                    })
    found.sort(key=lambda period: period["from"])
    shown, seen, jupiter = [], set(), 0
    # The heaviest first; one planet over one point in one manner once (the first time); few of Jupiter.
    for period in sorted(found, key=lambda period: -period["weight"]):
        key = (period["planet"], period["target"], period["type"] in ("square", "opposition"))
        if key in seen or (period["planet"] == "jupiter" and jupiter >= MAX_JUPITER):
            continue
        seen.add(key)
        jupiter += period["planet"] == "jupiter"
        shown.append(period)
        if len(shown) == SHOWN:
            break
    return sorted(shown, key=lambda period: period["from"])
