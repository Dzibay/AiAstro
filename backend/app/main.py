import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app import backups, faults, notes
from app.api.admin import router as admin_router
from app.api.pay import router as pay_router
from app.api.site import router as site_router
from app.api.web import router as web_router
from app.config import settings
from app.db import close_pool, ensure_schema
from app.security import read_web_session

log = logging.getLogger("aiastro")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    log.info("Публичный адрес: %s", settings.public_base_url)
    host = (settings.public_base_url or "").lower()
    if "localhost" in host or "127.0.0.1" in host:
        log.warning(
            "PUBLIC_BASE_URL=%s — ЮKassa получит return_url на localhost и подставит «Адрес сайта» магазина (часто главную)",
            settings.public_base_url,
        )
    if not settings.web_session_secret:
        log.warning("WEB_SESSION_SECRET пуст — вход в кабинет закрыт")
    if not settings.admin_session_secret or not settings.admin_password:
        log.warning("Секрет или пароль админки пуст — вход оператора закрыт")
    ensure_schema()
    faults.install()
    loops = [asyncio.create_task(notes.loop()), asyncio.create_task(backups.loop())]
    yield
    for task in loops:
        task.cancel()
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


@app.exception_handler(Exception)
async def unexpected(request: Request, exc: Exception) -> JSONResponse:
    """What no endpoint caught: into the journal of errors; the person gets «Сервис временно недоступен»."""
    user_id = None
    token = (request.headers.get("authorization") or "").removeprefix("Bearer ").strip()
    if token:
        try:
            user_id = read_web_session(token)
        except Exception:  # noqa: BLE001 — an admin's or a stale token: the error is recorded without a person
            pass
    faults.from_exception(exc, path=f"{request.method} {request.url.path}", user_id=user_id)
    return JSONResponse({"detail": "server"}, status_code=500)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}
