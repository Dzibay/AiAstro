import datetime as dt

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from pydantic import BaseModel, Field

from app import notes
from app.analytics import analytics, create_link, delete_link, link_detail, list_links, update_link, user_events
from app.accounts import (
    SKY_MAX_DAYS, admin_delete, list_users, operator_confirm, operator_user, set_birth, set_sky, set_sky_until,
    user_activity,
)
from app.api.deps import as_http, require_admin
from app.config import settings
from app.errors import DomainError
from app.letters import Letter, html, text
from app.mailer import link, mail_on, send
from app.partners import admin_pairs, admin_partners, mine_changed, set_bought, set_pair_bought
from app.payments import list_payments
from app.pulse import journey, money, pulse, segments, way, weeks
from app.security import check_admin_password, make_admin_session
from app.settings_store import list_editable, set_setting
from app.stats import stats

router = APIRouter(prefix="/admin")


class LoginIn(BaseModel):
    password: str = Field(max_length=200)


class SkyIn(BaseModel):
    # days: 30 opens «Небосвод» for a month more, 0 closes it; until: open till the end of that day instead.
    days: int | None = Field(default=None, ge=0, le=SKY_MAX_DAYS)
    until: dt.date | None = None


class DeleteIn(BaseModel):
    # The person's email typed again: the page asks for it so a click alone never deletes.
    email: str = Field(max_length=254)


class BoughtIn(BaseModel):
    bought: bool


class BirthIn(BaseModel):
    date: dt.date
    time: dt.time | None = None
    place: str | None = Field(default=None, max_length=200)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)


class TestMailIn(BaseModel):
    email: str = Field(max_length=254)


class LinkIn(BaseModel):
    # Empty: the page gets a random token.
    token: str = Field(default="", max_length=40)
    name: str = Field(default="", max_length=80)
    note: str = Field(default="", max_length=300)


class LinkEditIn(BaseModel):
    # Absent — left as it is: the spend is saved alone from the money table.
    name: str | None = Field(default=None, max_length=80)
    note: str | None = Field(default=None, max_length=300)
    # What the campaign has cost in all, roubles; absent — left as it is.
    spend: int | None = Field(default=None, ge=0, le=100_000_000)


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
        return {"items": list_editable(), "mail": mail_on()}
    except DomainError as exc:
        raise as_http(exc) from exc


@router.put("/settings", dependencies=[Depends(require_admin)])
def settings_update(body: SettingIn) -> dict:
    try:
        return set_setting(body.key, body.value)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.post("/mail/test", dependencies=[Depends(require_admin)])
def mail_test(body: TestMailIn) -> dict:
    """A letter sent now, not in the background: the operator sees the SMTP server's own answer."""
    if not mail_on():
        raise as_http(DomainError("mail_off", 409))
    try:
        letter = Letter(
            subject="Пробное письмо",
            title="Почта настроена",
            hello="Здравствуйте!",
            lines=["Письма с подтверждением почты, новым паролем и напоминаниями будут уходить с этого адреса — и выглядеть так."],
            button="Открыть сайт",
            url=link("/"),
        )
        send(body.email.strip(), letter.subject, text(letter), html(letter))
    except Exception as exc:  # noqa: BLE001 — whatever the server said goes back to the operator
        return {"ok": False, "error": str(exc)[:300]}
    return {"ok": True}


@router.get("/stats", dependencies=[Depends(require_admin)])
def stats_view(days: int = Query(default=30)) -> dict:
    """Money and new accounts by day for the period, the products and the totals."""
    try:
        return stats(days)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.get("/analytics", dependencies=[Depends(require_admin)])
def analytics_view(days: int = Query(default=30)) -> dict:
    """Visitors, the funnel, where people stop, the tours, the sources and the devices."""
    try:
        return analytics(days)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.get("/pulse", dependencies=[Depends(require_admin)])
def pulse_view(days: int = Query(default=30)) -> dict:
    """The first screen: the period against the same span before, the way then and now, what stands out."""
    try:
        return pulse(days)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.get("/analytics/way", dependencies=[Depends(require_admin)])
def analytics_way(days: int = Query(default=30), entry: str = Query(default=""), device: str = Query(default="")) -> dict:
    """The way from the first visit to a payment, now and before; entry: '' | home | landings | other, device: '' | phone | desktop."""
    try:
        return way(days, entry, device)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.get("/analytics/weeks", dependencies=[Depends(require_admin)])
def analytics_weeks(weeks_n: int = Query(default=12, alias="weeks"), device: str = Query(default="")) -> dict:
    """The way of each week's new browsers, the steps made within a week of coming."""
    try:
        return weeks(weeks_n, device)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.get("/analytics/segments", dependencies=[Depends(require_admin)])
def analytics_segments(days: int = Query(default=30), by: str = Query(default="channel")) -> dict:
    """The way split by channel, first page or device."""
    try:
        return segments(days, by)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.get("/analytics/money", dependencies=[Depends(require_admin)])
def analytics_money(days: int = Query(default=30)) -> dict:
    """Visitors, accounts and money by channel, with the links' spend; days = 0 — all time."""
    try:
        return money(days)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.get("/links", dependencies=[Depends(require_admin)])
def links_list(days: int = Query(default=0)) -> dict:
    """The campaign links with their clicks, registrations and money; days = 0 — for all time."""
    try:
        return list_links(days)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.post("/links", dependencies=[Depends(require_admin)])
def links_create(body: LinkIn) -> dict:
    try:
        return create_link(body.token, body.name, body.note)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.get("/links/{link_id}", dependencies=[Depends(require_admin)])
