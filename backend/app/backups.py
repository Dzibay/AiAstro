"""Copies of the base on the operator's Яндекс Диск (admin → «Настройки → Копии базы»).

Once a day, after 04:00 Moscow time, pg_dump makes a compressed copy and WebDAV puts it into a folder
of the Disk; copies older than the keeping period are erased there — only after a new one has arrived.
A failed attempt is repeated an hour later, three times a day at most; each attempt is a row of
backup_runs, and a failure goes to the log as an error, so it reaches the journal «Ошибки» too.

The Disk wants an application password with access to files (WebDAV), not the Yandex password itself.
"""

import asyncio
import base64
import datetime as dt
import logging
import os
import re
import shutil
import subprocess
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

from app.config import settings
from app.db import pool
from app.errors import DomainError
from app.settings_store import BACKUP_KEEP_MAX, get_settings, setting

log = logging.getLogger("aiastro")

MOSCOW = ZoneInfo("Europe/Moscow")
HOUR = 4
CHECK_SECONDS = 300
RETRY_SECONDS = 3600
TRIES_A_DAY = 3
# However short the keeping period, the newest copies stay.
KEEP_AT_LEAST = 3
DUMP_SECONDS = 15 * 60
NET_SECONDS = 120
RUNS_KEPT_DAYS = 180
_NAME = re.compile(r"^astra-(\d{4}-\d{2}-\d{2})-\d{4}\.dump$")
_PROPFIND = (
    b'<?xml version="1.0" encoding="utf-8"?>'
    b'<d:propfind xmlns:d="DAV:"><d:prop><d:getcontentlength/><d:getlastmodified/><d:resourcetype/></d:prop></d:propfind>'
)

_lock = threading.Lock()


class BackupError(Exception):
    """What went wrong, in words for the operator."""


def _account() -> tuple[str, str, str] | None:
    data = get_settings()
    login, password = data.get("backup_login") or "", data.get("backup_password") or ""
    if not (login and password):
        return None
    return login, password, setting("backup_folder")


def keep_days() -> int:
    return min(int(setting("backup_keep")), BACKUP_KEEP_MAX)


# ---- The Disk ----

def _dav(method: str, path: str, account: tuple[str, str, str], *, body=None, headers: dict | None = None) -> tuple[int, bytes]:
    login, password, _ = account
    url = f"{settings.backup_webdav_url.rstrip('/')}/{urllib.parse.quote(path.strip('/'))}"
    request = urllib.request.Request(url, data=body, method=method)
    request.add_header("Authorization", "Basic " + base64.b64encode(f"{login}:{password}".encode()).decode())
    for key, value in (headers or {}).items():
        request.add_header(key, value)
    try:
        with urllib.request.urlopen(request, timeout=NET_SECONDS) as answer:
            return answer.status, answer.read()
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise BackupError("Яндекс Диск не принял логин или пароль приложения") from exc
        if exc.code == 507:
            raise BackupError("На Яндекс Диске не осталось места") from exc
        return exc.code, exc.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        raise BackupError(f"Яндекс Диск недоступен: {reason}") from exc


def _make_folder(account) -> None:
    code, _ = _dav("MKCOL", f"{account[2]}/", account)
    # 405 — the folder is there already.
    if code not in (200, 201, 405):
        raise BackupError(f"Папку «{account[2]}» на Диске не создать: ответ {code}")


def _upload(path: str, name: str, account) -> None:
    size = os.path.getsize(path)
    with open(path, "rb") as file:
        code, _ = _dav(
            "PUT", f"{account[2]}/{name}", account, body=file,
            headers={"Content-Type": "application/octet-stream", "Content-Length": str(size)},
        )
    if code not in (200, 201, 204):
        raise BackupError(f"Яндекс Диск не принял копию: ответ {code}")


def _list(account) -> list[dict]:
    """The site's copies in the folder, the newest first."""
    code, body = _dav("PROPFIND", f"{account[2]}/", account, body=_PROPFIND,
                      headers={"Depth": "1", "Content-Type": "application/xml; charset=utf-8"})
    if code == 404:
        return []
    if code != 207:
        raise BackupError(f"Список копий на Диске не получить: ответ {code}")
    items = []
    for response in ET.fromstring(body).iter("{DAV:}response"):
        name = urllib.parse.unquote((response.findtext("{DAV:}href") or "").rstrip("/").rsplit("/", 1)[-1])
        if not _NAME.match(name) or response.find(".//{DAV:}collection") is not None:
            continue
        size = response.findtext(".//{DAV:}getcontentlength")
        modified = response.findtext(".//{DAV:}getlastmodified")
        try:
            at = parsedate_to_datetime(modified).isoformat() if modified else None
        except (TypeError, ValueError):
            at = None
        items.append({"name": name, "size": int(size) if size and size.isdigit() else None, "at": at})
    return sorted(items, key=lambda item: item["name"], reverse=True)


def _prune(account) -> int:
    """Copies older than the keeping period leave the Disk; the newest few stay whatever their age."""
    edge = dt.datetime.now(MOSCOW).date() - dt.timedelta(days=keep_days())
    removed = 0
    for item in _list(account)[KEEP_AT_LEAST:]:
        if dt.date.fromisoformat(_NAME.match(item["name"]).group(1)) >= edge:
            continue
        code, _ = _dav("DELETE", f"{account[2]}/{item['name']}", account)
        if code in (200, 204, 404):
            removed += 1
        else:
            log.warning("Старая копия %s не стёрта: ответ %s", item["name"], code)
    return removed


# ---- The copy ----

