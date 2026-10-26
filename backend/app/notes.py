"""The letters the site writes by itself: the email confirmation, the new password link, the
payment that went through and the one that did not finish, «Небосвод» nearing its end, the partner
who has answered the invitation, and what happens to a pair shared by two cabinets. All of them in
the site's look (app.letters), each written to the journal (app.outbox).

Every kind has a builder — the letter from its data — and a sender. The builders also lay out the
samples the admin's catalogue of letters shows (preview), so the sample is the letter itself.

The reminders go only to those who keep the letters on (users.mail_notes); the confirmation, the
password link and the word about a payment go always, since the person has just asked or paid.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app import outbox
from app.accounts import CODE_MINUTES, CONFIRM_HOURS, RESET_MINUTES
from app.db import pool
from app.letters import Letter, deliver, html
from app.mailer import link, mail_on

log = logging.getLogger("aiastro")

# «Небосвод» reminds of its end this many days ahead; the loop looks once an hour.
SKY_AHEAD_DAYS = 3
LOOP_SECONDS = 3600
# A payment that did not finish is recalled after a day, while it is still fresh (up to three days),
# and a person hears of unfinished payments no more often than once a week.
PAY_LEFT_AFTER_HOURS = 24
PAY_LEFT_UNTIL_HOURS = 72
PAY_LEFT_PAUSE_DAYS = 7
_MONTHS = ("января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа",
           "сентября", "октября", "ноября", "декабря")
_SIGN_OFF = ("Напоминания о «Небосводе», о незавершённой оплате и о партнёрах можно отключить в кабинете, "
             "в разделе «Профиль».")
_RECEIPT = "Кассовый чек придёт отдельным письмом."
_CODE_NOTE = "Открываете письмо на другом устройстве? Введите этот код на странице, где ждёт вход:"
_SKY_OPENS = ("Вам открыты полные прогнозы на день и на неделю, звёздный календарь на тридцать дней, портрет "
              "вашей карты, ИИ-астролог каждый день и разбор пары по особой цене.")


def _hello(name: str) -> str:
    return f"{name}, здравствуйте!" if name else "Здравствуйте!"


def _day(moment) -> str:
    local = moment.astimezone(ZoneInfo("Europe/Moscow"))
    return f"{local.day} {_MONTHS[local.month - 1]}"


# The builders: data in, the letter out.


def _confirm(found: dict) -> Letter:
    url = link(f"/login?confirm={found['token']}")
    days = CONFIRM_HOURS // 24
    if found.get("change"):
        return Letter(
            kind="confirm_change",
            subject="Подтвердите новую почту",
            title="Новый адрес для вашего неба",
            hello=_hello(found["name"]),
            lines=[
                "Вы указали этот адрес для входа в кабинет. Подтвердите его — и входить вы будете с ним, "
                "а наши письма станут приходить сюда.",
            ],
            button="Подтвердить и перейти в кабинет",
            url=url,
            after=[f"Ссылка открыта {days} дня и сработает один раз. До подтверждения вход — с прежней почтой."],
            foot="Письмо пришло, потому что этот адрес указали в профиле на нашем сайте.",
        )
    # The same letter opens the cabinet by its button here and by its six digits on another device.
    shared = {
        "hello": _hello(found["name"]),
        "url": url,
        "code": found.get("code") or "",
        "code_note": _CODE_NOTE,
        "after": [f"Ссылка действует {days} дня и сработает один раз, код — {CODE_MINUTES} минут."],
    }
    if found.get("first", True):
        return Letter(
            kind="confirm",
            subject="Ваша натальная карта — в одном шаге",
            title="Ваше небо почти готово",
            lines=[
                "Остался один шаг: откройте кабинет по кнопке ниже — там вы укажете дату рождения "
                "и сразу увидите свою натальную карту.",
            ],
            button="Открыть кабинет",
            foot="Письмо пришло, потому что этот адрес указали на нашем сайте. Если это были не вы, просто "
                 "оставьте письмо без ответа: без ссылки и кода кабинет не откроется.",
            **shared,
        )
    return Letter(
        kind="sign_in",
        subject="Вход в кабинет",
        title="С возвращением",
        lines=["Ваш кабинет ждёт: нажмите кнопку — и он откроется."],
        button="Войти в кабинет",
        foot="Письмо пришло, потому что на нашем сайте попросили вход с этим адресом. Если это были не вы, "
             "просто оставьте письмо: без ссылки и кода в кабинет никто не войдёт.",
        **shared,
    )


def _proof(found: dict) -> Letter:
    return Letter(
        kind="code",
        subject="Код подтверждения",
        title="Ваш код",
        hello=_hello(found["name"]),
        lines=["Введите этот код в кабинете — он подтвердит, что это вы."],
        code=found.get("code") or "",
        code_note="Код подтверждения:",
        after=[f"Код действует {CODE_MINUTES} минут."],
        foot="Если вы ничего не подтверждали, просто оставьте письмо без ответа: без кода ничего не изменится.",
    )


def _reset(found: dict) -> Letter:
    return Letter(
        kind="reset",
        subject="Новый пароль от кабинета",
        title="Новый пароль",
        hello=_hello(found["name"]),
        lines=["Вы попросили новый пароль. Задайте его по кнопке ниже — и кабинет снова открыт."],
        button="Задать новый пароль",
        url=link(f"/login?reset={found['token']}"),
        after=[f"Ссылка открыта {RESET_MINUTES} минут и сработает один раз."],
        foot="Если вы ничего не просили, просто не открывайте ссылку: ваш пароль остался прежним.",
    )


def _pair(row: dict, kind: str, subject: str, title: str, lines: list[str]) -> Letter:
    return Letter(
        kind=kind,
        subject=subject,
        title=title,
        hello=_hello(row["inviter"]),
        lines=lines,
        button="Открыть пару",
        url=link(f"/cabinet/pair?partner={row['id']}"),
        foot=_SIGN_OFF,
    )


def _filled(row: dict) -> Letter:
    return _pair(
        row,
        "partner_filled",
        f"Вторая звезда зажглась: {row['name']}",
        "Вторая звезда зажглась",
        [
            f"Пришёл ответ на ваше приглашение: {row['name']} — вторая звезда пары зажглась. "
            "Тон пары, пять сфер и главные связи между картами уже ждут вас.",
        ],
    )


def _linked(row: dict) -> Letter:
    lines = [
        f"Партнёр — {row['name']} — открыл свой кабинет, и ваша пара теперь общая: она видна вам обоим. "
        "Если один из вас откроет разбор, он откроется у обоих.",
    ]
    if not row["share_at"]:
        lines.append(
            "Чтобы и у партнёра зажглась ваша звезда, согласитесь показать партнёру ваши данные рождения — "
            "кнопка ждёт на странице пары."
        )
    return _pair(row, "pair_linked", f"Пара стала общей: {row['name']}", "Пара стала общей", lines)


def _bought(row: dict) -> Letter:
    return _pair(
        row,
        "pair_bought",
        f"Разбор пары открыт для вас обоих: {row['name']}",
        "Разбор пары открыт",
        [
            f"Партнёр — {row['name']} — открыл полный разбор вашей пары для вас обоих. "
            "Он уже ждёт вас целиком: все связи между картами, пять сфер и полное толкование.",
        ],
    )


def _gift(row: dict) -> Letter:
    return _pair(
        row,
        "pair_gift",
        f"Подарок: разбор пары с партнёром {row['name']}",
        "Подарок для вашей пары",
        [
            f"Мы открыли для вас полный разбор пары с партнёром {row['name']}. "
            "Он уже ждёт вас целиком: все связи между картами, пять сфер и полное толкование.",
        ],
    )


def _left(row: dict) -> Letter:
    return _pair(
        row,
        "pair_left",
        f"Партнёр удалил пару: {row['name']}",
        "Ваша пара остаётся с вами",
        [
            f"Партнёр — {row['name']} — удалил вашу пару у себя. У вас она остаётся: "
            "звезда партнёра и всё, что было открыто, никуда не денутся.",
        ],
    )


def _sky_end(row: dict) -> Letter:
    day = _day(row["sky_until"])
    return Letter(
        kind="sky_end",
        subject=f"«Небосвод» открыт до {day}",
        title=f"«Небосвод» открыт до {day}",
        hello=_hello(row["name"]),
        lines=[
            f"Ваш «Небосвод» открыт до {day}. Потом прогнозы останутся без толкований, "
            "а портрет карты и ИИ-астролог закроются.",
            "Сам он не продлевается и ничего не спишет: если хотите остаться под этим небом, продлите его "
            "в кабинете — новый срок прибавится к оставшимся дням.",
        ],
        button="Продлить «Небосвод»",
        url=link("/cabinet/sky"),
        foot=_SIGN_OFF,
    )


def _paid_sky(row: dict) -> Letter:
    """`row`: name, sky_until — the new end, extended — whether the days were added to a running term."""
    day = _day(row["sky_until"])
    if row["extended"]:
        subject, title = f"«Небосвод» продлён до {day}", "«Небосвод» продлён"
        first = (f"Спасибо, что остаётесь с нами! Новый срок прибавился к оставшимся дням — "
                 f"теперь «Небосвод» открыт до {day}.")
    else:
        subject, title = f"«Небосвод» открыт до {day}", "«Небосвод» открыт"
        first = f"Спасибо за оплату! Ваш «Небосвод» зажёгся и открыт до {day}."
    return Letter(
        kind="paid_sky",
        subject=subject,
        title=title,
        hello=_hello(row["name"]),
        lines=[first, _SKY_OPENS],
        button="Открыть «Небосвод»",
        url=link("/cabinet/sky"),
        after=["«Небосвод» не продлевается сам и ничего не спишет без вас.", _RECEIPT],
        foot="Письмо пришло, потому что вы оплатили «Небосвод» на нашем сайте.",
    )


def _paid_pair(row: dict) -> Letter:
    """`row`: name, partner — the partner's name, partner_id, linked — whether the partner has a cabinet."""
    lines = [
        f"Спасибо за оплату! Полный разбор вашей пары с партнёром {row['partner']} открыт: все связи между "
        "картами, пять сфер и полное толкование.",
    ]
    if row["linked"]:
        lines.append("У партнёра тоже есть кабинет — разбор открылся у вас обоих.")
    return Letter(
        kind="paid_pair",
        subject=f"Разбор пары открыт: {row['partner']}",
        title="Разбор пары открыт",
        hello=_hello(row["name"]),
        lines=lines,
        button="Открыть разбор",
        url=link(f"/cabinet/pair?partner={row['partner_id']}"),
        after=[_RECEIPT],
        foot="Письмо пришло, потому что вы оплатили разбор пары на нашем сайте.",
    )


