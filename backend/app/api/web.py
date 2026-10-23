import datetime as dt

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from pydantic import BaseModel, Field

from app import notes
from app.accounts import (
    add_marks, authenticate, delete_account, get_user, register, request_reset, reset_password, set_birth, set_email,
    set_mail_notes, set_name, set_password,
)
from app.api.deps import as_http, optional_web_user, require_web_user
from app.charts import chart_item, chart_of, forecast_of, mark_task, month_of, portrait_of
from app.chat import LENGTH, ask, history
from app.errors import DomainError
from app.mailer import mail_on
from app.payments import create_payment
from app.partners import (
    accept_invite, create_partner, delete_partner, fill_invite, forecast_of as pair_forecast_of, invite, link_invite,
    list_partners, mine_changed, open_invite, seen, share, synastry_of, update_partner,
)
from app.places import search
from app.security import make_web_session
from app.track import attach

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
    # The browser's anonymous id: the account takes its campaign link.
    visitor: str | None = Field(default=None, max_length=40)


class PartnerIn(BaseModel):
    name: str = Field(max_length=80)
    # Without the birth data the partner waits for an invitation.
    birth: BirthIn | None = None


class InviteIn(BaseModel):
    name: str = Field(default="", max_length=80)
    consent: bool = False
    # The consent that the one who invited sees these data, and the pair is built of them.
    share: bool = False
    birth: BirthIn


class AcceptIn(BaseModel):
    share: bool = False


class LinkIn(BaseModel):
    claim: str = Field(max_length=100)


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


class PaymentIn(BaseModel):
    # sky1, sky3, sky12 or synastry; the pair's reading names its partner.
    product: str = Field(max_length=16)
    partner: int | None = None
    # The browser's own origin: kept for a local dev server; production uses PUBLIC_BASE_URL.
    origin: str | None = Field(default=None, max_length=200)


class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=200)
    visitor: str | None = Field(default=None, max_length=40)


class ForgotIn(BaseModel):
    email: str = Field(max_length=254)


class ResetIn(BaseModel):
    token: str = Field(max_length=100)
    password: str = Field(max_length=200)


class MailNotesIn(BaseModel):
    on: bool


class MarksIn(BaseModel):
    marks: list[str] = Field(min_length=1, max_length=10)


class TaskIn(BaseModel):
    day: dt.date
    key: str = Field(max_length=40)
    done: bool


@router.post("/register")
def register_user(body: RegisterIn, background: BackgroundTasks) -> dict:
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
    background.add_task(attach, user["id"], body.visitor, True)
    return {"token": token, "user": user}


@router.post("/login")
def login_user(body: LoginIn, background: BackgroundTasks) -> dict:
    try:
        user = authenticate(body.email, body.password)
        token = make_web_session(user["id"])
    except DomainError as exc:
        raise as_http(exc) from exc
    background.add_task(attach, user["id"], body.visitor)
    return {"token": token, "user": user}


@router.post("/password/forgot")
def forgot_password(body: ForgotIn, background: BackgroundTasks) -> dict:
    """Always the same answer, so the form does not tell whose mail is registered; the letter goes in the background."""
    try:
        if not mail_on():
            raise DomainError("mail_off", 409)
        found = request_reset(body.email)
    except DomainError as exc:
        raise as_http(exc) from exc
    if found:
        background.add_task(notes.reset_letter, found)
    return {"ok": True}


@router.post("/password/reset")
def new_password(body: ResetIn) -> dict:
    """The new password by the letter's link; the person is signed in at once."""
    try:
        user = reset_password(body.token, body.password)
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
        user = set_birth(user_id, body.date, body.time, body.place, body.lat, body.lon)
    except DomainError as exc:
        raise as_http(exc) from exc
    # The partners who see these data see them corrected (unless their pair is already bought).
    mine_changed(user_id)
    return user


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


@router.put("/me/mail")
def update_mail_notes(body: MailNotesIn, user_id: int = Depends(require_web_user)) -> dict:
    """The letters about «Небосвод» and the partners: on or off."""
    try:
        return set_mail_notes(user_id, body.on)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.post("/me/marks")
def save_marks(body: MarksIn, user_id: int = Depends(require_web_user)) -> dict:
    """A tour seen or a newcomer step taken: kept in the account, so another device knows it too."""
    try:
        return add_marks(user_id, body.marks)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.post("/me/delete")
def remove_account(body: DeleteIn, background: BackgroundTasks, user_id: int = Depends(require_web_user)) -> dict:
    """Deletes the account for good; a POST with the password, not a bare DELETE, so it is never an accident."""
    try:
        told = delete_account(user_id, body.password)
    except DomainError as exc:
        raise as_http(exc) from exc
    background.add_task(notes.pair_left, told)
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


