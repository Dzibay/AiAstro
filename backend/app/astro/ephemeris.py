"""Apparent geocentric positions on the ecliptic of date, from the JPL DE421 ephemeris.

DE421 covers 1900–2050: births since 1900 and forecasts for decades ahead. The file (17 MB)
is baked into the image at build time; without it Skyfield would download it on first use.
"""

import math
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from skyfield.api import Loader
from skyfield.framelib import ecliptic_frame

from app.config import settings

EPHEMERIS = "de421.bsp"

# The order of the chart: luminaries, personal, social, then the outer planets.
PLANETS = {
    "sun": "sun",
    "moon": "moon",
    "mercury": "mercury",
    "venus": "venus",
    "mars": "mars",
    "jupiter": "jupiter barycenter",
    "saturn": "saturn barycenter",
    "uranus": "uranus barycenter",
    "neptune": "neptune barycenter",
    "pluto": "pluto barycenter",
}

# Half a day each way is enough to tell the speed, and so a retrograde planet.
_STEP_DAYS = 0.5


def ephemeris_dir() -> Path:
    if settings.ephemeris_dir:
        return Path(settings.ephemeris_dir)
    return Path(__file__).resolve().parents[2] / "data"


@lru_cache(maxsize=1)
def _sky():
    loader = Loader(str(ephemeris_dir()), verbose=False)
    return loader.timescale(builtin=True), loader(EPHEMERIS)


def wrap(degrees: float) -> float:
    return degrees % 360.0


def delta(a: float, b: float) -> float:
    """The signed shortest way from b to a, in (-180, 180]."""
    d = (a - b) % 360.0
    return d - 360.0 if d > 180.0 else d


def mean_node(tt_centuries: float) -> float:
    """The Moon's mean ascending node (Meeus, Astronomical Algorithms, 47.7)."""
    t = tt_centuries
    return wrap(125.0445479 - 1934.1362891 * t + 0.0020754 * t**2 + t**3 / 467441 - t**4 / 60616000)


def sky_at(moment: datetime) -> dict:
    """Longitudes and daily speeds of the planets and the node, the sidereal time and the obliquity."""
    ts, eph = _sky()
    # Civil time is UT1 to within a second. Read as UTC, a moment before 1972 would be shifted
    # by the leap-second table by some forty seconds: a sixth of a degree on the Ascendant.
    m = moment.astimezone(timezone.utc)
    t = ts.ut1(m.year, m.month, m.day, m.hour, m.minute, m.second + m.microsecond / 1e6)
    times = ts.tt_jd([t.tt - _STEP_DAYS, t.tt, t.tt + _STEP_DAYS])
    earth = eph["earth"].at(times)
    points = {}
    for key, name in PLANETS.items():
        _, lon, _ = earth.observe(eph[name]).apparent().frame_latlon(ecliptic_frame)
        before, now, after = (float(value) for value in lon.degrees)
        points[key] = {"lon": wrap(now), "speed": delta(after, before) / (2 * _STEP_DAYS)}
    centuries = (float(t.tt) - 2451545.0) / 36525.0
    points["node"] = {
        "lon": mean_node(centuries),
        "speed": delta(mean_node(centuries + 1 / 36525.0), mean_node(centuries)),
    }
    obliquity = math.degrees(t._mean_obliquity_radians + t._nutation_angles_radians[1])
    return {"points": points, "gast": float(t.gast) * 15.0, "obliquity": float(obliquity)}
