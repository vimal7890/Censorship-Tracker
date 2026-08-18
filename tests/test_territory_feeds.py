#!/usr/bin/env python3
"""Every territory's feed must exist, parse, and match the changelog.

build_changelog.py writes feed/<slug>.xml per territory — the events filtered
to one place, with historical country names carried across renames. This
fails when the feeds drift from the CSV's territories (a rename leaving an
orphan, a new country with no feed) or when a feed stops being valid XML, and
checks that every item's guid is a real changelog sha, so a filter bug cannot
invent history for a territory.
"""
from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from territories import group_by_territory, load_rows  # noqa: E402


def main() -> int:
    groups = group_by_territory(load_rows())
    expected = {g["slug"] for g in groups.values()}
    on_disk = {p.stem for p in (ROOT / "feed").glob("*.xml")}

    # Every territory has history (its rows were added in some commit), so a
    # missing feed is drift, and an extra one is an orphaned territory.
    missing = expected - on_disk
    orphaned = on_disk - expected
    assert not missing, f"territories with no feed (run: python3 build_changelog.py): {sorted(missing)}"
    assert not orphaned, f"feeds for unknown territories: {sorted(orphaned)}"

    shas = {e["sha"] for e in
            json.loads((ROOT / "changelog.json").read_text(encoding="utf-8"))["events"]}

    by_slug = {g["slug"]: g for g in groups.values()}
    for slug in sorted(expected):
        path = ROOT / "feed" / f"{slug}.xml"
        tree = ET.parse(path)  # raises on invalid XML
        channel = tree.getroot().find("channel")
        title = channel.findtext("title") or ""
        assert by_slug[slug]["display"] in title, (
            f"feed/{slug}.xml titled {title!r}, expected it to name "
            f"{by_slug[slug]['display']!r}")
        items = channel.findall("item")
        assert items, f"feed/{slug}.xml has no items"
        for item in items:
            guid = item.findtext("guid") or ""
            assert guid in shas, (
                f"feed/{slug}.xml cites sha {guid[:10]} that is not in "
                "changelog.json — feeds and changelog were built from "
                "different histories (run: python3 build_changelog.py)")

    # And each country page advertises its feed.
    for g in groups.values():
        page = (ROOT / "country" / g["slug"] / "index.html").read_text(encoding="utf-8")
        assert f'/feed/{g["slug"]}.xml' in page, (
            f"country/{g['slug']}/ does not link its feed (run: python3 build_pages.py)")

    print(f"ok: {len(expected)} territory feeds parse, match the changelog "
          "and are linked from their pages")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
