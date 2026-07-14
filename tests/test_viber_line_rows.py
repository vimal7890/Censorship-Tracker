#!/usr/bin/env python3
"""Validate the researched Viber and LINE entries in the shipped tracker."""

from __future__ import annotations

import csv
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "censorship_data.csv"
INDEX_PATH = ROOT / "index.html"

EXPECTED = {
    "LINE": {"China", "North Korea", "Russia", "Turkmenistan", "UAE"},
    "Viber": {"China", "Iran", "North Korea", "Russia", "Turkmenistan", "UAE"},
}


def main() -> int:
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    for platform, countries in EXPECTED.items():
        platform_rows = [row for row in rows if row["platform"] == platform]
        assert {row["country"] for row in platform_rows} == countries, platform_rows
        assert not any(row["type"] == "age" for row in platform_rows), (
            f"{platform} has no platform-specific ID-based age-verification rule"
        )
        for row in platform_rows:
            assert row["type"] in {"complete", "partial"}, row
            assert row["source"].startswith("https://"), row

    line = {row["country"]: row for row in rows if row["platform"] == "LINE"}
    viber = {row["country"]: row for row in rows if row["platform"] == "Viber"}
    assert line["UAE"]["type"] == "partial"
    assert viber["UAE"]["type"] == "partial"
    assert all(line[country]["type"] == "complete" for country in EXPECTED["LINE"] - {"UAE"})
    assert all(viber[country]["type"] == "complete" for country in EXPECTED["Viber"] - {"UAE"})

    index = INDEX_PATH.read_text(encoding="utf-8")
    for platform, colour in (("LINE", "#00C300"), ("Viber", "#7360F2")):
        assert f'"{platform}":' in index, f"{platform} needs a rendered platform icon"
        assert f'"{platform}": "{colour}"' in index, f"{platform} needs its brand colour"

    print("OK: Viber countries:", sorted(viber))
    print("OK: LINE countries:", sorted(line))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
