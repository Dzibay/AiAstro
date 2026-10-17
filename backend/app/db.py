import logging
import time
from pathlib import Path

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import settings

log = logging.getLogger("aiastro")

pool = ConnectionPool(
    settings.dsn,
    min_size=1,
    max_size=10,
    open=False,
    kwargs={"row_factory": dict_row},
)


def _schema_path() -> Path:
    candidates = [
        Path("/app/database/init.sql"),
        Path(__file__).resolve().parents[2] / "database" / "init.sql",
        Path(__file__).resolve().parents[1] / "database" / "init.sql",
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError("database/init.sql")


def _statements(script: str) -> list[str]:
    parts: list[str] = []
    buffer: list[str] = []
    for line in script.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        buffer.append(line)
        if stripped.endswith(";"):
            statement = "\n".join(buffer).strip()
            if statement:
                parts.append(statement)
            buffer = []
    tail = "\n".join(buffer).strip()
    if tail:
        parts.append(tail)
    return parts


def ensure_schema() -> None:
    statements = _statements(_schema_path().read_text(encoding="utf-8"))
    delay = 0.5
    last_error: Exception | None = None
    for attempt in range(20):
        try:
            if pool.closed:
                pool.open(wait=True, timeout=3)
            with pool.connection() as conn:
                for statement in statements:
                    conn.execute(statement)
            return
        except Exception as exc:
            last_error = exc
            log.warning("База ещё не готова, попытка %s", attempt + 1)
            time.sleep(delay)
            delay = min(delay * 1.5, 5)
    raise RuntimeError("schema") from last_error


def close_pool() -> None:
    if not pool.closed:
        pool.close()
