import datetime as dt
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app import faults, landing, legal
from app.astro import forecast
from app.api.deps import as_http, optional_web_user
from app.errors import DomainError
from app.config import settings
from app.settings_store import public_config
from app.throttle import Window, address
from app.track import BATCH, track, track_many

router = APIRouter(prefix="/site")


@router.get("/config")
def site_config() -> dict:
    return public_config(settings.site_name)


def _fill(value, names: dict):
    if isinstance(value, str):
        return value.format(**names)
    if isinstance(value, list):
        return [_fill(item, names) for item in value]
    return {key: _fill(item, names) for key, item in value.items()}


@router.get("/sky")
def site_sky() -> dict:
    """Today's sky for the home page: the same for everyone, by the Moscow date."""
    return forecast.public_sky(datetime.now(ZoneInfo("Europe/Moscow")).date())


@router.get("/legal/{page}")
def legal_page(page: str) -> dict:
    document = legal.DOCUMENTS.get(page)
    if document is None:
        raise HTTPException(status_code=404, detail="missing")
    config = public_config(settings.site_name)
    email = config["support_email"] or "почта поддержки, указанная на сайте"
    names = {"site": settings.site_name, "url": settings.public_base_url.rstrip("/"), "email": email}
    sections = _fill(document["sections"], names)
    contacts = []
    if config["support_email"]:
        contacts.append(f"Почта поддержки: {config['support_email']}.")
    if config["support_telegram"]:
        contacts.append(f"Telegram поддержки: @{config['support_telegram']} (https://t.me/{config['support_telegram']}).")
    if contacts and not any(section.get("id") == "contacts" for section in sections):
        sections.append({"id": "contacts", "title": "Контакты", "items": contacts})
    return {
        "slug": page,
        "title": document["title"],
        "lead": _fill(document["lead"], names),
        "updated": legal.UPDATED,
        "sections": sections,
    }


class TrackIn(BaseModel):
    visitor: str = Field(max_length=40)
    kind: str = Field(max_length=16)
    name: str = Field(max_length=48)
    value: int | None = Field(default=None, ge=0, le=3600)
    ref: str = Field(default="", max_length=40)
    source: str = Field(default="", max_length=300)
    device: str = Field(default="", max_length=16)


@router.post("/track", status_code=204)
def site_track(body: TrackIn, background: BackgroundTasks, user_id: int | None = Depends(optional_web_user)) -> None:
    """A page seen or a tour ended, for the operator's figures; written after the answer, never fails the page."""
    background.add_task(_track_quietly, body, user_id)


def _track_quietly(body: TrackIn, user_id: int | None) -> None:
    try:
        track(body.visitor, body.kind, body.name, body.value, body.ref, body.source, body.device, user_id)
    except Exception:  # noqa: BLE001 — a lost view is better than a noisy log on every page
        pass


class TrackItem(BaseModel):
    kind: str = Field(max_length=16)
    name: str = Field(max_length=48)
    value: int | None = Field(default=None, ge=0, le=3600)
    page: str = Field(default="", max_length=48)


class TrackManyIn(BaseModel):
    visitor: str = Field(max_length=40)
    items: list[TrackItem] = Field(max_length=BATCH)


@router.post("/track/many", status_code=204)
def site_track_many(body: TrackManyIn, background: BackgroundTasks, user_id: int | None = Depends(optional_web_user)) -> None:
    """What a page gathered over a few seconds (scroll, attention, buttons, offers, the game), in one go."""
    background.add_task(_track_many_quietly, body, user_id)


def _track_many_quietly(body: TrackManyIn, user_id: int | None) -> None:
    try:
        track_many(body.visitor, [(i.kind, i.name, i.value, i.page) for i in body.items], user_id)
    except Exception:  # noqa: BLE001 — as with a view: the page never hears of it
        pass


class FaultIn(BaseModel):
    kind: str = Field(max_length=40)
    message: str = Field(max_length=1000)
    place: str = Field(default="", max_length=300)
    stack: str = Field(default="", max_length=8000)
    page: str = Field(default="", max_length=300)


# A page in a loop of errors, or someone filling the journal on purpose: past these, quietly dropped.
_faults_by_address = Window(30, 60 * 60)
_faults_all = Window(600, 60 * 60)


@router.post("/fault", status_code=204)
def site_fault(body: FaultIn, request: Request, user_id: int | None = Depends(optional_web_user)) -> None:
    """An error in a visitor's browser, for the journal in the admin; the page never hears back."""
    try:
        _faults_by_address.take(address(request))
        _faults_all.take("all")
    except DomainError:
        return
    faults.record("front", body.kind, body.message, place=body.place, path=body.page, detail=body.stack,
                  agent=request.headers.get("user-agent", ""), user_id=user_id)


# ---- The landing pages' calculation, open without an account ----

class PreviewBirthIn(BaseModel):
    date: dt.date
    time: dt.time | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)

    def args(self) -> dict:
        return {"birth_date": self.date, "birth_time": self.time.replace(second=0, microsecond=0, tzinfo=None) if self.time else None,
                "lat": self.lat, "lon": self.lon}


class NatalPreviewIn(PreviewBirthIn):
    focus: str = Field(default="", max_length=16)


class PairPreviewIn(BaseModel):
    mine: PreviewBirthIn
    theirs: PreviewBirthIn


def _preview(request: Request, make):
    try:
        landing.allow(address(request))
        return make()
    except DomainError as exc:
        raise as_http(exc) from exc


@router.post("/preview/natal")
def preview_natal(body: NatalPreviewIn, request: Request) -> dict:
    """A few points of the chart with their readings: what a landing shows before the registration."""
    return _preview(request, lambda: landing.natal_preview(**body.args(), focus=body.focus))


@router.post("/preview/pair")
def preview_pair(body: PairPreviewIn, request: Request) -> dict:
    return _preview(request, lambda: landing.pair_preview(body.mine.args(), body.theirs.args()))


@router.post("/preview/forecast")
def preview_forecast(body: PreviewBirthIn, request: Request) -> dict:
    return _preview(request, lambda: landing.forecast_preview(**body.args()))
