"""Natal charts of the users, computed once per set of birth data and kept in the database.

The key is a hash of the inputs and the chart version: corrected birth data or a new version
of the calculation simply miss the cache, and the stale rows are never read again.
"""

import hashlib
import json
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from psycopg.types.json import Jsonb

from app.accounts import get_user
from app.astro import forecast
from app.astro.chart import VERSION, natal
from app.astro.texts import forecast_title, interpreter, item_title
from app.db import pool
from app.errors import DomainError
from app.readings import cached


def _key(birth: dict) -> str:
    inputs = [VERSION, birth["date"], birth["time"], birth["lat"], birth["lon"], birth["tz"]]
    return hashlib.sha256(json.dumps(inputs).encode()).hexdigest()


def chart_of(user_id: int) -> dict:
    birth = get_user(user_id)["birth"]
    if birth is None:
        raise DomainError("no_birth", 409)
    return chart_for(birth)


def chart_for(birth: dict) -> dict:
    """The chart of any birth data in the public shape (the person's own, a partner's)."""
    key = _key(birth)
    with pool.connection() as conn:
        row = conn.execute("SELECT data FROM charts WHERE key = %s", (key,)).fetchone()
    if row is not None:
        return row["data"]
    data = natal(
        date.fromisoformat(birth["date"]),
        time.fromisoformat(birth["time"]) if birth["time"] else None,
        birth["lat"],
        birth["lon"],
        birth["tz"] or "",
    )
    with pool.connection() as conn:
        conn.execute(
            "INSERT INTO charts (key, data) VALUES (%s, %s) ON CONFLICT (key) DO NOTHING",
            (key, Jsonb(data)),
        )
    return data


def chart_item(user_id: int, item: str) -> dict:
    """A planet, the node or an angle of the person's chart, with its reading."""
    chart = chart_of(user_id)
    found = next((point for point in chart["points"] if point["id"] == item), None)
    if found is None and chart["angles"] and item in chart["angles"]:
        found = {"id": item, **chart["angles"][item]}
    if found is None:
        raise DomainError("missing", 404)
    house = found.get("house")
    retro = bool(found.get("retro"))
    text = cached(
        "natal_item",
        [item, found["sign"], house, retro],
        lambda: interpreter.natal_item(item, found["sign"], house, retro),
    )
    return {"id": item, "title": item_title(item, found["sign"], house), "text": text}


def _zone(name: str | None) -> str | None:
    if not name or len(name) > 64:
        return None
    try:
        ZoneInfo(name)
    except (ValueError, KeyError, OSError):
        return None
    return name


def forecast_of(user_id: int, period: str, tz: str | None = None) -> dict:
    """The day or the week from today, where the person is now (the browser's zone, else the birth one).

    The transits are free: they are a calculation. The text is «Небосвод»: without it only its
    first paragraph leaves the server, and the page fades it out.
    """
    if period not in forecast.PERIODS:
        raise DomainError("period", 422)
    user = get_user(user_id)
    chart = chart_of(user_id)
    zone = _zone(tz) or _zone(user["birth"]["tz"]) or "UTC"
    today = datetime.now(ZoneInfo(zone)).date()
    data = forecast.build(chart, today, period, zone)
    inputs = [
        period, data["start"], data["tone"], data["moon"],
        [[t["a"], t["b"], t["type"], t["lean"] > 0, t.get("date")] for t in data["transits"][:2]],
        [day["tone"] for day in data["days"] or []],
    ]
    text = cached("forecast", inputs, lambda: interpreter.forecast(data))
    paragraphs = text.split("\n\n")
    return {
        **data,
        "title": forecast_title(data),
        "paragraphs": paragraphs if user["sky"] else paragraphs[:1],
        "locked": not user["sky"],
    }
