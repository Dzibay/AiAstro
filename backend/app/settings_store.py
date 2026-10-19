import time

from app.db import pool
from app.errors import DomainError

TTL_SECONDS = 10

# key: (label, default, group). The admin page lays the groups out under their own headings.
FIELDS = {
    "site_name": ("Название", "Астра", "site"),
    "tagline": ("Подзаголовок", "Натальная карта обычным языком", "site"),
    "support_email": ("Почта поддержки", "", "site"),
    # Whole roubles as text; an empty price keeps «от … ₽» on the site and that tariff unpaid.
    "price_sky": ("«Небосвод» на месяц, ₽", "", "prices"),
    "price_sky_3": ("«Небосвод» на 3 месяца, ₽", "", "prices"),
    "price_sky_12": ("«Небосвод» на 12 месяцев, ₽", "", "prices"),
    "price_synastry": ("Разбор пары, ₽", "", "prices"),
    "price_synastry_sky": ("Разбор пары с «Небосводом», ₽", "", "prices"),
    # ЮKassa: payment opens once both are set. The receipt codes are ЮKassa's own (54-ФЗ).
    "yookassa_shop_id": ("shopId магазина", "", "pay"),
    "yookassa_secret_key": ("Секретный ключ", "", "pay"),
    "receipt_vat_code": ("Ставка НДС в чеке, код ЮKassa (1 — без НДС)", "1", "pay"),
    "receipt_tax_system": ("Система налогообложения, код ЮKassa 1–6 (пусто — не передавать)", "", "pay"),
}
PRICES = ("price_sky", "price_sky_3", "price_sky_12", "price_synastry", "price_synastry_sky")
# Never sent back to the page: the admin sees only whether it is set.
SECRETS = ("yookassa_secret_key",)

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


def public_config(fallback_name: str) -> dict:
    data = get_settings()
    return {
        "site_name": data.get("site_name") or fallback_name or FIELDS["site_name"][1],
        "tagline": data.get("tagline") or FIELDS["tagline"][1],
        "support_email": data.get("support_email") or "",
        "prices": {key.removeprefix("price_"): data.get(key) or "" for key in PRICES},
        "pay": payments_on(data),
    }


def payments_on(data: dict[str, str] | None = None) -> bool:
    data = data if data is not None else get_settings()
    return bool(data.get("yookassa_shop_id") and data.get("yookassa_secret_key"))


def setting(key: str) -> str:
    return get_settings().get(key) or FIELDS[key][1]


def list_editable() -> list[dict[str, str]]:
    data = get_settings()
    items = []
    for key, (label, default, group) in FIELDS.items():
        value = data.get(key, default)
        if key in SECRETS:
            items.append({"key": key, "label": label, "group": group, "value": "", "secret": True, "filled": bool(value)})
        else:
            items.append({"key": key, "label": label, "group": group, "value": value})
    return items


def _digits(value: str, longest: int) -> bool:
    return value.isascii() and value.isdigit() and len(value) <= longest


def set_setting(key: str, value: str) -> dict[str, str]:
    global _loaded, _loaded_at
    if key not in FIELDS:
        raise DomainError("setting")
    cleaned = " ".join(value.split())
    if key == "support_email":
        cleaned = cleaned.lower()
    if key in PRICES and cleaned and not _digits(cleaned, 7):
        raise DomainError("setting")
    if key == "yookassa_shop_id" and cleaned and not _digits(cleaned, 12):
        raise DomainError("setting")
    # live_… or test_…: the key ЮKassa gives in «Интеграция → Ключи API».
    if key == "yookassa_secret_key" and cleaned and not (
        cleaned.isascii() and " " not in cleaned and cleaned.startswith(("live_", "test_")) and len(cleaned) <= 120
    ):
        raise DomainError("setting")
    if key == "receipt_vat_code" and not (_digits(cleaned, 2) and 1 <= int(cleaned) <= 12):
        raise DomainError("setting")
    if key == "receipt_tax_system" and cleaned and not (_digits(cleaned, 1) and 1 <= int(cleaned) <= 6):
        raise DomainError("setting")
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
    label, _, group = FIELDS[key]
    if key in SECRETS:
        return {"key": key, "label": label, "group": group, "value": "", "secret": True, "filled": bool(cleaned)}
    return {"key": key, "label": label, "group": group, "value": cleaned}
