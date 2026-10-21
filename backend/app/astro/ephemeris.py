"""Apparent geocentric positions on the ecliptic of date, from the JPL DE421 ephemeris.

DE421 covers 1900–2050: births since 1900 and forecasts for decades ahead. The file (17 MB)
is baked into the image at build time; without it Skyfield would download it on first use.
"""

import math

import numpy as np
from datetime import datetime, timedelta, timezone
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


def mean_apogee(tt_centuries: float) -> float:
    """Black Moon Lilith: the mean apogee of the Moon, opposite her mean perigee (Meeus, 47.7)."""
    t = tt_centuries
    perigee = 83.3532465 + 4069.0137287 * t - 0.0103200 * t**2 - t**3 / 80053 + t**4 / 18999000
    return wrap(perigee + 180.0)


def true_node(eph, times) -> list[float]:
    """The Moon's true ascending node: where her osculating orbit crosses the ecliptic of date.

    The orbit's plane is the one of the Moon's position and velocity around the Earth (their
    cross product is its pole), as in the Swiss Ephemeris. It sways up to 1.5° around the mean
    node and now and then stands still or moves forward.
    """
    pos, vel = (eph["moon"] - eph["earth"]).at(times).frame_xyz_and_velocity(ecliptic_frame)
    pole = np.cross(pos.km, vel.km_per_s, axis=0)
    return [wrap(math.degrees(math.atan2(x, -y))) for x, y in zip(pole[0], pole[1])]


_CHIRON_START = datetime(1900, 1, 1, tzinfo=timezone.utc)
_CHIRON_STEP = 2.0


@lru_cache(maxsize=1)
def _chiron_table() -> list[float]:
    """Chiron from JPL Horizons (chiron.txt): DE421 knows only the planets, and Chiron's orbit,
    swung by Saturn and Uranus, drifts away from any fixed elements within years."""
    path = Path(__file__).with_name("chiron.txt")
    return [int(line) / 1e4 for line in path.read_text(encoding="ascii").splitlines() if line and line[0] != "#"]


def chiron(moment: datetime) -> float:
    """Chiron's longitude, read between the table's rows: two days apart, the error stays under 5″."""
    table = _chiron_table()
    days = (moment - _CHIRON_START).total_seconds() / 86400.0 / _CHIRON_STEP
    index = max(0, min(len(table) - 2, int(days // 1)))
    share = days - index
    return wrap(table[index] + delta(table[index + 1], table[index]) * share)


def sky_at(moment: datetime) -> dict:
    """Longitudes and daily speeds of the planets, the node, Chiron and Lilith, the sidereal time and the obliquity."""
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
    before, now, after = true_node(eph, times)
    points["node"] = {"lon": now, "speed": delta(after, before) / (2 * _STEP_DAYS)}
    step = timedelta(days=_STEP_DAYS)
    points["chiron"] = {
        "lon": chiron(m),
        "speed": delta(chiron(m + step), chiron(m - step)) / (2 * _STEP_DAYS),
    }
    # The mean apogee is counted from the mean equinox; the nutation brings it to the true one, as the planets.
    nutation = math.degrees(t._nutation_angles_radians[0])
    centuries = (float(t.tt) - 2451545.0) / 36525.0
    points["lilith"] = {
        "lon": wrap(mean_apogee(centuries) + nutation),
        "speed": delta(mean_apogee(centuries + 1 / 36525.0), mean_apogee(centuries)),
    }
    obliquity = math.degrees(t._mean_obliquity_radians + t._nutation_angles_radians[1])
    return {"points": points, "gast": float(t.gast) * 15.0, "obliquity": float(obliquity)}
