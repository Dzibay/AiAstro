"""The letters the site writes by itself: the new password link, «Небосвод» nearing its end,
the partner who has answered the invitation, and what happens to a pair shared by two cabinets.

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


def _sides(ids: list[int]) -> list[dict]:
    """The sides of pairs with the people to write to: those who keep the letters on."""
    if not ids or not mail_on():
        return []
    with pool.connection() as conn:
        return conn.execute(
            """
            SELECT p.id, p.name, p.share_at, u.email, u.name AS inviter
            FROM partners p JOIN users u ON u.id = p.user_id
            WHERE p.id = ANY(%s) AND u.mail_notes AND NOT u.blocked
            """,
            (ids,),
        ).fetchall()


def partner_filled(partner_id: int) -> None:
    """The partner has given their data by the invitation: the one who invited hears of it."""
    for row in _sides([partner_id]):
        _filled(row)


def _filled(row: dict) -> None:
    send_quietly(
        row["email"],
        f"Вторая звезда зажглась: {row['name']}",
        f"""{_hello(row["inviter"])}

Пришёл ответ на ваше приглашение: {row["name"]} — вторая звезда пары зажглась. Тон пары, пять сфер и главные связи между картами уже ждут вас:

{link(f"/cabinet/pair?partner={row['id']}")}

{_SIGN_OFF}""",
    )


def pair_linked(partner_id: int) -> None:
    """The partner has opened a cabinet of their own: the pair is now the same for both."""
    for row in _sides([partner_id]):
        ask = "" if row["share_at"] else (
            "\n\nЧтобы и у партнёра зажглась ваша звезда, согласитесь показать партнёру ваши данные рождения — "
            "кнопка ждёт на странице пары."
        )
        send_quietly(
            row["email"],
            f"Пара стала общей: {row['name']}",
            f"""{_hello(row["inviter"])}

Партнёр — {row["name"]} — открыл свой кабинет, и ваша пара теперь общая: она видна вам обоим. Если один из вас откроет разбор, он откроется у обоих.{ask}

{link(f"/cabinet/pair?partner={row['id']}")}

{_SIGN_OFF}""",
        )


def pair_bought(told: list[dict]) -> None:
    """The partner has bought the reading of the pair: it is open on this side too."""
    for row in _sides([side["partner_id"] for side in told]):
        send_quietly(
            row["email"],
            f"Разбор пары открыт для вас обоих: {row['name']}",
            f"""{_hello(row["inviter"])}

Партнёр — {row["name"]} — открыл полный разбор вашей пары для вас обоих. Он уже ждёт вас целиком: все связи между картами, пять сфер и полное толкование.

{link(f"/cabinet/pair?partner={row['id']}")}

{_SIGN_OFF}""",
        )


def pair_gift(told: list[dict]) -> None:
    """The operator has opened the reading of the pair."""
    for row in _sides([side["partner_id"] for side in told]):
        send_quietly(
            row["email"],
            f"Подарок: разбор пары с партнёром {row['name']}",
            f"""{_hello(row["inviter"])}

Мы открыли для вас полный разбор пары с партнёром {row["name"]}. Он уже ждёт вас целиком: все связи между картами, пять сфер и полное толкование.

{link(f"/cabinet/pair?partner={row['id']}")}

{_SIGN_OFF}""",
        )


def pair_left(told: list[dict]) -> None:
    """The partner has deleted the pair on their side: this side keeps it."""
    for row in _sides([side["partner_id"] for side in told]):
        send_quietly(
            row["email"],
            f"Партнёр удалил пару: {row['name']}",
            f"""{_hello(row["inviter"])}

Партнёр — {row["name"]} — удалил вашу пару у себя. У вас она остаётся: звезда партнёра и всё, что было открыто, никуда не денутся.

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
