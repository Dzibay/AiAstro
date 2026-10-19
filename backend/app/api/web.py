import datetime as dt

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from app.accounts import authenticate, delete_account, get_user, register, set_birth, set_email, set_name, set_password
from app.api.deps import as_http, require_web_user
from app.charts import chart_item, chart_of, forecast_of, month_of
from app.chat import LENGTH, ask, history
from app.errors import DomainError
from app.partners import create_partner, delete_partner, fill_invite, invite, list_partners, open_invite, synastry_of
from app.places import search
from app.security import make_web_session

router = APIRouter(prefix="/web")


class BirthIn(BaseModel):
    date: dt.date
    time: dt.time | None = None
    place: str | None = Field(default=None, max_length=200)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)


class RegisterIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=200)
    name: str = Field(default="", max_length=80)
    consent: bool = False
    birth: BirthIn | None = None


class PartnerIn(BaseModel):
    name: str = Field(max_length=80)
    # Without the birth data the partner waits for an invitation.
    birth: BirthIn | None = None


class InviteIn(BaseModel):
    name: str = Field(default="", max_length=80)
    consent: bool = False
    birth: BirthIn


class QuestionIn(BaseModel):
    # The length is checked again after the spaces are folded: here only the crude bound.
    text: str = Field(max_length=LENGTH * 2)


class NameIn(BaseModel):
    name: str = Field(max_length=80)


class EmailIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=200)


class PasswordIn(BaseModel):
    current: str = Field(max_length=200)
    password: str = Field(max_length=200)


class DeleteIn(BaseModel):
    password: str = Field(max_length=200)


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
            birth.lat if birth else None,
            birth.lon if birth else None,
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
        return set_birth(user_id, body.date, body.time, body.place, body.lat, body.lon)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.put("/me/name")
def update_name(body: NameIn, user_id: int = Depends(require_web_user)) -> dict:
    try:
        return set_name(user_id, body.name)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.put("/me/email")
def update_email(body: EmailIn, user_id: int = Depends(require_web_user)) -> dict:
    """A new email for signing in; the password confirms it is the person themselves."""
    try:
        return set_email(user_id, body.email, body.password)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.put("/me/password")
def update_password(body: PasswordIn, user_id: int = Depends(require_web_user)) -> dict:
    try:
        set_password(user_id, body.current, body.password)
    except DomainError as exc:
        raise as_http(exc) from exc
    return {"ok": True}


@router.post("/me/delete")
def remove_account(body: DeleteIn, user_id: int = Depends(require_web_user)) -> dict:
    """Deletes the account for good; a POST with the password, not a bare DELETE, so it is never an accident."""
    try:
        delete_account(user_id, body.password)
    except DomainError as exc:
        raise as_http(exc) from exc
    return {"ok": True}


@router.get("/me/chart")
def my_chart(user_id: int = Depends(require_web_user)) -> dict:
    try:
        return chart_of(user_id)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.get("/me/chart/items/{item}")
def my_chart_item(item: str, user_id: int = Depends(require_web_user)) -> dict:
    """The reading of one planet or angle of the chart: «Венера в Скорпионе, в VIII доме» and its text."""
    try:
        return chart_item(user_id, item)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.get("/me/forecast")
def my_forecast(
    period: str = Query(default="day", max_length=8),
    tz: str = Query(default="", max_length=64),
    user_id: int = Depends(require_web_user),
) -> dict:
    """Transits of the day or the week over the natal chart; the full text only with «Небосвод»."""
    try:
        return forecast_of(user_id, period, tz)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.get("/me/forecast/month")
def my_month(tz: str = Query(default="", max_length=64), user_id: int = Depends(require_web_user)) -> dict:
    """The star calendar of thirty days; without «Небосвод» only its first week is open."""
    try:
        return month_of(user_id, tz)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.get("/me/partners")
def my_partners(user_id: int = Depends(require_web_user)) -> dict:
    try:
        return {"items": list_partners(user_id)}
    except DomainError as exc:
        raise as_http(exc) from exc


@router.post("/me/partners")
def add_partner(body: PartnerIn, user_id: int = Depends(require_web_user)) -> dict:
    birth = body.birth
    try:
        return create_partner(
            user_id,
            body.name,
            birth.date if birth else None,
            birth.time if birth else None,
            birth.place if birth else None,
            birth.lat if birth else None,
            birth.lon if birth else None,
        )
    except DomainError as exc:
        raise as_http(exc) from exc


@router.delete("/me/partners/{partner_id}")
def remove_partner(partner_id: int, user_id: int = Depends(require_web_user)) -> dict:
    try:
        delete_partner(user_id, partner_id)
    except DomainError as exc:
        raise as_http(exc) from exc
    return {"ok": True}


@router.post("/me/partners/{partner_id}/invite")
def invite_partner(partner_id: int, user_id: int = Depends(require_web_user)) -> dict:
    """The partner with its invitation token: the page turns it into a link /invite/<token>."""
    try:
        return invite(user_id, partner_id)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.get("/me/partners/{partner_id}/synastry")
def partner_synastry(partner_id: int, user_id: int = Depends(require_web_user)) -> dict:
    """The tone of the pair and its key aspects; the full reading once the pair is bought."""
    try:
        return synastry_of(user_id, partner_id)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.get("/me/chat")
def my_chat(user_id: int = Depends(require_web_user)) -> dict:
    """The conversation with the astrologer, the questions to start with and the trial left."""
    try:
        return history(user_id)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.post("/me/chat")
def ask_astrologer(body: QuestionIn, user_id: int = Depends(require_web_user)) -> dict:
    """A question and its answer; without «Небосвод» only the trial ones (402 trial_over after them)."""
    try:
        return ask(user_id, body.text)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.get("/invite/{token}")
def invitation(token: str) -> dict:
    """Open: the partner has no account. Only the first names are shown."""
    try:
        return open_invite(token)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.post("/invite/{token}")
def answer_invitation(token: str, body: InviteIn) -> dict:
    birth = body.birth
    try:
        return fill_invite(token, body.name, body.consent, birth.date, birth.time, birth.place, birth.lat, birth.lon)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.get("/places")
def places(request: Request, q: str = Query(default="", max_length=100)) -> list[dict]:
    """City suggestions for the birth place: open, since registration asks for it before an account exists."""
    try:
        return search(q, request.client.host if request.client else "")
    except DomainError as exc:
        raise as_http(exc) from exc
