#!/usr/bin/env python3
"""Write data.json — the dataset as one stable, documented artifact.

The CSV is the working format; this is the reuse format. Anyone building on
the tracker — a researcher, a journalist's graphics desk, another site —
should not have to parse our CSV conventions or guess which columns are
derived. data.json carries every row plus the ISO code and subnational flag
the site itself resolves, a schema version that only moves when a field
changes meaning, and the license inline, so the file explains itself wherever
it ends up.

Consume it from: https://censorship.my/data.json

    python3 build_data.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from country_registry import load_registry
from build_status import parse_since
from stable_write import write_json
from territories import load_rows

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data.json"

SCHEMA_VERSION = 1

FIELD_DOCS = {
    "platform": "Platform name as shown on the site.",
    "country": "Territory name as recorded — may be a state or disputed territory; see iso and subnational.",
    "iso": "ISO 3166-1 alpha-2 code of the (parent) country.",
    "subnational": "True when the row is a state-level or territorial measure, not a national one.",
    "since": "Free-text date the restriction started or takes effect.",
    "since_iso": "Derived from since: YYYY-MM-DD where the free-text date parses (month precision becomes the first of the month); empty when undated ('Ongoing', 'Forever', ...).",
    "type": "complete | partial | age (age-verification requirement).",
    "notes": "Case-file text, when the row has something platform-specific to say.",
    "source": "Cited URL. Empty for default-restricted countries with no platform-specific reporting (see the site's methodology).",
    "status": "Derived: scheduled | enforced | in_force | reported.",
    "evidence": "Derived: dedicated | country-default | uncorroborated.",
}

def main() -> int:
    registry = load_registry()
    entries = []
    for row in load_rows():
        info = registry.resolve(row["country"].strip()) or {}
        since_text = (row.get("since") or "").strip()
        parsed = parse_since(since_text)
        entries.append({
            "platform": row["platform"].strip(),
            "country": row["country"].strip(),
            "iso": info.get("iso", ""),
            "subnational": bool(info.get("subnational")),
            "since": since_text,
            "since_iso": parsed.isoformat() if parsed else "",
            "type": (row.get("type") or "complete").strip(),
            "notes": (row.get("more_info") or "").strip(),
            "source": (row.get("source") or "").strip(),
            "status": (row.get("status") or "").strip(),
            "evidence": (row.get("evidence") or "").strip(),
        })

    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "title": "Global Censorship Tracker",
        "site": "https://censorship.my",
        "repository": "https://github.com/vimal7890/Censorship-Tracker",
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "attribution": "Global Censorship Tracker, https://censorship.my",
        "fields": FIELD_DOCS,
        "count": len(entries),
        "entries": entries,
    }
    wrote = write_json(OUT, payload)
    print(f"{'wrote' if wrote else 'unchanged'} {OUT.name}: {len(entries)} entries, "
          f"schema v{SCHEMA_VERSION}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
