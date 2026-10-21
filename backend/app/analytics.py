"""The operator's analytics: visitors, the funnel from a first view to a payment, where people stop,
the tours, the sources — and the campaign links with everything that came by each.

Days are Moscow days, as on the overview. A funnel counts the people who registered in the period
and how far each of them has gone by now; a campaign gets its people's registrations and payments
for good (the first link a browser came by).
"""

import secrets

from psycopg.errors import UniqueViolation

from app.config import settings
from app.db import pool
from app.errors import DomainError
from app.partners import PRODUCT as PAIR
from app.track import TOKEN

PERIODS = (7, 30, 90, 365)
TZ = "Europe/Moscow"
SINCE = f"(((now() AT TIME ZONE '{TZ}')::date - (%(days)s - 1))::timestamp AT TIME ZONE '{TZ}')"
DAY = f"AT TIME ZONE '{TZ}')::date"


def _rows(conn, sql: str, params: dict) -> list[dict]:
    return [dict(row) for row in conn.execute(sql, params).fetchall()]


def _num(value) -> float | int:
    if value is None:
        return 0
    number = float(value)
    return int(number) if number.is_integer() else round(number, 2)


def _clean(rows: list[dict]) -> list[dict]:
    return [{key: (_num(value) if isinstance(value, (int, float)) or type(value).__name__ == "Decimal" else value) for key, value in row.items()} for row in rows]


# The steps of the funnel, for the people registered in the period: (key, SQL condition on u).
FUNNEL = (
    ("signup", "TRUE"),
    ("birth", "u.birth_date IS NOT NULL"),
    ("intro", "'tour:intro' = ANY(u.marks)"),
    ("section", "EXISTS (SELECT 1 FROM events e WHERE e.user_id = u.id AND e.kind = 'view' AND e.name IN ('cabinet-chart', 'cabinet-forecast', 'cabinet-pair', 'cabinet-chat', 'cabinet-sky'))"),
    ("pair", "EXISTS (SELECT 1 FROM partners p WHERE p.user_id = u.id)"),
    ("chat", "EXISTS (SELECT 1 FROM chat_messages c WHERE c.user_id = u.id AND c.role = 'user')"),
    ("checkout", "EXISTS (SELECT 1 FROM payments pa WHERE pa.user_id = u.id)"),
    ("paid", "EXISTS (SELECT 1 FROM payments pa WHERE pa.user_id = u.id AND pa.status = 'succeeded')"),
    ("sky", "EXISTS (SELECT 1 FROM payments pa WHERE pa.user_id = u.id AND pa.status = 'succeeded' AND pa.product LIKE 'sky%%')"),
    ("pair_bought", f"EXISTS (SELECT 1 FROM payments pa WHERE pa.user_id = u.id AND pa.status = 'succeeded' AND pa.product = '{PAIR}')"),
)


def _funnel(conn, where: str, params: dict) -> dict:
    columns = ", ".join(f"count(*) FILTER (WHERE {condition}) AS {key}" for key, condition in FUNNEL)
    row = conn.execute(f"SELECT {columns} FROM users u WHERE {where}", params).fetchone()
    return {key: int(row[key]) for key, _ in FUNNEL}


