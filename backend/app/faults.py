"""The journal of errors for the operator (admin → «Ошибки»): what broke on the server and in the
visitors' browsers. The same error from the same place is one line with a count, the first and the
last time; one marked as fixed that happens again comes back to the open ones, marked as returned.

A record never holds up what it describes: it goes to a queue, and one thread writes it to the base.
When the base itself is down, the error stays only in the server's log.
"""

import hashlib
import logging
import queue
import re
import threading
import time
import traceback
from pathlib import Path

from app.db import pool
from app.errors import DomainError

log = logging.getLogger("aiastro")
# The journal's own troubles go here: below ERROR, so they never come back into the journal.
_quiet = logging.getLogger("aiastro.faults")

PAGE = 50
KEEP_DAYS = 90
STATES = ("open", "resolved", "all")
_SIDES = ("back", "front")
_LIMITS = {"kind": 80, "message": 600, "place": 240, "path": 240, "detail": 12000, "agent": 300}

_queue: queue.Queue = queue.Queue(maxsize=500)
_started = False
_start_lock = threading.Lock()
_APP = Path(__file__).resolve().parent
# Numbers, ids and hashes vary from one occurrence to the next: without them it is the same error.
_VARYING = re.compile(r"0x[0-9a-f]+|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|\d+", re.I)


def _cut(field: str, value) -> str:
    return str(value or "")[: _LIMITS[field]]


def _signature(side: str, kind: str, message: str, place: str) -> str:
    same = "|".join((side, kind, _VARYING.sub("N", message)[:200], _VARYING.sub("N", place)))
    return hashlib.sha1(same.encode("utf-8")).hexdigest()


def record(side: str, kind: str, message: str, *, place: str = "", path: str = "", detail: str = "",
           agent: str = "", user_id: int | None = None) -> None:
    """One occurrence, for the journal; past a full queue it is dropped, never waited for."""
    if side not in _SIDES:
        return
    item = {
        "side": side,
        "kind": _cut("kind", kind) or "error",
        "message": _cut("message", message).strip() or "(без текста)",
        "place": _cut("place", place),
        "path": _cut("path", path),
        "detail": _cut("detail", detail),
        "agent": _cut("agent", agent),
        "user_id": user_id,
    }
    item["signature"] = _signature(side, item["kind"], item["message"], item["place"])
    _start()
    try:
        _queue.put_nowait(item)
    except queue.Full:
        pass


def _where(tb) -> str:
    """The deepest line of the site's own code in the traceback: where to look first."""
    place = last = ""
    for frame in traceback.extract_tb(tb):
        last = f"{Path(frame.filename).name}:{frame.lineno} {frame.name}"
        try:
            relative = Path(frame.filename).resolve().relative_to(_APP.parent)
        except ValueError:
            continue
        place = f"{relative.as_posix()}:{frame.lineno} {frame.name}"
    # Not in the site's code at all (a library, a thread): at least the line where it fell.
    return place or last


def from_exception(exc: BaseException, *, path: str = "", user_id: int | None = None) -> None:
    """An exception no endpoint caught: the person got «Сервис временно недоступен»."""
    record(
        "back",
        type(exc).__name__,
        str(exc),
        place=_where(exc.__traceback__),
        path=path,
        detail="".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
        user_id=user_id,
    )


class _Journal(logging.Handler):
    """The site's own log.error / log.exception lines: a letter that did not leave, a payment that does not match."""

    def __init__(self) -> None:
        super().__init__(level=logging.ERROR)

    def emit(self, line: logging.LogRecord) -> None:
        if line.name.startswith(_quiet.name):
            return
        try:
            exc = line.exc_info[1] if line.exc_info else None
            try:
                relative = Path(line.pathname).resolve().relative_to(_APP.parent).as_posix()
            except ValueError:
                relative = line.module
            record(
                "back",
                type(exc).__name__ if exc else "log",
                line.getMessage(),
                place=_where(exc.__traceback__) if exc else f"{relative}:{line.lineno} {line.funcName}",
                detail="".join(traceback.format_exception(*line.exc_info)) if line.exc_info else "",
            )
        except Exception:  # noqa: BLE001 — a log line must never fail what wrote it
            pass


def install() -> None:
    """At the start of the backend: the log's errors go to the journal too."""
    if not any(isinstance(handler, _Journal) for handler in log.handlers):
        log.addHandler(_Journal())
    _start()


