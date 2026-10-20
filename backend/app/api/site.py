from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException

from app import legal
from app.astro import forecast
from app.config import settings
from app.settings_store import public_config

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
