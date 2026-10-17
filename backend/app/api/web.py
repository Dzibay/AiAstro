from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.accounts import authenticate, get_user, register
from app.api.deps import as_http, require_web_user
from app.errors import DomainError
from app.security import make_web_session

router = APIRouter(prefix="/web")


class RegisterIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=200)
    name: str = Field(default="", max_length=80)


class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=200)


@router.post("/register")
def register_user(body: RegisterIn) -> dict:
    try:
        user = register(body.email, body.password, body.name)
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
