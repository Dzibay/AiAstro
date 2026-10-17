import time

from app.db import pool
from app.errors import DomainError

TTL_SECONDS = 10

FIELDS = {
    "site_name": ("Название", "Астра"),
    "tagline": ("Подзаголовок", "Натальная карта обычным языком"),
    "support_email": ("Почта поддержки", ""),
}

_cache: dict[str, str] = {}
_loaded = False
_loaded_at = 0.0


def get_settings() -> dict[str, str]:
    global _loaded, _loaded_at
    now = time.monotonic()
    if _loaded and now - _loaded_at < TTL_SECONDS:
        return dict(_cache)
    with pool.connection() as conn:
        rows = conn.execute("SELECT key, value FROM app_settings").fetchall()
    _cache.clear()
    for row in rows:
        _cache[row["key"]] = row["value"]
    _loaded = True
    _loaded_at = now
    return dict(_cache)


def public_config(fallback_name: str) -> dict[str, str]:
    data = get_settings()
    return {
        "site_name": data.get("site_name") or fallback_name or FIELDS["site_name"][1],
        "tagline": data.get("tagline") or FIELDS["tagline"][1],
        "support_email": data.get("support_email") or "",
    }


def list_editable() -> list[dict[str, str]]:
    data = get_settings()
    items = []
    for key, (label, default) in FIELDS.items():
        items.append({"key": key, "label": label, "value": data.get(key, default)})
    return items


def set_setting(key: str, value: str) -> dict[str, str]:
    global _loaded, _loaded_at
    if key not in FIELDS:
        raise DomainError("setting")
    cleaned = " ".join(value.split())
    if key == "support_email":
        cleaned = cleaned.lower()
    if len(cleaned) > 300:
        raise DomainError("setting")
    with pool.connection() as conn:
        conn.execute(
            """
            INSERT INTO app_settings (key, value) VALUES (%s, %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """,
            (key, cleaned),
        )
    _cache[key] = cleaned
    _loaded = True
    _loaded_at = time.monotonic()
    label = FIELDS[key][0]
    return {"key": key, "label": label, "value": cleaned}
