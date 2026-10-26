"""The pulse for the operator: one way from a first visit to a payment and where it loses people.

Everything here follows the browsers that first came in a period (a cohort) and how far each has
gone. Compared with the period before, both are taken at the same age: the earlier period has the
same length and ends the same time ago, and its steps count only up to that moment — so a day that
has not ended yet never looks like a fall. A later step stands in for an earlier one that went
unrecorded (a payer has seen the chart), so no step outgrows the one before.

The way begins with the address: the person starts typing it (or sends it) in one of the start
places, the letter leaves (the account is made), its link or code opens the cabinet, the birth data
follow there, then the chart. Besides the way: the same steps week by week, by source, first page
and device, by start place, how people sign in, the cabinet's actions beside the payments, the
money each source brings, and one person's way for their card.
"""

from math import sqrt

from app.analytics import PERIODS, SINCE, TZ, _clean, _num, _rows
from app.db import pool
from app.errors import DomainError
from app.partners import PRODUCT as PAIR

# The steps in their order: the first view, the address begun in a start form, the letter asked
# for (the account), its link or code opened (the cabinet), the birth data there, the chart seen,
# a payment started, a payment made.
STEPS = ("visit", "start", "signup", "confirm", "birth", "chart", "checkout", "paid")
# The recorded moment behind each step after the visit, in the same order.
RAW = ("started", "signed", "confirmed", "birthed", "charted", "checkout", "paid")

# The first saving of the birth data: its event, or the account's making when they came with it.
BIRTH_AT = "COALESCE((SELECT min(b.created_at) FROM events b WHERE b.user_id = {u} AND b.kind = 'birth'), {signed})"
# The chart seen: the act chart:seen (the chart drawn), before it the chart page's view — after the birth data.
CHART_AT = (
    "(SELECT min(e.created_at) FROM events e WHERE e.user_id = {u}"
    " AND ((e.kind = 'act' AND e.name = 'chart:seen') OR (e.kind = 'view' AND e.name = 'cabinet-chart'))"
    " AND e.created_at >= {birth})"
)

# The first page a browser opened: the home page, the landing pages for search and ads, the rest.
ENTRIES = {
    "": "TRUE",
    "home": "v.landing = 'home'",
    "landings": "v.landing LIKE 'lp-%%'",
    "other": "v.landing <> 'home' AND v.landing NOT LIKE 'lp-%%'",
}
DEVICES = {"": "TRUE", "phone": "v.device = 'phone'", "desktop": "v.device = 'desktop'"}

# The period and the one before it, of the same length and age.
NOW = (SINCE, "now()")
BEFORE = (f"({SINCE} - make_interval(days => %(days)s))", "(now() - make_interval(days => %(days)s))")


def _channel(ref: str) -> str:
    """Where a browser came from: its campaign link, the site that sent it, or nowhere (typed, a bookmark)."""
    return f"CASE WHEN {ref} IS NOT NULL THEN 'ref:' || {ref} WHEN COALESCE(v.source, '') <> '' THEN 'site:' || v.source ELSE 'direct' END"