def analytics(days: int) -> dict:
    if days not in PERIODS:
        raise DomainError("state")
    p = {"days": days, "pair": PAIR}
    cohort = f"u.created_at >= {SINCE}"
    with pool.connection() as conn:
        totals = conn.execute(
            f"""
            WITH ev AS (SELECT * FROM events WHERE created_at >= {SINCE}),
            fresh AS (SELECT * FROM visitors WHERE first_at >= {SINCE})
            SELECT
                (SELECT count(DISTINCT visitor_id) FROM ev WHERE kind = 'view') AS visitors,
                (SELECT count(*) FROM fresh) AS new_visitors,
                (SELECT count(*) FROM ev WHERE kind = 'visit') AS visits,
                (SELECT count(*) FROM ev WHERE kind = 'view') AS views,
                (SELECT count(*) FROM fresh WHERE visits > 1) AS returning,
                (SELECT count(*) FROM fresh f WHERE (SELECT count(*) FROM events e WHERE e.visitor_id = f.id AND e.kind = 'view') = 1) AS bounced,
                (SELECT count(DISTINCT visitor_id) FROM ev WHERE kind = 'ref') AS ref_visitors,
                (SELECT count(*) FROM users u WHERE {cohort}) AS signups,
                (SELECT count(*) FROM fresh f JOIN users u ON u.visitor_id = f.id) AS fresh_signups,
                (SELECT count(*) FROM users) AS users,
                (SELECT count(*) FROM users WHERE sky_until > now()) AS sky_now,
                (SELECT count(*) FROM users WHERE sky_until <= now()) AS sky_lapsed,
                (SELECT count(*) FROM (SELECT user_id FROM payments WHERE status = 'succeeded' AND product LIKE 'sky%%' AND user_id IS NOT NULL
                    GROUP BY user_id HAVING count(*) > 1) r) AS sky_renewed,
                (SELECT COALESCE(sum(amount), 0) FROM payments WHERE status = 'succeeded' AND paid_at >= {SINCE}) AS revenue,
                (SELECT count(*) FROM payments WHERE status = 'succeeded' AND paid_at >= {SINCE}) AS payments,
                (SELECT count(DISTINCT COALESCE(user_id::text, email)) FROM payments WHERE status = 'succeeded' AND paid_at >= {SINCE}) AS paying,
                (SELECT count(*) FROM payments WHERE created_at >= {SINCE}) AS checkouts,
                (SELECT count(*) FROM payments WHERE created_at >= {SINCE} AND status <> 'succeeded') AS abandoned,
                (SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY extract(epoch FROM f.first - u.created_at) / 3600)
                    FROM (SELECT user_id, min(paid_at) AS first FROM payments WHERE status = 'succeeded' AND user_id IS NOT NULL GROUP BY user_id) f
                    JOIN users u ON u.id = f.user_id WHERE f.first >= {SINCE}) AS hours_to_pay
            """,
            p,
        ).fetchone()

        series = _rows(
            conn,
            f"""
            WITH span AS (
                SELECT generate_series((now() AT TIME ZONE '{TZ}')::date - (%(days)s - 1), (now() AT TIME ZONE '{TZ}')::date, '1 day')::date AS day
            ),
            ev AS (
                SELECT (created_at {DAY} AS day,
                       count(DISTINCT visitor_id) FILTER (WHERE kind = 'view') AS visitors,
                       count(*) FILTER (WHERE kind = 'visit') AS visits,
                       count(*) FILTER (WHERE kind = 'view') AS views
                FROM events WHERE created_at >= {SINCE} GROUP BY 1
            ),
            joined AS (SELECT (created_at {DAY} AS day, count(*) AS signups FROM users WHERE created_at >= {SINCE} GROUP BY 1),
            paid AS (
                SELECT (paid_at {DAY} AS day, count(*) AS payments, sum(amount) AS revenue
                FROM payments WHERE status = 'succeeded' AND paid_at >= {SINCE} GROUP BY 1
            )
            SELECT span.day, COALESCE(ev.visitors, 0) AS visitors, COALESCE(ev.visits, 0) AS visits, COALESCE(ev.views, 0) AS views,
                   COALESCE(joined.signups, 0) AS signups, COALESCE(paid.payments, 0) AS payments, COALESCE(paid.revenue, 0) AS revenue
            FROM span LEFT JOIN ev USING (day) LEFT JOIN joined USING (day) LEFT JOIN paid USING (day)
            ORDER BY span.day
            """,
            p,
        )

        funnel = _funnel(conn, cohort, p)

        # Where the people who have not paid stopped: the last page each of them saw.
        stuck = _rows(
            conn,
            f"""
            SELECT COALESCE(last.name, '') AS name, count(*) AS people
            FROM users u
            LEFT JOIN LATERAL (
                SELECT e.name FROM events e WHERE e.user_id = u.id AND e.kind = 'view' ORDER BY e.created_at DESC LIMIT 1
            ) last ON TRUE
            WHERE {cohort} AND NOT EXISTS (SELECT 1 FROM payments pa WHERE pa.user_id = u.id AND pa.status = 'succeeded')
            GROUP BY 1 ORDER BY people DESC LIMIT 12
            """,
            p,
        )

        pages = _rows(
            conn,
            f"""
            SELECT name, count(*) AS views, count(DISTINCT visitor_id) AS visitors, count(DISTINCT user_id) AS users
            FROM events WHERE kind = 'view' AND created_at >= {SINCE}
            GROUP BY name ORDER BY views DESC LIMIT 24
            """,
            p,
        )

        # The first page of each visitor; the landing pages' goals (track.py: `<page>:calc`, `<page>:cta`) beside it.
        landings = _rows(
            conn,
            f"""
            SELECT v.landing AS name, count(*) AS visitors,
                   count(*) FILTER (WHERE EXISTS (
                       SELECT 1 FROM events g WHERE g.visitor_id = v.id AND g.kind = 'goal' AND g.name = v.landing || ':calc'
                   )) AS calcs,
                   count(*) FILTER (WHERE EXISTS (
                       SELECT 1 FROM events g WHERE g.visitor_id = v.id AND g.kind = 'goal' AND g.name = v.landing || ':cta'
                   )) AS ctas,
                   count(u.id) AS signups,
                   count(u.id) FILTER (WHERE EXISTS (SELECT 1 FROM payments pa WHERE pa.user_id = u.id AND pa.status = 'succeeded')) AS paying
            FROM visitors v LEFT JOIN users u ON u.visitor_id = v.id
            WHERE v.first_at >= {SINCE} GROUP BY 1 ORDER BY visitors DESC LIMIT 16
            """,
            p,
        )

        sources = _rows(
            conn,
            f"""
            SELECT CASE WHEN v.ref_id IS NOT NULL THEN 'ref' WHEN v.source <> '' THEN 'site' ELSE 'direct' END AS kind,
                   COALESCE(NULLIF(r.name, ''), r.token, NULLIF(v.source, ''), '') AS label,
                   count(*) AS visitors, count(u.id) AS signups,
                   count(u.id) FILTER (WHERE EXISTS (SELECT 1 FROM payments pa WHERE pa.user_id = u.id AND pa.status = 'succeeded')) AS paying
            FROM visitors v
            LEFT JOIN ref_links r ON r.id = v.ref_id
            LEFT JOIN users u ON u.visitor_id = v.id
            WHERE v.first_at >= {SINCE}
            GROUP BY 1, 2 ORDER BY visitors DESC LIMIT 16
            """,
            p,
        )

        devices = _rows(
            conn,
            f"""
            SELECT COALESCE(NULLIF(v.device, ''), 'unknown') AS device, count(*) AS visitors, count(u.id) AS signups,
                   count(u.id) FILTER (WHERE EXISTS (SELECT 1 FROM payments pa WHERE pa.user_id = u.id AND pa.status = 'succeeded')) AS paying
            FROM visitors v LEFT JOIN users u ON u.visitor_id = v.id
            WHERE v.first_at >= {SINCE} GROUP BY 1 ORDER BY visitors DESC
            """,
            p,
        )

        # The tours in the period (shown, finished, skipped, the step where skipped) and, for all
        # time, how many accounts have each tour and newcomer step marked as seen.
        tours = _rows(
            conn,
            f"""
            SELECT split_part(name, ':', 1) AS tour,
                   count(*) FILTER (WHERE split_part(name, ':', 2) = 'start') AS started,
                   count(*) FILTER (WHERE split_part(name, ':', 2) = 'done') AS done,
                   count(*) FILTER (WHERE split_part(name, ':', 2) = 'skip') AS skipped,
                   avg(value) FILTER (WHERE split_part(name, ':', 2) = 'skip') AS skip_step,
                   max(value) FILTER (WHERE split_part(name, ':', 2) = 'done') AS steps
            FROM events WHERE kind = 'tour' AND created_at >= {SINCE}
            GROUP BY 1
            """,
            p,
        )
        marks = _rows(conn, "SELECT m AS mark, count(*) AS users FROM users, unnest(marks) m GROUP BY m", {})

        actions = conn.execute(
            f"""
            SELECT
                (SELECT count(*) FROM users u WHERE {cohort} AND u.birth_date IS NOT NULL) AS births,
                (SELECT count(*) FROM partners WHERE created_at >= {SINCE}) AS partners,
                (SELECT count(*) FROM partners WHERE created_at >= {SINCE} AND invite_token IS NOT NULL) AS invites,
                (SELECT count(*) FROM partners WHERE filled_at >= {SINCE} AND invite_token IS NOT NULL) AS answered,
                (SELECT count(*) FROM partners WHERE joined_at >= {SINCE}) AS joined,
                (SELECT count(*) FROM chat_messages WHERE role = 'user' AND created_at >= {SINCE}) AS questions,
                (SELECT count(DISTINCT user_id) FROM chat_messages WHERE role = 'user' AND created_at >= {SINCE}) AS askers,
                (SELECT count(*) FROM events WHERE kind = 'view' AND name = 'cabinet-chart' AND created_at >= {SINCE}) AS chart_views,
                (SELECT count(*) FROM events WHERE kind = 'view' AND name = 'cabinet-forecast' AND created_at >= {SINCE}) AS forecast_views,
                (SELECT count(*) FROM purchases WHERE product = %(pair)s AND source = 'admin' AND created_at >= {SINCE}) AS gifts
            """,
            p,
        ).fetchone()

        products = _rows(
            conn,
            f"""
            SELECT product, count(*) FILTER (WHERE status = 'succeeded') AS paid, count(*) AS started,
                   COALESCE(sum(amount) FILTER (WHERE status = 'succeeded'), 0) AS revenue
            FROM payments WHERE created_at >= {SINCE}
            GROUP BY product ORDER BY revenue DESC
            """,
            p,
        )

    return {
        "days": days,
        "totals": {key: _num(value) for key, value in totals.items()},
        "series": [{**row, "day": row["day"].isoformat(), "revenue": int(row["revenue"])} for row in _clean(series)],
        "funnel": funnel,
        "stuck": _clean(stuck),
        "pages": _clean(pages),
        "landings": _clean(landings),
        "sources": _clean(sources),
        "devices": _clean(devices),
        "tours": _clean(tours),
        "marks": _clean(marks),
        "actions": {key: int(value) for key, value in actions.items()},
        "products": _clean(products),
    }


