from fastapi import APIRouter, HTTPException, Request

from app.errors import DomainError
from app.payments import notify

router = APIRouter(prefix="/pay")


@router.post("/yookassa")
async def yookassa_notification(request: Request) -> dict:
    """ЮKassa's notifications (payment.succeeded, payment.canceled): set this address in the shop's settings.

    The body is not trusted: only the payment's id is read from it and the payment is asked from
    ЮKassa again. A 5xx answer makes ЮKassa repeat the notification later.
    """
    try:
        event = await request.json()
    except ValueError:
        return {"ok": True}
    if not isinstance(event, dict):
        return {"ok": True}
    try:
        notify(event)
    except DomainError as exc:
        raise HTTPException(status_code=503, detail=exc.code) from exc
    return {"ok": True}
