"""The cache of readings: a reading is written once per input and then read from the database.

The key is a hash of what is being read and of the interpreter's version, never of the person:
the same Venus in Scorpio in the eighth house is one row for everyone, new birth data simply
asks for another row, and new texts (or a new interpreter) miss the old rows altogether.
A reading ({essence, parts}) is kept as JSON in the text column.
"""

import hashlib
import json
from collections.abc import Callable

from app.astro.texts import interpreter
from app.db import pool


def _key(inputs: list) -> str:
    payload = [type(interpreter).__name__, interpreter.version, inputs]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()


def cached(kind: str, inputs: list, make: Callable[[], dict]) -> dict:
    key = _key(inputs)
    with pool.connection() as conn:
        row = conn.execute("SELECT text FROM readings WHERE kind = %s AND key = %s", (kind, key)).fetchone()
    if row is not None:
        return json.loads(row["text"])
    reading = make()
    text = json.dumps(reading, ensure_ascii=False)
    with pool.connection() as conn:
        conn.execute(
            "INSERT INTO readings (kind, key, text) VALUES (%s, %s, %s) ON CONFLICT (kind, key) DO NOTHING",
            (kind, key, text),
        )
    return reading
