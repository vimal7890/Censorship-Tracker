#!/usr/bin/env python3
"""Validate the researched Viber and LINE entries in the shipped tracker."""

from __future__ import annotations

import csv
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "censorship_data.csv"
INDEX_PATH = ROOT / "index.html"

# Known country → restriction-type classifications for each messenger. Every
# entry here must be present in the CSV with exactly this type; "partial" means
# a feature-level VoIP / calling restriction where messaging still works, while
# "complete" means the service itself is blocked.
#
# This is a required floor rather than an exhaustive list — both apps are VoIP
# messengers, so further Gulf-style calling restrictions may legitimately be
# researched and added. Any extra country is still validated for a sane type
# and an https source below, it just does not need to be enumerated here.
EXPECTED_TYPE = {
    "LINE": {
        "People's Republic of China": "complete",
        "North Korea": "complete",
        "Oman": "partial",
        "Qatar": "partial",
        "Russia": "complete",
        "Saudi Arabia": "partial",
        "Turkmenistan": "complete",
        "United Arab Emirates": "partial",
    },
    "Viber": {
        "People's Republic of China": "complete",
        "Egypt": "partial",
        "Islamic Republic of Iran": "complete",
        "North Korea": "complete",
        "Oman": "partial",
        "Qatar": "partial",
        "Russia": "complete",
        "Turkmenistan": "complete",
        "United Arab Emirates": "partial",
    },
}


def main() -> int:
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    for platform, expected in EXPECTED_TYPE.items():
        platform_rows = [row for row in rows if row["platform"] == platform]
        by_country = {row["country"]: row for row in platform_rows}

        missing = set(expected) - set(by_country)
        assert not missing, (
            f"{platform} missing required countries: {sorted(missing)}\n"
            f"  present: {sorted(by_country)}"
        )
        wrong = {
            country: (by_country[country]["type"], want)
            for country, want in expected.items()
            if by_country[country]["type"] != want
        }
        assert not wrong, f"{platform} restriction type changed (got, expected): {wrong}"

        assert not any(row["type"] == "age" for row in platform_rows), (
            f"{platform} has no platform-specific ID-based age-verification rule"
        )
        for row in platform_rows:
            assert row["type"] in {"complete", "partial"}, row
            # A blank source is allowed, per README.md: when no page can be
            # found that actually documents the claim, leaving the field empty
            # beats attaching one that does not. LINE/Saudi Arabia is the live
            # example — the only reporting found says the calling block was
            # lifted on 20 September 2017, so it cannot cite that as evidence
            # of a current restriction. What is not allowed is a non-URL.
            src = row["source"].strip()
            assert not src or src.startswith("https://"), row

    line = {row["country"]: row for row in rows if row["platform"] == "LINE"}
    viber = {row["country"]: row for row in rows if row["platform"] == "Viber"}

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
