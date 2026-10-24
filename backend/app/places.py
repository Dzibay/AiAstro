"""Birth places: city suggestions from the geocoder and the time zone of a point.

Suggestions come from Nominatim (OpenStreetMap). Its public server allows one request per
second and asks for an identifying User-Agent, so requests go through one lock with a pause
between them, and answers are cached: people type the same cities.
"""

import json
import threading
import time
from collections import OrderedDict
from functools import lru_cache
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.config import settings
from app.errors import DomainError
from app.throttle import Window

_CACHE_SIZE = 512
_LIMIT = 6
# Settlements only: a birth place is a city, a town or a village, not a street.
_SETTLEMENT_KEYS = ("city", "town", "village", "hamlet", "municipality", "locality")

# The suggestions are open to the registration form, so each address gets its own budget.
allow = Window(40, 60).take
# A request that would wait longer than this for its turn at the geocoder is turned away.
_QUEUE_SECONDS = 3.0

_cache: OrderedDict[str, list[dict]] = OrderedDict()
_lock = threading.Lock()
_last_call = 0.0


def _user_agent() -> str:
    """HTTP headers are Latin-1: a Cyrillic site name («Астра») would fail the request before it is sent."""
    name = settings.site_name if settings.site_name.isascii() else "Astra"
    contact = f"; {settings.geocoder_contact}" if settings.geocoder_contact else ""
    agent = f"{name}/1.0 (+{settings.public_base_url}{contact})"
    return agent if agent.isascii() else f"{name}/1.0"


def _fetch(query: str) -> list:
    """One request to the geocoder, never sooner than a second after the previous one."""
    global _last_call
    params = urlencode({
        "q": query,
        "format": "jsonv2",
        "addressdetails": 1,
        "limit": _LIMIT,
        "featureType": "settlement",
        "accept-language": "ru",
    })
    request = Request(f"{settings.geocoder_url}?{params}", headers={"User-Agent": _user_agent()})
    if not _lock.acquire(timeout=_QUEUE_SECONDS):
        raise DomainError("busy", 429)
    try:
        wait = _last_call + settings.geocoder_interval - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        try:
            with urlopen(request, timeout=6) as response:
                return json.load(response)
        except (OSError, ValueError) as exc:
            raise DomainError("places", 503) from exc
        finally:
            _last_call = time.monotonic()
    finally:
        _lock.release()


def _place(item: dict) -> dict | None:
    try:
        lat = round(float(item["lat"]), 5)
        lon = round(float(item["lon"]), 5)
    except (KeyError, TypeError, ValueError):
        return None
    address = item.get("address") or {}
    name = item.get("name") or next((address[key] for key in _SETTLEMENT_KEYS if address.get(key)), "")
    if not name:
        return None
    # «Татарстан, Россия»: enough to tell the two Kirovs apart, short enough for one line.
    # The state first: Russia's «region» is the federal district, too wide to tell the towns apart.
    detail = []
    for value in (address.get("state") or address.get("region"), address.get("country")):
        if value and value != name and value not in detail:
            detail.append(value)
    region = ", ".join(detail)
    return {
        "name": name,
        "region": region,
        "label": f"{name}, {region}" if region else name,
        "lat": lat,
        "lon": lon,
        "tz": timezone_at(lat, lon),
    }


def search(query: str, address: str = "") -> list[dict]:
    cleaned = " ".join(query.split())[:100]
    if len(cleaned) < 2:
        return []
    key = cleaned.casefold()
    if key in _cache:
        _cache.move_to_end(key)
        return _cache[key]
    if address:
        allow(address)
    places = []
    seen = set()
    for item in _fetch(cleaned):
        place = _place(item) if isinstance(item, dict) else None
        # The same town comes back as a node and as a boundary: one line is enough.
        if place and place["label"] not in seen:
            seen.add(place["label"])
            places.append(place)
    _cache[key] = places
    if len(_cache) > _CACHE_SIZE:
        _cache.popitem(last=False)
    return places


@lru_cache(maxsize=1)
def _finder():
    from timezonefinder import TimezoneFinder

    return TimezoneFinder()


def timezone_at(lat: float, lon: float) -> str:
    """The IANA zone of the point; the offset on the birth date comes from zoneinfo later."""
    name = _finder().timezone_at(lat=lat, lng=lon)
    if name:
        try:
            ZoneInfo(name)
            return name
        except (ZoneInfoNotFoundError, ValueError):
            pass
    # Open sea or a zone this tzdata does not know: the nautical zone by longitude.
    hours = max(-12, min(12, round(lon / 15)))
    return "UTC" if hours == 0 else f"Etc/GMT{-hours:+d}"
