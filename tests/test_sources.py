#!/usr/bin/env python3
"""Every cited domain must be in the publisher registry, and sources.json fresh.

Citations render as "Reuters · Reporting · 12 Jun 2026" rather than "[47]", which
only works while sources.py knows who each domain is. An unregistered one still
renders — it degrades to the bare hostname — which is exactly the kind of quiet
shabbiness that survives review forever unless something fails.

Fix a failure by adding the domain to sources.REGISTRY and re-running:
    python3 build_sources.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import build_sources  # noqa: E402
import sources  # noqa: E402

SOURCES_JSON = ROOT / "sources.json"


def main() -> int:
    urls = build_sources.collect()
    assert urls, "no source URLs found in the datasets"

    unregistered = sorted({
        sources.classify(u)["domain"] for u in urls if not sources.classify(u)["registered"]
    })
    assert not unregistered, (
        f"{len(unregistered)} cited domain(s) missing from sources.REGISTRY, so their "
        f"citations show a bare hostname: {unregistered}"
    )

    assert SOURCES_JSON.is_file(), "sources.json missing (run: python3 build_sources.py)"
    data = json.loads(SOURCES_JSON.read_text(encoding="utf-8"))
    entries = data["sources"]

    missing = sorted(set(urls) - set(entries))
    extra = sorted(set(entries) - set(urls))
    assert not missing, (
        f"{len(missing)} cited URL(s) absent from sources.json "
        f"(run: python3 build_sources.py): {missing[:5]}"
    )
    assert not extra, (
        f"{len(extra)} URL(s) in sources.json no longer cited "
        f"(run: python3 build_sources.py): {extra[:5]}"
    )

    for url, entry in entries.items():
        assert entry["kind"] in sources.KIND_LABEL, f"{url}: unknown kind {entry['kind']!r}"
        assert entry["publisher"], f"{url}: empty publisher"

    # Dates are read out of the URL and never guessed, so any that is present
    # must be a real ISO date that is not in the future.
    from datetime import date
    today = date.today().isoformat()
    for url, entry in entries.items():
        if not entry["date"]:
            continue
        assert len(entry["date"]) == 10 and entry["date"][4] == "-", f"{url}: bad date {entry['date']!r}"
        assert entry["date"] <= today, f"{url}: publication date {entry['date']} is in the future"

    dated = sum(1 for e in entries.values() if e["date"])
    print(f"ok: {len(entries)} sources, every domain registered, {dated} carry a URL-derived date")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
