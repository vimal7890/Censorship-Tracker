#!/usr/bin/env python3
"""Validate Brazil and Indonesia under-16 age rows in the shipped CSV.

Drives the real censorship_data.csv used by index.html (no mocks).
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "censorship_data.csv"

# Platforms the Brazil ECA Digital social-network rules must cover (Art. 24
# parental-link for under-16). This is a required floor, not an exhaustive
# list: the law is written by platform category, so newly tracked platforms
# legitimately join it. Every age row is still content-checked below.
BRAZIL_AGE_REQUIRED = {
    "Discord",
    "Facebook",
    "Instagram",
    "Reddit",
    "Snapchat",
    "TikTok",
    "Twitch",
    "X",
    "YouTube",
}

# Indonesia high-risk list (BBC) ∩ platforms already on the tracker.
# Required floor; anything added must also appear in INDONESIA_HIGH_RISK_NAMED.
INDONESIA_AGE_REQUIRED = {
    "Facebook",
    "Instagram",
    "TikTok",
    "X",
    "YouTube",
}

INDONESIA_HIGH_RISK_NAMED = {
    "YouTube",
    "TikTok",
    "Facebook",
    "Instagram",
    "Threads",
    "X",
    "Bigo Live",
    "Roblox",
}

BRAZIL_SOURCE_NEEDLE = "planalto.gov.br"
INDONESIA_SOURCE_NEEDLE = "bbc.com"
NEWS_OR_GOV_HOSTS = (
    "planalto.gov.br",
    "bbc.com",
    "reuters.com",
    "apnews.com",
    "gov.br",
    "go.id",
    "esafety.gov.au",
)


def load_rows() -> list[dict[str, str]]:
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> int:
    assert CSV_PATH.is_file(), f"missing shipped data file: {CSV_PATH}"
    rows = load_rows()
    assert rows, "CSV parsed zero data rows"

    brazil_age = [
        r for r in rows if r["country"] == "Brazil" and r["type"] == "age"
    ]
    indo_age = [
        r for r in rows if r["country"] == "Indonesia" and r["type"] == "age"
    ]

    brazil_platforms = {r["platform"] for r in brazil_age}
    indo_platforms = {r["platform"] for r in indo_age}

    brazil_missing = BRAZIL_AGE_REQUIRED - brazil_platforms
    assert not brazil_missing, (
        f"Brazil age rows missing required platforms: {sorted(brazil_missing)}\n"
        f"  present: {sorted(brazil_platforms)}"
    )
    indo_missing = INDONESIA_AGE_REQUIRED - indo_platforms
    assert not indo_missing, (
        f"Indonesia age rows missing required platforms: {sorted(indo_missing)}\n"
        f"  present: {sorted(indo_platforms)}"
    )

    # Indonesia age platforms must be subset of named high-risk list
    for p in indo_platforms:
        ok = p in INDONESIA_HIGH_RISK_NAMED or p.startswith("X")
        assert ok, f"Indonesia age platform not on high-risk list: {p}"

    for r in brazil_age + indo_age:
        assert r["more_info"].strip(), f"empty more_info: {r['platform']}/{r['country']}"
        src = r["source"].strip()
        assert src.startswith("http://") or src.startswith("https://"), (
            f"source not http(s): {r['platform']}/{r['country']}: {src!r}"
        )
        assert any(h in src for h in NEWS_OR_GOV_HOSTS) or "planalto" in src or "bbc.com" in src, (
            f"source not news/gov: {src}"
        )

    for r in brazil_age:
        assert BRAZIL_SOURCE_NEEDLE in r["source"], r
        assert "17/03/2026" in r["since"] or "March 2026" in r["since"]
        assert "under 16" in r["more_info"].lower() or "under-16" in r["more_info"].lower()

    for r in indo_age:
        assert INDONESIA_SOURCE_NEEDLE in r["source"], r
        assert "28/03/2026" in r["since"] or "March 2026" in r["since"]

    # Prior non-age Indonesia rows must remain
    def has(platform: str, country: str, typ: str) -> bool:
        return any(
            r["platform"] == platform and r["country"] == country and r["type"] == typ
            for r in rows
        )

    assert has("DuckDuckGo", "Indonesia", "complete"), "DuckDuckGo Indonesia ban missing"
    assert has("Reddit", "Indonesia", "complete"), "Reddit Indonesia ban missing"
    # Grok partial ban (Jan 2026) was lifted in early 2026 — must not reappear
    assert not has("X", "Indonesia", "partial"), "stale X Grok Indonesia partial"
    assert has("X", "Indonesia", "age"), "X Indonesia age missing"

    print("OK: Brazil age platforms:", sorted(brazil_platforms))
    print("OK: Indonesia age platforms:", sorted(indo_platforms))
    print(f"OK: parsed {len(rows)} rows from {CSV_PATH.name}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        raise SystemExit(1)
