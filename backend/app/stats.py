"""The operator's figures: money and new accounts by day, the products, the totals.

Days are Moscow days, as everywhere else on the site; a payment counts on the day it was paid.
"""

from app.db import pool
from app.errors import DomainError
from app.partners import PRODUCT as PAIR

PERIODS = (7, 30, 90, 365)
TZ = "Europe/Moscow"


def stats(days: int) -> dict:
    if days not in PERIODS:
        raise DomainError("state")
    with pool.connection() as conn:
        series = conn.execute(
            f"""
            WITH span AS (
                SELECT generate_series((now() AT TIME ZONE '{TZ}')::date - (%(days)s - 1), (now() AT TIME ZONE '{TZ}')::date, '1 day')::date AS day
            ),
            paid AS (
                SELECT (paid_at AT TIME ZONE '{TZ}')::date AS day, sum(amount) AS revenue, count(*) AS payments
                FROM payments WHERE status = 'succeeded' AND paid_at IS NOT NULL
                GROUP BY 1
            ),
            joined AS (
                SELECT (created_at AT TIME ZONE '{TZ}')::date AS day, count(*) AS signups FROM users GROUP BY 1
            )
            SELECT span.day, COALESCE(paid.revenue, 0) AS revenue, COALESCE(paid.payments, 0) AS payments,
                   COALESCE(joined.signups, 0) AS signups
            FROM span LEFT JOIN paid USING (day) LEFT JOIN joined USING (day)
            ORDER BY span.day
            """,
            {"days": days},
        ).fetchall()
        since = f"(((now() AT TIME ZONE '{TZ}')::date - (%(days)s - 1))::timestamp AT TIME ZONE '{TZ}')"
        products = conn.execute(
            f"""
            SELECT product, sum(amount) AS revenue, count(*) AS payments
            FROM payments WHERE status = 'succeeded' AND paid_at >= {since}
            GROUP BY product ORDER BY revenue DESC
            """,
            {"days": days},
        ).fetchall()
        totals = conn.execute(
            f"""
            SELECT
                (SELECT count(*) FROM users) AS users,
                (SELECT count(*) FROM users WHERE sky_until > now()) AS sky,
                (SELECT count(*) FROM pairs) AS pairs,
                (SELECT count(*) FROM purchases WHERE product = %(pair)s AND pair_id IS NOT NULL) AS pairs_bought,
                (SELECT count(DISTINCT user_id) FROM payments WHERE status = 'succeeded' AND user_id IS NOT NULL) AS paying,
                (SELECT COALESCE(sum(amount), 0) FROM payments WHERE status = 'succeeded' AND paid_at >= {since}) AS revenue,
                (SELECT COALESCE(sum(amount), 0) FROM payments WHERE status = 'succeeded'
                    AND paid_at >= {since} - make_interval(days => %(days)s) AND paid_at < {since}) AS revenue_before,
                (SELECT count(*) FROM users WHERE created_at >= {since}) AS signups,
                (SELECT count(*) FROM users WHERE created_at >= {since} - make_interval(days => %(days)s)
                    AND created_at < {since}) AS signups_before
            """,
            {"days": days, "pair": PAIR},
        ).fetchone()
    return {
        "days": days,
        "series": [
            {"day": row["day"].isoformat(), "revenue": int(row["revenue"]), "payments": row["payments"], "signups": row["signups"]}
            for row in series
        ],
        "products": [
            {"product": row["product"], "revenue": int(row["revenue"]), "payments": row["payments"]} for row in products
        ],
        "totals": {key: int(value) for key, value in totals.items()},
    }
