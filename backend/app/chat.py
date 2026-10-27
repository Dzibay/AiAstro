"""The conversation with the ИИ-астролог: the history in the database, the answers from the model or the templates.

Without «Небосвод» a person has TRIAL questions; everyone has the admin's daily limit. Only a
question that gets an answer counts: a turn away from the chart, an attempt on the role, rudeness
or a cry for help does not. Three turns away within STRIKE_WINDOW pause the talk for PAUSE minutes.

The model thinks for seconds, so it is never asked inside a transaction: the question is written
first as «pending» under the lock on the person's row (a second tab gets «busy»), the model is
asked with no lock held, and the answer is written in a second short transaction. When the model
is off, out of budget or fails, the templates answer, as before the model.
"""

import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.accounts import get_user
from app.ai import guard, replies, store, talk
from app.astro import forecast
from app.astro.texts import as_reading, chat_suggestions, interpreter, reading_text
from app.charts import chart_of
from app.db import pool
from app.errors import DomainError
from app.partners import pairs_of

TRIAL = 2
LENGTH = 600
# How much of the history the page shows, and how much of it the model reads.
SHOWN = 80
CONTEXT = 12
STRIKE_WINDOW = "30 minutes"
STRIKES = 3
PAUSE = 10
# A question without its answer this long is taken as lost: another may be asked.
PENDING = "3 minutes"
# The model is asked at most this many times the daily limit a day: the turns that do not count cost too.
CALLS = 2

_DAY = f"date_trunc('day', now() AT TIME ZONE '{store.TZ}') AT TIME ZONE '{store.TZ}'"


def _public(row: dict) -> dict:
    """An answer is kept as a reading in JSON: the page gets it whole, and as plain text besides."""
    public = {"id": row["id"], "role": row["role"], "text": row["text"], "created_at": row["created_at"].isoformat()}
    if row["role"] == "astrologer":
        public["reading"] = guard.mend(as_reading(row["text"]))
        public["text"] = reading_text(public["reading"])
    return public


def _plain(row: dict) -> dict:
    """The history as the model reads it: text, whoever wrote it; the model's own key apart."""
    if row["role"] != "astrologer":
        return {"role": row["role"], "text": row["text"]}
    reading = guard.mend(as_reading(row["text"]))
    if reading.get("kind") == "talk":
        return {"role": "astrologer", "text": "\n\n".join(part["text"] for part in reading["parts"]), "key": reading.get("key", "")}
    return {"role": "astrologer", "text": reading_text(reading)}


def _talk_reading(reply: dict) -> dict:
    """The model's answer (or the service's own) as a reading: paragraphs without labels, the key, what to ask next."""
    return {
        "kind": "talk",
        "essence": "",
        "parts": [{"label": "", "text": paragraph} for paragraph in reply["answer"].split("\n\n") if paragraph],
        "key": reply.get("key", ""),
        "follow": reply.get("follow", []),
    }


def _left(sky: bool, asked: int) -> int | None:
    """The trial questions left, or None with «Небосвод»: then there is no count."""
    return None if sky else max(0, TRIAL - asked)


def _counts(conn, user_id: int) -> tuple[int, int]:
    """The questions that counted: in all, and today (a Moscow day)."""
    row = conn.execute(
        f"""
        SELECT count(*) AS asked, count(*) FILTER (WHERE created_at >= {_DAY}) AS today
        FROM chat_messages WHERE user_id = %s AND role = 'user' AND counted
        """,
        (user_id,),
    ).fetchone()
    return row["asked"], row["today"]


def _pause(conn, user_id: int, lock: bool = False) -> datetime | None:
    row = conn.execute(
        "SELECT chat_pause_until AS until FROM users WHERE id = %s" + (" FOR UPDATE" if lock else ""), (user_id,)
    ).fetchone()
    until = row["until"] if row else None
    return until if until and until > datetime.now(timezone.utc) else None


def _state(conn, user: dict, daily: int) -> dict:
    """What the page shows around the field: the trial left, today's questions left, the pause."""
    asked, today = _counts(conn, user["id"])
    pause = _pause(conn, user["id"])
    return {
        "left": _left(user["sky"], asked),
        "today_left": max(0, daily - today),
        "daily": daily,
        "pause_until": pause.isoformat() if pause else None,
    }


def history(user_id: int) -> dict:
    """The last messages, oldest first, the questions to start with, the trial and the day left."""
    user = get_user(user_id)
    cfg = talk.config()
    with pool.connection() as conn:
        rows = conn.execute(
            "SELECT id, role, text, created_at FROM chat_messages WHERE user_id = %s ORDER BY id DESC LIMIT %s",
            (user_id, SHOWN),
        ).fetchall()
        state = _state(conn, user, cfg["daily"])
    return {
        "items": [_public(row) for row in reversed(rows)],
        "trial": TRIAL,
        # The suggestions speak of the person's own planets: without the chart there are none.
        "suggestions": chat_suggestions(chart_of(user_id)) if user["birth"] else [],
        **state,
    }


