from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import as_http, require_admin
from app.errors import DomainError
from app.security import check_admin_password, make_admin_session
from app.settings_store import list_editable, set_setting

router = APIRouter(prefix="/admin")


class LoginIn(BaseModel):
    password: str = Field(max_length=200)


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