def _pay_left(row: dict) -> Letter:
    """`row`: name, product — «synastry» or a plan of «Небосвод», partner and partner_id for a pair."""
    why = "так бывает: банк попросил подтверждение, оборвалась связь или просто отвлекли дела."
    if row["product"] == "synastry":
        return Letter(
            kind="pay_left",
            subject=f"Разбор пары с партнёром {row['partner']} ждёт вас",
            title="Разбор пары ждёт вас",
            hello=_hello(row["name"]),
            lines=[
                f"Недавно вы начали оплату разбора пары с партнёром {row['partner']}, но она не завершилась — {why}",
                "Разбор по-прежнему ждёт вас: все связи между картами, пять сфер и полное толкование. "
                "Продолжить можно на странице пары — это займёт минуту.",
            ],
            button="Открыть пару",
            url=link(f"/cabinet/pair?partner={row['partner_id']}"),
            after=["За незавершённую оплату деньги не списываются."],
            foot=_SIGN_OFF,
        )
    return Letter(
        kind="pay_left",
        subject="«Небосвод» ждёт вас",
        title="«Небосвод» ждёт вас",
        hello=_hello(row["name"]),
        lines=[
            f"Недавно вы начали оплату «Небосвода», но она не завершилась — {why}",
            f"{_SKY_OPENS} Продолжить можно в кабинете — это займёт минуту.",
        ],
        button="Вернуться к «Небосводу»",
        url=link("/cabinet/sky"),
        after=["За незавершённую оплату деньги не списываются."],
        foot=_SIGN_OFF,
    )