def _cohort(start: str, end: str, where: str = "TRUE") -> str:
    """CTEs c, f, g, s: the browsers first seen in [start, end), each with the moment it reached every
    step (only before `end`), and its device, first page and channel."""
    cut = {raw: f"(CASE WHEN {raw} < {end} THEN {raw} END)" for raw in RAW}
    reach = ", ".join(f"LEAST({', '.join(cut[raw] for raw in RAW[i:])}) AS {key}_at" for i, key in enumerate(STEPS[1:]))
    birth = BIRTH_AT.format(u="c.user_id", signed="c.signed")
    chart = CHART_AT.format(u="f.user_id", birth="f.birth_first")
    return f"""
    c AS (
        SELECT v.id, v.first_at, COALESCE(NULLIF(v.device, ''), 'unknown') AS device,
               COALESCE(NULLIF(v.landing, ''), 'unknown') AS landing, {_channel('v.ref_id')} AS channel,
               u.id AS user_id, u.created_at AS signed, u.email_confirmed_at AS confirmed, u.birth_date
        FROM visitors v
        LEFT JOIN LATERAL (
            SELECT u.id, u.created_at, u.email_confirmed_at, u.birth_date FROM users u
            WHERE u.visitor_id = v.id ORDER BY u.created_at LIMIT 1
        ) u ON TRUE
        WHERE v.first_at >= {start} AND v.first_at < {end} AND {where}
    ),
    f AS MATERIALIZED (
        SELECT c.*,
            (SELECT min(e.created_at) FROM events e WHERE e.visitor_id = c.id AND e.kind = 'act'
                AND (e.name LIKE 'email:%%' OR e.name LIKE 'start:%%')) AS started,
            CASE WHEN c.birth_date IS NOT NULL THEN {birth} END AS birth_first,
            (SELECT min(pa.created_at) FROM payments pa WHERE pa.user_id = c.user_id) AS checkout,
            (SELECT min(pa.paid_at) FROM payments pa WHERE pa.user_id = c.user_id AND pa.status = 'succeeded') AS paid
        FROM c
    ),
    g AS (
        -- Birth data typed on the home page come with the account: in the cabinet they count once it is open.
        SELECT f.*, CASE WHEN f.confirmed IS NOT NULL AND f.birth_first IS NOT NULL THEN GREATEST(f.birth_first, f.confirmed) END AS birthed,
               CASE WHEN f.birth_first IS NOT NULL THEN {chart} END AS charted
        FROM f
    ),
    s AS (SELECT g.*, g.first_at AS visit_at, {reach} FROM g)
    """


COUNTS = ", ".join(f"count({key}_at) AS {key}" for key in STEPS)


def _steps(row) -> dict:
    return {key: int(row[key]) for key in STEPS}


def _open(conn) -> None:
    """These queries look costly to the planner (a lookup per browser) but run in milliseconds:
    compiling them (JIT) would take longer than running them."""
    conn.execute("SET LOCAL jit = off")


def _check(days: int, entry: str = "", device: str = "") -> None:
    if days not in PERIODS or entry not in ENTRIES or device not in DEVICES:
        raise DomainError("state")


# ---- The way, now and before ----

# What a person can do in the cabinet, each with its first moment (for those whose cabinet opened).
ACTIONS = (
    ("birth", "s.birth_first"),
    ("intro", "(SELECT min(e.created_at) FROM events e WHERE e.user_id = s.user_id AND e.kind = 'tour' AND e.name = 'intro:done')"),
    ("chart", "s.charted"),
    ("name", "(SELECT min(e.created_at) FROM events e WHERE e.user_id = s.user_id AND e.kind = 'name')"),
    ("password", "(SELECT min(e.created_at) FROM events e WHERE e.user_id = s.user_id AND e.kind = 'password')"),
    ("game", "(SELECT min(e.created_at) FROM events e WHERE e.user_id = s.user_id AND e.kind = 'act' AND e.name = 'game:land')"),
    ("forecast", "(SELECT min(e.created_at) FROM events e WHERE e.user_id = s.user_id AND e.kind = 'view' AND e.name = 'cabinet-forecast')"),
    ("pair", "(SELECT min(p.created_at) FROM partners p WHERE p.user_id = s.user_id)"),
    ("chat", "(SELECT min(m.created_at) FROM chat_messages m WHERE m.user_id = s.user_id AND m.role = 'user')"),
    ("sky", "(SELECT min(e.created_at) FROM events e WHERE e.user_id = s.user_id AND e.kind = 'view' AND e.name = 'cabinet-sky')"),
    ("offer", "(SELECT min(e.created_at) FROM events e WHERE e.user_id = s.user_id AND e.kind = 'offer')"),
)


