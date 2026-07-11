#!/usr/bin/env python3
"""Validate Age Verification Tracker page structure and shipped data.

Reads real HTML + age_verification_data.json (no mocks).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
AGE_PAGE = ROOT / "age-verification.html"
DATA = ROOT / "age_verification_data.json"


def main() -> int:
    assert INDEX.is_file(), "missing index.html"
    assert AGE_PAGE.is_file(), "missing age-verification.html"
    assert DATA.is_file(), "missing age_verification_data.json"

    index_html = INDEX.read_text(encoding="utf-8")
    age_html = AGE_PAGE.read_text(encoding="utf-8")

    # Nav labels on both pages
    for label, html, path in (
        ("Banned Websites Tracker", index_html, "index.html"),
        ("Age Verification Tracker", index_html, "index.html"),
        ("Banned Websites Tracker", age_html, "age-verification.html"),
        ("Age Verification Tracker", age_html, "age-verification.html"),
    ):
        assert label in html, f"{path} missing nav label: {label}"

    assert 'href="age-verification.html"' in index_html
    assert 'href="index.html"' in age_html
    assert re.search(r"Age\s+Verification\s+Tracker", age_html)
    assert "Current Legislative Efforts" in age_html, "missing exact section title"

    data = json.loads(DATA.read_text(encoding="utf-8"))
    timeline = data.get("timeline") or []
    efforts = data.get("legislative_efforts") or []

    assert len(timeline) >= 5, f"timeline too short: {len(timeline)}"
    for item in timeline:
        assert item.get("country"), item
        assert item.get("implementation_date") or item.get("implementation_label"), item
        assert item.get("status") in ("implemented", "scheduled"), item
        assert item.get("source", "").startswith("http"), item

    assert len(efforts) >= 4, f"efforts too short: {len(efforts)}"
    us_sub = [
        e for e in efforts
        if e.get("level") == "subnational"
        and ("United States" in e.get("country", "") or "United States" in e.get("jurisdiction", ""))
    ]
    assert us_sub, "need at least one US subnational legislative effort"
    non_us = [
        e for e in efforts
        if "United States" not in e.get("country", "")
        and "United States" not in e.get("jurisdiction", "")
    ]
    assert non_us, "need at least one non-US legislative effort"

    for e in efforts:
        assert e.get("jurisdiction") and e.get("title") and e.get("status"), e
        assert e.get("source", "").startswith("http"), e
        low = (e.get("summary") or "").lower() + " " + (e.get("title") or "").lower()
        assert any(
            k in low
            for k in ("age", "verification", "social media", "parental", "id", "identity")
        ), e

    print("OK: nav labels present on both pages")
    print("OK: timeline countries:", [t["country"] for t in timeline])
    print("OK: US subnational efforts:", [e["jurisdiction"] for e in us_sub])
    print("OK: non-US efforts:", [e["jurisdiction"] for e in non_us])
    print(f"OK: parsed {len(timeline)} timeline + {len(efforts)} efforts")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        raise SystemExit(1)
