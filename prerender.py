#!/usr/bin/env python3
"""Bake a static platform index into index.html for crawlers and no-JS visitors.

The homepage renders its list client-side from censorship_data.csv, so anything
that does not run JavaScript — search-engine crawlers, text browsers, readers
with scripting off — sees an empty shell. That is bad for a reference site whose
whole value is answering "is <platform> blocked in <country>?".

This writes the full platform -> countries list, as plain semantic HTML, between
the PRERENDER:START/END markers inside #platformGrid. The app overwrites that
node on load, so JS visitors never notice; everyone else gets the real content
(and it doubles as the pre-hydration paint, so there is no loading spinner).

Idempotent — safe to re-run after editing the CSV. Run it whenever the data
changes (and in CI/pre-deploy):  python3 prerender.py
"""
from __future__ import annotations

import csv
import html
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "censorship_data.csv"
INDEX = ROOT / "index.html"

TYPE_LABEL = {
    "complete": "complete ban",
    "partial": "partial restriction",
    "age": "age verification",
}

START = "<!-- PRERENDER:START"
END = "<!-- PRERENDER:END -->"


def build_block() -> str:
    by_platform: dict[str, list[tuple[str, str]]] = defaultdict(list)
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            platform = (row.get("platform") or "").strip()
            country = (row.get("country") or "").strip()
            btype = (row.get("type") or "complete").strip()
            if platform and country:
                by_platform[platform].append((country, btype))

    rows = []
    for platform in sorted(by_platform, key=str.lower):
        entries = by_platform[platform]
        seen: set[tuple[str, str]] = set()
        parts = []
        for country, btype in sorted(entries, key=lambda e: e[0].lower()):
            if (country, btype) in seen:
                continue
            seen.add((country, btype))
            parts.append(f"{html.escape(country)} ({TYPE_LABEL.get(btype, btype)})")
        n = len({c for c, _ in entries})
        noun = "country or territory" if n == 1 else "countries and territories"
        rows.append(
            '                    <article class="pr-row">\n'
            f'                        <h3 class="pr-name">{html.escape(platform)}</h3>\n'
            f'                        <p class="pr-countries"><b>{html.escape(platform)}</b> '
            f'is restricted in {n} {noun}: {", ".join(parts)}.</p>\n'
            '                    </article>'
        )

    return (
        '\n                <div class="prerender-index">\n'
        + "\n".join(rows)
        + "\n                </div>\n                "
    )


def main() -> int:
    if not INDEX.is_file():
        print("index.html not found", file=sys.stderr)
        return 1
    text = INDEX.read_text(encoding="utf-8")
    if START not in text or END not in text:
        print("PRERENDER markers not found in index.html", file=sys.stderr)
        return 1

    block = build_block()
    # Keep the START comment (and its guidance) and the END marker; replace only
    # what sits between them.
    new_text, count = re.subn(
        r"(" + re.escape(START) + r".*?-->).*?(" + re.escape(END) + r")",
        lambda m: m.group(1) + block + m.group(2),
        text,
        flags=re.S,
    )
    if count != 1:
        print(f"expected exactly one marker block, matched {count}", file=sys.stderr)
        return 1

    INDEX.write_text(new_text, encoding="utf-8")
    platforms = new_text.count('class="pr-row"')
    print(f"prerendered {platforms} platforms into index.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
