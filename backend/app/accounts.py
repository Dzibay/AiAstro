from datetime import date, datetime, time, timezone

from psycopg.errors import UniqueViolation

from app.config import settings
from app.db import pool
from app.errors import DomainError
from app.places import timezone_at
from app.security import hash_password, verify_password

_DUMMY_HASH = hash_password("not-a-real-password")
_EARLIEST_BIRTH = date(1900, 1, 1)
_USER_COLUMNS = (
    "id, email, name, blocked, created_at, birth_date, birth_time, birth_place, birth_lat, birth_lon, birth_tz, sky_until"
)


def _clean_email(email: str) -> str:
    cleaned = email.strip().lower()
    if " " in cleaned or cleaned.count("@") != 1:
        raise DomainError("email")
    local, domain = cleaned.split("@", 1)
    if not local or "." not in domain or len(cleaned) > 254:
        raise DomainError("email")
    return cleaned


def _clean_birth(
    birth_date: date,
    birth_time: time | None,
    place: str | None,
    lat: float | None = None,
    lon: float | None = None,
) -> tuple:
    if not _EARLIEST_BIRTH <= birth_date <= date.today():
        raise DomainError("birth")
    # Minutes are all a chart needs; seconds would only pretend to a precision nobody has.
    clean_time = birth_time.replace(second=0, microsecond=0, tzinfo=None) if birth_time else None
    clean_place = " ".join((place or "").split())[:120]
    # Coordinates come only with a place picked from the suggestions, and always as a pair.
    if (lat is None) != (lon is None) or (lat is not None and not clean_place):
        raise DomainError("place")
    if lat is None:
        return birth_date, clean_time, clean_place, None, None, ""
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise DomainError("place")
    lat, lon = round(lat, 5), round(lon, 5)
    # The zone is found here, not taken from the browser: the chart has one source of truth.
    return birth_date, clean_time, clean_place, lat, lon, timezone_at(lat, lon)


def _public(row: dict) -> dict:
    birth = None
    if row["birth_date"] is not None:
        birth = {
            "date": row["birth_date"].isoformat(),
            "time": row["birth_time"].strftime("%H:%M") if row["birth_time"] else None,
            "place": row["birth_place"] or None,
            "lat": float(row["birth_lat"]) if row["birth_lat"] is not None else None,
            "lon": float(row["birth_lon"]) if row["birth_lon"] is not None else None,
            "tz": row["birth_tz"] or None,
        }
    return {
        "id": row["id"],
        "email": row["email"],
        "name": row["name"],
        "created_at": row["created_at"],
        "birth": birth,
        # «Небосвод»: the forecasts' text and the astrologer. The date is shown, the flag decides.
        "sky_until": row["sky_until"].isoformat() if row["sky_until"] else None,
        "sky": _sky_active(row["sky_until"]),
    }


def _sky_active(until: datetime | None) -> bool:
    return until is not None and until > datetime.now(timezone.utc)


def _require_web_secret() -> None:
    if not settings.web_session_secret:
        raise DomainError("unauthorized", 401)


def register(
    email: str,
    password: str,
    name: str,
    consent: bool,
    birth_date: date | None = None,
    birth_time: time | None = None,
    birth_place: str | None = None,
    birth_lat: float | None = None,
    birth_lon: float | None = None,
) -> dict:
    _require_web_secret()
    cleaned = _clean_email(email)
    if len(password) < 8:
        raise DomainError("password")
    # Email, name and birth data are personal data: no account without the consent.
    if not consent:
        raise DomainError("consent")
    if birth_date:
        birth = _clean_birth(birth_date, birth_time, birth_place, birth_lat, birth_lon)
    else:
        birth = (None, None, "", None, None, "")
    display = " ".join(name.split())[:80] or cleaned.split("@", 1)[0][:80]
    try:
        with pool.connection() as conn:
            row = conn.execute(
                f"""
                INSERT INTO users (
                    email, password_hash, name,
                    birth_date, birth_time, birth_place, birth_lat, birth_lon, birth_tz, consent_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                RETURNING {_USER_COLUMNS}
                """,
                (cleaned, hash_password(password), display, *birth),
            ).fetchone()
    except UniqueViolation as exc:
        raise DomainError("exists", 409) from exc
    return _public(row)


def authenticate(email: str, password: str) -> dict:
    _require_web_secret()
    try:
        cleaned = _clean_email(email)
    except DomainError:
        verify_password(password, _DUMMY_HASH)
        raise DomainError("unauthorized", 401) from None
    with pool.connection() as conn:
        row = conn.execute(
            f"""
            SELECT {_USER_COLUMNS}, password_hash
            FROM users
            WHERE email = %s
            """,
            (cleaned,),
        ).fetchone()
    if row is None:
        verify_password(password, _DUMMY_HASH)
        raise DomainError("unauthorized", 401)
    if not verify_password(password, row["password_hash"]):
        raise DomainError("unauthorized", 401)
    if row["blocked"]:
        raise DomainError("blocked", 403)
    return _public(row)


