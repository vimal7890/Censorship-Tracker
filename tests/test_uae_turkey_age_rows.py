#!/usr/bin/env python3
"""Validate UAE and Türkiye pending age/ID rows in the shipped CSV.

Drives the real censorship_data.csv used by index.html (no mocks).
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "censorship_data.csv"

# Exactly the platforms the UAE cabinet resolution names in phase one. YouTube
# used to be listed here too, carried over from a generic "major social set"
# rather than from the resolution — a source audit found the official page
# names only these five, so the YouTube row was dropped. Required floor, not
# exhaustive: add a platform here when a later phase actually names it.
UAE_AGE_REQUIRED = {
    "Facebook",
    "Instagram",
    "Snapchat",
    "TikTok",
    "X",
}

# Social set minus Discord (complete ban still in force for Türkiye).
# Required floor; the Discord exclusion is asserted separately below.
TURKEY_AGE_REQUIRED = {
    "Facebook",
    "Instagram",
    "Reddit",
    "Snapchat",
    "TikTok",
    "Twitch",
    "X",
    "YouTube",
}


def load_rows() -> list[dict[str, str]]:
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def has(rows: list[dict[str, str]], platform: str, country: str, typ: str) -> bool:
    return any(
        r["platform"] == platform and r["country"] == country and r["type"] == typ
        for r in rows
    )


def main() -> int:
    assert CSV_PATH.is_file(), f"missing shipped data file: {CSV_PATH}"
    rows = load_rows()
    assert rows, "CSV parsed zero data rows"

    uae_age = [r for r in rows if r["country"] == "United Arab Emirates" and r["type"] == "age"]
    turkey_age = [r for r in rows if r["country"] == "Türkiye" and r["type"] == "age"]

    uae_platforms = {r["platform"] for r in uae_age}
    turkey_platforms = {r["platform"] for r in turkey_age}

    uae_missing = UAE_AGE_REQUIRED - uae_platforms
    assert not uae_missing, (
        f"UAE age rows missing required platforms: {sorted(uae_missing)}\n"
        f"  present: {sorted(uae_platforms)}"
    )
    turkey_missing = TURKEY_AGE_REQUIRED - turkey_platforms
    assert not turkey_missing, (
        f"Türkiye age rows missing required platforms: {sorted(turkey_missing)}\n"
        f"  present: {sorted(turkey_platforms)}"
    )
    assert "Discord" not in turkey_platforms, "Discord must stay complete-only for Türkiye"

    for r in uae_age:
        info = r["more_info"].strip()
        src = r["source"].strip()
        assert info, f"empty more_info: United Arab Emirates/{r['platform']}"
        assert src.startswith("https://"), src
        assert "wikipedia" not in src.lower()
        low = info.lower()
        assert "15" in info and ("under 15" in low or "under-15" in low)
        assert "digital identity" in low or "digital id" in low or "identity" in low
        assert "self-declaration" in low or "self declaration" in low
        assert "2027" in r["since"] or "2027" in info
        assert "alusra.gov.ae" in src or "uae" in src.lower() or "biometricupdate" in src

    for r in turkey_age:
        info = r["more_info"].strip()
        src = r["source"].strip()
        assert info, f"empty more_info: Türkiye/{r['platform']}"
        assert src.startswith("https://"), src
        assert "wikipedia" not in src.lower()
        low = info.lower()
        assert "15" in info and ("under 15" in low or "under-15" in low)
        assert "age-verification" in low or "age verification" in low
        assert "2026" in r["since"] or "2026" in info
        # Must not claim e-Devlet all-user ID is fully enacted
        if "e-devlet" in low or "e-government" in low:
            assert "draft" in low

    # Prior non-age rows preserved
    assert has(rows, "Discord", "United Arab Emirates", "partial"), "UAE Discord VoIP partial missing"
    assert has(rows, "WhatsApp", "United Arab Emirates", "partial"), "UAE WhatsApp VoIP partial missing"
    assert has(rows, "Discord", "Türkiye", "complete"), "Türkiye Discord complete missing"
    assert has(rows, "X", "Türkiye", "partial"), "Türkiye X Grok partial missing"
    assert has(rows, "X", "Türkiye", "age"), "Türkiye X age missing"

    print("OK: UAE age platforms:", sorted(uae_platforms))
    print("OK: Türkiye age platforms:", sorted(turkey_platforms))
    print(f"OK: parsed {len(rows)} rows from {CSV_PATH.name}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        raise SystemExit(1)
