"""The facts a portrait of the chart is written from: what stands out, rather than every point in turn.

All of it is read from the chart's public shape (app.astro.chart.natal), so a cached chart
needs no new calculation. What needs the birth time (the Ascendant, the houses, the Moon's
phase) is left out when the time is not known.
"""

from app.astro.chart import ELEMENTS, MODES, SIGNS
from app.astro.ephemeris import PLANETS, delta

# The modern rulers: the planet that keeps each sign.
RULERS = {
    "aries": "mars", "taurus": "venus", "gemini": "mercury", "cancer": "moon", "leo": "sun", "virgo": "mercury",
    "libra": "venus", "scorpio": "pluto", "sagittarius": "jupiter", "capricorn": "saturn", "aquarius": "uranus",
    "pisces": "neptune",
}
# Eight phases of the Moon by her distance from the Sun, 45° each, from the new Moon on.
PHASES = ("new", "crescent", "first_quarter", "gibbous", "full", "disseminating", "last_quarter", "balsamic")
# Three planets in one sign or one house make a stellium: a part of life the chart leans on.
STELLIUM = 3
# A planet this close to the Ascendant or the Midheaven stands on the angle: it is seen first.
ANGLE_ORB = 8.0
HARD = ("square", "opposition")
# Between two of these an aspect belongs to a whole generation, not to one person.
SLOW = {"uranus", "neptune", "pluto"}
# The points beside the planets: the tightest aspects of the portrait are between planets.
MINOR = {"node", "chiron", "lilith"}
SOFT = ("trine", "sextile")


def element_of(sign: str) -> str:
    return ELEMENTS[SIGNS.index(sign) % 4]


def mode_of(sign: str) -> str:
    return MODES[SIGNS.index(sign) % 3]


def _strongest(counts: dict) -> str | None:
    """The element or cross that leads by at least one planet; None when two share the lead."""
    ranked = sorted(counts.items(), key=lambda item: -item[1])
    return ranked[0][0] if ranked[0][1] > ranked[1][1] else None


def _pair(counts: dict) -> list[str]:
    """The two elements that share the lead, when they stand clearly above the other two; else empty."""
    ranked = sorted(counts.items(), key=lambda item: -item[1])
    if ranked[0][1] == ranked[1][1] > ranked[2][1] and ranked[0][1] - ranked[3][1] >= 2:
        return sorted((ranked[0][0], ranked[1][0]), key=ELEMENTS.index)
    return []


def moon_phase(sun_lon: float, moon_lon: float) -> str:
    return PHASES[int(((moon_lon - sun_lon) % 360) // 45) % 8]


def _tightest(chart: dict, kinds: tuple) -> dict | None:
    """The tightest aspect of these kinds between planets (not the node), the angles allowed on one side."""
    for aspect in chart["aspects"]:
        ids = {aspect["a"], aspect["b"]}
        if aspect["type"] in kinds and not ids & MINOR and ids & set(PLANETS) and not ids <= SLOW:
            return {key: aspect[key] for key in ("a", "b", "type", "orb")}
    return None


def facts(chart: dict) -> dict:
    """What a portrait speaks of. Each key is None (or empty) when the chart cannot tell it."""
    points = {point["id"]: point for point in chart["points"]}
    planets = [point for point in chart["points"] if point["id"] in PLANETS and not point.get("approx")]
    angles = chart.get("angles") or {}

    elements = chart["balance"]["elements"]
    modes = chart["balance"]["modes"]

    by_sign: dict[str, list[str]] = {}
    by_house: dict[int, list[str]] = {}
    for point in planets:
        by_sign.setdefault(point["sign"], []).append(point["id"])
        if point.get("house"):
            by_house.setdefault(point["house"], []).append(point["id"])

    ruler = None
    if angles:
        ruler_id = RULERS[angles["asc"]["sign"]]
        found = points[ruler_id]
        ruler = {"id": ruler_id, "sign": found["sign"], "house": found.get("house"), "rising": angles["asc"]["sign"]}

    on_angles = []
    for key, angle in angles.items():
        for point in planets:
            if abs(delta(point["lon"], angle["lon"])) <= ANGLE_ORB:
                on_angles.append({"id": point["id"], "angle": key})

    hemispheres = None
    housed = [point["house"] for point in planets if point.get("house")]
    if housed:
        below = sum(1 for house in housed if house <= 6)
        east = sum(1 for house in housed if house in (10, 11, 12, 1, 2, 3))
        hemispheres = {
            # A lean counts when at least seven of the ten stand on one side.
            "vertical": "below" if below >= 7 else "above" if below <= 3 else None,
            "horizontal": "east" if east >= 7 else "west" if east <= 3 else None,
        }

    phase = None
    if chart["time_known"]:
        phase = moon_phase(points["sun"]["lon"], points["moon"]["lon"])

    # The planets behind each element, for the wheel to light (the same ten the balance counts).
    element_points = {element: [] for element in ELEMENTS}
    for point in chart["points"]:
        if point["id"] in PLANETS:
            element_points[element_of(point["sign"])].append(point["id"])

    node = points["node"]
    return {
        "sun": points["sun"]["sign"],
        "moon": None if points["moon"].get("approx") else points["moon"]["sign"],
        "asc": angles["asc"]["sign"] if angles else None,
        "element": _strongest(elements),
        "element_pair": _pair(elements),
        "element_points": element_points,
        "missing": [element for element in ELEMENTS if elements[element] == 0],
        "mode": _strongest(modes),
        "ruler": ruler,
        "stellium_signs": [{"sign": sign, "points": ids} for sign, ids in by_sign.items() if len(ids) >= STELLIUM],
        "stellium_houses": [{"house": house, "points": ids} for house, ids in sorted(by_house.items()) if len(ids) >= STELLIUM],
        "on_angles": on_angles,
        "hemispheres": hemispheres,
        "phase": phase,
        "tension": _tightest(chart, HARD),
        "gift": _tightest(chart, SOFT),
        "node": {"sign": node["sign"], "house": node.get("house")},
    }
