#!/usr/bin/env python3
"""Write meta.json — the one place the site learns how fresh it is.

All three pages used to carry the string "Data As Of: JUL 2026", typed by hand
into three files. It had already drifted from verified.json, which said the
sources were last checked on 26 July. A freshness claim that nobody updates is
worse than none: it is the one number a reference site cannot be casually wrong
about.

So nothing states a date any more. This derives them:

  data_updated     when the underlying data last actually changed — the newest
                   commit touching any dataset file, or today when a dataset has
                   uncommitted edits (the working tree is the truth then)
  sources_checked  when verify_links.py last confirmed every URL resolves,
                   read straight out of verified.json

They are different questions and the pages now show them as two separate lines,
because "we edited the data" and "we re-opened every citation" are different
promises.

Also carries the dataset counts and the status/evidence breakdown, so the
coverage panel does not have to recount 454 rows in the browser to say what
share of the index rests on a dedicated source.

Regenerate after any data change:  python3 build_meta.py
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from stable_write import write_json

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "censorship_data.csv"
VPN_PATH = ROOT / "vpn_data.json"
AGE_PATH = ROOT / "age_verification_data.json"
VERIFIED_PATH = ROOT / "verified.json"
OUT = ROOT / "meta.json"

DATA_FILES = [CSV_PATH, VPN_PATH, AGE_PATH]


def git(*args: str) -> str:
    try:
        res = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                             text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return ""
    return res.stdout.strip() if res.returncode == 0 else ""


def last_changed(path: Path) -> str:
    """ISO date this dataset last changed, from git — or today if it is dirty.

    Falls back to the file's mtime outside a git checkout (a deploy that only
    ships the files, for instance), so this never returns nothing.
    """
    if not path.is_file():
        return ""
    if git("status", "--porcelain", "--", path.name):
        return datetime.now().date().isoformat()
    committed = git("log", "-1", "--format=%cs", "--", path.name)
    if committed:
        return committed
    return datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()


def csv_summary() -> dict:
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    types: Counter[str] = Counter()
    status: Counter[str] = Counter()
    evidence: Counter[str] = Counter()
    for row in rows:
        types[(row.get("type") or "complete").strip()] += 1
        if row.get("status"):
            status[row["status"].strip()] += 1
        if row.get("evidence"):
            evidence[row["evidence"].strip()] += 1
    return {
        "entries": len(rows),
        "platforms": len({r["platform"] for r in rows if r.get("platform")}),
        "territories": len({r["country"] for r in rows if r.get("country")}),
        "by_type": dict(types),
        "by_status": dict(status),
        "by_evidence": dict(evidence),
    }


def json_len(path: Path, *keys: str) -> dict:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {k: len(data.get(k, [])) for k in keys}


def main() -> int:
    verified = {}
    if VERIFIED_PATH.is_file():
        try:
            verified = json.loads(VERIFIED_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            verified = {}

    dataset_dates = {p.name: last_changed(p) for p in DATA_FILES}
    payload = {
        "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        # The freshest of the three: a visitor asking "how current is this site?"
        # means the site, not whichever file they happen to be looking at.
        "data_updated": max((d for d in dataset_dates.values() if d), default=""),
        "dataset_updated": dataset_dates,
        "sources_checked": verified.get("date", ""),
        "sources_count": verified.get("sources", 0),
        "censorship": csv_summary(),
        "vpn": json_len(VPN_PATH, "restrictions", "legislative_efforts", "rejected_efforts"),
        "age_verification": json_len(AGE_PATH, "timeline", "legislative_efforts"),
    }
    wrote = write_json(OUT, payload)

    print(f"{'wrote' if wrote else 'unchanged'} {OUT.name}")
    print(f"  data updated:    {payload['data_updated'] or '(unknown)'}")
    print(f"  sources checked: {payload['sources_checked'] or '(never — run verify_links.py)'}")
    for name, when in dataset_dates.items():
        print(f"    {name}: {when or '(missing)'}")
    if payload["sources_checked"] and payload["data_updated"] > payload["sources_checked"]:
        print("  note: data has changed since the last link check — "
              "run verify_links.py so the citation date catches up")
    return 0


if __name__ == "__main__":
    sys.exit(main())
