"""The letters the site writes by itself: the email confirmation, the new password link,
«Небосвод» nearing its end, the partner who has answered the invitation, and what happens to a
pair shared by two cabinets. All of them in the site's look (app.letters).

The reminders go only to those who keep the letters on (users.mail_notes); the confirmation and
the password link go always, since the person has just asked for them.
"""

import asyncio
import logging
from zoneinfo import ZoneInfo

from app.accounts import CONFIRM_HOURS, RESET_MINUTES
from app.db import pool
from app.letters import Letter, deliver
from app.mailer import link, mail_on

log = logging.getLogger("aiastro")

# «Небосвод» reminds of its end this many days ahead; the loop looks once an hour.
SKY_AHEAD_DAYS = 3
LOOP_SECONDS = 3600
_MONTHS = ("января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа",
           "сентября", "октября", "ноября", "декабря")
_SIGN_OFF = "Письма о сроке «Небосвода» и о партнёрах можно отключить в кабинете, в разделе «Профиль»."


def _hello(name: str) -> str:
    return f"{name}, здравствуйте!" if name else "Здравствуйте!"


def confirm_letter(found: dict) -> None:
    """`found` is what accounts.confirm_request or set_email gave: email, name, the token and
    whether it is a new address for an account already open."""
    url = link(f"/login?confirm={found['token']}")
    days = CONFIRM_HOURS // 24
    if found.get("change"):
        letter = Letter(
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
    else:
        letter = Letter(
            subject="Подтвердите почту — и кабинет откроется",
            title="Ваше небо почти готово",
            hello=_hello(found["name"]),
            lines=[
                "Спасибо, что вы с нами! Остался один шаг: подтвердите, что это ваша почта, — и кабинет откроется.",
                "Там вас ждут натальная карта, толкования планет и всё, что мы приготовили именно для вас.",
            ],
            button="Подтвердить и перейти в кабинет",
            url=url,
            after=[f"Ссылка открыта {days} дня и сработает один раз."],
            foot="Письмо пришло, потому что этот адрес указали при регистрации на нашем сайте. "
                 "Если регистрировались не вы, просто оставьте его без ответа.",
        )
    deliver(found["email"], letter)


def reset_letter(found: dict) -> None:
    """`found` is what accounts.request_reset gave: email, name and the token."""
    deliver(
        found["email"],
        Letter(
            subject="Новый пароль от кабинета",
            title="Новый пароль",
            hello=_hello(found["name"]),
            lines=["Вы попросили новый пароль. Задайте его по кнопке ниже — и кабинет снова открыт."],
            button="Задать новый пароль",
            url=link(f"/login?reset={found['token']}"),
            after=[f"Ссылка открыта {RESET_MINUTES} минут и сработает один раз."],
            foot="Если вы ничего не просили, просто не открывайте ссылку: ваш пароль остался прежним.",
        ),
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


def _pair_letter(row: dict, subject: str, title: str, lines: list[str]) -> None:
    deliver(
        row["email"],
        Letter(
            subject=subject,
            title=title,
            hello=_hello(row["inviter"]),
            lines=lines,
            button="Открыть пару",
            url=link(f"/cabinet/pair?partner={row['id']}"),
            foot=_SIGN_OFF,
        ),
    )


def partner_filled(partner_id: int) -> None:
    """The partner has given their data by the invitation: the one who invited hears of it."""
    for row in _sides([partner_id]):
        _filled(row)


def _filled(row: dict) -> None:
    _pair_letter(
        row,
        f"Вторая звезда зажглась: {row['name']}",
        "Вторая звезда зажглась",
        [
            f"Пришёл ответ на ваше приглашение: {row['name']} — вторая звезда пары зажглась. "
            "Тон пары, пять сфер и главные связи между картами уже ждут вас.",
        ],
    )


def pair_linked(partner_id: int) -> None:
    """The partner has opened a cabinet of their own: the pair is now the same for both."""
    for row in _sides([partner_id]):
        lines = [
            f"Партнёр — {row['name']} — открыл свой кабинет, и ваша пара теперь общая: она видна вам обоим. "
            "Если один из вас откроет разбор, он откроется у обоих.",
        ]
        if not row["share_at"]:
            lines.append(
                "Чтобы и у партнёра зажглась ваша звезда, согласитесь показать партнёру ваши данные рождения — "
                "кнопка ждёт на странице пары."
            )
        _pair_letter(row, f"Пара стала общей: {row['name']}", "Пара стала общей", lines)


def pair_bought(told: list[dict]) -> None:
    """The partner has bought the reading of the pair: it is open on this side too."""
    for row in _sides([side["partner_id"] for side in told]):
        _pair_letter(
            row,
            f"Разбор пары открыт для вас обоих: {row['name']}",
            "Разбор пары открыт",
            [
                f"Партнёр — {row['name']} — открыл полный разбор вашей пары для вас обоих. "
                "Он уже ждёт вас целиком: все связи между картами, пять сфер и полное толкование.",
            ],
        )


def pair_gift(told: list[dict]) -> None:
    """The operator has opened the reading of the pair."""
    for row in _sides([side["partner_id"] for side in told]):
        _pair_letter(
            row,
            f"Подарок: разбор пары с партнёром {row['name']}",
            "Подарок для вашей пары",
            [
                f"Мы открыли для вас полный разбор пары с партнёром {row['name']}. "
                "Он уже ждёт вас целиком: все связи между картами, пять сфер и полное толкование.",
            ],
        )


def pair_left(told: list[dict]) -> None:
    """The partner has deleted the pair on their side: this side keeps it."""
    for row in _sides([side["partner_id"] for side in told]):
        _pair_letter(
            row,
            f"Партнёр удалил пару: {row['name']}",
            "Ваша пара остаётся с вами",
            [
                f"Партнёр — {row['name']} — удалил вашу пару у себя. У вас она остаётся: "
                "звезда партнёра и всё, что было открыто, никуда не денутся.",
            ],
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
        deliver(
            row["email"],
            Letter(
                subject=f"«Небосвод» открыт до {_day(row['sky_until'])}",
                title=f"«Небосвод» открыт до {_day(row['sky_until'])}",
                hello=_hello(row["name"]),
                lines=[
                    f"Ваш «Небосвод» открыт до {_day(row['sky_until'])}. Потом прогнозы останутся без толкований, "
                    "а портрет карты и ИИ-астролог закроются.",
                    "Сам он не продлевается и ничего не спишет: если хотите остаться под этим небом, продлите его "
                    "в кабинете — новый срок прибавится к оставшимся дням.",
                ],
                button="Продлить «Небосвод»",
                url=link("/cabinet/sky"),
                foot=_SIGN_OFF,
            ),
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
