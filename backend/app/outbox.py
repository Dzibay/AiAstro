"""The journal of letters: every letter the site sends, what became of it and whether its button
was pressed.

A letter is written down before it goes (status «sending»), then marked «sent», «failed» with the
server's answer, or «off» when the mail is not set up. Its button leads through our own address,
/api/site/go/<token>?to=/path: the press is counted and the person goes on to the page. The path is
carried in the link, not kept here, so the one-time tokens of the confirmation and the new password
never land in the database.

A person's letters live as long as their cabinet (ON DELETE CASCADE); the operator's test letters,
which belong to nobody, are wiped after TEST_DAYS.
"""

import secrets
from urllib.parse import urlencode, urlsplit

from app.db import pool
from app.mailer import link

# key: (name, when it goes, who gets it). «always» — goes whatever the person's choice; «notes» —
# only to those who keep the letters on (users.mail_notes); «operator» — sent by hand from the admin.
KINDS = {
    "confirm": (
        "Первый вход: ссылка и код",
        "Когда новый человек указал почту (на главной, на странице входа, на лендинге) и по кнопке «Отправить ещё "
        "раз». Ссылка и шесть цифр открывают кабинет и подтверждают почту.",
        "always",
    ),
    "sign_in": (
        "Вход по почте: ссылка и код",
        "Когда человек с подтверждённой почтой входит по почте, а не паролем.",
        "always",
    ),
    "code": ("Код подтверждения", "В профиле: смена почты, нового пароля или удаление аккаунта без пароля.", "always"),
    "confirm_change": ("Подтверждение новой почты", "Когда в профиле указали новый адрес — уходит на него.", "always"),
    "reset": ("Новый пароль", "По просьбе на странице входа «Забыли пароль?».", "always"),
    "paid_sky": ("Оплата «Небосвода»", "Сразу после успешной оплаты «Небосвода»: до какого числа он открыт.", "always"),
    "paid_pair": ("Оплата разбора пары", "Сразу после успешной оплаты разбора пары — тому, кто платил.", "always"),
    "pay_left": (
        "Незавершённая оплата",
        "Через сутки после оплаты, которая не завершилась (ожидает или отменена), если тот же продукт так и "
        "не оплачен. Не чаще раза в 7 дней, по платежу — один раз.",
        "notes",
    ),
    "sky_end": ("Скорый конец «Небосвода»", "За 3 дня до конца срока, по каждому сроку один раз.", "notes"),
    "partner_filled": ("Партнёр ответил на приглашение", "Партнёр заполнил данные по ссылке-приглашению.", "notes"),
    "pair_linked": ("Пара стала общей", "Партнёр открыл свой кабинет, и пара теперь видна обоим.", "notes"),
    "pair_bought": ("Партнёр открыл разбор пары", "Партнёр оплатил разбор — он открылся и на этой стороне.", "notes"),
    "pair_gift": ("Подарок: разбор пары", "Оператор открыл разбор пары в админке.", "notes"),
    "pair_left": ("Партнёр удалил пару", "Партнёр удалил пару у себя — на этой стороне она остаётся.", "notes"),
    "test": ("Пробное письмо", "Кнопка «Отправить пробное письмо» в настройках почты.", "operator"),
}
STATUSES = ("sending", "sent", "failed", "off")
TEST_DAYS = 90
PAGE = 50
_COLUMNS = "l.id, l.user_id, l.kind, l.email, l.subject, l.status, l.error, l.clicks, l.clicked_at, l.created_at, l.sent_at"


def begin(user_id: int | None, kind: str, email: str, subject: str) -> dict:
    """Writes the letter down before it goes: {id, token}."""
    if kind not in KINDS:
        raise ValueError(f"unknown letter kind {kind}")
    with pool.connection() as conn:
        return conn.execute(
            "INSERT INTO letters (user_id, kind, email, subject, token) VALUES (%s, %s, %s, %s, %s) RETURNING id, token",
            (user_id, kind, email, subject[:300], secrets.token_urlsafe(9)),
        ).fetchone()


def end(entry: dict, status: str, error: str = "") -> None:
    with pool.connection() as conn:
        conn.execute(
            """
            UPDATE letters SET status = %s, error = %s, sent_at = CASE WHEN %s = 'sent' THEN now() END
            WHERE id = %s
            """,
            (status, error[:500], status, entry["id"]),
        )


def tracked(token: str, url: str) -> str:
    """The button's address through ours, so the press is counted; a link elsewhere stays as it is."""
    base = link("")
    if not url.startswith(f"{base}/"):
        return url
    return link(f"/api/site/go/{token}?{urlencode({'to': url[len(base):]})}")


