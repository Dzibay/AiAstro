"""Partners for the compatibility: entered by the person, or by the partner through an invitation.

An invitation is a partner row without birth data and with a token. Whoever opens the link sees
only the inviter's first name, gives their own data with their consent, and the row is filled:
the link then shows that the star is lit and takes nothing more.

A purchase opens the full reading of one pair. Until payment is connected the operator marks it.
"""

import secrets
from datetime import date, time

from psycopg.errors import UniqueViolation

from app.accounts import _clean_birth, get_user
from app.astro import synastry
from app.astro.texts import interpreter, pair_aspect_title, pair_phrase
from app.charts import chart_for, chart_of
from app.db import pool
from app.errors import DomainError
from app.readings import cached

PRODUCT = "synastry"
LIMIT = 20
_COLUMNS = (
    "id, user_id, name, birth_date, birth_time, birth_place, birth_lat, birth_lon, birth_tz, "
    "invite_token, filled_at, created_at"
)


def _clean_name(name: str) -> str:
    cleaned = " ".join(name.split())[:80]
    if not cleaned:
        raise DomainError("name")
    return cleaned


def _birth(row: dict) -> dict | None:
    if row["birth_date"] is None:
        return None
    return {
        "date": row["birth_date"].isoformat(),
        "time": row["birth_time"].strftime("%H:%M") if row["birth_time"] else None,
        "place": row["birth_place"] or None,
        "lat": float(row["birth_lat"]) if row["birth_lat"] is not None else None,
        "lon": float(row["birth_lon"]) if row["birth_lon"] is not None else None,
        "tz": row["birth_tz"] or None,
    }


def _public(row: dict, bought: set[int] | None = None) -> dict:
    birth = _birth(row)
    return {
        "id": row["id"],
        "name": row["name"],
        "birth": birth,
        # Waiting for the partner: the link is shown again until they fill it in.
        "invite": row["invite_token"] if birth is None else None,
        "filled_at": row["filled_at"].isoformat() if row["filled_at"] else None,
        "created_at": row["created_at"].isoformat(),
        "bought": row["id"] in (bought or set()),
    }


def _bought(user_id: int) -> set[int]:
    with pool.connection() as conn:
        rows = conn.execute(
            "SELECT partner_id FROM purchases WHERE user_id = %s AND product = %s AND partner_id IS NOT NULL",
            (user_id, PRODUCT),
        ).fetchall()
    return {row["partner_id"] for row in rows}


def list_partners(user_id: int) -> list[dict]:
    get_user(user_id)
    with pool.connection() as conn:
        rows = conn.execute(
            f"SELECT {_COLUMNS} FROM partners WHERE user_id = %s ORDER BY created_at, id",
            (user_id,),
        ).fetchall()
    bought = _bought(user_id)
    return [_public(row, bought) for row in rows]


def _own(user_id: int, partner_id: int) -> dict:
    with pool.connection() as conn:
        row = conn.execute(
            f"SELECT {_COLUMNS} FROM partners WHERE id = %s AND user_id = %s",
            (partner_id, user_id),
        ).fetchone()
    if row is None:
        raise DomainError("missing", 404)
    return row


def create_partner(
    user_id: int,
    name: str,
    birth_date: date | None = None,
    birth_time: time | None = None,
    place: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
) -> dict:
    """With the birth data the partner is entered by hand; without them, it waits for an invitation."""
    get_user(user_id)
    cleaned = _clean_name(name)
    birth = _clean_birth(birth_date, birth_time, place, lat, lon) if birth_date else (None, None, "", None, None, "")
    with pool.connection() as conn:
        count = conn.execute("SELECT count(*) AS n FROM partners WHERE user_id = %s", (user_id,)).fetchone()["n"]
        if count >= LIMIT:
            raise DomainError("partners_limit", 409)
        row = conn.execute(
            f"""
            INSERT INTO partners (
                user_id, name, birth_date, birth_time, birth_place, birth_lat, birth_lon, birth_tz, filled_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CASE WHEN %s THEN now() END)
            RETURNING {_COLUMNS}
            """,
            (user_id, cleaned, *birth, birth_date is not None),
        ).fetchone()
    return _public(row)


def delete_partner(user_id: int, partner_id: int) -> None:
    with pool.connection() as conn:
        row = conn.execute(
            "DELETE FROM partners WHERE id = %s AND user_id = %s RETURNING id",
            (partner_id, user_id),
        ).fetchone()
    if row is None:
        raise DomainError("missing", 404)


