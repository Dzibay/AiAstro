"""What the site's pages tell about their visitors: views, visits, arrivals by a campaign link, tours,
and what people do on a page: how far they scroll, how long it holds them, the buttons they press,
the offers they see, the game's steps.

A visitor is an anonymous id the browser keeps (localStorage); nothing here names a person until
they register or sign in, and then only their own account id is written next to it.
"""

import re

from app.db import pool

VISITOR = re.compile(r"^[a-z0-9-]{16,40}$")
NAME = re.compile(r"^[a-z0-9][a-z0-9:_-]{0,47}$")
TOKEN = re.compile(r"^[a-z0-9][a-z0-9_-]{1,39}$")
# What a page may report; signup, confirm, login, birth, name and password are written by the server
# itself (login's name — link | code | password). A goal is a landing's step:
# «lp-natal:calc» (the calculation shown), «lp-natal:cta» (on to the registration).
KINDS = {"view", "tour", "goal"}
# What a page gathers and sends in batches (track_many), each with the page it happened on:
# click — a button or a link («home:hero», «to:cabinet-sky»); scroll — the page reached 25/50/75/100 %;
# time — seconds of attention on the page; act — a step of the game («game:found», value — the planet's
# number) or of the way in («email:hero» — the address begun, «start:hero» — sent, «chart:seen»);
# offer — an offer seen («sky:chat»); pick — a plan chosen in «Небосвод» (value — months).
QUEUED = {"tour", "goal", "click", "scroll", "time", "act", "offer", "pick"}
BATCH = 40
DEVICES = {"phone", "desktop"}
# Silence after which the next view opens a new visit.
VISIT_GAP = "30 minutes"


def _host(source: str) -> str:
    """The referrer's host only, without www: the path may carry someone's search."""
    host = re.sub(r"^[a-z]+://", "", source.strip().lower()).split("/", 1)[0].split("?", 1)[0].split(":", 1)[0]
    host = host.removeprefix("www.")
    return host[:80] if re.fullmatch(r"[a-z0-9.-]+", host or "-") else ""


def track(
    visitor: str,
    kind: str,
    name: str,
    value: int | None = None,
    ref: str = "",
    source: str = "",
    device: str = "",
    user_id: int | None = None,
) -> None:
    """Writes one event; anything malformed is dropped quietly, the page never waits on it."""
    if not VISITOR.match(visitor) or kind not in KINDS or not NAME.match(name):
        return
    ref = ref.strip().lower()
    device = device if device in DEVICES else ""
    with pool.connection() as conn:
        ref_id = None
        if ref and TOKEN.match(ref):
            row = conn.execute("SELECT id FROM ref_links WHERE token = %s", (ref,)).fetchone()
            ref_id = row["id"] if row else None
        before = conn.execute(
            f"SELECT last_at < now() - interval '{VISIT_GAP}' AS quiet FROM visitors WHERE id = %s", (visitor,)
        ).fetchone()
        # A new visit: the first view ever, a view after half an hour of silence, an arrival by a link.
        opened = kind == "view" and (before is None or before["quiet"] or ref_id is not None)
        conn.execute(
            """
            INSERT INTO visitors (id, ref_id, user_id, source, landing, device)
            VALUES (%(v)s, %(ref)s, %(user)s, %(source)s, %(name)s, %(device)s)
            ON CONFLICT (id) DO UPDATE SET
                visits = visitors.visits + %(more)s,
                ref_id = COALESCE(visitors.ref_id, EXCLUDED.ref_id),
                user_id = COALESCE(EXCLUDED.user_id, visitors.user_id),
                device = CASE WHEN visitors.device = '' THEN EXCLUDED.device ELSE visitors.device END,
                last_at = now()
            """,
            {
                "v": visitor, "ref": ref_id, "user": user_id, "source": _host(source), "name": name, "device": device,
                "more": 1 if opened and before is not None else 0,
            },
        )
        if opened:
            conn.execute(
                "INSERT INTO events (visitor_id, user_id, ref_id, kind, name) VALUES (%s, %s, %s, 'visit', %s)",
                (visitor, user_id, ref_id, name),
            )
        if ref_id:
            conn.execute(
                "INSERT INTO events (visitor_id, user_id, ref_id, kind, name) VALUES (%s, %s, %s, 'ref', %s)",
                (visitor, user_id, ref_id, name),
            )
        conn.execute(
            "INSERT INTO events (visitor_id, user_id, kind, name, value) VALUES (%s, %s, %s, %s, %s)",
            (visitor, user_id, kind, name, value),
        )