def _test(_row: dict | None = None) -> Letter:
    return Letter(
        kind="test",
        subject="Пробное письмо",
        title="Почта настроена",
        hello="Здравствуйте!",
        lines=["Письма с подтверждением почты, новым паролем и напоминаниями будут уходить с этого адреса — и выглядеть так."],
        button="Открыть сайт",
        url=link("/"),
    )


# The senders.


def confirm_letter(found: dict) -> None:
    """`found` is what accounts.start_sign_in, confirm_request or set_email gave: user_id, email, name,
    the token and the code, whether the address is still to be confirmed (first) and whether it is a
    new address for an account already open (change)."""
    deliver(found["email"], _confirm(found), found.get("user_id"))


def code_letter(found: dict) -> None:
    """`found` is what accounts.request_code gave: the six digits for the profile's guarded steps."""
    deliver(found["email"], _proof(found), found.get("user_id"))


def reset_letter(found: dict) -> None:
    """`found` is what accounts.request_reset gave: user_id, email, name and the token."""
    deliver(found["email"], _reset(found), found.get("user_id"))


def test_letter(to: str) -> str:
    """The operator's test letter, sent now: '' when it went, else what the server said."""
    return deliver(to, _test())


def _sides(ids: list[int]) -> list[dict]:
    """The sides of pairs with the people to write to: those who keep the letters on."""
    if not ids or not mail_on():
        return []
    with pool.connection() as conn:
        return conn.execute(
            """
            SELECT p.id, p.name, p.share_at, u.id AS user_id, u.email, u.name AS inviter
            FROM partners p JOIN users u ON u.id = p.user_id
            WHERE p.id = ANY(%s) AND u.mail_notes AND NOT u.blocked
            """,
            (ids,),
        ).fetchall()