def invite(user_id: int, partner_id: int) -> dict:
    """The link for the partner. Asked again, it stays the same; a filled partner needs none."""
    row = _own(user_id, partner_id)
    if row["birth_date"] is not None:
        raise DomainError("filled", 409)
    if row["invite_token"]:
        return _public(row, _bought(user_id))
    for _ in range(3):
        try:
            with pool.connection() as conn:
                row = conn.execute(
                    f"UPDATE partners SET invite_token = %s WHERE id = %s AND user_id = %s RETURNING {_COLUMNS}",
                    (secrets.token_urlsafe(18), partner_id, user_id),
                ).fetchone()
            return _public(row, _bought(user_id))
        except UniqueViolation:
            continue
    raise DomainError("invite", 500)


# ---- The partner's side: open, no account ----

def _by_token(token: str) -> dict:
    if not token or len(token) > 64:
        raise DomainError("missing", 404)
    with pool.connection() as conn:
        row = conn.execute(
            f"""
            SELECT p.{_COLUMNS.replace(', ', ', p.')}, u.name AS inviter, u.blocked
            FROM partners p JOIN users u ON u.id = p.user_id
            WHERE p.invite_token = %s
            """,
            (token,),
        ).fetchone()
    if row is None or row["blocked"]:
        raise DomainError("missing", 404)
    return row


def _invitation(row: dict) -> dict:
    # Only the first names: the inviter's data and chart stay theirs.
    return {"inviter": row["inviter"], "name": row["name"], "filled": row["birth_date"] is not None}


def open_invite(token: str) -> dict:
    return _invitation(_by_token(token))


def fill_invite(
    token: str,
    name: str,
    consent: bool,
    birth_date: date,
    birth_time: time | None,
    place: str | None,
    lat: float | None = None,
    lon: float | None = None,
) -> dict:
    row = _by_token(token)
    if row["birth_date"] is not None:
        raise DomainError("filled", 409)
    # These are the partner's own personal data: nothing is kept without their consent.
    if not consent:
        raise DomainError("consent")
    cleaned = _clean_name(name) if name.strip() else row["name"]
    birth = _clean_birth(birth_date, birth_time, place, lat, lon)
    with pool.connection() as conn:
        filled = conn.execute(
            f"""
            UPDATE partners
            SET name = %s, birth_date = %s, birth_time = %s, birth_place = %s, birth_lat = %s, birth_lon = %s,
                birth_tz = %s, consent_at = now(), filled_at = now()
            WHERE id = %s AND birth_date IS NULL
            RETURNING {_COLUMNS}
            """,
            (cleaned, *birth, row["id"]),
        ).fetchone()
    if filled is None:
        raise DomainError("filled", 409)
    return _invitation({**filled, "inviter": row["inviter"]})


# ---- The pair ----

def synastry_of(user_id: int, partner_id: int) -> dict:
    """The free part (tone, spheres, key aspects, the reading's opening) always; the whole reading once bought."""
    row = _own(user_id, partner_id)
    birth = _birth(row)
    if birth is None:
        raise DomainError("pending", 409)
    mine = chart_of(user_id)
    pair = synastry.build(mine, chart_for(birth))
    bought = partner_id in _bought(user_id)
    inputs = [pair["tone"], pair["elements"], [[a["a"], a["b"], a["type"]] for a in pair["key"][:3]]]
    reading = cached("synastry", inputs, lambda: interpreter.synastry(pair))
    # Before the purchase only the essence and the first part leave the server: the page fades them.
    if not bought:
        reading = {**reading, "parts": reading["parts"][:1]}
    return {
        "partner": _public(row, {partner_id} if bought else set()),
        "tone": pair["tone"],
        "phrase": pair_phrase(pair),
        "aspects": [
            {key: aspect[key] for key in ("a", "b", "type", "orb")} | {"title": pair_aspect_title(aspect)}
            for aspect in pair["key"]
        ],
        "spheres": pair["spheres"],
        "reading": reading,
        "locked": not bought,
    }


# ---- The operator's side ----

def admin_partners(user_id: int) -> list[dict]:
    with pool.connection() as conn:
        rows = conn.execute(
            f"SELECT {_COLUMNS} FROM partners WHERE user_id = %s ORDER BY created_at, id",
            (user_id,),
        ).fetchall()
    bought = _bought(user_id)
    return [_public(row, bought) for row in rows]


def set_bought(user_id: int, partner_id: int, bought: bool) -> dict:
    row = _own(user_id, partner_id)
    with pool.connection() as conn:
        if bought:
            conn.execute(
                """
                INSERT INTO purchases (user_id, product, partner_id) VALUES (%s, %s, %s)
                ON CONFLICT (user_id, product, partner_id) WHERE partner_id IS NOT NULL DO NOTHING
                """,
                (user_id, PRODUCT, partner_id),
            )
        else:
            conn.execute(
                "DELETE FROM purchases WHERE user_id = %s AND product = %s AND partner_id = %s",
                (user_id, PRODUCT, partner_id),
            )
    return _public(row, {partner_id} if bought else set())
