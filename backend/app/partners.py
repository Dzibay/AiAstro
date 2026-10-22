"""Pairs: two charts side by side, shared by the two people when both have a cabinet.

A pair (table pairs) has a side in the cabinet of each person in it (a row of partners): the
row holds the other one's name and birth data. A partner typed in by hand is a pair with one
side. An invitation is a side without birth data and with a token: whoever opens the link gives
their own data with their consent, and the star lights up. If they then open a cabinet of their
own (right from the invitation, or later: the page keeps a key for it), or accept the invitation
from the cabinet they already have, the pair gains its second side and is the same for both.

The purchase belongs to the pair, not to the one who paid: the reading opens on both sides, and
stays open on the side that is left when the other deletes the pair. A side deleted and added
again is a new pair, to be bought anew.

Whose data a side shows is the other person's own: they agree to it, the invitee in the form,
the inviter when sending the link (or later, when the partner has joined).
"""

import hashlib
import secrets
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from psycopg.errors import UniqueViolation

from app.accounts import _clean_birth, get_user
from app.astro import pair_forecast, synastry
from app.astro.texts import interpreter, pair_aspect_title, pair_phrase
from app.charts import _zone, chart_for, chart_of
from app.db import pool
from app.errors import DomainError
from app.readings import cached

PRODUCT = "synastry"
# The links between two charts a bought pair lists, strongest first.
MAX_ASPECTS = 16
LIMIT = 20
_FIELDS = (
    "id", "user_id", "pair_id", "name", "birth_date", "birth_time", "birth_place", "birth_lat", "birth_lon",
    "birth_tz", "invite_token", "linked_user_id", "joined_at", "share_at", "consent_at", "claim_hash", "news", "news_at",
    "filled_at", "created_at",
)
_BIRTH = ("birth_date", "birth_time", "birth_place", "birth_lat", "birth_lon", "birth_tz")


def _cols(alias: str = "p") -> str:
    return ", ".join(f"{alias}.{field}" for field in _FIELDS)


# Whether the pair still has another side: gone, the partner has deleted the pair on their end.
_MUTUAL = "EXISTS (SELECT 1 FROM partners o WHERE o.pair_id = p.pair_id AND o.id <> p.id) AS mutual"


def _clean_name(name: str) -> str:
    cleaned = " ".join(name.split())[:80]
    if not cleaned:
        raise DomainError("name")
    return cleaned


def _hash(claim: str) -> str:
    return hashlib.sha256(claim.encode()).hexdigest()


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


def _kind(row: dict) -> str:
    """linked — the partner has a cabinet; invite — they answer by the link; manual — typed in by hand."""
    # Joined once, the side stays a linked one even when the partner's cabinet is gone.
    if row["linked_user_id"] is not None or row["joined_at"] is not None:
        return "linked"
    return "invite" if row["invite_token"] or row["consent_at"] else "manual"


def _who(purchase: dict | None, user_id: int) -> str | None:
    if purchase is None:
        return None
    if purchase["source"] == "admin":
        return "gift"
    return "me" if purchase["user_id"] == user_id else "partner"


def _public(row: dict, bought: dict[int, dict] | None = None, user_id: int | None = None) -> dict:
    birth = _birth(row)
    purchase = (bought or {}).get(row["pair_id"])
    kind = _kind(row)
    linked = kind == "linked"
    return {
        "id": row["id"],
        "pair": row["pair_id"],
        "name": row["name"],
        "birth": birth,
        "kind": kind,
        # Waiting for the partner: the link is shown again until they fill it in.
        "invite": row["invite_token"] if birth is None and not linked else None,
        # A linked partner still waiting for the other's consent to show their data.
        "waiting_share": linked and birth is None and row.get("mutual", True),
        # The person's own consent to show the partner their data: given by sending the invitation.
        "shared": row["share_at"] is not None,
        # The partner has deleted the pair on their end: what was opened stays here.
        "left": linked and not row.get("mutual", True),
        "filled_at": row["filled_at"].isoformat() if row["filled_at"] else None,
        "created_at": row["created_at"].isoformat(),
        "bought": purchase is not None,
        # me, partner (the reading is their gift for both), gift (opened by the operator).
        "bought_by": _who(purchase, user_id if user_id is not None else row["user_id"]),
        "bought_at": purchase["created_at"].isoformat() if purchase else None,
        # Only a partner typed in by hand, and only until the reading is bought: else one purchase would open any pair.
        "editable": kind == "manual" and purchase is None,
        "news": row["news"] or None,
    }


