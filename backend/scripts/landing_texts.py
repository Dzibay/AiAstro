"""Writes the twelve signs of the Ascendant, Lilith and Chiron for the landing pages.

The landings are prerendered from the frontend's own files, so the words of app.astro are copied
there as JSON. Run from the backend folder after the texts change: python scripts/landing_texts.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.astro.chart import SIGNS  # noqa: E402
from app.astro.texts import interpreter, item_title  # noqa: E402

TARGET = ROOT.parent / "frontend" / "src" / "landing" / "signs.json"


def main() -> None:
    data = {}
    for point in ("asc", "lilith", "chiron"):
        rows = []
        for sign in SIGNS:
            reading = interpreter.natal_item(point, sign, None)
            rows.append({"sign": sign, "title": item_title(point, sign, None), "essence": reading["essence"], "text": reading["parts"][1]["text"]})
        data[point] = rows
    TARGET.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{TARGET}: {sum(len(rows) for rows in data.values())} readings")


if __name__ == "__main__":
    main()
