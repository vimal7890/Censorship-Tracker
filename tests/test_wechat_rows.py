#!/usr/bin/env python3
"""Validate the sourced WeChat classification in the shipped tracker data."""
from __future__ import annotations

import csv
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "censorship_data.csv"
INDEX_PATH = ROOT / "index.html"


def main() -> int:
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        rows = [row for row in csv.DictReader(f) if row["platform"] == "WeChat"]

    EXPECTED = {"India", "North Korea", "Turkmenistan", "Eritrea"}

    by_country = {row["country"]: row for row in rows}
    # WeChat is a domestic Chinese platform and fully legal there — no China row.
    assert "China" not in by_country, "WeChat is legal in China; do not list a China restriction"
    # Iran blocked WeChat in September 2013 and unblocked it on 4 January 2018.
    # No reporting or OONI measurement shows a current restriction, so a stale
    # row was removed rather than reclassified.
    assert "Iran" not in by_country, "WeChat was unblocked in Iran in 2018; do not re-add"
    assert set(by_country) == EXPECTED, by_country
    # North Korea, Turkmenistan and Eritrea are blanket entries: each blocks
    # effectively the whole foreign internet rather than WeChat specifically.
    for country in sorted(EXPECTED):
        assert by_country[country]["type"] == "complete", country
    assert not any(row["type"] == "age" for row in rows), "real-name checks are not age checks"
    assert not any(row["type"] == "partial" for row in rows), "no partial WeChat rows expected"

    assert "pib.gov.in" in by_country["India"]["source"]
    # README: Wikipedia is barred as a source, with one narrow exception — the
    # default-restricted countries may fall back to their own country article
    # when no platform-specific reporting exists, which is exactly the case for
    # the blanket entries above. verify_links.py enforces the same carve-out.
    # India is not exempt and must keep citing real reporting.
    WIKI_EXEMPT = {"China", "Eritrea", "Iran", "North Korea", "Turkmenistan"}
    wiki = sorted(c for c, r in by_country.items()
                  if "wikipedia.org" in r["source"] and c not in WIKI_EXEMPT)
    assert not wiki, f"Wikipedia cited as a WeChat source for: {wiki}"

    index = INDEX_PATH.read_text(encoding="utf-8")
    assert '"WeChat":' in index, "WeChat needs a rendered platform icon"
    assert '"WeChat": "#07C160"' in index, "WeChat needs its brand colour"

    print("OK: WeChat countries:", sorted(by_country))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