def _bought(user_id: int) -> dict[int, dict]:
    """The bought pairs among the person's sides: pair id → the purchase (who paid, how and when)."""
    with pool.connection() as conn:
        rows = conn.execute(
            """
            SELECT pu.pair_id, pu.user_id, pu.source, pu.created_at FROM purchases pu
            WHERE pu.product = %s AND pu.pair_id IN (SELECT pair_id FROM partners WHERE user_id = %s)
            """,
            (PRODUCT, user_id),
        ).fetchall()
    return {row["pair_id"]: row for row in rows}


def _pair_bought(conn, pair_id: int) -> bool:
    return conn.execute(
        "SELECT 1 FROM purchases WHERE product = %s AND pair_id = %s", (PRODUCT, pair_id),
    ).fetchone() is not None


def _toned(user_id: int, items: list[dict]) -> list[dict]:
    """Each pair with both charts known gets its tone (easy, calm, tense, mixed): the colour of its thread in the list."""
    birth = get_user(user_id)["birth"]
    if birth is None:
        return items
    mine = chart_for(birth)
    return [{**item, "tone": synastry.build(mine, chart_for(item["birth"]))["tone"]} if item["birth"] else item for item in items]


def list_partners(user_id: int) -> list[dict]:
    with pool.connection() as conn:
        rows = conn.execute(
            f"SELECT {_cols()}, {_MUTUAL} FROM partners p WHERE p.user_id = %s ORDER BY p.created_at, p.id",
            (user_id,),
        ).fetchall()
    bought = _bought(user_id)
    return _toned(user_id, [_public(row, bought) for row in rows])


def _own(user_id: int, partner_id: int) -> dict:
    with pool.connection() as conn:
        row = conn.execute(
            f"SELECT {_cols()}, {_MUTUAL} FROM partners p WHERE p.id = %s AND p.user_id = %s",
            (partner_id, user_id),
        ).fetchone()
    if row is None:
        raise DomainError("missing", 404)
    return row


def _one(user_id: int, partner_id: int) -> dict:
    return _toned(user_id, [_public(_own(user_id, partner_id), _bought(user_id))])[0]


def create_partner(
    user_id: int,
    name: str,
    birth_date: date | None = None,
    birth_time: time | None = None,
    place: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
) -> dict:
    """With the birth data the partner is entered by hand; without them, it waits for an invitation.

    Sending the invitation is itself the consent to show the partner one's own data once they join.
    """
    get_user(user_id)
    cleaned = _clean_name(name)
    birth = _clean_birth(birth_date, birth_time, place, lat, lon) if birth_date else (None, None, "", None, None, "")
    with pool.connection() as conn:
        count = conn.execute("SELECT count(*) AS n FROM partners WHERE user_id = %s", (user_id,)).fetchone()["n"]
        if count >= LIMIT:
            raise DomainError("partners_limit", 409)
        pair = conn.execute("INSERT INTO pairs DEFAULT VALUES RETURNING id").fetchone()["id"]
        row = conn.execute(
            f"""
            INSERT INTO partners AS p (
                user_id, pair_id, name, birth_date, birth_time, birth_place, birth_lat, birth_lon, birth_tz,
                filled_at, share_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CASE WHEN %s THEN now() END, CASE WHEN %s THEN now() END)
            RETURNING {_cols()}
            """,
            (user_id, pair, cleaned, *birth, birth_date is not None, birth_date is None),
        ).fetchone()
    return _toned(user_id, [_public(row)])[0]


