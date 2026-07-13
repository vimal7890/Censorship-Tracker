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
    assert set(by_country) == {"Canada", "China", "India", "Taiwan"}, by_country
    assert by_country["India"]["type"] == "complete"
    assert all(by_country[country]["type"] == "partial" for country in ("Canada", "China", "Taiwan"))
    assert not any(row["type"] == "age" for row in rows), "real-name checks are not age checks"

    assert "pib.gov.in" in by_country["India"]["source"]
    assert "canada.ca" in by_country["Canada"]["source"]
    assert "cac.gov.cn" in by_country["China"]["source"]
    assert "taipeitimes.com" in by_country["Taiwan"]["source"]
    assert "not a blanket WeChat-specific ID-based age-verification rule" in by_country["China"]["more_info"]

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
