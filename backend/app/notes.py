"""The letters the site writes by itself: the new password link, «Небосвод» nearing its end,
the partner who has answered the invitation.

The reminders go only to those who keep the letters on (users.mail_notes); the password link
goes always, since the person has just asked for it.
"""

import asyncio
import logging
from zoneinfo import ZoneInfo

from app.accounts import RESET_MINUTES
from app.db import pool
from app.mailer import link, mail_on, send_quietly

log = logging.getLogger("aiastro")

# «Небосвод» reminds of its end this many days ahead; the loop looks once an hour.
SKY_AHEAD_DAYS = 3
LOOP_SECONDS = 3600
_MONTHS = ("января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа",
           "сентября", "октября", "ноября", "декабря")
_SIGN_OFF = "Письма о сроке «Небосвода» и о партнёрах можно отключить в кабинете, в разделе «Профиль»."


def _hello(name: str) -> str:
    return f"{name}, здравствуйте!" if name else "Здравствуйте!"


def reset_letter(found: dict) -> None:
    """`found` is what accounts.request_reset gave: email, name and the token."""
    send_quietly(
        found["email"],
        "Новый пароль от кабинета",
        f"""{_hello(found["name"])}

Вы попросили новый пароль. Задайте его по этой ссылке — она открыта {RESET_MINUTES} минут и сработает один раз:

{link(f"/login?reset={found['token']}")}

Если вы ничего не просили, просто не открывайте её: ваш пароль остался прежним.""",
    )


def partner_filled(token: str) -> None:
    """The partner has given their data by the invitation: the one who invited hears of it."""
    if not mail_on():
        return
    with pool.connection() as conn:
        row = conn.execute(
            """
            SELECT p.id, p.name, u.email, u.name AS inviter, u.mail_notes, u.blocked
            FROM partners p JOIN users u ON u.id = p.user_id
            WHERE p.invite_token = %s
            """,
            (token,),
        ).fetchone()
    if row is None or row["blocked"] or not row["mail_notes"]:
        return
    send_quietly(
        row["email"],
        f"Вторая звезда зажглась: {row['name']}",
        f"""{_hello(row["inviter"])}

Пришёл ответ на ваше приглашение: {row["name"]} — вторая звезда пары зажглась. Тон пары, пять сфер и главные связи между картами уже ждут вас:

{link(f"/cabinet/pair?partner={row['id']}")}

{_SIGN_OFF}""",
    )


def _day(moment) -> str:
    local = moment.astimezone(ZoneInfo("Europe/Moscow"))
    return f"{local.day} {_MONTHS[local.month - 1]}"


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
            RETURNING email, name, sky_until
            """,
            (SKY_AHEAD_DAYS,),
        ).fetchall()
    for row in rows:
        send_quietly(
            row["email"],
            f"«Небосвод» открыт до {_day(row['sky_until'])}",
            f"""{_hello(row["name"])}

Ваш «Небосвод» открыт до {_day(row["sky_until"])}. Потом прогнозы останутся без толкований, а портрет карты и астролог закроются. Сам он не продлевается и ничего не спишет: если хотите остаться под этим небом, продлите его в кабинете — новый срок прибавится к оставшимся дням.

{link("/cabinet/sky")}

{_SIGN_OFF}""",
        )
    return len(rows)


async def loop() -> None:
    """The reminders, once an hour while the backend runs."""
    while True:
        try:
            await asyncio.to_thread(remind_sky)
        except Exception as exc:  # noqa: BLE001 — a bad hour must not stop the next one
            log.warning("Напоминания не разосланы: %s", exc)
        await asyncio.sleep(LOOP_SECONDS)
