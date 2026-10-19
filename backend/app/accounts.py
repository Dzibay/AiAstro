from datetime import date, time

from psycopg.errors import UniqueViolation

from app.config import settings
from app.db import pool
from app.errors import DomainError
from app.security import hash_password, verify_password

_DUMMY_HASH = hash_password("not-a-real-password")
_EARLIEST_BIRTH = date(1900, 1, 1)
_USER_COLUMNS = "id, email, name, blocked, created_at, birth_date, birth_time, birth_place"


def _clean_email(email: str) -> str:
    cleaned = email.strip().lower()
    if " " in cleaned or cleaned.count("@") != 1:
        raise DomainError("email")
    local, domain = cleaned.split("@", 1)
    if not local or "." not in domain or len(cleaned) > 254:
        raise DomainError("email")
    return cleaned


def _clean_birth(birth_date: date, birth_time: time | None, place: str | None) -> tuple:
    if not _EARLIEST_BIRTH <= birth_date <= date.today():
        raise DomainError("birth")
    # Minutes are all a chart needs; seconds would only pretend to a precision nobody has.
    clean_time = birth_time.replace(second=0, microsecond=0, tzinfo=None) if birth_time else None
    clean_place = " ".join((place or "").split())[:120]
    return birth_date, clean_time, clean_place


def _public(row: dict) -> dict:
    birth = None
    if row["birth_date"] is not None:
        birth = {
            "date": row["birth_date"].isoformat(),
            "time": row["birth_time"].strftime("%H:%M") if row["birth_time"] else None,
            "place": row["birth_place"] or None,
        }
    return {
        "id": row["id"],
        "email": row["email"],
        "name": row["name"],
        "created_at": row["created_at"],
        "birth": birth,
    }


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
) -> dict:
    _require_web_secret()
    cleaned = _clean_email(email)
    if len(password) < 8:
        raise DomainError("password")
    # Email, name and birth data are personal data: no account without the consent.
    if not consent:
        raise DomainError("consent")
    birth = _clean_birth(birth_date, birth_time, birth_place) if birth_date else (None, None, "")
    display = " ".join(name.split())[:80] or cleaned.split("@", 1)[0][:80]
    try:
        with pool.connection() as conn:
            row = conn.execute(
                f"""
                INSERT INTO users (email, password_hash, name, birth_date, birth_time, birth_place, consent_at)
                VALUES (%s, %s, %s, %s, %s, %s, now())
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


def set_birth(user_id: int, birth_date: date, birth_time: time | None, birth_place: str | None) -> dict:
    """For those who chose «Заполню позже»: the consent was given at registration."""
    birth = _clean_birth(birth_date, birth_time, birth_place)
    with pool.connection() as conn:
        row = conn.execute(
            f"""
            UPDATE users
            SET birth_date = %s, birth_time = %s, birth_place = %s
            WHERE id = %s AND NOT blocked
            RETURNING {_USER_COLUMNS}
            """,
            (*birth, user_id),
        ).fetchone()
    if row is None:
        raise DomainError("unauthorized", 401)
    return _public(row)
