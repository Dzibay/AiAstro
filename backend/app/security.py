import hashlib
import hmac
import secrets
import time

from app.config import settings
from app.errors import DomainError

_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), _ITERATIONS
    ).hex()
    return f"pbkdf2_sha256${_ITERATIONS}${salt}${digest}"


def _equal(left: str, right: str) -> bool:
    try:
        return hmac.compare_digest(left.encode(), right.encode())
    except (ValueError, TypeError):
        return False


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, rounds, salt, digest = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        check = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), int(rounds)
        ).hex()
        return _equal(check, digest)
    except (ValueError, TypeError):
        return False


def check_admin_password(password: str) -> bool:
    expected = settings.admin_password
    if not expected:
        return False
    return _equal(password, expected)


def _sign(secret: str, payload: str) -> str:
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def sign_code(email: str, code: str) -> str:
    """The letter's six digits as the database keeps them: bound to the address, nothing without the secret."""
    return _sign(settings.web_session_secret or "", f"code.{email}.{code}")


def same_code(left: str, right: str) -> bool:
    return _equal(left, right)


def make_web_session(user_id: int) -> str:
    if not settings.web_session_secret:
        raise DomainError("unauthorized", 401)
    expires = int(time.time()) + settings.session_ttl_seconds
    payload = f"{user_id}.{expires}"
    return f"{payload}.{_sign(settings.web_session_secret, payload)}"


def read_web_session(token: str) -> int:
    secret = settings.web_session_secret
    if not secret or token.count(".") < 2:
        raise DomainError("unauthorized", 401)
    user_id_raw, exp_raw, signature = token.split(".", 2)
    if not user_id_raw.isdigit() or not exp_raw.isdigit():
        raise DomainError("unauthorized", 401)
    expected = _sign(secret, f"{user_id_raw}.{exp_raw}")
    if not _equal(signature, expected):
        raise DomainError("unauthorized", 401)
    if int(exp_raw) < int(time.time()):
        raise DomainError("expired", 401)
    return int(user_id_raw)


def make_admin_session() -> str:
    if not settings.admin_session_secret:
        raise DomainError("unauthorized", 401)
    expires = int(time.time()) + settings.session_ttl_seconds
    payload = f"admin.{expires}"
    return f"{expires}.{_sign(settings.admin_session_secret, payload)}"


def read_admin_session(token: str) -> None:
    secret = settings.admin_session_secret
    if not secret or "." not in token:
        raise DomainError("unauthorized", 401)
    exp_raw, signature = token.split(".", 1)
    if not exp_raw.isdigit():
        raise DomainError("unauthorized", 401)
    expected = _sign(secret, f"admin.{exp_raw}")
    if not _equal(signature, expected):
        raise DomainError("unauthorized", 401)
    if int(exp_raw) < int(time.time()):
        raise DomainError("expired", 401)