def update_partner(
    user_id: int,
    partner_id: int,
    name: str,
    birth_date: date | None = None,
    birth_time: time | None = None,
    place: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
) -> dict:
    """The name is the person's own label and changes always; the birth data only of a partner
    typed in by hand, and only until the reading is bought."""
    row = _own(user_id, partner_id)
    cleaned = _clean_name(name)
    with pool.connection() as conn:
        if birth_date is not None:
            if _kind(row) != "manual":
                raise DomainError("partner_locked", 409)
            if _pair_bought(conn, row["pair_id"]):
                raise DomainError("partner_locked", 409)
            birth = _clean_birth(birth_date, birth_time, place, lat, lon)
            conn.execute(
                """
                UPDATE partners SET birth_date = %s, birth_time = %s, birth_place = %s, birth_lat = %s,
                    birth_lon = %s, birth_tz = %s
                WHERE id = %s
                """,
                (*birth, partner_id),
            )
        conn.execute("UPDATE partners SET name = %s WHERE id = %s", (cleaned, partner_id))
    return _one(user_id, partner_id)


def delete_partner(user_id: int, partner_id: int) -> list[dict]:
    """Deletes the person's side. The partner's side, if there is one, keeps the pair and what was
    bought; it is told so. Gives those to write to: [{user_id, partner_id}]."""
    with pool.connection() as conn:
        row = conn.execute(
            "DELETE FROM partners WHERE id = %s AND user_id = %s RETURNING pair_id",
            (partner_id, user_id),
        ).fetchone()
        if row is None:
            raise DomainError("missing", 404)
        others = conn.execute(
            """
            UPDATE partners SET news = 'left', news_at = now()
            WHERE pair_id = %s AND joined_at IS NOT NULL
            RETURNING id AS partner_id, user_id
            """,
            (row["pair_id"],),
        ).fetchall()
    return others


def seen(user_id: int, partner_id: int) -> None:
    """The person has opened the pair: its mark goes out."""
    with pool.connection() as conn:
        conn.execute("UPDATE partners SET news = '' WHERE id = %s AND user_id = %s AND news <> ''", (partner_id, user_id))


def invite(user_id: int, partner_id: int) -> dict:
    """The link for the partner. Asked again, it stays the same; a filled partner needs none."""
    row = _own(user_id, partner_id)
    if row["birth_date"] is not None or row["joined_at"] is not None:
        raise DomainError("filled", 409)
    if row["invite_token"]:
        return _one(user_id, partner_id)
    for _ in range(3):
        try:
            with pool.connection() as conn:
                conn.execute(
                    "UPDATE partners SET invite_token = %s WHERE id = %s AND user_id = %s",
                    (secrets.token_urlsafe(18), partner_id, user_id),
                )
            return _one(user_id, partner_id)
        except UniqueViolation:
            continue
    raise DomainError("invite", 500)


def _copy_mine(conn, user_id: int) -> None:
    """The person's birth data onto the partners' sides that show them: where the person agreed
    to it, and while the pair is not bought (a bought reading keeps the data it was bought with;
    a side still without any gets them anyway)."""
    conn.execute(
        """
        UPDATE partners o
        SET birth_date = u.birth_date, birth_time = u.birth_time, birth_place = u.birth_place,
            birth_lat = u.birth_lat, birth_lon = u.birth_lon, birth_tz = u.birth_tz,
            filled_at = COALESCE(o.filled_at, CASE WHEN u.birth_date IS NOT NULL THEN now() END)
        FROM users u, partners m
        WHERE u.id = %s AND o.linked_user_id = u.id AND m.user_id = u.id AND m.pair_id = o.pair_id
          AND m.share_at IS NOT NULL AND u.birth_date IS NOT NULL
          AND (o.birth_date IS NULL OR NOT EXISTS (
              SELECT 1 FROM purchases pu WHERE pu.product = %s AND pu.pair_id = o.pair_id))
        """,
        (user_id, PRODUCT),
    )


def share(user_id: int, partner_id: int) -> dict:
    """The consent to show the partner who has joined one's own birth data: their star of you lights up."""
    row = _own(user_id, partner_id)
    if row["linked_user_id"] is None:
        raise DomainError("missing", 404)
    with pool.connection() as conn:
        conn.execute("UPDATE partners SET share_at = COALESCE(share_at, now()) WHERE id = %s", (partner_id,))
        conn.execute(
            "UPDATE partners SET news = 'filled', news_at = now() WHERE pair_id = %s AND user_id = %s AND birth_date IS NULL",
            (row["pair_id"], row["linked_user_id"]),
        )
        _copy_mine(conn, user_id)
    return _one(user_id, partner_id)


