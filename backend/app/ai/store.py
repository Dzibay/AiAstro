"""What the ИИ-астролог keeps: the journal of its calls and what they cost, and the person's memory.

Days and months are Moscow ones, as everywhere in the admin.
"""

from psycopg.types.json import Jsonb

from app.db import pool

TZ = "Europe/Moscow"
# Facts the person told about themself, newest last; the oldest go when there are more.
MEMORY = 12

_DAY = f"date_trunc('day', now() AT TIME ZONE '{TZ}') AT TIME ZONE '{TZ}'"
_MONTH = f"date_trunc('month', now() AT TIME ZONE '{TZ}') AT TIME ZONE '{TZ}'"


def log(conn, *, user_id: int | None = None, message_id: int | None = None, kind: str = "chat", category: str = "",
        source: str = "", model: str = "", prompt: int = 0, cached: int = 0, output: int = 0, cost: float = 0.0,
        ms: int = 0, error: str = "", flagged: bool = False, note: str = "") -> None:
    conn.execute(
        """
        INSERT INTO ai_runs (user_id, message_id, kind, category, source, model, prompt_tokens, cached_tokens,
                             output_tokens, cost, ms, error, flagged, note)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (user_id, message_id, kind, category, source, model, prompt, cached, output, cost, ms, error[:500], flagged, note[:500]),
    )


def month_spent(conn=None) -> float:
    """Roubles spent on the model since the start of this Moscow month, the admin's own tries included."""
    query = f"SELECT coalesce(sum(cost), 0) AS spent FROM ai_runs WHERE created_at >= {_MONTH}"
    if conn is not None:
        return float(conn.execute(query).fetchone()["spent"])
    with pool.connection() as own:
        return float(own.execute(query).fetchone()["spent"])


def calls_today(conn, user_id: int) -> int:
    """How many times the model was asked for this person today, whatever came of it."""
    row = conn.execute(
        f"SELECT count(*) AS n FROM ai_runs WHERE user_id = %s AND kind = 'chat' AND model <> '' AND created_at >= {_DAY}",
        (user_id,),
    ).fetchone()
    return row["n"]


def memory_of(user_id: int, conn=None) -> list[str]:
    query, args = "SELECT facts FROM chat_memory WHERE user_id = %s", (user_id,)
    if conn is not None:
        row = conn.execute(query, args).fetchone()
    else:
        with pool.connection() as own:
            row = own.execute(query, args).fetchone()
    return [fact for fact in (row["facts"] if row else []) if isinstance(fact, str)]


def remember(conn, user_id: int, facts: list[str]) -> None:
    """New facts after the old ones; a fact already known is not written twice."""
    if not facts:
        return
    known = memory_of(user_id, conn)
    seen = {fact.casefold() for fact in known}
    for fact in facts:
        if fact.casefold() not in seen:
            known.append(fact)
            seen.add(fact.casefold())
    conn.execute(
        """
        INSERT INTO chat_memory (user_id, facts, updated_at) VALUES (%s, %s, now())
        ON CONFLICT (user_id) DO UPDATE SET facts = EXCLUDED.facts, updated_at = now()
        """,
        (user_id, Jsonb(known[-MEMORY:])),
    )


def forget(user_id: int) -> None:
    with pool.connection() as conn:
        conn.execute("DELETE FROM chat_memory WHERE user_id = %s", (user_id,))
