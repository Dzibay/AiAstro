from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.accounts import SKY_DAYS, list_users, set_sky
from app.api.deps import as_http, require_admin
from app.errors import DomainError
from app.partners import admin_partners, set_bought
from app.security import check_admin_password, make_admin_session
from app.settings_store import list_editable, set_setting

router = APIRouter(prefix="/admin")


class LoginIn(BaseModel):
    password: str = Field(max_length=200)


class SkyIn(BaseModel):
    # 30 opens «Небосвод» for a month more, 0 closes it.
    days: int = Field(ge=0, le=SKY_DAYS)


class BoughtIn(BaseModel):
    bought: bool


class SettingIn(BaseModel):
    key: str = Field(max_length=64)
    value: str = Field(max_length=300)


@router.post("/login")
def login(body: LoginIn) -> dict:
    if not check_admin_password(body.password):
        raise as_http(DomainError("unauthorized", 401))
    try:
        token = make_admin_session()
    except DomainError as exc:
        raise as_http(exc) from exc
    return {"token": token}


@router.get("/me", dependencies=[Depends(require_admin)])
def me() -> dict:
    return {"role": "admin"}


@router.get("/settings", dependencies=[Depends(require_admin)])
def settings_list() -> dict:
    try:
        return {"items": list_editable()}
    except DomainError as exc:
        raise as_http(exc) from exc


@router.put("/settings", dependencies=[Depends(require_admin)])
def settings_update(body: SettingIn) -> dict:
    try:
        return set_setting(body.key, body.value)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.get("/users", dependencies=[Depends(require_admin)])
def users_list(q: str = Query(default="", max_length=100)) -> dict:
    return {"items": list_users(q)}


@router.put("/users/{user_id}/sky", dependencies=[Depends(require_admin)])
def users_sky(user_id: int, body: SkyIn) -> dict:
    try:
        return set_sky(user_id, body.days)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.get("/users/{user_id}/partners", dependencies=[Depends(require_admin)])
def users_partners(user_id: int) -> dict:
    return {"items": admin_partners(user_id)}


@router.put("/users/{user_id}/partners/{partner_id}/purchase", dependencies=[Depends(require_admin)])
def users_purchase(user_id: int, partner_id: int, body: BoughtIn) -> dict:
    """Marks the reading of this pair as bought (or takes the mark back) until payment is connected."""
    try:
        return set_bought(user_id, partner_id, body.bought)
    except DomainError as exc:
        raise as_http(exc) from exc
