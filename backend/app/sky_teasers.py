"""What «Небосвод» holds for this person now: a short fact per feature, from their own chart and sky.

Without the subscription the page shows what waits behind the haze: the portrait's chapters
still closed, the light days of the month ahead, the questions already asked. With it, what burns
today and where to find it. Only counts, dates and the names of the screens leave the server; the
texts themselves stay where they open, as the forecasts and the portrait keep them.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from app.accounts import get_user
from app.astro import forecast
from app.charts import OPEN_DAYS, _zone, chart_of, forecast_of, portrait_of
from app.chat import questions_of
from app.partners import pairs_in_short


def _titles(reading: dict) -> list[str]:
    """The names of the screens after the first: the closed ones as the outline gives them, else from the parts."""
    if reading.get("outline") is not None:
        return reading["outline"]
    return [part.get("title") or part["label"] for part in reading["parts"][1:]]


def _screens(reading: dict) -> int:
    return len(reading["parts"]) + len(reading.get("outline") or [])


def _forecast(user_id: int, period: str, tz: str | None) -> dict:
    data = forecast_of(user_id, period, tz)
    tasks = data.get("tasks") or []
    return {
        "title": data["title"],
        "tone": data["tone"],
        "screens": _screens(data["reading"]),
        "titles": _titles(data["reading"])[:3],
        "best": data.get("best") or {},
        "tasks": len(tasks),
        "done": sum(1 for task in tasks if task.get("done")),
    }


def _calendar(user_id: int, tz: str | None) -> dict:
    """The month ahead: the light days of the month that is mostly behind the haze, and the nearest light day.

    Without «Небосвод» the nearest one is looked for only in the open week, the rest is only counted.
    """
    user = get_user(user_id)
    chart = chart_of(user_id)
    zone = _zone(tz) or _zone(user["birth"]["tz"]) or "UTC"
    today = datetime.now(ZoneInfo(zone)).date()
    days = forecast.month(chart, today, zone)
    later = days[OPEN_DAYS:]
    months: dict[str, int] = {}
    for day in later:
        months[day["date"][:7]] = months.get(day["date"][:7], 0) + 1
    month = max(months, key=months.get) if months else today.isoformat()[:7]
    # Lit, the whole month counts; without «Небосвод», the days still behind the haze.
    counted = days if user["sky"] else later
    seen = days if user["sky"] else days[:OPEN_DAYS]
    nearest = next((day["date"] for day in seen if day["tone"] == "easy"), None)
    return {
        "start": today.isoformat(),
        "month": month,
        "easy": sum(1 for day in counted if day["date"].startswith(month) and day["tone"] == "easy"),
        "nearest": nearest,
    }


def teasers(user_id: int, tz: str | None = None) -> dict:
    user = get_user(user_id)
    result = {
        "lit": bool(user["sky"]),
        "chat": questions_of(user_id),
        "pair": pairs_in_short(user_id),
        "chart": None,
        "day": None,
        "week": None,
        "calendar": None,
    }
    # Without the birth data there is no chart, and nothing of it to tell.
    if user["birth"] is None:
        return result
    portrait = portrait_of(user_id)
    result["chart"] = {
        "chapters": portrait["total"],
        "titles": _titles(portrait["reading"]),
        "aspects": len(chart_of(user_id)["aspects"]),
    }
    result["day"] = _forecast(user_id, "day", tz)
    result["week"] = _forecast(user_id, "week", tz)
    result["calendar"] = _calendar(user_id, tz)
    return result
