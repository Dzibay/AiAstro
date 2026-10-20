"""Synastry: the aspects between two natal charts, and the tone of the pair they add up to.

Both charts come in their public shape (app.astro.chart.natal). The first is the person's own,
the second the partner's: an aspect's `a` is always on the person's side, `b` on the partner's.
"""

from app.astro import aspects, houses
from app.astro.chart import SIGNS
from app.astro.ephemeris import delta, wrap
from app.astro.forecast import valence

# How much a point says about two people together: the lights, love and desire first.
WEIGHT = {
    "sun": 1.3, "moon": 1.3, "venus": 1.3, "mars": 1.2, "mercury": 1.0, "asc": 1.1,
    "jupiter": 0.8, "saturn": 0.9, "mc": 0.7, "uranus": 0.5, "neptune": 0.5, "pluto": 0.6,
}
# The slow planets stand in nearly the same place for everyone born within a few years:
# between them an aspect describes a generation, not a couple.
SLOW = {"uranus", "neptune", "pluto"}
ELEMENTS = ("fire", "earth", "air", "water")
# The planets whose place in the other's houses a pair reading tells.
OVERLAYS = ("sun", "moon", "venus", "mars")
KEY = 4
_TONE_LIMIT = 0.25
# The spheres of the pair, each read from the aspects that touch its points on either side.
SPHERES = (
    ("feelings", {"moon", "venus"}),
    ("passion", {"mars", "venus", "pluto", "asc"}),
    ("talk", {"mercury", "sun"}),
    ("home", {"moon", "saturn", "asc"}),
    ("path", {"sun", "jupiter", "saturn", "mc"}),
)


def _points(chart: dict) -> list[dict]:
    # A Moon without the birth time may be six degrees off: her aspects would be guesses.
    points = [
        {"id": point["id"], "lon": point["lon"]}
        for point in chart["points"]
        if point["id"] in WEIGHT and not point.get("approx")
    ]
    for key, angle in (chart.get("angles") or {}).items():
        points.append({"id": key, "lon": angle["lon"]})
    return points


def _strength(aspect: dict) -> float:
    closeness = 1 - aspect["orb"] / aspects.limit(aspect["type"], aspect["a"], aspect["b"])
    return round((WEIGHT[aspect["a"]] + WEIGHT[aspect["b"]]) / 2 * (0.4 + 0.6 * max(0.0, closeness)), 3)


def _element(chart: dict) -> str:
    """The leading element; when two share the lead, the Sun's own one (as the star passport reads it)."""
    counts = chart["balance"]["elements"]
    sun = next(point["sign"] for point in chart["points"] if point["id"] == "sun")
    sun_element = ELEMENTS[SIGNS.index(sun) % 4]
    return max(ELEMENTS, key=lambda element: (counts[element], element == sun_element))


def build(mine: dict, theirs: dict) -> dict:
    found = []
    for aspect in aspects.find(_points(mine), _points(theirs)):
        if aspect["a"] in SLOW and aspect["b"] in SLOW:
            continue
        # Two still charts: nothing applies or separates between them.
        aspect.pop("applying", None)
        aspect["strength"] = _strength(aspect)
        aspect["lean"] = valence(aspect)
        found.append(aspect)
    found.sort(key=lambda aspect: -aspect["strength"])

    total = sum(aspect["strength"] for aspect in found)
    score = sum(aspect["strength"] * aspect["lean"] for aspect in found) / total if total else 0.0
    if len(found) < 3:
        tone = "calm"
    elif score > _TONE_LIMIT:
        tone = "easy"
    elif score < -_TONE_LIMIT:
        tone = "tense"
    else:
        tone = "mixed"
    return {
        "tone": tone,
        "aspects": found,
        "spheres": spheres(found),
        "key": found[:KEY],
        "elements": {"mine": _element(mine), "theirs": _element(theirs)},
        "overlays": {"theirs_in_mine": _overlays(theirs, mine), "mine_in_theirs": _overlays(mine, theirs)},
        "composite": _composite(mine, theirs),
    }


def _overlays(guest: dict, host: dict) -> list[dict]:
    """Where the guest's planets fall in the host's houses: [{id, house}]; empty without the host's birth time."""
    if not host.get("houses"):
        return []
    cusps = [cusp["lon"] for cusp in host["houses"]]
    points = {point["id"]: point for point in guest["points"]}
    return [{"id": key, "house": houses.house_of(points[key]["lon"], cusps)}
            for key in OVERLAYS if not points[key].get("approx")]


def _midpoint(a: float, b: float) -> float:
    """The midpoint on the shorter arc between two longitudes."""
    return wrap(b + delta(a, b) / 2)


def _composite(mine: dict, theirs: dict) -> dict:
    """The union as a third chart: the signs of the midpoints of two Suns and of two Moons."""
    a = {point["id"]: point for point in mine["points"]}
    b = {point["id"]: point for point in theirs["points"]}
    result = {"sun": SIGNS[int(_midpoint(a["sun"]["lon"], b["sun"]["lon"]) // 30) % 12], "moon": None}
    if not a["moon"].get("approx") and not b["moon"].get("approx"):
        result["moon"] = SIGNS[int(_midpoint(a["moon"]["lon"], b["moon"]["lon"]) // 30) % 12]
    return result


def spheres(found: list[dict]) -> list[dict]:
    """Five spheres of the pair, each from 1 to 5: the strength-weighted lean of the aspects touching it.

    3 is even, the easy aspects raise it, the tense lower it, but they count for a little less:
    a square between two charts is friction, and friction is also what holds two people together.
    """
    result = []
    for sphere, points in SPHERES:
        touching = [aspect for aspect in found if aspect["a"] in points or aspect["b"] in points]
        total = sum(aspect["strength"] for aspect in touching)
        lean = sum(aspect["strength"] * (aspect["lean"] if aspect["lean"] > 0 else aspect["lean"] * 0.8) for aspect in touching)
        score = 3 + 3 * (lean / total if total else 0.0)
        result.append({"id": sphere, "score": max(1, min(5, round(score)))})
    return result