def _dump(target: str) -> None:
    program = shutil.which(settings.backup_pg_dump)
    if program is None:
        raise BackupError("На сервере нет pg_dump — пересоберите образ backend")
    command = [
        program, "--format=custom", "--no-owner", "--no-privileges",
        "--host", settings.db_host, "--port", str(settings.db_port),
        "--username", settings.db_user, "--dbname", settings.db_name, "--file", target,
    ]
    try:
        done = subprocess.run(command, env={**os.environ, "PGPASSWORD": settings.db_password},
                              capture_output=True, timeout=DUMP_SECONDS, check=False)
    except subprocess.TimeoutExpired as exc:
        raise BackupError("pg_dump не уложился в 15 минут") from exc
    if done.returncode != 0:
        said = done.stderr.decode("utf-8", "replace").strip().splitlines()
        raise BackupError(f"pg_dump не сделал копию: {said[-1] if said else done.returncode}")


def _finish(run_id: int, ok: bool, size: int | None = None, error: str = "") -> None:
    with pool.connection() as conn:
        conn.execute(
            "UPDATE backup_runs SET finished_at = now(), ok = %s, size = %s, error = %s WHERE id = %s",
            (ok, size, error[:500], run_id),
        )


def _run(manual: bool) -> None:
    account = _account()
    if account is None:
        return
    name = f"astra-{dt.datetime.now(MOSCOW):%Y-%m-%d-%H%M}.dump"
    with pool.connection() as conn:
        run_id = conn.execute(
            "INSERT INTO backup_runs (manual, name) VALUES (%s, %s) RETURNING id", (manual, name)
        ).fetchone()["id"]
        conn.execute("DELETE FROM backup_runs WHERE started_at < now() - make_interval(days => %s)", (RUNS_KEPT_DAYS,))
    size = None
    try:
        with tempfile.TemporaryDirectory(prefix="astra-backup-") as folder:
            path = os.path.join(folder, name)
            _dump(path)
            size = os.path.getsize(path)
            _make_folder(account)
            _upload(path, name, account)
    except Exception as exc:  # noqa: BLE001 — whatever it was, the operator reads it in the admin and in «Ошибки»
        _finish(run_id, False, size, str(exc) if isinstance(exc, BackupError) else f"{type(exc).__name__}: {exc}")
        log.error("Копия базы не сохранена: %s", exc, exc_info=None if isinstance(exc, BackupError) else exc)
        return
    _finish(run_id, True, size)
    log.info("Копия базы на Диске: %s, %s байт", name, size)
    try:
        _prune(account)
    except Exception as exc:  # noqa: BLE001 — the copy is there; the old ones wait for the next night
        log.warning("Старые копии не разобраны: %s", exc)


def _work(manual: bool) -> None:
    try:
        _run(manual)
    except Exception as exc:  # noqa: BLE001 — the base itself is down: only the log
        log.error("Копия базы не сохранена: %s", exc, exc_info=exc)
    finally:
        _lock.release()


def start(manual: bool) -> None:
    """A copy in its own thread: the night's or the operator's «Сделать копию сейчас»; one at a time."""
    if _account() is None:
        raise DomainError("backup_off", 409)
    if not _lock.acquire(blocking=False):
        raise DomainError("backup_busy", 409)
    threading.Thread(target=_work, args=(manual,), name="backup", daemon=True).start()


def _due() -> bool:
    if _account() is None:
        return False
    now = dt.datetime.now(MOSCOW)
    if now.hour < HOUR:
        return False
    with pool.connection() as conn:
        row = conn.execute(
            """
            SELECT coalesce(bool_or(ok), false) AS done, count(*) AS tries, max(started_at) AS last
            FROM backup_runs WHERE started_at >= %s
            """,
            (now.replace(hour=0, minute=0, second=0, microsecond=0),),
        ).fetchone()
    if row["done"] or row["tries"] >= TRIES_A_DAY:
        return False
    return row["last"] is None or (now - row["last"]).total_seconds() >= RETRY_SECONDS


async def loop() -> None:
    """Every few minutes: is tonight's copy due? A copy cut off by a restart is marked as such."""
    try:
        with pool.connection() as conn:
            conn.execute(
                "UPDATE backup_runs SET finished_at = now(), ok = false, error = 'Прервана перезапуском сервера' WHERE finished_at IS NULL"
            )
    except Exception as exc:  # noqa: BLE001
        log.warning("Прерванные копии не отмечены: %s", exc)
    while True:
        await asyncio.sleep(CHECK_SECONDS)
        try:
            if await asyncio.to_thread(_due):
                start(manual=False)
        except DomainError:
            pass
        except Exception as exc:  # noqa: BLE001 — a bad check must not stop the next one
            log.error("Копия базы не запущена: %s", exc, exc_info=exc)


# ---- For the admin ----

def status() -> dict:
    with pool.connection() as conn:
        runs = conn.execute(
            "SELECT id, started_at, finished_at, manual, ok, name, size, error FROM backup_runs ORDER BY started_at DESC LIMIT 10"
        ).fetchall()
        last = conn.execute(
            "SELECT started_at, name, size FROM backup_runs WHERE ok ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
    return {
        "on": _account() is not None,
        "running": _lock.locked(),
        "hour": HOUR,
        "keep": keep_days(),
        "folder": setting("backup_folder"),
        "db": {"name": settings.db_name, "user": settings.db_user},
        "last": last,
        "runs": runs,
    }


def copies() -> dict:
    account = _account()
    if account is None:
        raise DomainError("backup_off", 409)
    try:
        return {"items": _list(account), "error": ""}
    except BackupError as exc:
        return {"items": [], "error": str(exc)}
