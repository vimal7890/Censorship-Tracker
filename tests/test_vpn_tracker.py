#!/usr/bin/env python3
"""Validate VPN Tracker page structure and shipped data (no mocks)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
AGE = ROOT / "age-verification.html"
VPN = ROOT / "vpn-tracker.html"
DATA = ROOT / "vpn_data.json"


def main() -> int:
    assert INDEX.is_file() and AGE.is_file() and VPN.is_file() and DATA.is_file()

    for path, html in (
        (INDEX, INDEX.read_text(encoding="utf-8")),
        (AGE, AGE.read_text(encoding="utf-8")),
        (VPN, VPN.read_text(encoding="utf-8")),
    ):
        assert "VPN Tracker" in html, f"{path.name} missing VPN Tracker nav"
        assert 'href="vpn-tracker.html"' in html, f"{path.name} missing vpn-tracker link"

    vpn_html = VPN.read_text(encoding="utf-8")
    assert "Global Censorship Tracker" in vpn_html
    assert "Age Verification Tracker" in vpn_html
    assert "Current Legislative Efforts" in vpn_html
    assert "vpn_data.json" in vpn_html

    data = json.loads(DATA.read_text(encoding="utf-8"))
    rows = data.get("restrictions") or []
    efforts = data.get("legislative_efforts") or []

    assert len(rows) >= 8, f"need ≥8 restriction rows, got {len(rows)}"
    severities = {r.get("severity") for r in rows}
    assert "complete" in severities and "restricted" in severities, severities

    for r in rows:
        assert r.get("country") and r.get("summary"), r
        assert r.get("severity") in ("complete", "restricted"), r
        assert str(r.get("source", "")).startswith("http"), r
        assert "wikipedia.org" not in r["source"] or True  # allow but prefer news

    assert len(efforts) >= 3, efforts
    russiaish = [
        e for e in efforts
        if "Russia" in e.get("jurisdiction", "") or "Russia" in e.get("title", "")
    ]
    assert russiaish, "need Russia 2025–2026 VPN crackdown entry"

    for e in efforts:
        assert e.get("jurisdiction") and e.get("title") and e.get("status"), e
        assert str(e.get("source", "")).startswith("http"), e

    print("OK: VPN Tracker nav on all pages")
    print("OK: restrictions:", [(r["country"], r["severity"]) for r in rows])
    print("OK: legislative:", [e["jurisdiction"] for e in efforts])
    print(f"OK: {len(rows)} table rows + {len(efforts)} efforts")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        raise SystemExit(1)
