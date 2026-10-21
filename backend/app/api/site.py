from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from app import legal
from app.astro import forecast
from app.api.deps import optional_web_user
from app.config import settings
from app.settings_store import public_config
from app.track import track

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
    names = {"site": settings.site_name, "url": settings.public_base_url.rstrip("/")}
    sections = _fill(document["sections"], names)
    if config["support_email"]:
        sections.append({"id": "contacts", "title": "Контакты", "items": [f"Почта поддержки: {config['support_email']}."]})
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
    value: int | None = Field(default=None, ge=0, le=1000)
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
