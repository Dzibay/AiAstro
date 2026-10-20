"""The conversation with the astrologer: the history in the database, the answers from the interpreter.

Without «Небосвод» a person has TRIAL questions. They are counted here, from the same table, so
a reload or a second tab gives no more; the lock on the person's row lets one question in at a time.
"""

import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.accounts import get_user
from app.astro import forecast
from app.astro.texts import as_reading, chat_suggestions, interpreter, reading_text
from app.charts import chart_of
from app.db import pool
from app.errors import DomainError
from app.partners import pairs_of

TRIAL = 2
LENGTH = 600
# How much of the history the page shows, and how much of it the interpreter reads.
SHOWN = 80
CONTEXT = 12


def _public(row: dict) -> dict:
    """An answer is kept as a reading in JSON: the page gets it whole, and as plain text besides."""
    public = {"id": row["id"], "role": row["role"], "text": row["text"], "created_at": row["created_at"].isoformat()}
    if row["role"] == "astrologer":
        public["reading"] = as_reading(row["text"])
        public["text"] = reading_text(public["reading"])
    return public


def _plain(row: dict) -> dict:
    """The history as the interpreter reads it: text, whoever wrote it."""
    text = reading_text(as_reading(row["text"])) if row["role"] == "astrologer" else row["text"]
    return {"role": row["role"], "text": text}


def _asked(conn, user_id: int) -> int:
    row = conn.execute(
        "SELECT count(*) AS n FROM chat_messages WHERE user_id = %s AND role = 'user'", (user_id,)
    ).fetchone()
    return row["n"]


def _left(sky: bool, asked: int) -> int | None:
    """The trial questions left, or None with «Небосвод»: then there is no count."""
    return None if sky else max(0, TRIAL - asked)


def history(user_id: int) -> dict:
    """The last messages, oldest first, the questions to start with and what is left of the trial."""
    user = get_user(user_id)
    with pool.connection() as conn:
        rows = conn.execute(
            "SELECT id, role, text, created_at FROM chat_messages WHERE user_id = %s ORDER BY id DESC LIMIT %s",
            (user_id, SHOWN),
        ).fetchall()
        asked = _asked(conn, user_id)
    return {
        "items": [_public(row) for row in reversed(rows)],
        "left": _left(user["sky"], asked),
        "trial": TRIAL,
        # The suggestions speak of the person's own planets: without the chart there are none.
        "suggestions": chat_suggestions(chart_of(user_id)) if user["birth"] else [],
    }


def _context(user_id: int, user: dict, chart: dict) -> dict:
    """What the astrologer knows besides the chart: today's sky over it, the month ahead, the pairs."""
    zone = user["birth"].get("tz") or "UTC"
    try:
        today = datetime.now(ZoneInfo(zone)).date()
    except (ValueError, KeyError, OSError):
        zone, today = "UTC", datetime.now(timezone.utc).date()
    return {
        "today": forecast.build(chart, today, "day", zone),
        "month": forecast.month(chart, today, zone),
        "partners": pairs_of(user_id, chart),
    }


def ask(user_id: int, text: str) -> dict:
    """Writes the question and its answer; returns both and what is left of the trial."""
    question = "\n".join(" ".join(line.split()) for line in text.strip().splitlines()).strip()
    if not question:
        raise DomainError("question")
    if len(question) > LENGTH:
        raise DomainError("question_long")
    user = get_user(user_id)
    chart = chart_of(user_id)
    # Read before the lock: the sky of the month takes a moment, and the row should not wait for it.
    context = _context(user_id, user, chart)
    with pool.connection() as conn:
        conn.execute("SELECT id FROM users WHERE id = %s FOR UPDATE", (user_id,))
        asked = _asked(conn, user_id)
        if not user["sky"] and asked >= TRIAL:
            raise DomainError("trial_over", 402)
        recent = conn.execute(
            "SELECT role, text FROM chat_messages WHERE user_id = %s ORDER BY id DESC LIMIT %s",
            (user_id, CONTEXT),
        ).fetchall()
        answer = interpreter.chat([*map(_plain, reversed(recent)), {"role": "user", "text": question}], chart, context)
        rows = [
            conn.execute(
                "INSERT INTO chat_messages (user_id, role, text) VALUES (%s, %s, %s) RETURNING id, role, text, created_at",
                (user_id, role, body),
            ).fetchone()
            for role, body in (("user", question), ("astrologer", json.dumps(answer, ensure_ascii=False)))
        ]
    return {"items": [_public(row) for row in rows], "left": _left(user["sky"], asked + 1)}
