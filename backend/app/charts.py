"""Natal charts of the users, computed once per set of birth data and kept in the database.

The key is a hash of the inputs and the chart version: corrected birth data or a new version
of the calculation simply miss the cache, and the stale rows are never read again.
"""

import hashlib
import json
import re
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from psycopg.types.json import Jsonb

from app.accounts import get_user
from app.astro import forecast, portrait
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
    reading = cached(
        "natal_item",
        [item, found["sign"], house, retro],
        lambda: interpreter.natal_item(item, found["sign"], house, retro),
    )
    sky = get_user(user_id)["sky"]
    # The aspects themselves are a calculation and free; what they mean opens with «Небосвод».
    aspects = []
    for aspect in chart["aspects"]:
        if item not in (aspect["a"], aspect["b"]):
            continue
        a, b, kind = aspect["a"], aspect["b"], aspect["type"]
        text = cached("natal_aspect", [a, b, kind], lambda: {"text": interpreter.natal_aspect(a, b, kind)})["text"] if sky else None
        aspects.append({"a": a, "b": b, "type": kind, "text": text})
    return {
        "id": item,
        "title": item_title(item, found["sign"], house),
        "reading": reading,
        "aspects": aspects,
        "locked": not sky,
    }


def portrait_of(user_id: int) -> dict:
    """The chart read as a whole. Without «Небосвод» only its essence and first part leave the server."""
    user = get_user(user_id)
    facts = portrait.facts(chart_of(user_id))
    reading = cached("portrait", [facts], lambda: interpreter.portrait(facts))
    return {
        # Without «Небосвод» the other chapters are only named, as in the forecasts.
        "reading": reading if user["sky"] else {
            **reading, "parts": reading["parts"][:1],
            "outline": [part.get("title") or part["label"] for part in reading["parts"][1:]],
        },
        "total": len(reading["parts"]),
        "locked": not user["sky"],
    }


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
    essence and first part leave the server, and the page fades them out.
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
        [[t["a"], t["b"], t["type"], t["lean"] > 0, t.get("date"), t.get("span")] for t in data["transits"][:3]],
        [day["tone"] for day in data["days"] or []],
        data["spheres"], data["retro"], data["events"], data["best"],
    ]
    reading = cached("forecast", inputs, lambda: interpreter.forecast(data))
    tasks = reading.get("tasks")
    reading = {key: value for key, value in reading.items() if key != "tasks"}
    if tasks and user["sky"]:
        done = set(_done(user_id, today))
        tasks = [{**task, "done": task["key"] in done} for task in tasks]
    return {
        **data,
        "title": forecast_title(data),
        # Without «Небосвод» the other screens are only named, so the reader sees what is behind the haze.
        "reading": reading if user["sky"] else {
            **reading, "parts": reading["parts"][:1],
            "outline": [part.get("title") or part["label"] for part in reading["parts"][1:]],
        },
        # The day's checklist comes with the text, so with «Небосвод».
        "tasks": tasks if user["sky"] else None,
        "locked": not user["sky"],
    }


# ---- The day's checklist ----

TASK_KEY = re.compile(r"(t:[a-z]+:(easy|hard)|m:[a-z_]+|q:\d)")
MAX_DONE = 10


def _done(user_id: int, day: date) -> list[str]:
    with pool.connection() as conn:
        row = conn.execute("SELECT done FROM day_tasks WHERE user_id = %s AND day = %s", (user_id, day)).fetchone()
    return row["done"] if row else []


def mark_task(user_id: int, day: date, key: str, done: bool) -> dict:
    """A task of the day ticked or unticked. Only around today: yesterday's list is closed, tomorrow's not yet there."""
    if not TASK_KEY.fullmatch(key):
        raise DomainError("task")
    if abs((day - datetime.now(ZoneInfo("UTC")).date()).days) > 1:
        raise DomainError("day")
    with pool.connection() as conn:
        row = conn.execute(
            """
            INSERT INTO day_tasks (user_id, day, done)
            VALUES (%(user)s, %(day)s, CASE WHEN %(done)s THEN ARRAY[%(key)s]::text[] ELSE '{}'::text[] END)
            ON CONFLICT (user_id, day) DO UPDATE SET done = CASE
                WHEN NOT %(done)s THEN array_remove(day_tasks.done, %(key)s)
                WHEN %(key)s = ANY(day_tasks.done) OR cardinality(day_tasks.done) >= %(max)s THEN day_tasks.done
                ELSE day_tasks.done || %(key)s::text
            END
            RETURNING done
            """,
            {"user": user_id, "day": day, "done": done, "key": key, "max": MAX_DONE},
        ).fetchone()
    return {"day": day.isoformat(), "done": row["done"]}


# Without «Небосвод» the calendar shows the days the week forecast already shows; the rest stay veiled.
OPEN_DAYS = forecast.WEEK_DAYS


def month_of(user_id: int, tz: str | None = None) -> dict:
    """The star calendar: thirty days from today, each with its tone and its strongest transit."""
    user = get_user(user_id)
    chart = chart_of(user_id)
    zone = _zone(tz) or _zone(user["birth"]["tz"]) or "UTC"
    today = datetime.now(ZoneInfo(zone)).date()
    days = forecast.month(chart, today, zone)
    if not user["sky"]:
        # The sky's own events (lunations, stations) are the same for everyone, so they stay open.
        days = [day if index < OPEN_DAYS else {"date": day["date"], "tone": None, "score": None, "top": None,
                                               "spheres": None, "events": day["events"]}
                for index, day in enumerate(days)]
    return {"start": today.isoformat(), "days": days, "open": len(days) if user["sky"] else OPEN_DAYS, "locked": not user["sky"]}