def _start() -> None:
    global _started
    if _started:
        return
    with _start_lock:
        if not _started:
            threading.Thread(target=_work, name="faults", daemon=True).start()
            _started = True


def _work() -> None:
    swept = 0.0
    while True:
        try:
            item = _queue.get(timeout=3600)
        except queue.Empty:
            item = None
        try:
            if item:
                _write(item)
            if time.monotonic() - swept > 24 * 3600:
                _sweep()
                swept = time.monotonic()
        except Exception as exc:  # noqa: BLE001 — the base is down: the error stays in the server log only
            _quiet.warning("Ошибка не записана в журнал: %s", exc)


def _write(item: dict) -> None:
    with pool.connection() as conn:
        conn.execute(
            """
            INSERT INTO faults (signature, side, kind, message, place, path, detail, agent, user_id)
            VALUES (%(signature)s, %(side)s, %(kind)s, %(message)s, %(place)s, %(path)s, %(detail)s, %(agent)s, %(user_id)s)
            ON CONFLICT (signature) DO UPDATE SET
                count = faults.count + 1,
                last_at = now(),
                message = EXCLUDED.message,
                path = EXCLUDED.path,
                detail = CASE WHEN EXCLUDED.detail <> '' THEN EXCLUDED.detail ELSE faults.detail END,
                agent = EXCLUDED.agent,
                user_id = COALESCE(EXCLUDED.user_id, faults.user_id),
                returned = faults.returned OR faults.resolved_at IS NOT NULL,
                resolved_at = NULL
            """,
            item,
        )


def _sweep() -> None:
    """Fixed errors not seen for three months leave the journal."""
    with pool.connection() as conn:
        conn.execute(
            "DELETE FROM faults WHERE resolved_at IS NOT NULL AND last_at < now() - make_interval(days => %s)",
            (KEEP_DAYS,),
        )


# ---- For the admin ----

_FIELDS = "f.id, f.side, f.kind, f.message, f.place, f.path, f.count, f.first_at, f.last_at, f.resolved_at, f.returned"


def open_count() -> int:
    with pool.connection() as conn:
        return conn.execute("SELECT count(*) AS n FROM faults WHERE resolved_at IS NULL").fetchone()["n"]


def listing(q: str = "", state: str = "open", offset: int = 0) -> dict:
    if state not in STATES:
        raise DomainError("state", 400)
    where, params = [], []
    if state == "open":
        where.append("f.resolved_at IS NULL")
    elif state == "resolved":
        where.append("f.resolved_at IS NOT NULL")
    if q.strip():
        where.append("(f.message ILIKE %s OR f.place ILIKE %s OR f.path ILIKE %s OR f.kind ILIKE %s)")
        like = f"%{q.strip()}%"
        params += [like] * 4
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    with pool.connection() as conn:
        rows = conn.execute(
            f"SELECT {_FIELDS} FROM faults f {clause} ORDER BY f.last_at DESC LIMIT %s OFFSET %s",
            (*params, PAGE + 1, offset),
        ).fetchall()
        totals = conn.execute(
            """
            SELECT count(*) FILTER (WHERE resolved_at IS NULL) AS open,
                   count(*) FILTER (WHERE resolved_at IS NULL AND last_at > now() - interval '1 day') AS day,
                   coalesce(sum(count) FILTER (WHERE last_at > now() - interval '1 day'), 0) AS times
            FROM faults
            """
        ).fetchone()
    return {"items": rows[:PAGE], "more": len(rows) > PAGE, "totals": totals}


def detail(fault_id: int) -> dict:
    with pool.connection() as conn:
        row = conn.execute(
            f"""
            SELECT {_FIELDS}, f.detail, f.agent, f.user_id, u.email
            FROM faults f LEFT JOIN users u ON u.id = f.user_id
            WHERE f.id = %s
            """,
            (fault_id,),
        ).fetchone()
    if row is None:
        raise DomainError("missing", 404)
    return row


def set_resolved(fault_id: int | None, resolved: bool) -> int:
    """One error (or, with no id, every open one) marked as fixed, or back to the open ones."""
    with pool.connection() as conn:
        if fault_id is None:
            done = conn.execute("UPDATE faults SET resolved_at = now() WHERE resolved_at IS NULL")
        else:
            done = conn.execute(
                "UPDATE faults SET resolved_at = CASE WHEN %s THEN now() END, returned = returned AND NOT %s WHERE id = %s",
                (resolved, resolved, fault_id),
            )
            if done.rowcount == 0:
                raise DomainError("missing", 404)
        return done.rowcount
