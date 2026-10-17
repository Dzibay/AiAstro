from psycopg.errors import UniqueViolation

from app.config import settings
from app.db import pool
from app.errors import DomainError
from app.security import hash_password, verify_password

_DUMMY_HASH = hash_password("not-a-real-password")


def _clean_email(email: str) -> str:
    cleaned = email.strip().lower()
    if " " in cleaned or cleaned.count("@") != 1:
        raise DomainError("email")
    local, domain = cleaned.split("@", 1)
    if not local or "." not in domain or len(cleaned) > 254:
        raise DomainError("email")
    return cleaned


def _public(row: dict) -> dict:
    return {
        "id": row["id"],
        "email": row["email"],
        "name": row["name"],
        "created_at": row["created_at"],
    }


def _require_web_secret() -> None:
    if not settings.web_session_secret:
        raise DomainError("unauthorized", 401)


def register(email: str, password: str, name: str) -> dict:
    _require_web_secret()
    cleaned = _clean_email(email)
    if len(password) < 8:
        raise DomainError("password")
    display = " ".join(name.split())[:80] or cleaned.split("@", 1)[0][:80]
    try:
        with pool.connection() as conn:
            row = conn.execute(
                """
                INSERT INTO users (email, password_hash, name)
                VALUES (%s, %s, %s)
                RETURNING id, email, name, created_at
                """,
                (cleaned, hash_password(password), display),
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
            """
            SELECT id, email, name, password_hash, blocked, created_at
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
            """
            SELECT id, email, name, blocked, created_at
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