# ---- Campaign links ----

LINK_PERIODS = (0, *PERIODS)


def _since(days: int) -> str:
    return SINCE if days else "'-infinity'::timestamptz"


def _link_url(token: str) -> str:
    return f"{settings.public_base_url.rstrip('/')}/?ref={token}"


def list_links(days: int) -> dict:
    if days not in LINK_PERIODS:
        raise DomainError("state")
    since = _since(days)
    with pool.connection() as conn:
        rows = _rows(
            conn,
            f"""
            SELECT r.id, r.token, r.name, r.note, r.created_at,
                   COALESCE(e.clicks, 0) AS clicks, COALESCE(e.visitors, 0) AS visitors, e.last_click,
                   COALESCE(u.signups, 0) AS signups, COALESCE(u.birth, 0) AS birth, COALESCE(u.sky_now, 0) AS sky_now,
                   COALESCE(pa.paying, 0) AS paying, COALESCE(pa.payments, 0) AS payments, COALESCE(pa.sky, 0) AS sky,
                   COALESCE(pa.pairs, 0) AS pairs, COALESCE(pa.revenue, 0) AS revenue
            FROM ref_links r
            LEFT JOIN LATERAL (
                SELECT count(*) AS clicks, count(DISTINCT visitor_id) AS visitors, max(created_at) AS last_click
                FROM events WHERE ref_id = r.id AND kind = 'ref' AND created_at >= {since}
            ) e ON TRUE
            LEFT JOIN LATERAL (
                SELECT count(*) AS signups, count(*) FILTER (WHERE birth_date IS NOT NULL) AS birth,
                       count(*) FILTER (WHERE sky_until > now()) AS sky_now
                FROM users WHERE ref_id = r.id AND created_at >= {since}
            ) u ON TRUE
            LEFT JOIN LATERAL (
                SELECT count(DISTINCT COALESCE(user_id::text, email)) AS paying, count(*) AS payments,
                       count(*) FILTER (WHERE product LIKE 'sky%%') AS sky, count(*) FILTER (WHERE product = %(pair)s) AS pairs,
                       sum(amount) AS revenue
                FROM payments WHERE ref_id = r.id AND status = 'succeeded' AND paid_at >= {since}
            ) pa ON TRUE
            ORDER BY r.created_at DESC, r.id DESC
            """,
            {"days": days, "pair": PAIR},
        )
    items = []
    for row in _clean(rows):
        row["url"] = _link_url(row["token"])
        row["created_at"] = row["created_at"].isoformat()
        row["last_click"] = row["last_click"].isoformat() if row["last_click"] else None
        items.append(row)
    totals = {key: sum(item[key] for item in items) for key in ("clicks", "visitors", "signups", "birth", "paying", "payments", "sky", "pairs", "revenue")}
    return {"days": days, "items": items, "totals": totals, "base": f"{settings.public_base_url.rstrip('/')}/?ref="}


