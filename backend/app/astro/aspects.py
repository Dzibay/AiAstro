"""Major aspects between points, within one chart or across two (synastry, transits)."""

from app.astro.ephemeris import delta

# (name, angle, orb). The Sun and the Moon get two degrees more; the node and the angles, half.
ASPECTS = (
    ("conjunction", 0.0, 8.0),
    ("sextile", 60.0, 4.0),
    ("square", 90.0, 7.0),
    ("trine", 120.0, 7.0),
    ("opposition", 180.0, 8.0),
)
LUMINARIES = {"sun", "moon"}
POINTS = {"node", "asc", "mc"}


def _orb(base: float, a: str, b: str) -> float:
    if a in POINTS or b in POINTS:
        return base / 2
    if a in LUMINARIES or b in LUMINARIES:
        return base + 2
    return base


def limit(name: str, a: str, b: str, scale: float = 1.0) -> float:
    """The widest orb an aspect of this kind between these two points may have."""
    base = next(orb for aspect, _, orb in ASPECTS if aspect == name)
    return _orb(base, a, b) * scale


def _match(a: dict, b: dict, scale: float) -> dict | None:
    separation = abs(delta(a["lon"], b["lon"]))
    for name, angle, base in ASPECTS:
        orb = abs(separation - angle)
        if orb <= _orb(base, a["id"], b["id"]) * scale:
            # Applying when the orb shrinks over the next hour of motion.
            later = abs(delta(a["lon"] + a.get("speed", 0.0) / 24, b["lon"] + b.get("speed", 0.0) / 24))
            return {"a": a["id"], "b": b["id"], "type": name, "orb": round(orb, 2), "applying": abs(later - angle) < orb}
    return None


def find(points: list[dict], others: list[dict] | None = None, scale: float = 1.0) -> list[dict]:
    """Aspects inside `points`, or from each of `points` to each of `others`, tightest first.

    `scale` narrows the orbs: a transit is felt only while it is close.
    """
    if others is None:
        pairs = [(a, b) for index, a in enumerate(points) for b in points[index + 1:]]
    else:
        pairs = [(a, b) for a in points for b in others]
    found = []
    for a, b in pairs:
        # The node and the angles touch the planets, not each other.
        if a["id"] in POINTS and b["id"] in POINTS:
            continue
        aspect = _match(a, b, scale)
        if aspect:
            found.append(aspect)
    return sorted(found, key=lambda aspect: aspect["orb"])