def way(days: int, entry: str = "", device: str = "") -> dict:
    """The browsers that first came in the period (by first page and device): how many reached each
    step, the same for the period before, the median hours from the first visit to each step; for
    those whose cabinet opened, who did each of its actions before paying (or by now) and how many of
    them paid, beside those who did not; each start place with its starts, letters, opened cabinets
    and payments; and how people signed in during the period (link, code, password)."""
    _check(days, entry, device)
    where = f"{ENTRIES[entry]} AND {DEVICES[device]}"
    p = {"days": days}
    hours = ", ".join(
        f"percentile_cont(0.5) WITHIN GROUP (ORDER BY GREATEST(0, extract(epoch FROM {key}_at - first_at)) / 3600)"
        f" FILTER (WHERE {key}_at IS NOT NULL) AS h_{key}"
        for key in STEPS[1:]
    )
    moments = ", ".join(f"{sql} AS {key}" for key, sql in ACTIONS)
    # An action counts if it came before the first payment, or at any time for those who have not paid.
    did = ", ".join(
        f"count(*) FILTER (WHERE {key} < COALESCE(paid_at, now())) AS {key}, "
        f"count(*) FILTER (WHERE {key} < paid_at) AS {key}_paid"
        for key, _ in ACTIONS
    )
    with pool.connection() as conn:
        _open(conn)
        now = conn.execute(f"WITH {_cohort(*NOW, where)} SELECT {COUNTS}, {hours} FROM s", p).fetchone()
        before = conn.execute(f"WITH {_cohort(*BEFORE, where)} SELECT {COUNTS} FROM s", p).fetchone()
        acts = conn.execute(
            f"""
            WITH {_cohort(*NOW, where)},
            a AS (SELECT s.paid_at, {moments} FROM s WHERE s.confirm_at IS NOT NULL)
            SELECT count(*) AS people, count(paid_at) AS paid, {did} FROM a
            """,
            p,
        ).fetchone()
        # A browser may begin in one place and send from another: it counts in both.
        places = conn.execute(
            f"""
            WITH {_cohort(*NOW, where)},
            st AS (
                SELECT split_part(e.name, ':', 2) AS place, count(DISTINCT s.id) AS starts
                FROM s JOIN events e ON e.visitor_id = s.id AND e.kind = 'act' AND (e.name LIKE 'email:%%' OR e.name LIKE 'start:%%')
                GROUP BY 1
            ),
            sg AS (
                SELECT COALESCE(NULLIF((SELECT e.name FROM events e WHERE e.user_id = s.user_id AND e.kind = 'signup'
                                        ORDER BY e.created_at LIMIT 1), ''), 'unknown') AS place,
                       count(*) AS signups, count(s.confirm_at) AS confirms, count(s.birth_at) AS births, count(s.paid_at) AS paid
                FROM s WHERE s.signup_at IS NOT NULL GROUP BY 1
            )
            SELECT place, COALESCE(starts, 0) AS starts, COALESCE(signups, 0) AS signups, COALESCE(confirms, 0) AS confirms,
                   COALESCE(births, 0) AS births, COALESCE(paid, 0) AS paid
            FROM st FULL JOIN sg USING (place)
            ORDER BY starts DESC, signups DESC
            """,
            p,
        ).fetchall()
        logins = conn.execute(
            f"""
            SELECT name AS way, count(*) AS times, count(DISTINCT user_id) AS people
            FROM events WHERE kind = 'login' AND created_at >= {SINCE} GROUP BY 1 ORDER BY 2 DESC
            """,
            p,
        ).fetchall()
    return {
        "days": days,
        "entry": entry,
        "device": device,
        "now": _steps(now),
        "before": _steps(before),
        "hours": {key: (None if now[f"h_{key}"] is None else round(float(now[f"h_{key}"]), 2)) for key in STEPS[1:]},
        "cabinet": {
            "people": int(acts["people"]),
            "paid": int(acts["paid"]),
            "actions": [{"key": key, "did": int(acts[key]), "paid": int(acts[f"{key}_paid"])} for key, _ in ACTIONS],
        },
        "places": [{key: (row[key] if key == "place" else int(row[key])) for key in row} for row in places],
        "logins": [{"way": row["way"] or "unknown", "times": int(row["times"]), "people": int(row["people"])} for row in logins],
    }


# ---- By source, first page, device ----

SEGMENTS = ("channel", "landing", "device")
TOP = 12


def _labels(conn, keys) -> dict:
    """The campaign links' names for the channel keys 'ref:<id>'; sites keep their host."""
    ids = [int(key[4:]) for key in keys if key.startswith("ref:") and key[4:].isdigit()]
    names = {}
    if ids:
        for row in conn.execute("SELECT id, name, token FROM ref_links WHERE id = ANY(%s)", (ids,)).fetchall():
            names[f"ref:{row['id']}"] = row["name"] or row["token"]
    return {key: names.get(key, "удалённая ссылка") if key.startswith("ref:") else key.removeprefix("site:") for key in keys}