def _to_sides(ids: list[int], build) -> None:
    for row in _sides(ids):
        deliver(row["email"], build(row), row["user_id"])


def partner_filled(partner_id: int) -> None:
    """The partner has given their data by the invitation: the one who invited hears of it."""
    _to_sides([partner_id], _filled)


def pair_linked(partner_id: int) -> None:
    """The partner has opened a cabinet of their own: the pair is now the same for both."""
    _to_sides([partner_id], _linked)


def pair_bought(told: list[dict]) -> None:
    """The partner has bought the reading of the pair: it is open on this side too."""
    _to_sides([side["partner_id"] for side in told], _bought)


def pair_gift(told: list[dict]) -> None:
    """The operator has opened the reading of the pair."""
    _to_sides([side["partner_id"] for side in told], _gift)


def pair_left(told: list[dict]) -> None:
    """The partner has deleted the pair on their side: this side keeps it."""
    _to_sides([side["partner_id"] for side in told], _left)


def paid(payment_id: int, extended: bool = False) -> None:
    """A payment has just gone through (payments._apply, once): the one who paid hears what opened.

    Goes whatever the letters setting, like a receipt; `extended` — «Небосвод» was still running
    and the days were added to it.
    """
    with pool.connection() as conn:
        row = conn.execute(
            """
            SELECT p.product, p.partner_id, u.id AS user_id, u.email, u.name, u.sky_until, u.blocked,
                   pa.name AS partner, pa.linked_user_id
            FROM payments p
            JOIN users u ON u.id = p.user_id
            LEFT JOIN partners pa ON pa.id = p.partner_id
            WHERE p.id = %s AND p.status = 'succeeded'
            """,
            (payment_id,),
        ).fetchone()
    if row is None or row["blocked"]:
        return
    if row["product"] == "synastry":
        # The side it was paid from is gone meanwhile: nothing to lead to.
        if row["partner"] is None:
            return
        letter = _paid_pair({**row, "linked": row["linked_user_id"] is not None})
    else:
        if row["sky_until"] is None:
            return
        letter = _paid_sky({**row, "extended": extended})
    deliver(row["email"], letter, row["user_id"])


def remind_sky() -> int:
    """Writes to those whose «Небосвод» ends within SKY_AHEAD_DAYS; each term is reminded of once."""
    if not mail_on():
        return 0
    # The rows are claimed by the UPDATE itself: two workers never write the same letter twice.
    with pool.connection() as conn:
        rows = conn.execute(
            """
            UPDATE users SET sky_reminded = sky_until
            WHERE sky_until > now() AND sky_until < now() + make_interval(days => %s)
              AND mail_notes AND NOT blocked AND sky_reminded IS DISTINCT FROM sky_until
            RETURNING id, email, name, sky_until
            """,
            (SKY_AHEAD_DAYS,),
        ).fetchall()
    for row in rows:
        deliver(row["email"], _sky_end(row), row["id"])
    return len(rows)


