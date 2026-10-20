from fastapi import Header, HTTPException

from app.errors import DomainError
from app.security import read_admin_session, read_web_session


def _bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="unauthorized")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="unauthorized")
    return token


def require_web_user(authorization: str | None = Header(default=None)) -> int:
    token = _bearer(authorization)
    try:
        return read_web_session(token)
    except DomainError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.code) from exc


def optional_web_user(authorization: str | None = Header(default=None)) -> int | None:
    """The person if a valid session came along; an open page works without it."""
    try:
        return read_web_session(_bearer(authorization))
    except (HTTPException, DomainError):
        return None


def require_admin(authorization: str | None = Header(default=None)) -> None:
    token = _bearer(authorization)
    try:
        read_admin_session(token)
    except DomainError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.code) from exc


def as_http(exc: DomainError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.code)
