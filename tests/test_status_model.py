#!/usr/bin/env python3
"""The status/evidence columns must be present, valid and in step with the data.

Two ways this silently rots:

  1. Someone adds a CSV row by hand and leaves status/evidence blank, so the
     entry renders with no stage and no coverage grade while looking fine.
  2. A row marked "scheduled" reaches its date and nobody re-runs the build, so
     the site keeps calling a live restriction "not yet biting". The pages
     recompute that at render time, but the file should not stay wrong.

Also pins the country-default list to the copy in index.html: build_status.py
grades a sourceless row as resting on a country-wide fact only for the states
that block nearly everything, and the two lists disagreeing would mean the CSV
and the page tell different stories about the same row.

Fix a failure by running:  python3 build_status.py
"""
from __future__ import annotations

import csv
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import build_status  # noqa: E402

CSV_PATH = ROOT / "censorship_data.csv"
INDEX = ROOT / "index.html"


def heavy_censorship_from_index() -> set[str]:
    """The HEAVY_CENSORSHIP keys as index.html actually declares them."""
    text = INDEX.read_text(encoding="utf-8")
    block = re.search(r"const HEAVY_CENSORSHIP = \{(.*?)\n        \};", text, re.S)
    assert block, "HEAVY_CENSORSHIP not found in index.html"
    # Keys are JS string literals that may contain escaped quotes
    # (People's Republic of China's "Great Firewall").
    return set(re.findall(r'^\s{12}"((?:[^"\\]|\\.)*)":', block.group(1), re.M))


def main() -> int:
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        rows = list(reader)

    assert fields == build_status.FIELDS, (
        f"CSV header is {fields}, expected {build_status.FIELDS} "
        "(run: python3 build_status.py)"
    )

    today = date.today()
    for i, row in enumerate(rows, start=2):
        where = f'row {i} ({row["platform"]}/{row["country"]})'
        assert row["status"] in build_status.STATUSES, f"{where}: bad status {row['status']!r}"
        assert row["evidence"] in build_status.EVIDENCE, f"{where}: bad evidence {row['evidence']!r}"

        started = build_status.parse_since(row["since"])
        if row["status"] == "scheduled":
            assert started and started > today, (
                f"{where}: marked scheduled but its date ({row['since']!r}) has arrived "
                "(run: python3 build_status.py)")
        elif started and started > today:
            assert False, (
                f"{where}: dated {row['since']!r} in the future but not marked scheduled "
                "(run: python3 build_status.py)")

        if not row["source"].strip():
            expected = ("country-default" if row["country"] in build_status.COUNTRY_DEFAULT
                        else "uncorroborated")
            assert row["evidence"] == expected, (
                f"{where}: has no source, so evidence should be {expected!r}, "
                f"not {row['evidence']!r}")

    assert build_status.COUNTRY_DEFAULT == heavy_censorship_from_index(), (
        "build_status.COUNTRY_DEFAULT and index.html's HEAVY_CENSORSHIP disagree: "
        f"{build_status.COUNTRY_DEFAULT ^ heavy_censorship_from_index()}"
    )

    scheduled = sum(1 for r in rows if r["status"] == "scheduled")
    thin = sum(1 for r in rows if r["evidence"] == "uncorroborated")
    print(f"ok: {len(rows)} rows carry a valid status and coverage grade "
          f"({scheduled} scheduled, {thin} needing a source)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
