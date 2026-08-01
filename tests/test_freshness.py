#!/usr/bin/env python3
"""No page may state a freshness date of its own.

The whole point of meta.json is that "DATA AS OF: JUL 2026" was typed into three
files by hand and had already drifted a week away from verified.json. Deriving
it once fixes that exactly as long as nobody types a new one in — so this fails
if a hardcoded data-currency date reappears anywhere, and checks each page still
carries the readouts that meta.json fills.

Fix a failure by using the shared readout instead of a literal:

    <span data-meta-row hidden>Data updated: <b data-meta="data-updated"></b></span>

Regenerate meta.json with:  python3 build_meta.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ["index.html", "age-verification.html", "vpn-tracker.html", "changes.html"]
META = ROOT / "meta.json"

# "Data as of JUL 2026", "Updated: July 2026", "Last updated 2026-07-26" — the
# shapes a hand-typed currency claim actually takes. Deliberately narrow: the
# pages are full of legitimate dates ("blocked since March 2022") and flagging
# those would make this test noise that gets switched off.
STALE_PATTERNS = [
    re.compile(r"data\s+as\s+of", re.I),
    re.compile(r"(?:last\s+)?updated\s*:?\s*<?b?>?\s*(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4}", re.I),
    re.compile(r"sources?\s+(?:verified|checked)\s*:?\s*<?b?>?\s*\d{1,2}\s|sources?\s+(?:verified|checked)\s*:?\s*<?b?>?\s*(?:jan|feb|mar)", re.I),
]


def main() -> int:
    assert META.is_file(), "meta.json missing (run: python3 build_meta.py)"
    meta = json.loads(META.read_text(encoding="utf-8"))
    for key in ("data_updated", "sources_checked", "censorship"):
        assert key in meta, f"meta.json has no {key!r} (run: python3 build_meta.py)"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", meta["data_updated"]), (
        f"meta.json data_updated is {meta['data_updated']!r}, expected an ISO date")

    for name in PAGES:
        page = ROOT / name
        assert page.is_file(), f"{name} missing"
        text = page.read_text(encoding="utf-8")

        for pattern in STALE_PATTERNS:
            found = pattern.search(text)
            assert not found, (
                f"{name} states its own freshness date ({found.group(0)!r}). "
                "Use the shared data-meta readout instead so it comes from meta.json.")

        assert 'data-meta="data-updated"' in text, f"{name} has no 'data updated' readout"
        assert 'data-meta="sources-checked"' in text, f"{name} has no 'sources checked' readout"
        assert "assets/site.js" in text, f"{name} does not load assets/site.js, which fills them"

    print(f"ok: {len(PAGES)} pages derive both freshness dates from meta.json "
          f"(data {meta['data_updated']}, sources {meta['sources_checked'] or 'never'})")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