def link_detail(link_id: int, days: int) -> dict:
    if days not in LINK_PERIODS:
        raise DomainError("state")
    since = _since(days)
    with pool.connection() as conn:
        link = conn.execute("SELECT id, token, name, created_at FROM ref_links WHERE id = %s", (link_id,)).fetchone()
        if link is None:
            raise DomainError("missing", 404)
        # All time: from the link's first day, a year at most.
        span = days or min(365, max(1, conn.execute(
            f"SELECT (now() AT TIME ZONE '{TZ}')::date - (%s {DAY} + 1 AS n", (link["created_at"],)
        ).fetchone()["n"]))
        p = {"id": link_id, "days": span, "pair": PAIR}
        series = _rows(
            conn,
            f"""
            WITH span AS (
                SELECT generate_series((now() AT TIME ZONE '{TZ}')::date - (%(days)s - 1), (now() AT TIME ZONE '{TZ}')::date, '1 day')::date AS day
            ),
            clicks AS (SELECT (created_at {DAY} AS day, count(*) AS clicks FROM events WHERE ref_id = %(id)s AND kind = 'ref' GROUP BY 1),
            joined AS (SELECT (created_at {DAY} AS day, count(*) AS signups FROM users WHERE ref_id = %(id)s GROUP BY 1),
            paid AS (
                SELECT (paid_at {DAY} AS day, sum(amount) AS revenue, count(*) AS payments
                FROM payments WHERE ref_id = %(id)s AND status = 'succeeded' GROUP BY 1
            )
            SELECT span.day, COALESCE(clicks.clicks, 0) AS clicks, COALESCE(joined.signups, 0) AS signups,
                   COALESCE(paid.revenue, 0) AS revenue, COALESCE(paid.payments, 0) AS payments
            FROM span LEFT JOIN clicks USING (day) LEFT JOIN joined USING (day) LEFT JOIN paid USING (day)
            ORDER BY span.day
            """,
            p,
        )
        q = {"id": link_id, "days": days, "pair": PAIR}
        funnel = _funnel(conn, f"u.ref_id = %(id)s AND u.created_at >= {since}", q)
        clicks = conn.execute(
            f"SELECT count(*) AS clicks, count(DISTINCT visitor_id) AS visitors FROM events WHERE ref_id = %(id)s AND kind = 'ref' AND created_at >= {since}",
            q,
        ).fetchone()
        landings = _rows(
            conn,
            f"SELECT name, count(*) AS clicks FROM events WHERE ref_id = %(id)s AND kind = 'ref' AND created_at >= {since} GROUP BY 1 ORDER BY clicks DESC LIMIT 8",
            q,
        )
        devices = _rows(
            conn,
            f"""
            SELECT COALESCE(NULLIF(v.device, ''), 'unknown') AS device, count(DISTINCT v.id) AS visitors
            FROM events e JOIN visitors v ON v.id = e.visitor_id
            WHERE e.ref_id = %(id)s AND e.kind = 'ref' AND e.created_at >= {since} GROUP BY 1 ORDER BY visitors DESC
            """,
            q,
        )
        products = _rows(
            conn,
            f"""
            SELECT product, count(*) AS payments, sum(amount) AS revenue FROM payments
            WHERE ref_id = %(id)s AND status = 'succeeded' AND paid_at >= {since} GROUP BY 1 ORDER BY revenue DESC
            """,
            q,
        )
        people = _rows(
            conn,
            f"""
            SELECT u.id, u.email, u.name, u.created_at, u.birth_date IS NOT NULL AS birth, u.sky_until > now() AS sky,
                   COALESCE((SELECT sum(amount) FROM payments pa WHERE pa.user_id = u.id AND pa.status = 'succeeded'), 0) AS paid
            FROM users u WHERE u.ref_id = %(id)s AND u.created_at >= {since}
            ORDER BY u.created_at DESC LIMIT 30
            """,
            q,
        )
        hours = conn.execute(
            f"""
            SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY extract(epoch FROM f.first - u.created_at) / 3600) AS hours
            FROM (SELECT user_id, min(paid_at) AS first FROM payments WHERE ref_id = %(id)s AND status = 'succeeded' GROUP BY user_id) f
            JOIN users u ON u.id = f.user_id WHERE u.created_at >= {since}
            """,
            q,
        ).fetchone()["hours"]
    return {
        "id": link_id,
        "days": days,
        "series": [{**row, "day": row["day"].isoformat(), "revenue": int(row["revenue"])} for row in _clean(series)],
        "funnel": funnel,
        "clicks": int(clicks["clicks"]),
        "visitors": int(clicks["visitors"]),
        "landings": _clean(landings),
        "devices": _clean(devices),
        "products": _clean(products),
        "people": [{**row, "created_at": row["created_at"].isoformat(), "sky": bool(row["sky"])} for row in _clean(people)],
        "hours_to_pay": _num(hours),
    }


