#!/usr/bin/env python3
"""The static country/platform pages must match the CSV they were built from.

build_pages.py writes a page per territory and per platform plus sitemap.xml.
Like the prerender block, those are generated artifacts: this fails when the
CSV and the pages drift — a renamed territory leaving an orphaned directory, a
new platform with no page, a page whose entry count no longer matches the
data — so a forgotten `python3 build_pages.py` is caught before it ships.

Also pins the HEAVY_CENSORSHIP boilerplate in territories.py to the copy in
index.html: the static pages and the app must describe the default-restricted
countries in exactly the same words.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from territories import (HEAVY_CENSORSHIP, group_by_platform,  # noqa: E402
                         group_by_territory, load_rows, slugify)


def main() -> int:
    rows = load_rows()
    territories = group_by_territory(rows)
    platforms = group_by_platform(rows)

    # --- one page per territory, one per platform, no orphans ---
    expected_country = {g["slug"] for g in territories.values()}
    expected_platform = {slugify(name) for name in platforms}
    assert len(expected_platform) == len(platforms), "platform slug collision"

    on_disk_country = {p.name for p in (ROOT / "country").iterdir() if p.is_dir()}
    on_disk_platform = {p.name for p in (ROOT / "platform").iterdir() if p.is_dir()}
    assert on_disk_country == expected_country, (
        "country/ pages drift from the CSV (run: python3 build_pages.py) — "
        f"missing {sorted(expected_country - on_disk_country)}, "
        f"orphaned {sorted(on_disk_country - expected_country)}")
    assert on_disk_platform == expected_platform, (
        "platform/ pages drift from the CSV (run: python3 build_pages.py) — "
        f"missing {sorted(expected_platform - on_disk_platform)}, "
        f"orphaned {sorted(on_disk_platform - expected_platform)}")
    assert (ROOT / "country" / "index.html").is_file(), "country/ hub page missing"
    assert (ROOT / "platform" / "index.html").is_file(), "platform/ hub page missing"

    # --- each page reflects the data it claims to ---
    for group in territories.values():
        page = (ROOT / "country" / group["slug"] / "index.html").read_text(encoding="utf-8")
        n = page.count('<article class="entry')
        assert n == len(group["entries"]), (
            f"country/{group['slug']}/ shows {n} entries, CSV has "
            f"{len(group['entries'])} (run: python3 build_pages.py)")
        assert f'href="/#country={group["iso"]}"' in page, (
            f"country/{group['slug']}/ does not link its interactive dossier")
        ld = re.search(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)
        assert ld, f"country/{group['slug']}/ has no JSON-LD"
        json.loads(ld.group(1))  # must parse
        assert f'<link rel="canonical" href="https://censorship.my/country/{group["slug"]}/">' in page

    for name, entries in platforms.items():
        page = (ROOT / "platform" / slugify(name) / "index.html").read_text(encoding="utf-8")
        n = page.count('<article class="entry')
        assert n == len(entries), (
            f"platform/{slugify(name)}/ shows {n} entries, CSV has {len(entries)} "
            "(run: python3 build_pages.py)")

    # --- sitemap covers exactly the pages that exist ---
    sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    for slug in expected_country:
        assert f"<loc>https://censorship.my/country/{slug}/</loc>" in sitemap, (
            f"sitemap.xml is missing country/{slug}/")
    for slug in expected_platform:
        assert f"<loc>https://censorship.my/platform/{slug}/</loc>" in sitemap, (
            f"sitemap.xml is missing platform/{slug}/")
    listed = sitemap.count("<loc>")
    expected_total = len(expected_country) + len(expected_platform) + 6
    assert listed == expected_total, (
        f"sitemap.xml lists {listed} URLs, expected {expected_total}")

    # --- the shared boilerplate stays one text, not two ---
    index_html = (ROOT / "index.html").read_text(encoding="utf-8")
    block = re.search(r"const HEAVY_CENSORSHIP = \{(.*?)\n\s*\};", index_html, re.S)
    assert block, "HEAVY_CENSORSHIP not found in index.html"
    in_app = dict(re.findall(r'"((?:[^"\\]|\\.)+)":\s*"((?:[^"\\]|\\.)*)"', block.group(1)))
    in_app = {k.replace('\\"', '"'): v.replace('\\"', '"') for k, v in in_app.items()}
    assert in_app == HEAVY_CENSORSHIP, (
        "HEAVY_CENSORSHIP in territories.py drifted from index.html — "
        "the static pages and the app must use identical words")

    print(f"ok: {len(expected_country)} country pages and {len(expected_platform)} "
          f"platform pages match the CSV; sitemap lists {listed} URLs")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
