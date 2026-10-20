"""Payments through ЮKassa: «Небосвод» for 1, 3 or 12 months and the reading of one pair.

A payment is written here first, then created at ЮKassa and paid on its page. It comes back
twice: the person returns to the cabinet, and ЮKassa sends a notification. Neither is trusted
as it is: both only make us ask ЮKassa for the payment by its id, so neither can be forged.
Whichever comes first applies the purchase, and only once (see _apply).

There is no auto-renewal: every payment is one charge for one term, as the offer says.
"""

import base64
import json
import logging
import threading
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.accounts import get_user
from app.config import settings
from app.db import pool
from app.errors import DomainError
from app.partners import PRODUCT as PAIR, _bought, _own
from app.settings_store import get_settings, payments_on, setting

log = logging.getLogger("aiastro")

API = "https://api.yookassa.ru/v3/payments"
TIMEOUT = 15

# product: (days, price key, what the receipt and ЮKassa's page call it)
PLANS = {
    "sky1": (30, "price_sky", "Подписка «Небосвод» на 1 месяц"),
    "sky3": (90, "price_sky_3", "Подписка «Небосвод» на 3 месяца"),
    "sky12": (365, "price_sky_12", "Подписка «Небосвод» на 12 месяцев"),
}
PRODUCTS = (*PLANS, PAIR)

_COLUMNS = "id, user_id, email, product, partner_id, pair_id, days, amount, title, status, yookassa_id, created_at, paid_at"


