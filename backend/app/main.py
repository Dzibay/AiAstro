import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import notes
from app.api.admin import router as admin_router
from app.api.pay import router as pay_router
from app.api.site import router as site_router
from app.api.web import router as web_router
from app.config import settings
from app.db import close_pool, ensure_schema

log = logging.getLogger("aiastro")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    log.info("Публичный адрес: %s", settings.public_base_url)
    if not settings.web_session_secret:
        log.warning("WEB_SESSION_SECRET пуст — вход в кабинет закрыт")
    if not settings.admin_session_secret or not settings.admin_password:
        log.warning("Секрет или пароль админки пуст — вход оператора закрыт")
    ensure_schema()
    reminders = asyncio.create_task(notes.loop())
    yield
    reminders.cancel()
    close_pool()


app = FastAPI(
    title="Астра",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)
app.include_router(site_router, prefix="/api")
app.include_router(web_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(pay_router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}
