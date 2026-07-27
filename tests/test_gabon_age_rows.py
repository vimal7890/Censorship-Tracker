#!/usr/bin/env python3
"""Validate Gabon under-16 identity/age rows in the shipped CSV.

Drives the real censorship_data.csv used by index.html (no mocks).
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "censorship_data.csv"

# Required floor, mirroring the Australia/Brazil social set. Not exhaustive:
# the Gabonese rules are category-based, so newly tracked platforms
# legitimately join. Every age row is still content-checked below.
GABON_AGE_REQUIRED = {
    "Discord",
    "Facebook",
    "Instagram",
    "Reddit",
    "Snapchat",
    "TikTok",
    "Twitch",
    "X (formerly Twitter)",
    "YouTube",
}

SOURCE_NEEDLE = "biometricupdate.com"


def load_rows() -> list[dict[str, str]]:
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> int:
    assert CSV_PATH.is_file(), f"missing shipped data file: {CSV_PATH}"
    rows = load_rows()
    assert rows, "CSV parsed zero data rows"

    gabon_age = [
        r for r in rows if r["country"] == "Gabon" and r["type"] == "age"
    ]
    platforms = {r["platform"] for r in gabon_age}
    missing = GABON_AGE_REQUIRED - platforms
    assert not missing, (
        f"Gabon age rows missing required platforms: {sorted(missing)}\n"
        f"  present: {sorted(platforms)}"
    )

    for r in gabon_age:
        info = r["more_info"].strip()
        src = r["source"].strip()
        assert info, f"empty more_info: {r['platform']}"
        assert src.startswith("https://"), f"source not https: {r['platform']}: {src!r}"
        assert SOURCE_NEEDLE in src, f"unexpected source: {src}"

        low = info.lower()
        assert "under-16" in low or "under 16" in low or "age of majority of 16" in low, (
            f"missing under-16 / majority 16: {r['platform']}"
        )
        assert "parental" in low, f"missing parental consent: {r['platform']}"
        # More than bare ID: name, address, NIP
        assert "name" in low and "address" in low, f"missing name/address: {r['platform']}"
        assert "nip" in low or "personal identification" in low, (
            f"missing NIP / personal ID number: {r['platform']}"
        )
        assert "2027" in r["since"] or "2027" in info, (
            f"missing Feb 2027 compliance timing: {r['platform']}"
        )
        assert "12-month" in low or "12 month" in low, (
            f"missing 12-month transition: {r['platform']}"
        )

    print("OK: Gabon age platforms:", sorted(platforms))
    print(f"OK: parsed {len(rows)} rows from {CSV_PATH.name}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        raise SystemExit(1)
