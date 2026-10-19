import datetime as dt

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.accounts import authenticate, get_user, register, set_birth
from app.api.deps import as_http, require_web_user
from app.errors import DomainError
from app.security import make_web_session

router = APIRouter(prefix="/web")


class BirthIn(BaseModel):
    date: dt.date
    time: dt.time | None = None
    place: str | None = Field(default=None, max_length=200)


class RegisterIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=200)
    name: str = Field(default="", max_length=80)
    consent: bool = False
    birth: BirthIn | None = None


class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=200)


@router.post("/register")
def register_user(body: RegisterIn) -> dict:
    birth = body.birth
    try:
        user = register(
            body.email,
            body.password,
            body.name,
            body.consent,
            birth.date if birth else None,
            birth.time if birth else None,
            birth.place if birth else None,
        )
        token = make_web_session(user["id"])
    except DomainError as exc:
        raise as_http(exc) from exc
    return {"token": token, "user": user}


@router.post("/login")
def login_user(body: LoginIn) -> dict:
    try:
        user = authenticate(body.email, body.password)
        token = make_web_session(user["id"])
    except DomainError as exc:
        raise as_http(exc) from exc
    return {"token": token, "user": user}


@router.get("/me")
def me(user_id: int = Depends(require_web_user)) -> dict:
    try:
        return get_user(user_id)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.put("/me/birth")
def update_birth(body: BirthIn, user_id: int = Depends(require_web_user)) -> dict:
    try:
        return set_birth(user_id, body.date, body.time, body.place)
    except DomainError as exc:
        raise as_http(exc) from exc