def mine_changed(user_id: int) -> None:
    """After the person's own birth data are set or corrected: the partners' sides follow."""
    with pool.connection() as conn:
        _copy_mine(conn, user_id)


# ---- The partner's side of an invitation ----

def _by_token(token: str) -> dict:
    if not token or len(token) > 64:
        raise DomainError("missing", 404)
    with pool.connection() as conn:
        row = conn.execute(
            f"""
            SELECT {_cols()}, u.name AS inviter, u.blocked
            FROM partners p JOIN users u ON u.id = p.user_id
            WHERE p.invite_token = %s
            """,
            (token,),
        ).fetchone()
    if row is None or row["blocked"]:
        raise DomainError("missing", 404)
    return row


def _invitation(row: dict, user_id: int | None = None) -> dict:
    # Only the first names: the inviter's data and chart stay theirs until the pair is joined.
    return {
        "inviter": row["inviter"],
        "name": row["name"],
        "filled": row["birth_date"] is not None,
        "linked": row["linked_user_id"] is not None,
        # The invitation is this person's own: their pair, already in their cabinet.
        "mine": user_id is not None and user_id in (row["linked_user_id"], row["user_id"]),
        "own": user_id is not None and user_id == row["user_id"],
        "share": row["share_at"] is not None,
    }


def open_invite(token: str, user_id: int | None = None) -> dict:
    return _invitation(_by_token(token), user_id)


def fill_invite(
    token: str,
    name: str,
    consent: bool,
    share_consent: bool,
    birth_date: date,
    birth_time: time | None,
    place: str | None,
    lat: float | None = None,
    lon: float | None = None,
) -> dict:
    """The partner's data by the link, without a cabinet. Gives back a key: kept by the page, it
    joins the pair to the cabinet the partner opens next (link_invite)."""
    row = _by_token(token)
    if row["birth_date"] is not None or row["linked_user_id"] is not None:
        raise DomainError("filled", 409)
    # These are the partner's own personal data: nothing is kept without their consent, and the
    # inviter sees them only because the partner agrees to it.
    if not consent or not share_consent:
        raise DomainError("consent")
    cleaned = _clean_name(name) if name.strip() else row["name"]
    birth = _clean_birth(birth_date, birth_time, place, lat, lon)
    claim = secrets.token_urlsafe(24)
    with pool.connection() as conn:
        filled = conn.execute(
            f"""
            UPDATE partners p
            SET name = %s, birth_date = %s, birth_time = %s, birth_place = %s, birth_lat = %s, birth_lon = %s,
                birth_tz = %s, consent_at = now(), filled_at = now(), claim_hash = %s, news = 'filled', news_at = now()
            WHERE id = %s AND birth_date IS NULL AND linked_user_id IS NULL
            RETURNING {_cols()}
            """,
            (cleaned, *birth, _hash(claim), row["id"]),
        ).fetchone()
    if filled is None:
        raise DomainError("filled", 409)
    # side: the inviter's, for the letter; the route keeps it to itself.
    return {**_invitation({**filled, "inviter": row["inviter"]}), "claim": claim, "side": row["id"]}


