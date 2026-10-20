import hashlib
import secrets
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
    "id, email, name, blocked, created_at, birth_date, birth_time, birth_place, birth_lat, birth_lon, birth_tz, sky_until, mail_notes, birth_edits"
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
        "mail_notes": row["mail_notes"],
        # One correction of the birth data is the person's own; the next ones go through the support.
        "birth_locked": row["birth_date"] is not None and row["birth_edits"] >= BIRTH_EDITS,
    }


# A chart, a pair and a forecast are bought for these data: changed freely, they would open any other.
BIRTH_EDITS = 1


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
    operator: bool = False,
) -> dict:
    """Fills in or corrects the birth data; the consent was given at registration.

    The first time they are free, and so is a time added where it was unknown; a correction of
    them, once. `operator` is the support's hand from the admin panel, with no count.
    """
    birth = _clean_birth(birth_date, birth_time, birth_place, birth_lat, birth_lon)
    current = get_user(user_id)["birth"]
    with pool.connection() as conn:
        edits = conn.execute("SELECT birth_edits FROM users WHERE id = %s", (user_id,)).fetchone()["birth_edits"]
        free = operator or current is None or (
            current["time"] is None and birth[1] is not None and current["date"] == birth[0].isoformat()
            and (current["place"] or "") == birth[2]
        )
        if not free and edits >= BIRTH_EDITS:
            raise DomainError("birth_locked", 409)
        row = conn.execute(
            f"""
            UPDATE users
            SET birth_date = %s, birth_time = %s, birth_place = %s, birth_lat = %s, birth_lon = %s, birth_tz = %s,
                birth_edits = birth_edits + %s
            WHERE id = %s AND NOT blocked
            RETURNING {_USER_COLUMNS}
            """,
            (*birth, 0 if free else 1, user_id),
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


def set_mail_notes(user_id: int, on: bool) -> dict:
    with pool.connection() as conn:
        row = conn.execute(
            f"UPDATE users SET mail_notes = %s WHERE id = %s AND NOT blocked RETURNING {_USER_COLUMNS}",
            (on, user_id),
        ).fetchone()
    if row is None:
        raise DomainError("unauthorized", 401)
    return _public(row)


# ---- A forgotten password ----

RESET_MINUTES = 60
# One letter in this many minutes: the form cannot be turned into a way to flood someone's mail.
RESET_PAUSE_MINUTES = 2


def _reset_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def request_reset(email: str) -> dict | None:
    """The link's token and the person's name, or None when no letter should go.

    The page says the same either way, so the form does not tell whose mail is registered.
    """
    cleaned = _clean_email(email)
    with pool.connection() as conn:
        row = conn.execute("SELECT id, name, blocked FROM users WHERE email = %s", (cleaned,)).fetchone()
        if row is None or row["blocked"]:
            return None
        recent = conn.execute(
            "SELECT 1 FROM password_resets WHERE user_id = %s AND created_at > now() - make_interval(mins => %s)",
            (row["id"], RESET_PAUSE_MINUTES),
        ).fetchone()
        if recent:
            return None
        token = secrets.token_urlsafe(32)
        conn.execute("DELETE FROM password_resets WHERE user_id = %s AND expires_at < now()", (row["id"],))
        conn.execute(
            "INSERT INTO password_resets (token_hash, user_id, expires_at) VALUES (%s, %s, now() + make_interval(mins => %s))",
            (_reset_hash(token), row["id"], RESET_MINUTES),
        )
    return {"email": cleaned, "name": row["name"], "token": token}


def reset_password(token: str, password: str) -> dict:
    """The new password by the letter's link; the link is spent, and so are the person's other links."""
    if len(password) < 8:
        raise DomainError("password")
    if not token or len(token) > 100:
        raise DomainError("reset")
    _require_web_secret()
    with pool.connection() as conn:
        found = conn.execute(
            "DELETE FROM password_resets WHERE token_hash = %s RETURNING user_id, expires_at",
            (_reset_hash(token),),
        ).fetchone()
        if found is None or found["expires_at"] < datetime.now(timezone.utc):
            raise DomainError("reset")
        row = conn.execute(
            f"UPDATE users SET password_hash = %s WHERE id = %s AND NOT blocked RETURNING {_USER_COLUMNS}",
            (hash_password(password), found["user_id"]),
        ).fetchone()
        if row is None:
            raise DomainError("reset")
        conn.execute("DELETE FROM password_resets WHERE user_id = %s", (found["user_id"],))
    return _public(row)


def delete_account(user_id: int, password: str) -> list[dict]:
    """The account and everything of it: partners and the conversation go with it (ON DELETE CASCADE).

    A pair bought by the person stays bought for the partner who has it too: the purchase loses
    only its payer. The session is a signed token with no table behind it: once the row is gone it opens nothing.
    Gives the partners to write to: [{user_id, partner_id}].
    """
    _checked(user_id, password)
    return _remove(user_id)


def _remove(user_id: int) -> list[dict]:
    with pool.connection() as conn:
        others = conn.execute(
            """
            UPDATE partners o SET news = 'left', news_at = now()
            FROM partners m
            WHERE m.user_id = %s AND o.pair_id = m.pair_id AND o.id <> m.id AND o.joined_at IS NOT NULL
            RETURNING o.id AS partner_id, o.user_id
            """,
            (user_id,),
        ).fetchall()
        gone = conn.execute("DELETE FROM users WHERE id = %s RETURNING id", (user_id,)).fetchone()
    if gone is None:
        raise DomainError("missing", 404)
    return others


# ---- The operator's side ----

ADMIN_PAGE = 50
SKY_DAYS = 30
# The operator's longest single extension: a year, as the longest plan.
SKY_MAX_DAYS = 366

# The users' list filters: everyone, «Небосвод» on, no birth date yet, paid at least once.
USER_FILTERS = {
    "": "TRUE",
    "sky": "u.sky_until > now()",
    "nobirth": "u.birth_date IS NULL",
    "paid": "EXISTS (SELECT 1 FROM payments pa WHERE pa.user_id = u.id AND pa.status = 'succeeded')",
}


def _like(query: str) -> str:
    # LIKE's own wildcards in the query are taken literally.
    cleaned = " ".join(query.split()).lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{cleaned}%"


def _operator_view(row: dict) -> dict:
    return {
        **_public(row),
        "blocked": row["blocked"],
        "pairs": row.get("pairs", 0),
        "paid": row.get("paid", 0),
    }


_OPERATOR_COLUMNS = ", ".join(f"u.{column.strip()}" for column in _USER_COLUMNS.split(",")) + """,
    (SELECT count(*) FROM partners p WHERE p.user_id = u.id) AS pairs,
    (SELECT COALESCE(sum(pa.amount), 0) FROM payments pa WHERE pa.user_id = u.id AND pa.status = 'succeeded') AS paid"""


def list_users(query: str = "", state: str = "", offset: int = 0) -> dict:
    """The newest accounts, or those whose email or name contains `query`, a page at a time."""
    if state not in USER_FILTERS:
        raise DomainError("state")
    pattern = _like(query)
    with pool.connection() as conn:
        rows = conn.execute(
            f"""
            SELECT {_OPERATOR_COLUMNS}
            FROM users u
            WHERE (lower(u.email) LIKE %s OR lower(u.name) LIKE %s) AND {USER_FILTERS[state]}
            ORDER BY u.created_at DESC, u.id DESC
            LIMIT %s OFFSET %s
            """,
            (pattern, pattern, ADMIN_PAGE + 1, offset),
        ).fetchall()
    return {"items": [_operator_view(row) for row in rows[:ADMIN_PAGE]], "more": len(rows) > ADMIN_PAGE}


def operator_user(user_id: int) -> dict:
    with pool.connection() as conn:
        row = conn.execute(f"SELECT {_OPERATOR_COLUMNS} FROM users u WHERE u.id = %s", (user_id,)).fetchone()
    if row is None:
        raise DomainError("missing", 404)
    return _operator_view(row)


def set_sky(user_id: int, days: int) -> dict:
    """Opens «Небосвод» for `days` more days (counted from its end if it is still on), or closes it with 0."""
    if days:
        until = "GREATEST(COALESCE(sky_until, now()), now()) + make_interval(days => %s)"
        params: tuple = (days, user_id)
    else:
        until, params = "NULL", (user_id,)
    return _write_sky(until, params)


def set_sky_until(user_id: int, day: date) -> dict:
    """«Небосвод» till the end of this day, Moscow time; a day in the past closes it.

    The last second of the day, not the next midnight: the cabinet shows the date of sky_until.
    """
    return _write_sky("((%s::date + interval '23:59:59') AT TIME ZONE 'Europe/Moscow')", (day, user_id))


def _write_sky(until: str, params: tuple) -> dict:
    with pool.connection() as conn:
        row = conn.execute(
            f"UPDATE users SET sky_until = {until} WHERE id = %s RETURNING id",
            params,
        ).fetchone()
    if row is None:
        raise DomainError("missing", 404)
    return operator_user(params[-1])


def admin_delete(user_id: int) -> list[dict]:
    """The operator deletes an account the same way the person would, without the password."""
    return _remove(user_id)