def questions_of(user_id: int) -> dict:
    """The questions in numbers, for the «Небосвод» page: asked so far, the trial, the day's limit and what it still holds."""
    user = get_user(user_id)
    daily = talk.config()["daily"]
    with pool.connection() as conn:
        asked, today = _counts(conn, user_id)
    return {"asked": asked, "trial": TRIAL, "left": _left(user["sky"], asked), "daily": daily, "today_left": max(0, daily - today)}


def _context(user_id: int, user: dict, chart: dict) -> dict:
    """What the astrologer knows besides the chart: today's sky over it, the month ahead, the pairs, the date."""
    zone = user["birth"].get("tz") or "UTC"
    try:
        today = datetime.now(ZoneInfo(zone)).date()
    except (ValueError, KeyError, OSError):
        zone, today = "UTC", datetime.now(timezone.utc).date()
    return {
        "date": today,
        "today": forecast.build(chart, today, "day", zone),
        "month": forecast.month(chart, today, zone),
        "partners": pairs_of(user_id, chart),
    }


def _insert(conn, user_id: int, role: str, text: str, category: str, counted: bool, source: str) -> dict:
    return conn.execute(
        """
        INSERT INTO chat_messages (user_id, role, text, category, counted, source) VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id, role, text, created_at
        """,
        (user_id, role, text, category, counted, source),
    ).fetchone()


def _strike(conn, user_id: int) -> bool:
    """Counts the turns away from the chart since the last pause; the third within the window starts a new one."""
    row = conn.execute(
        f"""
        SELECT count(*) AS n FROM chat_messages m JOIN users u ON u.id = m.user_id
        WHERE m.user_id = %s AND m.role = 'user' AND m.category = ANY(%s)
          AND m.created_at > now() - interval '{STRIKE_WINDOW}'
          AND m.created_at > coalesce(u.chat_pause_until, '-infinity')
        """,
        (user_id, list(guard.STRIKES)),
    ).fetchone()
    if row["n"] < STRIKES:
        return False
    conn.execute(f"UPDATE users SET chat_pause_until = now() + interval '{PAUSE} minutes' WHERE id = %s", (user_id,))
    return True


def _clean(text: str) -> str:
    question = "\n".join(" ".join(line.split()) for line in text.strip().splitlines()).strip()
    if not question:
        raise DomainError("question")
    if len(question) > LENGTH:
        raise DomainError("question_long")
    return question


def ask(user_id: int, text: str) -> dict:
    """Writes the question and its answer; returns both and what is left of the trial, the day and the pause."""
    question = _clean(text)
    user = get_user(user_id)
    chart = chart_of(user_id)
    cfg = talk.config()
    caught = guard.classify(question)
    if caught:
        return _guarded(user, chart, question, caught, cfg)

    # Read before the lock: the sky of the month takes a moment, and the row should not wait for it.
    context = _context(user_id, user, chart)
    with pool.connection() as conn:
        if _pause(conn, user_id, lock=True):
            raise DomainError("chat_pause", 429)
        waiting = conn.execute(
            f"SELECT 1 FROM chat_messages WHERE user_id = %s AND category = 'pending' AND created_at > now() - interval '{PENDING}'",
            (user_id,),
        ).fetchone()
        if waiting:
            raise DomainError("busy", 409)
        asked, today = _counts(conn, user_id)
        if not user["sky"] and asked >= TRIAL:
            raise DomainError("trial_over", 402)
        if today >= cfg["daily"]:
            raise DomainError("day_limit", 429)
        mine = _insert(conn, user_id, "user", question, "pending", True, "")
        recent = conn.execute(
            """
            SELECT role, text FROM chat_messages
            WHERE user_id = %s AND id < %s AND category IN ('', 'astro', 'smalltalk')
            ORDER BY id DESC LIMIT %s
            """,
            (user_id, mine["id"], CONTEXT),
        ).fetchall()
        memory = store.memory_of(user_id, conn)
        model = cfg["trial_model"] if not user["sky"] and cfg["trial_model"] else cfg["model"]
        use_model = (
            talk.serves(cfg, user["email"])
            and store.month_spent(conn) < cfg["budget"]
            and store.calls_today(conn, user_id) < CALLS * cfg["daily"]
        )
    try:
        return _answer(user, chart, context, question, mine, [*map(_plain, reversed(recent))], memory, cfg,
                       model if use_model else "")
    except Exception:
        # The question would hang as «pending» and hold the next one for a while: it goes, the error stays.
        with pool.connection() as conn:
            conn.execute("DELETE FROM chat_messages WHERE id = %s", (mine["id"],))
        raise