def links_one(link_id: int, days: int = Query(default=0)) -> dict:
    try:
        return link_detail(link_id, days)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.put("/links/{link_id}", dependencies=[Depends(require_admin)])
def links_update(link_id: int, body: LinkEditIn) -> dict:
    try:
        return update_link(link_id, body.name, body.note, body.spend)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.delete("/links/{link_id}", dependencies=[Depends(require_admin)])
def links_delete(link_id: int) -> dict:
    """The link and its clicks go; the people who came by it stay, without the mark."""
    try:
        return delete_link(link_id)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.get("/payments", dependencies=[Depends(require_admin)])
def payments_list(
    q: str = Query(default="", max_length=100),
    status: str = Query(default="", max_length=16),
    offset: int = Query(default=0, ge=0),
    user: int | None = Query(default=None),
) -> dict:
    """The latest payments and the address to give ЮKassa for its notifications."""
    try:
        page = list_payments(q, status, offset, user)
    except DomainError as exc:
        raise as_http(exc) from exc
    base = settings.public_base_url.rstrip("/")
    return {
        **page,
        "notify_url": f"{base}/api/pay/yookassa",
        # What we put in confirmation.return_url; if ЮKassa's button still shows the home page,
        # its shop «Адрес сайта» is overriding this — set the same address there.
        "return_url": f"{base}/cabinet",
    }


@router.get("/users", dependencies=[Depends(require_admin)])
def users_list(
    q: str = Query(default="", max_length=100),
    state: str = Query(default="", max_length=16),
    offset: int = Query(default=0, ge=0),
) -> dict:
    try:
        return list_users(q, state, offset)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.get("/users/{user_id}", dependencies=[Depends(require_admin)])
def users_one(user_id: int) -> dict:
    try:
        return operator_user(user_id)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.get("/users/{user_id}/activity", dependencies=[Depends(require_admin)])
def users_activity(user_id: int, month: str = Query(default="", max_length=7)) -> dict:
    """Days of one Moscow month this person opened the site, with the pages of each day."""
    try:
        return user_activity(user_id, month)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.get("/users/{user_id}/journey", dependencies=[Depends(require_admin)])
def users_journey(user_id: int) -> dict:
    """Where this person came from and which steps and actions they have made, with the first moment of each."""
    try:
        return journey(user_id)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.get("/users/{user_id}/events", dependencies=[Depends(require_admin)])
def users_events(user_id: int, before: str = Query(default="", max_length=40)) -> dict:
    """This person's latest actions on the site and payments, newest first."""
    try:
        return user_events(user_id, before)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.post("/users/{user_id}/delete", dependencies=[Depends(require_admin)])
def users_delete(user_id: int, body: DeleteIn, background: BackgroundTasks) -> dict:
    """Deletes the account for good, as the person's own deletion does: payments stay for the books."""
    try:
        user = operator_user(user_id)
        if body.email.strip().lower() != user["email"].lower():
            raise DomainError("confirm")
        told = admin_delete(user_id)
    except DomainError as exc:
        raise as_http(exc) from exc
    background.add_task(notes.pair_left, told)
    return {"ok": True}


@router.post("/users/{user_id}/confirm", dependencies=[Depends(require_admin)])
def users_confirm(user_id: int) -> dict:
    """Confirms the email by hand, when the letter went astray and the person wrote from this address."""
    try:
        return operator_confirm(user_id)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.put("/users/{user_id}/sky", dependencies=[Depends(require_admin)])
def users_sky(user_id: int, body: SkyIn) -> dict:
    try:
        if body.until is not None:
            return set_sky_until(user_id, body.until)
        if body.days is None:
            raise DomainError("state")
        return set_sky(user_id, body.days)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.get("/users/{user_id}/partners", dependencies=[Depends(require_admin)])
def users_partners(user_id: int) -> dict:
    return {"items": admin_partners(user_id)}


@router.put("/users/{user_id}/partners/{partner_id}/purchase", dependencies=[Depends(require_admin)])
def users_purchase(user_id: int, partner_id: int, body: BoughtIn, background: BackgroundTasks) -> dict:
    """Marks the reading of this pair as bought by hand (a gift, a refund) or takes the mark back."""
    try:
        partner, told = set_bought(user_id, partner_id, body.bought)
    except DomainError as exc:
        raise as_http(exc) from exc
    background.add_task(notes.pair_gift, told)
    return partner


@router.put("/users/{user_id}/birth", dependencies=[Depends(require_admin)])
def users_birth(user_id: int, body: BirthIn) -> dict:
    """The support corrects the birth data once the person's own correction is spent."""
    try:
        user = set_birth(user_id, body.date, body.time, body.place, body.lat, body.lon, operator=True)
    except DomainError as exc:
        raise as_http(exc) from exc
    mine_changed(user_id)
    return user


@router.get("/pairs", dependencies=[Depends(require_admin)])
def pairs(
    q: str = Query(default="", max_length=100),
    state: str = Query(default="", max_length=16),
    offset: int = Query(default=0, ge=0),
) -> dict:
    """Every pair with both its sides: bought, linked or waiting for the partner."""
    try:
        return admin_pairs(q, state, offset)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.put("/pairs/{pair_id}/purchase", dependencies=[Depends(require_admin)])
def pair_purchase(pair_id: int, body: BoughtIn, background: BackgroundTasks) -> dict:
    """Opens the reading for the pair, on both sides at once (with a letter), or closes it."""
    try:
        told = set_pair_bought(pair_id, body.bought)
    except DomainError as exc:
        raise as_http(exc) from exc
    background.add_task(notes.pair_gift, told)
    return {"ok": True}
