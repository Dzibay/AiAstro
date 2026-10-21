"""What the site's pages tell about their visitors: views, visits, arrivals by a campaign link, tours.

A visitor is an anonymous id the browser keeps (localStorage); nothing here names a person until
they register or sign in, and then only their own account id is written next to it.
"""

import re

from app.db import pool

VISITOR = re.compile(r"^[a-z0-9-]{16,40}$")
NAME = re.compile(r"^[a-z0-9][a-z0-9:_-]{0,47}$")
TOKEN = re.compile(r"^[a-z0-9][a-z0-9_-]{1,39}$")
# What a page may report; signup is written by the server itself. A goal is a landing's step:
# «lp-natal:calc» (the calculation shown), «lp-natal:cta» (on to the registration).
KINDS = {"view", "tour", "goal"}
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


def attach(user_id: int, visitor: str | None, signup: bool = False) -> None:
    """The browser and the account meet: at the registration the account takes the browser's
    campaign link (the first one, for good); at a sign-in only the browser learns whose it is."""
    if not visitor or not VISITOR.match(visitor):
        if signup:
            with pool.connection() as conn:
                conn.execute("INSERT INTO events (user_id, kind) VALUES (%s, 'signup')", (user_id,))
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
                INSERT INTO events (visitor_id, user_id, ref_id, kind)
                SELECT id, %s, ref_id, 'signup' FROM visitors WHERE id = %s
                """,
                (user_id, visitor),
            )
