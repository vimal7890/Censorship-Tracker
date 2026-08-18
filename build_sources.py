#!/usr/bin/env python3
"""Write sources.json — one card's worth of context per cited URL.

The pages fetch this and render citations as "Reuters · Reporting · 12 Jun 2026"
instead of "[47]". Regenerate after editing any source URL:

    python3 build_sources.py

Titles are never derived here (see sources.py for why). The file carries a
`title` field per URL that starts empty and is filled in by verify_links.py,
which already fetches every page; this script preserves whatever is already
there, so running it after a verification pass does not throw the titles away.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import sources
from stable_write import write_json

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "censorship_data.csv"
JSON_PATHS = [ROOT / "vpn_data.json", ROOT / "age_verification_data.json"]
OUT = ROOT / "sources.json"


def collect() -> list[str]:
    """Every source URL cited anywhere in the datasets."""
    urls: set[str] = set()
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            url = (row.get("source") or "").strip()
            if url.startswith("http"):
                urls.add(url)
    for path in JSON_PATHS:
        if path.is_file():
            urls |= set(re.findall(r'"(https?://[^"]+)"', path.read_text(encoding="utf-8")))
    return sorted(urls)


def main() -> int:
    previous_payload: dict = {}
    if OUT.is_file():
        try:
            previous_payload = json.loads(OUT.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            previous_payload = {}
    previous: dict[str, dict] = previous_payload.get("sources", {}) or {}

    urls = collect()
    entries: dict[str, dict] = {}
    kinds: Counter[str] = Counter()
    unregistered: list[str] = []

    for url in urls:
        info = sources.classify(url)
        if not info.pop("registered"):
            unregistered.append(info["domain"])
        # A title only ever comes from a real fetch, so carry forward any that
        # a previous verify_links.py run recorded.
        info["title"] = (previous.get(url) or {}).get("title", "")
        entries[url] = info
        kinds[info["kind"]] += 1

    payload = {
        "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "count": len(entries),
        "by_kind": dict(sorted(kinds.items(), key=lambda kv: sources.KIND_RANK.index(kv[0]))),
        "kind_labels": sources.KIND_LABEL,
        "kind_blurbs": sources.KIND_BLURB,
        "sources": entries,
    }
    # verify_links.py stamps when it last captured titles; carry that through a
    # regeneration the same way the titles themselves are carried.
    if "titles_captured_utc" in previous_payload:
        payload["titles_captured_utc"] = previous_payload["titles_captured_utc"]
    wrote = write_json(OUT, payload)

    titled = sum(1 for e in entries.values() if e["title"])
    print(f"{'wrote' if wrote else 'unchanged'} {OUT.name}: "
          f"{len(entries)} sources, {titled} with a fetched title")
    print("  " + " · ".join(f"{k} {v}" for k, v in payload["by_kind"].items()))
    if unregistered:
        print(f"\n{len(set(unregistered))} domain(s) not in sources.REGISTRY — "
              "add them so the card shows a publisher instead of a hostname:")
        for host, n in Counter(unregistered).most_common():
            print(f"  {host} ({n} URL{'s' if n > 1 else ''})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