def get_user(user_id: int) -> dict:
    with pool.connection() as conn:
        row = conn.execute(
            f"""
            SELECT {_USER_COLUMNS}
            FROM users
            WHERE id = %s
            """,
            (user_id,),
        ).fetchone()
    if row is None:
        raise DomainError("unauthorized", 401)
    if row["blocked"]:
        raise DomainError("blocked", 403)
    return _public(row)


def set_birth(
    user_id: int,
    birth_date: date,
    birth_time: time | None,
    birth_place: str | None,
    birth_lat: float | None = None,
    birth_lon: float | None = None,
) -> dict:
    """Fills in or corrects the birth data; the consent was given at registration."""
    birth = _clean_birth(birth_date, birth_time, birth_place, birth_lat, birth_lon)
    with pool.connection() as conn:
        row = conn.execute(
            f"""
            UPDATE users
            SET birth_date = %s, birth_time = %s, birth_place = %s, birth_lat = %s, birth_lon = %s, birth_tz = %s
            WHERE id = %s AND NOT blocked
            RETURNING {_USER_COLUMNS}
            """,
            (*birth, user_id),
        ).fetchone()
    if row is None:
        raise DomainError("unauthorized", 401)
    return _public(row)


# ---- The person's own settings ----

def _checked(user_id: int, password: str) -> dict:
    """The person's row once the password is right: the email, the password and the account itself ask for it."""
    with pool.connection() as conn:
        row = conn.execute(
            f"SELECT {_USER_COLUMNS}, password_hash FROM users WHERE id = %s",
            (user_id,),
        ).fetchone()
    if row is None or row["blocked"]:
        raise DomainError("unauthorized", 401)
    if not verify_password(password, row["password_hash"]):
        raise DomainError("wrong_password", 403)
    return row


def set_name(user_id: int, name: str) -> dict:
    cleaned = " ".join(name.split())[:80]
    if not cleaned:
        raise DomainError("name")
    with pool.connection() as conn:
        row = conn.execute(
            f"UPDATE users SET name = %s WHERE id = %s AND NOT blocked RETURNING {_USER_COLUMNS}",
            (cleaned, user_id),
        ).fetchone()
    if row is None:
        raise DomainError("unauthorized", 401)
    return _public(row)


def set_email(user_id: int, email: str, password: str) -> dict:
    cleaned = _clean_email(email)
    _checked(user_id, password)
    try:
        with pool.connection() as conn:
            row = conn.execute(
                f"UPDATE users SET email = %s WHERE id = %s RETURNING {_USER_COLUMNS}",
                (cleaned, user_id),
            ).fetchone()
    except UniqueViolation as exc:
        raise DomainError("exists", 409) from exc
    return _public(row)


def set_password(user_id: int, current: str, password: str) -> None:
    if len(password) < 8:
        raise DomainError("password")
    _checked(user_id, current)
    with pool.connection() as conn:
        conn.execute("UPDATE users SET password_hash = %s WHERE id = %s", (hash_password(password), user_id))


def delete_account(user_id: int, password: str) -> None:
    """The account and everything of it: partners, purchases and the conversation go with it (ON DELETE CASCADE).

    The session is a signed token with no table behind it: once the row is gone it opens nothing.
    """
    _checked(user_id, password)
    with pool.connection() as conn:
        conn.execute("DELETE FROM users WHERE id = %s", (user_id,))


# ---- The operator's side ----

ADMIN_PAGE = 50
SKY_DAYS = 30


def list_users(query: str = "") -> list[dict]:
    """The newest accounts, or those whose email or name contains `query`."""
    # LIKE's own wildcards in the query are taken literally.
    cleaned = " ".join(query.split()).lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{cleaned}%"
    with pool.connection() as conn:
        rows = conn.execute(
            f"""
            SELECT {_USER_COLUMNS}
            FROM users
            WHERE lower(email) LIKE %s OR lower(name) LIKE %s
            ORDER BY created_at DESC, id DESC
            LIMIT %s
            """,
            (pattern, pattern, ADMIN_PAGE),
        ).fetchall()
    return [{**_public(row), "blocked": row["blocked"]} for row in rows]


def set_sky(user_id: int, days: int) -> dict:
    """Opens «Небосвод» for `days` more days (counted from its end if it is still on), or closes it with 0."""
    if days:
        until = "GREATEST(COALESCE(sky_until, now()), now()) + make_interval(days => %s)"
        params: tuple = (days, user_id)
    else:
        until, params = "NULL", (user_id,)
    with pool.connection() as conn:
        row = conn.execute(
            f"UPDATE users SET sky_until = {until} WHERE id = %s RETURNING {_USER_COLUMNS}",
            params,
        ).fetchone()
    if row is None:
        raise DomainError("missing", 404)
    return {**_public(row), "blocked": row["blocked"]}