def _call(method: str, url: str, body: dict | None = None, key: str = "") -> dict:
    """One request to ЮKassa's API with the shop's own key; DomainError if it does not answer well."""
    data = get_settings()
    token = base64.b64encode(f"{data.get('yookassa_shop_id', '')}:{data.get('yookassa_secret_key', '')}".encode()).decode()
    headers = {"Authorization": f"Basic {token}", "Accept": "application/json"}
    payload = None
    if body is not None:
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
        # The same key for the same payment: a repeated request does not charge twice.
        headers["Idempotence-Key"] = key
    try:
        with urlopen(Request(url, data=payload, headers=headers, method=method), timeout=TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        log.warning("ЮKassa ответила %s: %s", exc.code, detail)
        raise DomainError("pay_failed", 502) from exc
    except (URLError, TimeoutError, ValueError) as exc:
        log.warning("ЮKassa недоступна: %s", exc)
        raise DomainError("pay_failed", 502) from exc


def _money(amount: int) -> dict:
    return {"value": f"{amount}.00", "currency": "RUB"}


def _public(row: dict) -> dict:
    return {
        "id": row["id"],
        "product": row["product"],
        "partner_id": row["partner_id"],
        "pair_id": row["pair_id"],
        "days": row["days"],
        "amount": row["amount"],
        "title": row["title"],
        "status": row["status"],
        "created_at": row["created_at"],
        "paid_at": row["paid_at"],
    }


def _price(key: str) -> int:
    value = setting(key)
    if not value:
        raise DomainError("price", 409)
    return int(value)


def create_payment(user_id: int, product: str, partner_id: int | None = None) -> dict:
    """Writes the payment, creates it at ЮKassa and gives the page of ЮKassa to send the person to."""
    if not payments_on():
        raise DomainError("pay_off", 409)
    if product not in PRODUCTS:
        raise DomainError("product")
    user = get_user(user_id)
    pair_id = None
    if product == PAIR:
        if partner_id is None:
            raise DomainError("missing", 404)
        partner = _own(user_id, partner_id)
        if partner["birth_date"] is None:
            raise DomainError("pending", 409)
        pair_id = partner["pair_id"]
        if pair_id in _bought(user_id):
            raise DomainError("bought", 409)
        days = 0
        # The discount is decided now, by the subscription as it stands at the moment of buying.
        amount = _price("price_synastry_sky" if user["sky"] else "price_synastry")
        # With a partner who has a cabinet too, the reading opens for both: the receipt says so.
        both = partner["linked_user_id"] is not None
        title = f"Разбор пары: вы и {partner['name']}{' — для вас обоих' if both else ''}"[:128]
        back = f"/cabinet/pair?partner={partner_id}&paid="
    else:
        partner_id = None
        days, key, title = PLANS[product]
        amount = _price(key)
        back = "/cabinet/sky?paid="

    with pool.connection() as conn:
        row = conn.execute(
            f"""
            INSERT INTO payments (user_id, email, product, partner_id, pair_id, days, amount, title)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING {_COLUMNS}
            """,
            (user_id, user["email"], product, partner_id, pair_id, days, amount, title),
        ).fetchone()

    receipt = {
        "customer": {"email": user["email"]},
        "items": [
            {
                "description": title,
                "quantity": "1.00",
                "amount": _money(amount),
                "vat_code": int(setting("receipt_vat_code")),
                "payment_mode": "full_payment",
                "payment_subject": "service",
            }
        ],
    }
    tax_system = setting("receipt_tax_system")
    if tax_system:
        receipt["tax_system_code"] = int(tax_system)
    body = {
        "amount": _money(amount),
        "capture": True,
        "confirmation": {"type": "redirect", "return_url": f"{settings.public_base_url.rstrip('/')}{back}{row['id']}"},
        "description": title,
        "metadata": {"payment_id": str(row["id"]), "user_id": str(user_id)},
        "receipt": receipt,
    }
    try:
        answer = _call("POST", API, body, key=f"aiastro-payment-{row['id']}")
        url = answer["confirmation"]["confirmation_url"]
        yookassa_id = answer["id"]
    except (DomainError, KeyError, TypeError) as exc:
        with pool.connection() as conn:
            conn.execute("UPDATE payments SET status = 'failed' WHERE id = %s", (row["id"],))
        if isinstance(exc, DomainError):
            raise
        raise DomainError("pay_failed", 502) from exc

    with pool.connection() as conn:
        conn.execute(
            "UPDATE payments SET status = 'pending', yookassa_id = %s WHERE id = %s",
            (yookassa_id, row["id"]),
        )
    return {"id": row["id"], "url": url}


def _apply(row: dict) -> None:
    """The purchase, once: the status changes and the purchase is written in one transaction.

    A pair's reading belongs to the pair: it opens on the partner's side too, and they are told.
    """
    told = []
    with pool.connection() as conn:
        won = conn.execute(
            "UPDATE payments SET status = 'succeeded', paid_at = now() WHERE id = %s AND status <> 'succeeded' RETURNING id",
            (row["id"],),
        ).fetchone()
        if won is None or row["user_id"] is None:
            return
        if row["product"] == PAIR:
            # The pair stays even when the side it was paid from is deleted meanwhile.
            if row["pair_id"] is not None:
                bought = conn.execute(
                    """
                    INSERT INTO purchases (user_id, product, partner_id, pair_id, source) VALUES (%s, %s, %s, %s, 'pay')
                    ON CONFLICT (product, pair_id) WHERE pair_id IS NOT NULL DO NOTHING
                    RETURNING id
                    """,
                    (row["user_id"], PAIR, row["partner_id"], row["pair_id"]),
                ).fetchone()
                if bought is not None:
                    told = conn.execute(
                        """
                        UPDATE partners SET news = 'bought', news_at = now()
                        WHERE pair_id = %s AND user_id <> %s
                        RETURNING id AS partner_id, user_id
                        """,
                        (row["pair_id"], row["user_id"]),
                    ).fetchall()
        else:
            # Counted from the end of the current term if it still runs, as the offer says.
            conn.execute(
                """
                UPDATE users SET sky_until = GREATEST(COALESCE(sky_until, now()), now()) + make_interval(days => %s)
                WHERE id = %s
                """,
                (row["days"], row["user_id"]),
            )
    if told:
        from app import notes

        # Letters go by SMTP, slowly: the answer to ЮKassa or to the page does not wait for them.
        threading.Thread(target=notes.pair_bought, args=(told,), daemon=True).start()


def _settle(row: dict) -> dict:
    """Asks ЮKassa how a pending payment stands and acts on the answer."""
    if row["status"] != "pending" or not row["yookassa_id"]:
        return row
    answer = _call("GET", f"{API}/{row['yookassa_id']}")
    status = answer.get("status")
    paid = answer.get("amount", {}).get("value")
    ours = answer.get("metadata", {}).get("payment_id")
    if status == "succeeded":
        # The sum and our own id must be the ones this payment was created with.
        if ours != str(row["id"]) or paid != _money(row["amount"])["value"]:
            log.error("Платёж %s: ЮKassa вернула чужие данные (%s, %s)", row["id"], ours, paid)
            return row
        _apply(row)
        return {**row, "status": "succeeded"}
    if status == "canceled":
        with pool.connection() as conn:
            conn.execute("UPDATE payments SET status = 'canceled' WHERE id = %s AND status = 'pending'", (row["id"],))
        return {**row, "status": "canceled"}
    return row


def payment_of(user_id: int, payment_id: int) -> dict:
    """The person's payment after the return from ЮKassa; a pending one is checked with ЮKassa first."""
    with pool.connection() as conn:
        row = conn.execute(
            f"SELECT {_COLUMNS} FROM payments WHERE id = %s AND user_id = %s",
            (payment_id, user_id),
        ).fetchone()
    if row is None:
        raise DomainError("missing", 404)
    try:
        row = _settle(row)
    except DomainError:
        # ЮKassa is silent for now: the page asks again a little later.
        pass
    return _public(row)


def notify(event: dict) -> None:
    """ЮKassa's notification: only the payment's id is taken from it, the rest is asked again."""
    yookassa_id = (event.get("object") or {}).get("id")
    if not isinstance(yookassa_id, str) or not yookassa_id:
        return
    with pool.connection() as conn:
        row = conn.execute(f"SELECT {_COLUMNS} FROM payments WHERE yookassa_id = %s", (yookassa_id,)).fetchone()
    if row is None:
        return
    # A DomainError goes up: the answer is not 200 and ЮKassa sends the notification again.
    _settle(row)


def list_payments(limit: int = 50) -> list[dict]:
    """The latest payments for the operator, with the email the receipt went to."""
    with pool.connection() as conn:
        rows = conn.execute(f"SELECT {_COLUMNS} FROM payments ORDER BY id DESC LIMIT %s", (limit,)).fetchall()
    return [{**_public(row), "email": row["email"]} for row in rows]