def safe_path(path: str) -> str:
    """Only a page of this site: «/cabinet/sky?x=1», never «//elsewhere» or «https://…»."""
    if not isinstance(path, str) or not path.startswith("/") or path.startswith("//") or "\\" in path:
        return "/"
    parts = urlsplit(path)
    if parts.scheme or parts.netloc or any(ord(char) < 32 for char in path):
        return "/"
    return path


def click(token: str) -> None:
    """The button was pressed: counted, and the first press keeps its time."""
    if not token or len(token) > 40:
        return
    with pool.connection() as conn:
        conn.execute(
            "UPDATE letters SET clicks = clicks + 1, clicked_at = COALESCE(clicked_at, now()) WHERE token = %s",
            (token,),
        )


def sent_lately(user_id: int, kind: str, days: int) -> bool:
    with pool.connection() as conn:
        return conn.execute(
            "SELECT 1 FROM letters WHERE user_id = %s AND kind = %s AND created_at > now() - make_interval(days => %s)",
            (user_id, kind, days),
        ).fetchone() is not None


def tidy() -> None:
    """A letter that was «sending» when the backend stopped never got an answer; the test letters age out."""
    with pool.connection() as conn:
        conn.execute(
            """
            UPDATE letters SET status = 'failed', error = 'Отправка прервалась: сервер перезапустился'
            WHERE status = 'sending' AND created_at < now() - interval '15 minutes'
            """
        )
        conn.execute(
            "DELETE FROM letters WHERE user_id IS NULL AND created_at < now() - make_interval(days => %s)",
            (TEST_DAYS,),
        )


def _public(row: dict) -> dict:
    name, _, _ = KINDS.get(row["kind"], (row["kind"], "", ""))
    return {**row, "name": name}


def listing(query: str = "", kind: str = "", status: str = "", offset: int = 0) -> dict:
    """The journal for the admin, newest first: by address or subject, by kind, by status."""
    where, params = ["TRUE"], []
    if query.strip():
        like = f"%{query.strip().lower()}%"
        where.append("(lower(l.email) LIKE %s OR lower(l.subject) LIKE %s)")
        params += [like, like]
    if kind in KINDS:
        where.append("l.kind = %s")
        params.append(kind)
    if status == "clicked":
        where.append("l.clicks > 0")
    elif status in STATUSES:
        where.append("l.status = %s")
        params.append(status)
    offset = max(int(offset or 0), 0)
    with pool.connection() as conn:
        rows = conn.execute(
            f"""
            SELECT {_COLUMNS}, u.email AS user_email
            FROM letters l LEFT JOIN users u ON u.id = l.user_id
            WHERE {' AND '.join(where)}
            ORDER BY l.created_at DESC, l.id DESC
            LIMIT %s OFFSET %s
            """,
            (*params, PAGE + 1, offset),
        ).fetchall()
    return {"items": [_public(row) for row in rows[:PAGE]], "more": len(rows) > PAGE}


def of_user(user_id: int, limit: int = 100) -> list[dict]:
    with pool.connection() as conn:
        rows = conn.execute(
            f"SELECT {_COLUMNS} FROM letters l WHERE l.user_id = %s ORDER BY l.created_at DESC, l.id DESC LIMIT %s",
            (user_id, limit),
        ).fetchall()
    return [_public(row) for row in rows]


def catalogue() -> dict:
    """Every kind of letter the site can send, with the last 30 days of each."""
    with pool.connection() as conn:
        rows = conn.execute(
            """
            SELECT kind,
                   count(*) AS total,
                   count(*) FILTER (WHERE status = 'sent') AS sent,
                   count(*) FILTER (WHERE status = 'failed') AS failed,
                   count(*) FILTER (WHERE status = 'off') AS off,
                   count(*) FILTER (WHERE clicks > 0) AS clicked,
                   max(created_at) AS last_at
            FROM letters WHERE created_at > now() - interval '30 days'
            GROUP BY kind
            """
        ).fetchall()
    stats = {row["kind"]: row for row in rows}
    empty = {"total": 0, "sent": 0, "failed": 0, "off": 0, "clicked": 0, "last_at": None}
    kinds = []
    for key, (name, when, rule) in KINDS.items():
        row = stats.get(key) or empty
        kinds.append({"kind": key, "name": name, "when": when, "rule": rule, **{k: row[k] for k in empty}})
    return {"kinds": kinds}