def _answer(user: dict, chart: dict, context: dict, question: str, mine: dict, recent: list[dict], memory: list[str],
            cfg: dict, model: str) -> dict:
    """Asks the model (when `model` is set) with no lock held, falls back to the templates, writes the answer."""
    found = talk.ask(cfg, model, talk.request(cfg, chart, context, memory, recent, question, context["date"])) if model else None
    data = found.data if found else None
    if data is None:
        category, source = "astro", "stub"
        reading = interpreter.chat([*recent, {"role": "user", "text": question}], chart, context)
    elif data["category"] == "crisis":
        category, source = "crisis", "guard"
        reading = _talk_reading(replies.crisis(cfg["helpline"]))
    else:
        category, source = data["category"], "ai"
        reading = _talk_reading(data)
    with pool.connection() as conn:
        conn.execute("SELECT id FROM users WHERE id = %s FOR UPDATE", (user["id"],))
        row = conn.execute(
            "UPDATE chat_messages SET category = %s, counted = %s WHERE id = %s RETURNING id, role, text, created_at",
            (category, category == "astro", mine["id"]),
        ).fetchone()
        if category in guard.STRIKES and _strike(conn, user["id"]):
            reading["parts"].append({"label": "", "text": replies.PAUSE.format(minutes=PAUSE)})
            reading["follow"] = []
        answer = _insert(conn, user["id"], "astrologer", json.dumps(reading, ensure_ascii=False), category, False, source)
        if found:
            store.log(conn, user_id=user["id"], message_id=answer["id"], category=category, source=source, model=found.model,
                      prompt=found.prompt, cached=found.cached, output=found.output, cost=found.cost, ms=found.ms,
                      error=found.error, flagged=found.flagged)
        if data and category in guard.TALK:
            store.remember(conn, user["id"], data["remember"])
        state = _state(conn, user, cfg["daily"])
    return {"items": [_public(row), _public(answer)], **state}


def _guarded(user: dict, chart: dict, question: str, category: str, cfg: dict) -> dict:
    """A message the code caught: the service answers it itself, the model never sees it, nothing is counted.

    A cry for help is answered even during a pause; an attempt on the role or rudeness is a turn away."""
    if category == "crisis":
        reading = _talk_reading(replies.crisis(cfg["helpline"]))
    else:
        reading = _talk_reading(replies.redirect(category, chat_suggestions(chart)))
    with pool.connection() as conn:
        if _pause(conn, user["id"], lock=True) and category != "crisis":
            raise DomainError("chat_pause", 429)
        mine = _insert(conn, user["id"], "user", question, category, False, "")
        if category in guard.STRIKES and _strike(conn, user["id"]):
            reading = _talk_reading(replies.redirect(category, [], PAUSE))
        answer = _insert(conn, user["id"], "astrologer", json.dumps(reading, ensure_ascii=False), category, False, "guard")
        store.log(conn, user_id=user["id"], message_id=answer["id"], category=category, source="guard")
        state = _state(conn, user, cfg["daily"])
    return {"items": [_public(mine), _public(answer)], **state}


def transcript(user_id: int, limit: int = 300) -> dict:
    """The operator's view of one person's conversation: every turn with its topic and source, and the memory."""
    with pool.connection() as conn:
        rows = conn.execute(
            """
            SELECT m.id, m.role, m.text, m.created_at, m.category, m.counted, m.source,
                   r.model, r.cost, r.ms, r.error, r.flagged
            FROM chat_messages m LEFT JOIN ai_runs r ON r.message_id = m.id
            WHERE m.user_id = %s ORDER BY m.id DESC LIMIT %s
            """,
            (user_id, limit),
        ).fetchall()
        memory = store.memory_of(user_id, conn)
        pause = _pause(conn, user_id)
    items = []
    for row in reversed(rows):
        item = _public(row)
        item.update(category=row["category"], counted=row["counted"], source=row["source"])
        if row["model"] is not None:
            item.update(model=row["model"], cost=float(row["cost"]), ms=row["ms"], error=row["error"], flagged=row["flagged"])
        items.append(item)
    return {"items": items, "memory": memory, "pause_until": pause.isoformat() if pause else None}


def unpause(user_id: int) -> None:
    with pool.connection() as conn:
        conn.execute("UPDATE users SET chat_pause_until = NULL WHERE id = %s", (user_id,))
