from fastapi import Depends, Header, HTTPException

from app.accounts import is_member
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


def require_member(user_id: int = Depends(require_web_user)) -> int:
    """The person whose email is confirmed: the cabinet opens after the link in the letter."""
    try:
        confirmed = is_member(user_id)
    except DomainError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.code) from exc
    if not confirmed:
        raise HTTPException(status_code=403, detail="unconfirmed")
    return user_id


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