def create_link(token: str, name: str, note: str) -> dict:
    token = token.strip().lower()
    if token and not TOKEN.match(token):
        raise DomainError("token")
    name = " ".join(name.split())[:80]
    note = note.strip()[:300]
    for _ in range(5):
        value = token or secrets.token_hex(4)
        try:
            with pool.connection() as conn:
                row = conn.execute(
                    "INSERT INTO ref_links (token, name, note) VALUES (%s, %s, %s) RETURNING id",
                    (value, name, note),
                ).fetchone()
            return {"id": row["id"], "token": value, "url": _link_url(value)}
        except UniqueViolation as exc:
            if token:
                raise DomainError("token_taken", 409) from exc
    raise DomainError("token_taken", 409)


def update_link(link_id: int, name: str, note: str) -> dict:
    with pool.connection() as conn:
        row = conn.execute(
            "UPDATE ref_links SET name = %s, note = %s WHERE id = %s RETURNING id",
            (" ".join(name.split())[:80], note.strip()[:300], link_id),
        ).fetchone()
    if row is None:
        raise DomainError("missing", 404)
    return {"ok": True}


def delete_link(link_id: int) -> dict:
    with pool.connection() as conn:
        row = conn.execute("DELETE FROM ref_links WHERE id = %s RETURNING id", (link_id,)).fetchone()
    if row is None:
        raise DomainError("missing", 404)
    return {"ok": True}
