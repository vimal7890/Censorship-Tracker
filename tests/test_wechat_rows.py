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

    by_country = {row["country"]: row for row in rows}
    # WeChat is a domestic Chinese platform and fully legal there — no China row.
    assert "China" not in by_country, "WeChat is legal in China; do not list a China restriction"
    assert set(by_country) == {"India", "North Korea", "Turkmenistan"}, by_country
    assert by_country["India"]["type"] == "complete"
    assert by_country["North Korea"]["type"] == "complete"
    assert by_country["Turkmenistan"]["type"] == "complete"
    assert not any(row["type"] == "age" for row in rows), "real-name checks are not age checks"
    assert not any(row["type"] == "partial" for row in rows), "no partial WeChat rows expected"

    assert "pib.gov.in" in by_country["India"]["source"]

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
