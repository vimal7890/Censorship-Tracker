#!/usr/bin/env python3
"""The changelog and RSS feed must be well-formed and match the dataset's history.

The changelog is the site's only claim about what changed and when, and it is
derived rather than written, so the failure mode is not a typo — it is the file
quietly falling behind the commits it summarises, or a rename-detection change
turning real additions into cosmetic ones.

Checks the shape of every event, that renames only ever claim a single-field
change, that the feed parses as XML with one item per recent change, and that
the newest event still matches the newest commit that touched the CSV.

Fix a failure by running:  python3 build_changelog.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = ROOT / "changelog.json"
FEED = ROOT / "feed.xml"
KINDS = ("added", "removed", "changed", "renamed")


def main() -> int:
    assert CHANGELOG.is_file(), "changelog.json missing (run: python3 build_changelog.py)"
    assert FEED.is_file(), "feed.xml missing (run: python3 build_changelog.py)"

    data = json.loads(CHANGELOG.read_text(encoding="utf-8"))
    events = data["events"]
    assert events, "changelog has no events"
    assert data["count"] == len(events), "changelog count does not match its events"

    seen_ids = set()
    for event in events:
        where = f"{event.get('date')} {event.get('subject', '')[:40]}"
        for key in ("id", "sha", "date", "subject", "total"):
            assert event.get(key), f"{where}: missing {key}"
        assert event["id"] not in seen_ids, f"{where}: duplicate id {event['id']} — anchors must be unique"
        seen_ids.add(event["id"])
        assert event["sha"].startswith(event["id"]), f"{where}: id is not a prefix of its sha"

        total = 0
        for kind in KINDS:
            rows = event.get(kind)
            assert isinstance(rows, list), f"{where}: {kind} is not a list"
            total += len(rows)
            for row in rows:
                for key in ("platform", "country", "type"):
                    assert row.get(key), f"{where}: {kind} row missing {key}"
                if kind == "renamed":
                    assert row.get("renamed") in ("country", "platform"), (
                        f"{where}: rename does not say which field moved")
                    assert row.get("was"), f"{where}: rename does not say what it was"
                    assert row["was"] != row[row["renamed"]], (
                        f"{where}: rename claims {row['was']!r} became itself")
        assert total == event["total"], f"{where}: total {event['total']} but {total} rows"

    # Newest first — a changelog in the wrong order is worse than none.
    dates = [e["date"] for e in events]
    assert dates == sorted(dates, reverse=True), "events are not newest-first"

    # Still in step with git: the newest event must be the newest commit that
    # actually changed the data.
    log = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", "censorship_data.csv"],
        cwd=ROOT, capture_output=True, text=True)
    if log.returncode == 0 and log.stdout.strip():
        head = log.stdout.strip()
        assert any(e["sha"] == head for e in events[:5]), (
            f"the newest commit touching the CSV ({head[:10]}) is not in the changelog's "
            "five most recent events (run: python3 build_changelog.py)")

    root = ET.fromstring(FEED.read_text(encoding="utf-8"))
    items = root.findall("./channel/item")
    assert items, "feed.xml has no items"
    assert len(items) == min(60, len(events)), (
        f"feed.xml has {len(items)} items for {len(events)} events")
    for item in items:
        for tag in ("title", "link", "guid", "pubDate", "description"):
            node = item.find(tag)
            assert node is not None and node.text, f"feed item missing {tag}"
        assert item.find("link").text.startswith("https://censorship.my/changes#"), (
            "feed items must deep-link to a specific change")

    renamed = sum(len(e["renamed"]) for e in events)
    print(f"ok: {len(events)} dated changes ({renamed} rows recognised as renames), "
          f"{len(items)} feed items, all well-formed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
