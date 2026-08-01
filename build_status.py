#!/usr/bin/env python3
"""Give every row a stage and a coverage grade, and write both into the CSV.

"Age verification" and "partial" were doing too much work. A French law adopted
in July 2026 that bites in September 2026, a Chinese block that OONI has
measured every week for a decade, and a single news story saying a country has
started throttling something were all rendered identically. They are not the
same claim and the site should not pretend otherwise.

Two columns, appended to censorship_data.csv:

  status    scheduled  the rule exists but has not taken effect yet
            enforced   in effect, and a network measurement confirms it bites
            in_force   in effect, and an official instrument or the operator's
                       own notice establishes it
            reported   in effect according to reporting or NGO monitoring, with
                       no instrument or measurement behind it

  evidence  dedicated       the row cites a platform-specific source of its own
            country-default it rests on a country-wide fact rather than a
                            platform-specific one: either the default note for a
                            state that blocks nearly everything, or a country
                            article cited in place of a dedicated source
            uncorroborated  no source and no country default — an honest "we
                            list this but have not shown our working"

Both are derived, never invented: `status` from the date in `since` plus the
kind of the cited source (see sources.py), `evidence` from whether the row has
a source at all. They are written into the CSV rather than computed in the
browser so they are diffable, auditable and correctable by hand — an editor who
knows better can overwrite a cell and this script will leave it alone (pass
--force to re-derive everything).

The scheduled/active split is the one thing the pages recompute at render time,
because "is this date in the future?" goes stale on its own.

    python3 build_status.py [--force] [--check]
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import sources

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "censorship_data.csv"
SOURCES_PATH = ROOT / "sources.json"

FIELDS = ["platform", "country", "since", "type", "more_info", "source", "status", "evidence"]

STATUSES = ("scheduled", "enforced", "in_force", "reported")
EVIDENCE = ("dedicated", "country-default", "uncorroborated")

# States whose internet is restricted by default, so a row with no dedicated
# source still rests on something — the country-wide fact. Must stay identical
# to HEAVY_CENSORSHIP in index.html; tests/test_status_model.py enforces that.
COUNTRY_DEFAULT = {
    "People's Republic of China",
    "Eritrea",
    "North Korea",
    "Turkmenistan",
}

MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"], start=1)}


def parse_since(text: str) -> date | None:
    """Lenient read of the free-text `since` column.

    Mirrors parseSinceDate() in index.html: DD/MM/YYYY, "Month YYYY", bare
    year. Undated values ("Forever", "Longstanding", "Ongoing", "Unknown")
    return None, which reads as "in effect, start unknown" — never as scheduled.
    """
    text = (text or "").strip()
    if not text:
        return None
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None
    m = re.search(r"([A-Za-z]+)\s+((?:19|20)\d{2})", text)
    if m and m.group(1).lower() in MONTHS:
        return date(int(m.group(2)), MONTHS[m.group(1).lower()], 1)
    years = re.findall(r"(?:19|20)\d{2}", text)
    if years:
        return date(int(years[-1]), 1, 1)
    return None


def derive(row: dict, kinds: dict[str, str], today: date) -> tuple[str, str]:
    """(status, evidence) for one row."""
    url = (row.get("source") or "").strip()
    country = (row.get("country") or "").strip()
    kind = kinds.get(url, "")

    # A Wikipedia country article is a country-wide fallback wearing a link. It
    # says the state blocks nearly everything, not that it blocks this platform,
    # so grading it "dedicated" would flatter the row. README allows it only for
    # exactly those countries, and this is where that shows in the interface.
    if url and kind != "reference":
        evidence = "dedicated"
    elif url or country in COUNTRY_DEFAULT:
        evidence = "country-default"
    else:
        evidence = "uncorroborated"

    started = parse_since(row.get("since", ""))
    if started and started > today:
        return "scheduled", evidence

    if kind == "measurement":
        return "enforced", evidence
    if kind == "primary":
        return "in_force", evidence
    # research, reporting, reference and unsourced rows all sit at "reported":
    # credible, but nothing here shows the rule itself or the block in action.
    return "reported", evidence


def load_kinds() -> dict[str, str]:
    if not SOURCES_PATH.is_file():
        print(f"{SOURCES_PATH.name} missing — run: python3 build_sources.py", file=sys.stderr)
        raise SystemExit(1)
    data = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    return {url: entry["kind"] for url, entry in data["sources"].items()}


def main(argv: list[str]) -> int:
    force = "--force" in argv
    check = "--check" in argv
    kinds = load_kinds()
    today = date.today()

    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    changed = 0
    stale_scheduled = []
    status_counts: Counter[str] = Counter()
    evidence_counts: Counter[str] = Counter()

    for row in rows:
        status, evidence = derive(row, kinds, today)
        # A row hand-marked "scheduled" whose date has now passed is the one
        # case where a manual value must not survive: it is simply out of date.
        was = (row.get("status") or "").strip()
        if was == "scheduled" and status != "scheduled":
            stale_scheduled.append(f'{row["platform"]}/{row["country"]}')
        if force or not was or was not in STATUSES or was == "scheduled":
            if was != status:
                changed += 1
            row["status"] = status
        if force or (row.get("evidence") or "").strip() not in EVIDENCE:
            if (row.get("evidence") or "") != evidence:
                changed += 1
            row["evidence"] = evidence
        status_counts[row["status"]] += 1
        evidence_counts[row["evidence"]] += 1

    if check:
        print(f"{len(rows)} rows · " + " · ".join(f"{k} {v}" for k, v in status_counts.most_common()))
        print("           " + " · ".join(f"{k} {v}" for k, v in evidence_counts.most_common()))
        if changed:
            print(f"{changed} cell(s) would change — run: python3 build_status.py", file=sys.stderr)
            return 1
        print("status/evidence columns are up to date")
        return 0

    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"{CSV_PATH.name}: {len(rows)} rows, {changed} cell(s) updated")
    print("  status:   " + " · ".join(f"{k} {v}" for k, v in status_counts.most_common()))
    print("  evidence: " + " · ".join(f"{k} {v}" for k, v in evidence_counts.most_common()))
    if stale_scheduled:
        print(f"  {len(stale_scheduled)} row(s) came off 'scheduled' — their date has passed: "
              + ", ".join(stale_scheduled[:6])
              + (f" +{len(stale_scheduled) - 6} more" if len(stale_scheduled) > 6 else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