def _link(user_id: int, row: dict) -> dict:
    """The second side of the pair, in the cabinet of the one who answered the invitation."""
    if row["user_id"] == user_id:
        raise DomainError("self", 409)
    me = get_user(user_id)
    inviter = get_user(row["user_id"])
    with pool.connection() as conn:
        mine = conn.execute(
            "SELECT id FROM partners WHERE pair_id = %s AND user_id = %s", (row["pair_id"], user_id),
        ).fetchone()
        if mine is not None:
            return {"partner": mine["id"]}
        count = conn.execute("SELECT count(*) AS n FROM partners WHERE user_id = %s", (user_id,)).fetchone()["n"]
        if count >= LIMIT:
            raise DomainError("partners_limit", 409)
        # Claimed by the UPDATE itself: two cabinets never join the same invitation.
        won = conn.execute(
            """
            UPDATE partners SET linked_user_id = %s, joined_at = now(), claim_hash = NULL, news = 'linked', news_at = now()
            WHERE id = %s AND linked_user_id IS NULL AND birth_date IS NOT NULL
            RETURNING id
            """,
            (user_id, row["id"]),
        ).fetchone()
        if won is None:
            raise DomainError("linked", 409)
        if me["birth"] is None:
            # The cabinet opened from the invitation: the data the partner gave become their own.
            conn.execute(
                """
                UPDATE users SET birth_date = %s, birth_time = %s, birth_place = %s, birth_lat = %s, birth_lon = %s, birth_tz = %s
                WHERE id = %s AND birth_date IS NULL
                """,
                (*(row[field] for field in _BIRTH), user_id),
            )
        elif not _pair_bought(conn, row["pair_id"]):
            # The cabinet's own data are the partner's truth: the inviter's side follows them.
            conn.execute(
                """
                UPDATE partners p SET birth_date = u.birth_date, birth_time = u.birth_time, birth_place = u.birth_place,
                    birth_lat = u.birth_lat, birth_lon = u.birth_lon, birth_tz = u.birth_tz
                FROM users u WHERE u.id = %s AND p.id = %s
                """,
                (user_id, row["id"]),
            )
        # The inviter's data come over only with the inviter's consent; until then the star waits.
        shown = inviter["birth"] if row["share_at"] is not None else None
        created = conn.execute(
            f"""
            INSERT INTO partners AS p (
                user_id, pair_id, name, birth_date, birth_time, birth_place, birth_lat, birth_lon, birth_tz,
                linked_user_id, joined_at, share_at, consent_at, filled_at, news, news_at
            )
            SELECT %s, %s, %s, u.birth_date, u.birth_time, u.birth_place, u.birth_lat, u.birth_lon, u.birth_tz,
                   %s, now(), now(), %s, CASE WHEN u.birth_date IS NOT NULL THEN now() END, 'linked', now()
            FROM users u WHERE u.id = %s
            RETURNING id
            """,
            (user_id, row["pair_id"], inviter["name"] or "Партнёр", row["user_id"], row["share_at"], row["user_id"]),
        ).fetchone()
        if shown is None:
            conn.execute(
                "UPDATE partners SET birth_date = NULL, birth_time = NULL, birth_place = '', birth_lat = NULL, "
                "birth_lon = NULL, birth_tz = '', filled_at = NULL WHERE id = %s",
                (created["id"],),
            )
    # side: the inviter's, for the letter; the route keeps it to itself.
    return {"partner": created["id"], "side": row["id"]}


def link_invite(user_id: int, token: str, claim: str) -> dict:
    """The pair joins the cabinet opened after the invitation was answered: the key proves it is the same person."""
    row = _by_token(token)
    if row["linked_user_id"] == user_id:
        return {"partner": _side(user_id, row["pair_id"])}
    if not claim or not row["claim_hash"] or not secrets.compare_digest(_hash(claim), row["claim_hash"]):
        raise DomainError("claim", 403)
    return _link(user_id, row)


def accept_invite(user_id: int, token: str, share_consent: bool) -> dict:
    """The invitation answered from a cabinet that already exists: its own birth data light the star."""
    row = _by_token(token)
    if row["linked_user_id"] == user_id:
        return {"partner": _side(user_id, row["pair_id"])}
    if row["user_id"] == user_id:
        raise DomainError("self", 409)
    if row["birth_date"] is not None or row["linked_user_id"] is not None:
        raise DomainError("filled", 409)
    if not share_consent:
        raise DomainError("consent")
    me = get_user(user_id)
    if me["birth"] is None:
        raise DomainError("no_birth", 409)
    with pool.connection() as conn:
        filled = conn.execute(
            f"""
            UPDATE partners p
            SET name = u.name, birth_date = u.birth_date, birth_time = u.birth_time, birth_place = u.birth_place,
                birth_lat = u.birth_lat, birth_lon = u.birth_lon, birth_tz = u.birth_tz,
                consent_at = now(), filled_at = now(), news = 'filled', news_at = now()
            FROM users u
            WHERE u.id = %s AND p.id = %s AND p.birth_date IS NULL AND p.linked_user_id IS NULL
            RETURNING {_cols()}
            """,
            (user_id, row["id"]),
        ).fetchone()
    if filled is None:
        raise DomainError("filled", 409)
    return _link(user_id, {**filled, "inviter": row["inviter"]})