def _grouped(conn, by: str, start: str, end: str, p: dict) -> list[dict]:
    rows = conn.execute(f"WITH {_cohort(start, end)} SELECT {by} AS key, {COUNTS} FROM s GROUP BY 1", p).fetchall()
    return [{"key": row["key"], **_steps(row)} for row in rows]


def segments(days: int, by: str) -> dict:
    """The way of the period's browsers split by channel (link or site), first page or device: the
    biggest twelve, the rest together, and the whole for the comparison."""
    _check(days)
    if by not in SEGMENTS:
        raise DomainError("state")
    p = {"days": days}
    with pool.connection() as conn:
        _open(conn)
        rows = sorted(_grouped(conn, by, *NOW, p), key=lambda row: -row["visit"])
        labels = _labels(conn, [row["key"] for row in rows]) if by == "channel" else {}
    top, rest = rows[:TOP], rows[TOP:]
    if rest:
        top.append({"key": "", **{key: sum(row[key] for row in rest) for key in STEPS}, "others": len(rest)})
    total = {key: sum(row[key] for row in rows) for key in STEPS}
    for row in top:
        row["label"] = labels.get(row["key"], row["key"])
    return {"days": days, "by": by, "items": top, "total": total}


# ---- Week by week ----

WEEKS = (8, 12, 26)
HORIZON = 7  # days after the first visit a step has to happen in, so old and new weeks compare


def weeks(count: int = 12, device: str = "") -> dict:
    """The browsers of each Moscow week (by their first visit) and how many reached each step within
    a week of coming. A week whose last browsers have not had their week yet is marked unfinished."""
    if count not in WEEKS or device not in DEVICES:
        raise DomainError("state")
    start = f"((date_trunc('week', now() AT TIME ZONE '{TZ}') - interval '{count - 1} weeks') AT TIME ZONE '{TZ}')"
    within = ", ".join(f"count(*) FILTER (WHERE {key}_at < first_at + interval '{HORIZON} days') AS {key}" for key in STEPS)
    with pool.connection() as conn:
        _open(conn)
        rows = conn.execute(
            f"""
            WITH {_cohort(start, "now()", DEVICES[device])},
            w AS (SELECT date_trunc('week', first_at AT TIME ZONE '{TZ}')::date AS week, {within} FROM s GROUP BY 1),
            span AS (
                SELECT generate_series(date_trunc('week', now() AT TIME ZONE '{TZ}')::date - {(count - 1) * 7},
                                       date_trunc('week', now() AT TIME ZONE '{TZ}')::date, '7 days')::date AS week
            )
            SELECT span.week, span.week + {7 + HORIZON} <= (now() AT TIME ZONE '{TZ}')::date AS done,
                   {", ".join(f"COALESCE(w.{key}, 0) AS {key}" for key in STEPS)}
            FROM span LEFT JOIN w USING (week) ORDER BY span.week
            """,
            {},
        ).fetchall()
    return {
        "weeks": count,
        "device": device,
        "horizon": HORIZON,
        "items": [{"week": row["week"].isoformat(), "done": bool(row["done"]), **_steps(row)} for row in rows],
    }


# ---- Money by source ----

MONEY_PERIODS = (0, *PERIODS)