def attach(user_id: int, visitor: str | None, signup: bool = False, place: str = "") -> None:
    """The browser and the account meet: at the registration the account takes the browser's
    campaign link (the first one, for good); at a sign-in only the browser learns whose it is.
    A registration that came with the date of birth is its first saving too (birth). `place` names
    where the address was given (hero, final, login…): the signup event carries it."""
    place = place if NAME.match(place or "") else ""
    if not visitor or not VISITOR.match(visitor):
        if signup:
            with pool.connection() as conn:
                conn.execute(
                    """
                    INSERT INTO events (user_id, kind, name)
                    SELECT id, k, CASE WHEN k = 'signup' THEN %s ELSE '' END FROM users, unnest(ARRAY['signup', 'birth']) AS k
                    WHERE id = %s AND (k = 'signup' OR birth_date IS NOT NULL)
                    """,
                    (place, user_id),
                )
        return
    with pool.connection() as conn:
        conn.execute(
            "INSERT INTO visitors (id, user_id) VALUES (%s, %s) ON CONFLICT (id) DO UPDATE SET user_id = EXCLUDED.user_id, last_at = now()",
            (visitor, user_id),
        )
        if signup:
            conn.execute(
                """
                UPDATE users u SET visitor_id = v.id, ref_id = COALESCE(u.ref_id, v.ref_id)
                FROM visitors v WHERE u.id = %s AND v.id = %s
                """,
                (user_id, visitor),
            )
            conn.execute(
                """
                INSERT INTO events (visitor_id, user_id, ref_id, kind, name)
                SELECT v.id, u.id, v.ref_id, k, CASE WHEN k = 'signup' THEN %s ELSE '' END
                FROM visitors v, users u, unnest(ARRAY['signup', 'birth']) AS k
                WHERE v.id = %s AND u.id = %s AND (k = 'signup' OR u.birth_date IS NOT NULL)
                """,
                (place, visitor, user_id),
            )


def track_many(visitor: str, items: list[tuple[str, str, int | None, str]], user_id: int | None = None) -> None:
    """Writes a page's gathered events: (kind, name, value, page). Only for a browser that has
    already shown a page; it keeps the visit open, as a view does."""
    if not VISITOR.match(visitor):
        return
    rows = [
        (visitor, user_id, kind, name, value, page if NAME.match(page) else "")
        for kind, name, value, page in items[:BATCH]
        if kind in QUEUED and NAME.match(name)
    ]
    if not rows:
        return
    with pool.connection() as conn:
        known = conn.execute(
            "UPDATE visitors SET last_at = now(), user_id = COALESCE(%s, user_id) WHERE id = %s RETURNING id",
            (user_id, visitor),
        ).fetchone()
        if known is None:
            return
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO events (visitor_id, user_id, kind, name, value, page) VALUES (%s, %s, %s, %s, %s, %s)",
                rows,
            )


def server_event(user_id: int, kind: str, name: str = "") -> None:
    """A step the server sees for itself (birth — the date of birth saved the first time), with the
    browser the account signed up on."""
    with pool.connection() as conn:
        conn.execute(
            """
            INSERT INTO events (visitor_id, user_id, kind, name)
            SELECT (SELECT v.id FROM visitors v WHERE v.id = u.visitor_id), u.id, %s, %s FROM users u WHERE u.id = %s
            """,
            (kind, name, user_id),
        )
