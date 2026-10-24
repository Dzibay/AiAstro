import re
import time

from app.ai.models import DEFAULT_MODEL, MODELS
from app.ai.prompt import DEFAULT_EXAMPLES, DEFAULT_STYLE
from app.db import pool
from app.errors import DomainError

TTL_SECONDS = 10

# key: (label, default, group). The admin page lays the groups out under their own headings.
FIELDS = {
    "site_name": ("Название", "Астра", "site"),
    "tagline": ("Подзаголовок", "Натальная карта обычным языком", "site"),
    "support_email": ("Почта поддержки", "", "site"),
    # Kept without «@»: the site makes t.me/… of it; empty — no Telegram on the site.
    "support_telegram": ("Telegram поддержки — имя пользователя, например @astra_help", "", "site"),
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
    # SMTP: letters go out once the server and the sender's address are set.
    "smtp_host": ("SMTP-сервер", "", "mail"),
    "smtp_port": ("Порт (465 — SSL, 587 — STARTTLS)", "465", "mail"),
    "smtp_user": ("Логин", "", "mail"),
    "smtp_password": ("Пароль", "", "mail"),
    "mail_from": ("Адрес отправителя (пусто — логин)", "", "mail"),
    # ИИ-астролог (Yandex AI Studio): off — отвечают шаблоны, test — модель только для почт из списка, on — для всех.
    "ai_mode": ("Режим", "off", "ai"),
    "ai_testers": ("Почты тестировщиков через запятую", "", "ai"),
    "ai_api_key": ("API-ключ сервисного аккаунта", "", "ai"),
    "ai_folder": ("ID каталога", "", "ai"),
    "ai_model": ("Модель", DEFAULT_MODEL, "ai"),
    # Пусто — та же модель; без «Небосвода» человек задаёт два пробных вопроса, их можно отдать модели сильнее.
    "ai_trial_model": ("Модель для пробных вопросов (пусто — та же)", "", "ai"),
    "ai_daily_limit": ("Вопросов в день на человека", "20", "ai"),
    "ai_month_budget": ("Бюджет на месяц, ₽ (по нему модель уступает шаблонам)", "1000", "ai"),
    "ai_helpline": ("Телефон психологической помощи в кризисном ответе", "8-800-333-44-34", "ai"),
    "ai_style": ("Стиль ответов", DEFAULT_STYLE, "ai"),
    "ai_examples": ("Примеры вопросов и ответов", DEFAULT_EXAMPLES, "ai"),
    # Копии базы на Яндекс Диск по WebDAV: включаются, когда заданы логин и пароль приложения.
    "backup_login": ("Логин Яндекса (почта или имя)", "", "backup"),
    "backup_password": ("Пароль приложения для «Файлы (WebDAV)»", "", "backup"),
    "backup_folder": ("Папка на Диске", "astra-backups", "backup"),
    "backup_keep": ("Сколько дней хранить копии (не больше 30)", "14", "backup"),
}
PRICES = ("price_sky", "price_sky_3", "price_sky_12", "price_synastry", "price_synastry_sky")
# Never sent back to the page: the admin sees only whether it is set.
SECRETS = ("yookassa_secret_key", "smtp_password", "ai_api_key", "backup_password")
# Copies of the base live no longer than this many days (see backups.keep_days).
BACKUP_KEEP_MAX = 30
# Long texts: the line breaks stay, the length is theirs.
LONG = {"ai_style": 4000, "ai_examples": 6000, "ai_testers": 2000}
AI_MODES = ("off", "test", "on")

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
        "support_telegram": data.get("support_telegram") or "",
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


def _long(value: str) -> str:
    """Line breaks kept, spaces within a line folded, no more than one empty line in a row."""
    lines = [" ".join(line.split()) for line in value.replace("\r", "").split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def set_setting(key: str, value: str) -> dict[str, str]:
    global _loaded, _loaded_at
    if key not in FIELDS:
        raise DomainError("setting")
    # A password may hold spaces of its own; the long texts keep their lines; everything else folds them.
    if key == "smtp_password":
        cleaned = value.strip()
    elif key in LONG:
        cleaned = _long(value)
    else:
        cleaned = " ".join(value.split())
    if key in ("support_email", "mail_from", "smtp_host", "ai_testers"):
        cleaned = cleaned.lower()
    # @name, t.me/name or the whole link: only the name is kept.
    if key == "support_telegram":
        cleaned = re.sub(r"^(https?://)?(www\.)?(t\.me|telegram\.me)/", "", cleaned).lstrip("@").strip("/")
        if cleaned and not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{3,31}", cleaned):
            raise DomainError("setting")
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
    if key == "smtp_port" and not (_digits(cleaned, 5) and 1 <= int(cleaned) <= 65535):
        raise DomainError("setting")
    if key == "smtp_host" and cleaned and not (cleaned.isascii() and " " not in cleaned):
        raise DomainError("setting")
    if key == "mail_from" and cleaned and not (" " not in cleaned and cleaned.count("@") == 1):
        raise DomainError("setting")
    if key == "ai_mode" and cleaned not in AI_MODES:
        raise DomainError("setting")
    if key == "ai_testers" and cleaned and not all(
        part.count("@") == 1 and " " not in part for part in re.split(r"[,;\s]+", cleaned) if part
    ):
        raise DomainError("setting")
    # The key of AI Studio is one ASCII word; the folder is like b1g…
    if key == "ai_api_key" and cleaned and not (cleaned.isascii() and " " not in cleaned and len(cleaned) <= 300):
        raise DomainError("setting")
    if key == "ai_folder" and cleaned and not (cleaned.isascii() and cleaned.isalnum() and len(cleaned) <= 40):
        raise DomainError("setting")
    if key == "ai_model" and cleaned not in MODELS:
        raise DomainError("setting")
    if key == "ai_trial_model" and cleaned and cleaned not in MODELS:
        raise DomainError("setting")
    if key == "ai_daily_limit" and not (_digits(cleaned, 3) and 1 <= int(cleaned) <= 500):
        raise DomainError("setting")
    if key == "ai_month_budget" and not _digits(cleaned, 7):
        raise DomainError("setting")
    if key == "ai_helpline" and cleaned and not re.fullmatch(r"[\d\s()+-]{3,30}", cleaned):
        raise DomainError("setting")
    if key == "backup_login":
        cleaned = cleaned.lower()
        if cleaned and not re.fullmatch(r"[a-z0-9._@+-]{2,100}", cleaned):
            raise DomainError("setting")
    if key == "backup_password" and cleaned and not (cleaned.isascii() and " " not in cleaned and len(cleaned) <= 100):
        raise DomainError("setting")
    # One folder in the root of the Disk; empty — the default one.
    if key == "backup_folder" and cleaned and not re.fullmatch(r"\w[\w .-]{0,59}", cleaned):
        raise DomainError("setting")
    # The privacy policy promises a deleted account is gone within 30 days — from the copies too.
    if key == "backup_keep" and not (_digits(cleaned, 2) and 1 <= int(cleaned) <= BACKUP_KEEP_MAX):
        raise DomainError("setting")
    if len(cleaned) > LONG.get(key, 300):
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