def money(days: int) -> dict:
    """For each channel: the new browsers of the period, the accounts made in it, the payments made
    in it (each by the channel the payer first came by), and for the campaign links what was spent on
    them and all they have brought, for the payback. days = 0 — all time."""
    if days not in MONEY_PERIODS:
        raise DomainError("state")
    since = SINCE if days else "'-infinity'::timestamptz"
    p = {"days": days}
    with pool.connection() as conn:
        _open(conn)
        rows = _rows(
            conn,
            f"""
            WITH vis AS (
                SELECT {_channel('v.ref_id')} AS key, count(*) AS visitors FROM visitors v WHERE v.first_at >= {since} GROUP BY 1
            ),
            reg AS (
                SELECT {_channel('COALESCE(u.ref_id, v.ref_id)')} AS key, count(*) AS signups
                FROM users u LEFT JOIN visitors v ON v.id = u.visitor_id WHERE u.created_at >= {since} GROUP BY 1
            ),
            pay AS (
                SELECT {_channel('COALESCE(pa.ref_id, u.ref_id, v.ref_id)')} AS key,
                       count(DISTINCT COALESCE(pa.user_id::text, pa.email)) AS payers, count(*) AS payments, sum(pa.amount) AS revenue
                FROM payments pa LEFT JOIN users u ON u.id = pa.user_id LEFT JOIN visitors v ON v.id = u.visitor_id
                WHERE pa.status = 'succeeded' AND pa.paid_at >= {since} GROUP BY 1
            )
            SELECT key, COALESCE(visitors, 0) AS visitors, COALESCE(signups, 0) AS signups, COALESCE(payers, 0) AS payers,
                   COALESCE(payments, 0) AS payments, COALESCE(revenue, 0) AS revenue
            FROM vis FULL JOIN reg USING (key) FULL JOIN pay USING (key)
            """,
            p,
        )
        links = {
            f"ref:{row['id']}": row
            for row in conn.execute(
                """
                SELECT r.id, r.spend, COALESCE((SELECT sum(amount) FROM payments WHERE ref_id = r.id AND status = 'succeeded'), 0) AS revenue_all
                FROM ref_links r
                """
            ).fetchall()
        }
        # A link with money spent stays in the table even in a quiet period: its payback is for all time.
        seen = {row["key"] for row in rows}
        rows += [
            {"key": key, "visitors": 0, "signups": 0, "payers": 0, "payments": 0, "revenue": 0}
            for key, link in links.items() if link["spend"] and key not in seen
        ]
        labels = _labels(conn, [row["key"] for row in rows])
    items = []
    for row in _clean(rows):
        key = row["key"]
        link = links.get(key)
        items.append({
            **row,
            "kind": key.split(":", 1)[0],
            "label": labels.get(key, key),
            "link_id": int(key[4:]) if link else None,
            "spend": _num(link["spend"]) if link else None,
            "revenue_all": _num(link["revenue_all"]) if link else None,
        })
    items.sort(key=lambda item: (-item["revenue"], -item["visitors"]))
    totals = {key: sum(item[key] for item in items) for key in ("visitors", "signups", "payers", "payments", "revenue")}
    totals["spend"] = sum(item["spend"] or 0 for item in items)
    return {"days": days, "items": items, "totals": totals}


# ---- The pulse: the period against the one before, and what stands out ----

MIN_BASE = 20  # fewer people than this at a step's start say nothing about its share
SHIFT = 0.03  # a change of a step's share against the period before worth a line
GAP = 0.10  # how far a segment trails the rest at a step to be worth a line


def _rate(steps: dict, i: int) -> float | None:
    base = steps[STEPS[i - 1]]
    return steps[STEPS[i]] / base if base else None


def _insights(now: dict, before: dict, groups: dict) -> list[dict]:
    """What stands out, as facts for the page to word: a step that moved against the period before,
    the narrowest step, a device or a segment that trails the rest at some step."""
    found = []
    for i in range(1, len(STEPS)):
        if now[STEPS[i - 1]] < MIN_BASE or before[STEPS[i - 1]] < MIN_BASE:
            continue
        rate, was = _rate(now, i), _rate(before, i)
        if abs(rate - was) >= SHIFT:
            found.append({"kind": "shift", "tone": "bad" if rate < was else "good", "step": STEPS[i], "rate": rate, "other": was, "weight": abs(rate - was)})

    narrow = [(i, _rate(now, i)) for i in range(2, len(STEPS)) if now[STEPS[i - 1]] >= MIN_BASE]
    if narrow:
        i, rate = min(narrow, key=lambda pair: pair[1])
        found.append({"kind": "narrow", "tone": "info", "step": STEPS[i], "rate": rate, "lost": now[STEPS[i - 1]] - now[STEPS[i]], "weight": 0})

    phone = next((row for row in groups["device"] if row["key"] == "phone"), None)
    desktop = next((row for row in groups["device"] if row["key"] == "desktop"), None)
    if phone and desktop:
        best = None
        for i in range(1, len(STEPS)):
            if phone[STEPS[i - 1]] < MIN_BASE or desktop[STEPS[i - 1]] < MIN_BASE:
                continue
            a, b = _rate(phone, i), _rate(desktop, i)
            if abs(a - b) >= GAP and (best is None or abs(a - b) > best["weight"]):
                worse, other = ("phone", "desktop") if a < b else ("desktop", "phone")
                best = {"kind": "device", "tone": "bad", "step": STEPS[i], "segment": worse, "against": other,
                        "rate": min(a, b), "other": max(a, b), "weight": abs(a - b)}
        if best:
            found.append(best)

    trailing = []
    for by in ("channel", "landing"):
        for row in groups[by]:
            worst = None
            for i in range(1, len(STEPS)):
                base, rest_base = row[STEPS[i - 1]], now[STEPS[i - 1]] - row[STEPS[i - 1]]
                if base < MIN_BASE or rest_base < MIN_BASE:
                    continue
                rate, rest = _rate(row, i), (now[STEPS[i]] - row[STEPS[i]]) / rest_base
                # The weight leans on the size too: a big source trailing a little beats a tiny one trailing a lot.
                weight = (rest - rate) * sqrt(base / MIN_BASE)
                if rest - rate >= GAP and (worst is None or weight > worst["weight"]):
                    worst = {"kind": "segment", "tone": "bad", "by": by, "segment": row["key"], "label": row.get("label", row["key"]),
                             "step": STEPS[i], "rate": rate, "other": rest, "weight": weight}
            if worst:
                trailing.append(worst)
    found += sorted(trailing, key=lambda item: -item["weight"])[:3]

    order = {"bad": 0, "info": 1, "good": 2}
    found.sort(key=lambda item: (order[item["tone"]], -item["weight"]))
    for item in found:
        for key in ("rate", "other"):
            if key in item:
                item[key] = round(item[key], 4)
        item["weight"] = round(item["weight"], 4)
    return found[:8]


