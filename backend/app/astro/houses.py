"""Ascendant, Midheaven and house cusps from the local sidereal time, latitude and obliquity.

Placidus divides the time each degree of the ecliptic spends above and below the horizon.
Beyond the polar circles some degrees never rise or set and the system has no answer; there
the chart falls back to Porphyry, which divides each quadrant between the angles in three.
"""

import math

_EPSILON = 1e-10


def _sin(d: float) -> float:
    return math.sin(math.radians(d))


def _cos(d: float) -> float:
    return math.cos(math.radians(d))


def _ecliptic_of(ra: float, obliquity: float) -> float:
    """The longitude of the ecliptic point with this right ascension."""
    return math.degrees(math.atan2(_sin(ra), _cos(ra) * _cos(obliquity))) % 360.0


def angles(ramc: float, obliquity: float, latitude: float) -> tuple[float, float]:
    mc = _ecliptic_of(ramc, obliquity)
    tan_lat = math.tan(math.radians(latitude))
    asc = math.degrees(math.atan2(_cos(ramc), -(_sin(ramc) * _cos(obliquity) + tan_lat * _sin(obliquity)))) % 360.0
    # Beyond the polar circles the formula may give the western point; by convention the
    # Ascendant stays in the eastern half, the first quadrant after the Midheaven.
    if (asc - mc) % 360.0 > 180.0:
        asc = (asc + 180.0) % 360.0
    return asc, mc


def _placidus_cusp(ramc: float, obliquity: float, latitude: float, part: float, above: bool) -> float | None:
    """The cusp `part` of the way along the semi-arc: above the horizon from the MC, below it from the Ascendant."""
    tan_lat = math.tan(math.radians(latitude))
    lon = _ecliptic_of(ramc + (90.0 if above else 180.0) * part + (0.0 if above else 90.0), obliquity)
    for _ in range(100):
        dec = math.degrees(math.asin(_sin(obliquity) * _sin(lon)))
        x = -tan_lat * math.tan(math.radians(dec))
        if abs(x) > 1.0:
            return None
        day_arc = math.degrees(math.acos(x))
        ra = ramc + day_arc * part if above else ramc + day_arc + (180.0 - day_arc) * part
        next_lon = _ecliptic_of(ra, obliquity)
        if abs((next_lon - lon + 180.0) % 360.0 - 180.0) < _EPSILON:
            return next_lon
        lon = next_lon
    return None


def placidus(ramc: float, obliquity: float, latitude: float) -> list[float] | None:
    asc, mc = angles(ramc, obliquity, latitude)
    found = [
        _placidus_cusp(ramc, obliquity, latitude, 1 / 3, True),
        _placidus_cusp(ramc, obliquity, latitude, 2 / 3, True),
        _placidus_cusp(ramc, obliquity, latitude, 1 / 3, False),
        _placidus_cusp(ramc, obliquity, latitude, 2 / 3, False),
    ]
    if any(cusp is None for cusp in found):
        return None
    c11, c12, c2, c3 = found
    return _twelve(asc, c2, c3, mc, c11, c12)


def porphyry(asc: float, mc: float) -> list[float]:
    upper = (asc - mc) % 360.0
    lower = (mc + 180.0 - asc) % 360.0
    return _twelve(asc, asc + lower / 3, asc + 2 * lower / 3, mc, mc + upper / 3, mc + 2 * upper / 3)


def _twelve(asc: float, c2: float, c3: float, mc: float, c11: float, c12: float) -> list[float]:
    first = [asc, c2, c3, mc + 180.0, c11 + 180.0, c12 + 180.0]
    return [value % 360.0 for value in first + [value + 180.0 for value in first]]


def house_of(lon: float, cusps: list[float]) -> int:
    for index in range(12):
        start = cusps[index]
        span = (cusps[(index + 1) % 12] - start) % 360.0
        if (lon - start) % 360.0 < span:
            return index + 1
    return 12