@router.get("/me/chart/portrait")
def my_portrait(user_id: int = Depends(require_web_user)) -> dict:
    """The chart read as a whole: the core, the temperament, the accents, the way; whole with «Небосвод»."""
    try:
        return portrait_of(user_id)
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


@router.post("/me/forecast/tasks")
def tick_task(body: TaskIn, user_id: int = Depends(require_web_user)) -> dict:
    """A task of the day's checklist done or undone; kept in the account for that day."""
    try:
        if not get_user(user_id)["sky"]:
            raise DomainError("sky", 403)
        return mark_task(user_id, body.day, body.key, body.done)
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


@router.put("/me/partners/{partner_id}")
def edit_partner(partner_id: int, body: PartnerIn, user_id: int = Depends(require_web_user)) -> dict:
    """The name always; the birth data of a partner typed in by hand until the reading is bought."""
    birth = body.birth
    try:
        return update_partner(
            user_id,
            partner_id,
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
def remove_partner(partner_id: int, background: BackgroundTasks, user_id: int = Depends(require_web_user)) -> dict:
    """The person's side only: the partner's side keeps the pair and what was opened."""
    try:
        told = delete_partner(user_id, partner_id)
    except DomainError as exc:
        raise as_http(exc) from exc
    background.add_task(notes.pair_left, told)
    return {"ok": True}


@router.post("/me/partners/{partner_id}/share")
def share_with_partner(partner_id: int, user_id: int = Depends(require_web_user)) -> dict:
    """The consent to show the joined partner one's own birth data."""
    try:
        return share(user_id, partner_id)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.post("/me/partners/{partner_id}/seen")
def partner_seen(partner_id: int, user_id: int = Depends(require_web_user)) -> dict:
    seen(user_id, partner_id)
    return {"ok": True}


@router.get("/me/partners/{partner_id}/forecast")
def partner_forecast(
    partner_id: int, tz: str = Query(default="", max_length=64), user_id: int = Depends(require_web_user),
) -> dict:
    """The pair's day under the sky: a bought pair with «Небосвод»; otherwise only what opens it."""
    try:
        return pair_forecast_of(user_id, partner_id, tz or None)
    except DomainError as exc:
        raise as_http(exc) from exc


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


@router.post("/me/payments")
def pay(body: PaymentIn, request: Request, user_id: int = Depends(require_web_user)) -> dict:
    """Creates the payment at ЮKassa: the page sends the person on to `url` and gets them back with `id`."""
    try:
        return create_payment(
            user_id,
            body.product,
            body.partner,
            origin=body.origin or request.headers.get("origin"),
        )
    except DomainError as exc:
        raise as_http(exc) from exc


@router.get("/invite/{token}")
def invitation(token: str, user_id: int | None = Depends(optional_web_user)) -> dict:
    """Open: the partner may have no account. Only the first names are shown."""
    try:
        return open_invite(token, user_id)
    except DomainError as exc:
        raise as_http(exc) from exc


@router.post("/invite/{token}")
def answer_invitation(token: str, body: InviteIn, background: BackgroundTasks) -> dict:
    birth = body.birth
    try:
        answer = fill_invite(
            token, body.name, body.consent, body.share, birth.date, birth.time, birth.place, birth.lat, birth.lon,
        )
    except DomainError as exc:
        raise as_http(exc) from exc
    background.add_task(notes.partner_filled, answer.pop("side"))
    return answer


@router.post("/invite/{token}/accept")
def accept_invitation(
    token: str, body: AcceptIn, background: BackgroundTasks, user_id: int = Depends(require_web_user),
) -> dict:
    """The invitation answered from a cabinet: its own birth data light the star, the pair is shared at once."""
    try:
        answer = accept_invite(user_id, token, body.share)
    except DomainError as exc:
        raise as_http(exc) from exc
    side = answer.pop("side", None)
    if side:
        background.add_task(notes.pair_linked, side)
    return answer


@router.post("/invite/{token}/link")
def link_invitation(
    token: str, body: LinkIn, background: BackgroundTasks, user_id: int = Depends(require_web_user),
) -> dict:
    """The cabinet opened after the invitation was answered: the page's key joins the pair to it."""
    try:
        answer = link_invite(user_id, token, body.claim)
    except DomainError as exc:
        raise as_http(exc) from exc
    side = answer.pop("side", None)
    if side:
        background.add_task(notes.pair_linked, side)
    return answer


@router.get("/places")
def places(request: Request, q: str = Query(default="", max_length=100)) -> list[dict]:
    """City suggestions for the birth place: open, since registration asks for it before an account exists."""
    try:
        return search(q, request.client.host if request.client else "")
    except DomainError as exc:
        raise as_http(exc) from exc