def pulse(days: int) -> dict:
    """The operator's first screen: the period's figures against the same span before, the way with
    its steps then and now, and what stands out."""
    _check(days)
    p = {"days": days}
    start, end = BEFORE
    with pool.connection() as conn:
        _open(conn)
        figures = conn.execute(
            f"""
            SELECT
                (SELECT count(*) FROM visitors WHERE first_at >= {SINCE}) AS visitors,
                (SELECT count(*) FROM visitors WHERE first_at >= {start} AND first_at < {end}) AS visitors_before,
                (SELECT count(*) FROM users WHERE created_at >= {SINCE}) AS signups,
                (SELECT count(*) FROM users WHERE created_at >= {start} AND created_at < {end}) AS signups_before,
                (SELECT COALESCE(sum(amount), 0) FROM payments WHERE status = 'succeeded' AND paid_at >= {SINCE}) AS revenue,
                (SELECT COALESCE(sum(amount), 0) FROM payments WHERE status = 'succeeded' AND paid_at >= {start} AND paid_at < {end}) AS revenue_before,
                (SELECT count(*) FROM payments WHERE status = 'succeeded' AND paid_at >= {SINCE}) AS payments,
                (SELECT count(*) FROM payments WHERE status = 'succeeded' AND paid_at >= {start} AND paid_at < {end}) AS payments_before,
                (SELECT count(*) FROM (SELECT user_id, min(paid_at) AS first FROM payments WHERE status = 'succeeded' AND user_id IS NOT NULL GROUP BY 1) f
                    WHERE f.first >= {SINCE}) AS new_payers,
                (SELECT count(*) FROM (SELECT user_id, min(paid_at) AS first FROM payments WHERE status = 'succeeded' AND user_id IS NOT NULL GROUP BY 1) f
                    WHERE f.first >= {start} AND f.first < {end}) AS new_payers_before,
                (SELECT count(*) FROM payments WHERE status = 'succeeded' AND product LIKE 'sky%%' AND paid_at >= {SINCE}
                    AND EXISTS (SELECT 1 FROM payments o WHERE o.user_id = payments.user_id AND o.status = 'succeeded'
                                AND o.product LIKE 'sky%%' AND o.paid_at < payments.paid_at)) AS renewals,
                (SELECT count(*) FROM users WHERE sky_until > now()) AS sky_now
            """,
            p,
        ).fetchone()
        now = _steps(conn.execute(f"WITH {_cohort(*NOW)} SELECT {COUNTS} FROM s", p).fetchone())
        before = _steps(conn.execute(f"WITH {_cohort(*BEFORE)} SELECT {COUNTS} FROM s", p).fetchone())
        groups = {by: _grouped(conn, by, *NOW, p) for by in SEGMENTS}
        labels = _labels(conn, [row["key"] for row in groups["channel"]])
    for row in groups["channel"]:
        row["label"] = labels.get(row["key"], row["key"])
    return {
        "days": days,
        "figures": {key: int(value) for key, value in figures.items()},
        "now": now,
        "before": before,
        "devices": {row["key"]: {key: row[key] for key in STEPS} for row in groups["device"]},
        "insights": _insights(now, before, groups),
    }