def _side(user_id: int, pair_id: int) -> int | None:
    with pool.connection() as conn:
        found = conn.execute("SELECT id FROM partners WHERE pair_id = %s AND user_id = %s", (pair_id, user_id)).fetchone()
    return found["id"] if found else None


# ---- The pair ----

def synastry_of(user_id: int, partner_id: int) -> dict:
    """The free part (tone, spheres, key aspects, the reading's opening) always; the whole reading once bought."""
    row = _own(user_id, partner_id)
    birth = _birth(row)
    if birth is None:
        raise DomainError("pending", 409)
    mine = chart_of(user_id)
    pair = synastry.build(mine, chart_for(birth))
    bought_map = _bought(user_id)
    bought = row["pair_id"] in bought_map
    inputs = [pair["tone"], pair["elements"], [[a["a"], a["b"], a["type"]] for a in pair["key"][:3]],
              pair["spheres"], pair["overlays"], pair["composite"]]
    reading = cached("synastry", inputs, lambda: interpreter.synastry(pair))
    total = len(reading["parts"])
    # Before the purchase only the essence and the first part leave the server: the page fades them.
    if not bought:
        reading = {**reading, "parts": reading["parts"][:1]}
    # Bought, the pair shows every link between the charts with its meaning; before, the key ones by name.
    shown = pair["aspects"][:MAX_ASPECTS] if bought else pair["key"]
    return {
        "partner": _public(row, bought_map),
        "tone": pair["tone"],
        "phrase": pair_phrase(pair),
        "aspects": [
            {key: aspect[key] for key in ("a", "b", "type", "orb")} | {
                "title": pair_aspect_title(aspect),
                "text": cached("pair_aspect", [aspect["a"], aspect["b"], aspect["type"]],
                               lambda aspect=aspect: {"text": interpreter.pair_aspect(aspect["a"], aspect["b"], aspect["type"])})["text"]
                if bought else None,
            }
            for aspect in shown
        ],
        "aspects_total": min(len(pair["aspects"]), MAX_ASPECTS),
        "spheres": pair["spheres"],
        "reading": reading,
        "total": total,
        "locked": not bought,
    }


def forecast_of(user_id: int, partner_id: int, tz: str | None = None) -> dict:
    """The pair's day: the sky over both charts. Open with a bought reading and «Небосвод» together."""
    row = _own(user_id, partner_id)
    birth = _birth(row)
    if birth is None:
        raise DomainError("pending", 409)
    user = get_user(user_id)
    bought = row["pair_id"] in _bought(user_id)
    if not bought or not user["sky"]:
        # Nothing is counted for a closed forecast: the page only says what opens it.
        return {"locked": True, "needs": [need for need, ok in (("bought", bought), ("sky", user["sky"])) if not ok]}
    zone = _zone(tz) or _zone(user["birth"]["tz"]) or "UTC"
    today = datetime.now(ZoneInfo(zone)).date()
    data = pair_forecast.build(chart_of(user_id), chart_for(birth), today, zone)
    return {**data, "text": pair_forecast.text(data, row["name"]), "locked": False}


def pairs_of(user_id: int, mine: dict, limit: int = 3) -> list[dict]:
    """The person's pairs in short, for the astrologer: [{name, tone, spheres}] of the partners with a birth date."""
    with pool.connection() as conn:
        rows = conn.execute(
            f"SELECT {_cols()} FROM partners p WHERE p.user_id = %s AND p.birth_date IS NOT NULL ORDER BY p.created_at, p.id LIMIT %s",
            (user_id, limit),
        ).fetchall()
    pairs = []
    for row in rows:
        birth = _birth(row)
        if birth is None:
            continue
        pair = synastry.build(mine, chart_for(birth))
        pairs.append({"name": row["name"], "tone": pair["tone"], "spheres": pair["spheres"]})
    return pairs


# ---- The operator's side ----

def admin_partners(user_id: int) -> list[dict]:
    with pool.connection() as conn:
        rows = conn.execute(
            f"SELECT {_cols()}, {_MUTUAL} FROM partners p WHERE p.user_id = %s ORDER BY p.created_at, p.id",
            (user_id,),
        ).fetchall()
    bought = _bought(user_id)
    return [_public(row, bought) for row in rows]


