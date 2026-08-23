#!/usr/bin/env python3
"""The Wayback fields verify_links.py stores must be real, confirmed captures.

A stored snapshot link that 404s is worse than none: it looks like evidence.
These tests pin the pure half of the snapshot machinery — timestamp parsing,
age maths, availability-response parsing — so the rules documented in
verify_links.py ("only ever one the Archive itself confirmed") hold at the
edges where they could silently break.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import verify_links  # noqa: E402

SOURCES_JSON = ROOT / "sources.json"


def main() -> int:
    # --- timestamp -> ISO date -------------------------------------------
    assert verify_links.iso_from_timestamp("20250803123456") == "2025-08-03"
    assert verify_links.iso_from_timestamp("20250803") == "2025-08-03"
    assert verify_links.iso_from_timestamp("") == ""
    assert verify_links.iso_from_timestamp("not-a-date") == ""
    assert verify_links.iso_from_timestamp("2025-08-03") == ""      # wrong shape
    assert verify_links.iso_from_timestamp("20251303000000") == ""  # month 13 — must not parse as anything

    # --- age maths ---------------------------------------------------------
    today = date(2026, 8, 23)
    assert verify_links.snapshot_age_days("2026-08-23", today) == 0
    assert verify_links.snapshot_age_days("2026-08-22", today) == 1
    assert verify_links.snapshot_age_days("2025-08-23", today) == 365
    assert verify_links.snapshot_age_days("", today) is None
    assert verify_links.snapshot_age_days("garbage", today) is None
    # A future-dated stamp is bad data, not a fountain of youth.
    assert verify_links.snapshot_age_days("2027-01-01", today) is None

    # --- availability response parsing --------------------------------------
    good = json.dumps({"archived_snapshots": {"closest": {
        "status": "200",
        "timestamp": "20250803123456",
        "url": "https://web.archive.org/web/20250803123456/https://example.com/"}}})
    url, ts = verify_links.parse_availability(good)
    assert url.endswith("example.com/") and ts == "20250803123456"

    for empty in ('{"archived_snapshots": {}}', "{}", "not json",
                  '{"archived_snapshots": {"closest": {"status": "404", '
                  '"timestamp": "20250803123456", "url": "https://web.archive.org/web/x/"}}}',
                  '{"archived_snapshots": {"closest": {"status": "200"}}}'):
        assert verify_links.parse_availability(empty) == ("", ""), f"should be nothing: {empty!r}"

    # --- whatever reached sources.json obeys the same rules ------------------
    # Note a stored snapshot may legitimately be older than the freshness bar:
    # verify_links keeps the best capture it has while queuing a refresh, so
    # age alone is not a defect — an unparseable or future date is.
    if SOURCES_JSON.is_file():
        entries = json.loads(SOURCES_JSON.read_text(encoding="utf-8")).get("sources", {})
        snapshotted = stale = 0
        for url, entry in entries.items():
            snap = entry.get("snapshot") or ""
            if not snap:
                continue
            snapshotted += 1
            assert snap.startswith("https://web.archive.org/"), f"{url}: odd snapshot URL {snap!r}"
            stamped = entry.get("snapshot_date") or ""
            age = verify_links.snapshot_age_days(stamped, date.today())
            assert age is not None, f"{url}: unusable snapshot_date {stamped!r}"
            if age > verify_links.SNAPSHOT_MAX_AGE_DAYS:
                stale += 1
        print(f"ok: snapshot helpers behave; sources.json holds {snapshotted} confirmed "
              f"snapshot(s), {stale} awaiting a fresher capture")
    else:
        print("ok: snapshot helpers behave (sources.json not built yet)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