# ---- One person's way, for their card ----

def journey(user_id: int) -> dict:
    """Where this person came from and the first moment of each step and action: done or not yet.
    A later step stands in for an earlier one that went unrecorded (then it has no moment)."""
    p = {"id": user_id, "pair": PAIR}
    with pool.connection() as conn:
        _open(conn)
        user = conn.execute("SELECT id, created_at, email_confirmed_at, birth_date, visitor_id, ref_id, sky_until FROM users WHERE id = %(id)s", p).fetchone()
        if user is None:
            raise DomainError("missing", 404)
        row = conn.execute(
            """
            WITH vs AS (
                SELECT * FROM visitors v WHERE v.user_id = %(id)s OR v.id = (SELECT visitor_id FROM users WHERE id = %(id)s)
            ),
            ev AS (
                SELECT e.kind, e.name, e.created_at FROM events e
                WHERE e.user_id = %(id)s OR (e.user_id IS NULL AND e.visitor_id IN (SELECT id FROM vs))
            ),
            pay AS (SELECT * FROM payments WHERE user_id = %(id)s)
            SELECT
                (SELECT min(first_at) FROM vs) AS visit,
                (SELECT COALESCE(sum(visits), 0) FROM vs) AS visits,
                (SELECT max(last_at) FROM vs) AS last_at,
                (SELECT min(created_at) FROM ev WHERE kind = 'act' AND (name LIKE 'email:%%' OR name LIKE 'start:%%')) AS start,
                (SELECT name FROM ev WHERE kind = 'signup' ORDER BY created_at LIMIT 1) AS place,
                (SELECT array_agg(DISTINCT name) FROM ev WHERE kind = 'login') AS login_ways,
                (SELECT count(*) FROM ev WHERE kind = 'login') AS logins,
                (SELECT min(created_at) FROM pay) AS checkout,
                (SELECT count(*) FROM pay WHERE status <> 'succeeded') AS unfinished,
                (SELECT min(paid_at) FROM pay WHERE status = 'succeeded') AS paid,
                (SELECT min(created_at) FROM ev WHERE kind = 'birth') AS birth,
                (SELECT min(created_at) FROM ev WHERE kind = 'tour' AND name = 'intro:done') AS intro,
                (SELECT min(created_at) FROM ev WHERE kind = 'tour' AND name = 'intro:skip') AS intro_skip,
                (SELECT min(created_at) FROM ev WHERE ((kind = 'act' AND name = 'chart:seen') OR (kind = 'view' AND name = 'cabinet-chart'))
                    AND created_at >= COALESCE((SELECT min(created_at) FROM ev WHERE kind = 'birth'),
                                               (SELECT created_at FROM users WHERE id = %(id)s))) AS chart,
                (SELECT min(created_at) FROM ev WHERE kind = 'name') AS named,
                (SELECT min(created_at) FROM ev WHERE kind = 'password') AS password,
                (SELECT min(created_at) FROM ev WHERE kind = 'act' AND name = 'game:begin') AS game_begin,
                (SELECT min(created_at) FROM ev WHERE kind = 'act' AND name = 'game:land') AS game,
                (SELECT count(*) FROM ev WHERE kind = 'act' AND name = 'game:land') AS game_n,
                (SELECT min(created_at) FROM ev WHERE kind = 'view' AND name = 'cabinet-forecast') AS forecast,
                (SELECT count(*) FROM ev WHERE kind = 'view' AND name = 'cabinet-forecast') AS forecast_n,
                (SELECT min(created_at) FROM partners WHERE user_id = %(id)s) AS pair,
                (SELECT count(*) FROM partners WHERE user_id = %(id)s) AS pair_n,
                (SELECT min(created_at) FROM chat_messages WHERE user_id = %(id)s AND role = 'user') AS chat,
                (SELECT count(*) FROM chat_messages WHERE user_id = %(id)s AND role = 'user') AS chat_n,
                (SELECT min(created_at) FROM ev WHERE kind = 'view' AND name = 'cabinet-sky') AS sky_view,
                (SELECT min(created_at) FROM ev WHERE kind = 'offer') AS offer,
                (SELECT count(DISTINCT name) FROM ev WHERE kind = 'offer') AS offer_n,
                (SELECT min(created_at) FROM ev WHERE kind = 'pick') AS pick,
                (SELECT min(paid_at) FROM pay WHERE status = 'succeeded' AND product LIKE 'sky%%') AS sky_paid,
                (SELECT count(*) FROM pay WHERE status = 'succeeded' AND product LIKE 'sky%%') AS sky_paid_n,
                (SELECT min(paid_at) FROM pay WHERE status = 'succeeded' AND product = %(pair)s) AS pair_paid,
                (SELECT count(*) FROM pay WHERE status = 'succeeded' AND product = %(pair)s) AS pair_paid_n,
                (SELECT COALESCE(sum(amount), 0) FROM pay WHERE status = 'succeeded') AS revenue,
                (SELECT array_agg(DISTINCT split_part(name, ':', 1)) FROM ev WHERE kind = 'tour' AND name LIKE '%%:done') AS tours
            """,
            p,
        ).fetchone()
        first = conn.execute(
            """
            SELECT v.first_at, v.device, v.landing, v.source, r.name AS link, r.token
            FROM visitors v LEFT JOIN ref_links r ON r.id = v.ref_id
            WHERE v.user_id = %(id)s OR v.id = (SELECT visitor_id FROM users WHERE id = %(id)s)
            ORDER BY v.first_at LIMIT 1
            """,
            p,
        ).fetchone()

    def at(value):
        return value.isoformat() if value else None

    birth = row["birth"] or (user["created_at"] if user["birth_date"] else None)
    confirmed = user["email_confirmed_at"]
    moments = {
        "visit": row["visit"],
        "start": row["start"],
        "signup": user["created_at"],
        "confirm": confirmed,
        # Birth data from the home page count in the cabinet, once it is open.
        "birth": max(birth, confirmed) if birth and confirmed else None,
        "chart": row["chart"] if birth else None,
        "checkout": row["checkout"],
        "paid": row["paid"],
    }
    steps, later = [], False
    for key in reversed(STEPS):
        done = moments[key] is not None or later
        later = later or done
        steps.append({"key": key, "done": done, "at": at(moments[key])})
    steps.reverse()

    def action(key, moment, count=None, note=""):
        return {"key": key, "done": moment is not None, "at": at(moment), "count": count, "note": note}

    actions = [
        action("birth", birth),
        action("intro", row["intro"] or row["intro_skip"], note="skip" if not row["intro"] and row["intro_skip"] else ""),
        action("chart", row["chart"]),
        action("name", row["named"]),
        action("password", row["password"]),
        action("game", row["game"], int(row["game_n"]), note="begin" if not row["game"] and row["game_begin"] else ""),
        action("forecast", row["forecast"], int(row["forecast_n"])),
        action("pair", row["pair"], int(row["pair_n"])),
        action("chat", row["chat"], int(row["chat_n"])),
        action("sky_view", row["sky_view"]),
        action("offer", row["offer"], int(row["offer_n"])),
        action("pick", row["pick"]),
        action("sky_paid", row["sky_paid"], int(row["sky_paid_n"])),
        action("pair_paid", row["pair_paid"], int(row["pair_paid_n"])),
    ]
    return {
        "id": user_id,
        "first": None if first is None else {
            "at": at(first["first_at"]),
            "device": first["device"],
            "landing": first["landing"],
            "source": first["source"],
            "link": first["link"] or first["token"],
        },
        "visits": int(row["visits"]),
        "last_at": at(row["last_at"]),
        "steps": steps,
        "place": row["place"] or "",
        "logins": int(row["logins"]),
        "login_ways": [name for name in (row["login_ways"] or []) if name],
        "unfinished": int(row["unfinished"]),
        "actions": actions,
        "tours": sorted(name for name in (row["tours"] or []) if name),
        "revenue": int(row["revenue"]),
    }