def remind_pay() -> int:
    """A word, gently, to those whose payment did not finish a day ago and who have not paid since.

    Only a payment from one to three days old that was never recalled; only when that product is
    still not theirs (no later «Небосвод» paid, the pair's reading not open); only to those who keep
    the letters on and have confirmed their mail; once a week at most. A payment ЮKassa still holds
    as pending is asked about first: it may have gone through and only the notification was lost.
    """
    from app import payments  # payments imports this module on a payment, not at load

    if not mail_on() or not payments.payments_on():
        return 0
    with pool.connection() as conn:
        rows = conn.execute(
            f"""
            SELECT DISTINCT ON (p.user_id) {", ".join(f"p.{column.strip()}" for column in payments._COLUMNS.split(","))},
                   u.email AS to_email, u.name, pa.name AS partner
            FROM payments p
            JOIN users u ON u.id = p.user_id
            LEFT JOIN partners pa ON pa.id = p.partner_id
            WHERE p.status IN ('pending', 'canceled') AND p.reminded_at IS NULL
              AND p.created_at < now() - make_interval(hours => %s)
              AND p.created_at > now() - make_interval(hours => %s)
              AND u.mail_notes AND NOT u.blocked AND u.email_confirmed_at IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM letters l
                  WHERE l.user_id = p.user_id AND l.kind = 'pay_left' AND l.created_at > now() - make_interval(days => %s)
              )
              AND CASE WHEN p.product = 'synastry' THEN
                    pa.id IS NOT NULL AND p.pair_id IS NOT NULL
                    AND NOT EXISTS (SELECT 1 FROM purchases b WHERE b.product = 'synastry' AND b.pair_id = p.pair_id)
                  ELSE NOT EXISTS (
                    SELECT 1 FROM payments s
                    WHERE s.user_id = p.user_id AND s.product <> 'synastry' AND s.status = 'succeeded'
                      AND COALESCE(s.paid_at, s.created_at) > p.created_at
                  ) END
            ORDER BY p.user_id, p.created_at DESC
            """,
            (PAY_LEFT_AFTER_HOURS, PAY_LEFT_UNTIL_HOURS, PAY_LEFT_PAUSE_DAYS),
        ).fetchall()
    sent = 0
    for row in rows:
        if row["status"] == "pending":
            try:
                if payments._settle(row)["status"] == "succeeded":
                    continue
            except Exception as exc:  # noqa: BLE001 — ЮKassa not answering: try again next hour
                log.warning("Платёж %s: не узнали статус перед напоминанием: %s", row["id"], exc)
                continue
        with pool.connection() as conn:
            claimed = conn.execute(
                "UPDATE payments SET reminded_at = now() WHERE id = %s AND reminded_at IS NULL RETURNING id",
                (row["id"],),
            ).fetchone()
        if claimed is None:
            continue
        deliver(row["to_email"], _pay_left(row), row["user_id"])
        sent += 1
    return sent


# The admin's catalogue: each kind laid out on made-up data, with the site's own name and links.

def _samples() -> dict:
    soon = datetime.now(timezone.utc) + timedelta(days=SKY_AHEAD_DAYS)
    later = datetime.now(timezone.utc) + timedelta(days=30)
    found = {"name": "Анна", "token": "пример", "code": "482915", "change": False, "first": True}
    side = {"id": 0, "name": "Михаил", "inviter": "Анна", "share_at": None}
    return {
        "confirm": lambda: _confirm({**found, "name": ""}),
        "sign_in": lambda: _confirm({**found, "first": False}),
        "code": lambda: _proof(found),
        "confirm_change": lambda: _confirm({**found, "change": True}),
        "reset": lambda: _reset(found),
        "paid_sky": lambda: _paid_sky({"name": "Анна", "sky_until": later, "extended": False}),
        "paid_pair": lambda: _paid_pair({"name": "Анна", "partner": "Михаил", "partner_id": 0, "linked": True}),
        "pay_left": lambda: _pay_left({"name": "Анна", "product": "sky1"}),
        "sky_end": lambda: _sky_end({"name": "Анна", "sky_until": soon}),
        "partner_filled": lambda: _filled(side),
        "pair_linked": lambda: _linked(side),
        "pair_bought": lambda: _bought(side),
        "pair_gift": lambda: _gift(side),
        "pair_left": lambda: _left(side),
        "test": _test,
    }


def preview(kind: str) -> dict | None:
    """The letter of this kind on made-up data, as the person would see it: {subject, html}."""
    build = _samples().get(kind)
    if build is None:
        return None
    letter = build()
    return {"subject": letter.subject, "html": html(letter)}


async def loop() -> None:
    """The reminders, once an hour while the backend runs."""
    while True:
        for job in (outbox.tidy, remind_sky, remind_pay):
            try:
                await asyncio.to_thread(job)
            except Exception as exc:  # noqa: BLE001 — a bad hour must not stop the next one
                log.error("Напоминания не разосланы (%s): %s", job.__name__, exc, exc_info=exc)
        await asyncio.sleep(LOOP_SECONDS)