ADMIN_PAGE = 100
STATES = ("", "bought", "linked", "waiting")


def admin_pairs(query: str = "", state: str = "", offset: int = 0) -> dict:
    """Every pair with its sides, newest first: by the email or name of either person, or the partner's name.

    state: bought — the reading is open; linked — both have a cabinet; waiting — an invitation not yet answered.
    """
    if state not in STATES:
        raise DomainError("state")
    cleaned = " ".join(query.split()).lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{cleaned}%"
    having = {
        "": "TRUE",
        "bought": "pu.id IS NOT NULL",
        "linked": "bool_or(p.linked_user_id IS NOT NULL)",
        "waiting": "bool_or(p.birth_date IS NULL AND p.invite_token IS NOT NULL)",
    }[state]
    with pool.connection() as conn:
        rows = conn.execute(
            f"""
            SELECT pa.id, pa.created_at, pu.created_at AS bought_at, pu.source, bu.email AS payer_email,
                   json_agg(json_build_object(
                       'partner_id', p.id, 'user_id', p.user_id, 'email', u.email, 'user_name', u.name,
                       'name', p.name, 'filled', p.birth_date IS NOT NULL, 'invite', p.invite_token IS NOT NULL,
                       'linked', p.linked_user_id IS NOT NULL, 'news', p.news, 'created_at', p.created_at
                   ) ORDER BY p.created_at, p.id) AS sides
            FROM pairs pa
            JOIN partners p ON p.pair_id = pa.id
            JOIN users u ON u.id = p.user_id
            LEFT JOIN purchases pu ON pu.pair_id = pa.id AND pu.product = %s
            LEFT JOIN users bu ON bu.id = pu.user_id
            GROUP BY pa.id, pu.id, bu.id
            HAVING {having} AND bool_or(lower(u.email) LIKE %s OR lower(u.name) LIKE %s OR lower(p.name) LIKE %s)
            ORDER BY pa.id DESC
            LIMIT %s OFFSET %s
            """,
            (PRODUCT, pattern, pattern, pattern, ADMIN_PAGE + 1, offset),
        ).fetchall()
    items = [
        {
            "id": row["id"],
            "created_at": row["created_at"].isoformat(),
            "bought": row["bought_at"] is not None,
            "bought_at": row["bought_at"].isoformat() if row["bought_at"] else None,
            "source": row["source"],
            "payer": row["payer_email"],
            "sides": row["sides"],
        }
        for row in rows[:ADMIN_PAGE]
    ]
    return {"items": items, "more": len(rows) > ADMIN_PAGE}


def set_pair_bought(pair_id: int, bought: bool) -> list[dict]:
    """The operator opens the reading of the pair (a gift, a payment that got lost) or closes it.

    Gives the sides to write to when it was opened: [{user_id, partner_id}].
    """
    with pool.connection() as conn:
        if conn.execute("SELECT 1 FROM pairs WHERE id = %s", (pair_id,)).fetchone() is None:
            raise DomainError("missing", 404)
        if not bought:
            conn.execute("DELETE FROM purchases WHERE product = %s AND pair_id = %s", (PRODUCT, pair_id))
            return []
        won = conn.execute(
            """
            INSERT INTO purchases (user_id, product, pair_id, source) VALUES (NULL, %s, %s, 'admin')
            ON CONFLICT (product, pair_id) WHERE pair_id IS NOT NULL DO NOTHING
            RETURNING id
            """,
            (PRODUCT, pair_id),
        ).fetchone()
        if won is None:
            return []
        return conn.execute(
            "UPDATE partners SET news = 'gift', news_at = now() WHERE pair_id = %s RETURNING id AS partner_id, user_id",
            (pair_id,),
        ).fetchall()


def set_bought(user_id: int, partner_id: int, bought: bool) -> tuple[dict, list[dict]]:
    """The same from the person's card in the admin panel: the pair of this side, and whom to write to."""
    row = _own(user_id, partner_id)
    told = set_pair_bought(row["pair_id"], bought)
    return _one(user_id, partner_id), told
