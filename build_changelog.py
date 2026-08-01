#!/usr/bin/env python3
"""Turn the git history of the dataset into a changelog and an RSS feed.

A censorship tracker that only ever shows the current state answers "what is
blocked?" but not "what changed?" — which is the question anyone following this
subject actually has. The answer already exists: every edit to
censorship_data.csv is a commit, with a date and a message. It just was not
readable by anybody who was not going to run `git log`.

This replays the CSV commit by commit and records, per commit, which rows were
added, removed, or had their date / notes / source changed. Output:

  changelog.json   what changes.html renders
  feed.xml         RSS 2.0, one item per dated change, so the tracker can be
                   followed in a reader without an account or an email address

Rows are keyed on (platform, country, type), which is what makes an entry the
same entry across commits. A row that changes type — a partial block hardened
into a complete one — therefore shows as a removal plus an addition, which is
the honest reading: that is a different restriction, not an edited one.

Renames are pulled back out of that churn, but only when it can be done without
guessing. This repo's history is full of them ("Turkey" to "Türkiye", "China" to
"People's Republic of China"), and left alone they read as 39 restrictions
appearing and 39 vanishing on the same day — alarming, and false. A removal and
an addition in the same commit are folded into one rename when every other field
matches byte for byte and the pairing is unambiguous. Anything short of that
stays reported as a removal and an addition, because a wrong pairing would
misreport a real change as cosmetic.

    python3 build_changelog.py [--limit N]
"""
from __future__ import annotations

import csv
import io
import json
import subprocess
import sys
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent
CSV_NAME = "censorship_data.csv"
OUT_JSON = ROOT / "changelog.json"
OUT_FEED = ROOT / "feed.xml"

SITE = "https://censorship.my"
FEED_TITLE = "Global Censorship Tracker — what changed"
FEED_DESC = ("Every addition, removal and revision to the tracked index of blocked, "
             "restricted and age-gated platforms, straight from the dataset's history.")

# Fields worth reporting a change in. `status` and `evidence` are derived by
# build_status.py, so they flip on their own — a scheduled restriction taking
# effect is real news, but it is not an editorial change and would otherwise
# swamp the feed on the day the script is re-run.
TRACKED = ("since", "more_info", "source")
FIELD_LABEL = {"since": "date", "more_info": "notes", "source": "source"}


def git(*args: str) -> str:
    res = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return res.stdout if res.returncode == 0 else ""


def commits() -> list[dict]:
    """Every commit that touched the CSV, oldest first."""
    out = git("log", "--reverse", "--format=%H%x1f%cI%x1f%an%x1f%s", "--", CSV_NAME)
    entries = []
    for line in out.splitlines():
        parts = line.split("\x1f")
        if len(parts) == 4:
            entries.append({"sha": parts[0], "iso": parts[1], "author": parts[2], "subject": parts[3]})
    return entries


def snapshot(sha: str) -> dict[tuple[str, str, str], dict]:
    """The CSV at one commit, keyed by (platform, country, type)."""
    text = git("show", f"{sha}:{CSV_NAME}")
    rows: dict[tuple[str, str, str], dict] = {}
    for row in csv.DictReader(io.StringIO(text)):
        platform = (row.get("platform") or "").strip()
        country = (row.get("country") or "").strip()
        if not platform or not country:
            continue
        key = (platform, country, (row.get("type") or "complete").strip())
        rows[key] = {f: (row.get(f) or "").strip() for f in TRACKED}
    return rows


def describe(key: tuple[str, str, str], row: dict) -> dict:
    platform, country, btype = key
    return {"platform": platform, "country": country, "type": btype,
            "since": row.get("since", "")}


def _pair_on(added: set, removed: set, before: dict, after: dict,
             fields: tuple[str, ...]) -> list[dict]:
    """One rename-matching pass over the leftovers, on the given fields.

    A removal and an addition pair when they differ in exactly one of platform
    or country and agree on `fields`. A signature matching more than one row on
    either side is skipped: ambiguity here would mean inventing a
    correspondence, and reporting a rename where a restriction was actually
    lifted is a worse error than some churn. Mutates the two key sets.
    """
    renames: list[dict] = []
    for field, index in (("country", 1), ("platform", 0)):
        def signature(key, row):
            rest = tuple(v for i, v in enumerate(key) if i != index)
            return rest + tuple(row[f] for f in fields)

        gone: dict = {}
        for key in removed:
            gone.setdefault(signature(key, before[key]), []).append(key)
        new: dict = {}
        for key in added:
            new.setdefault(signature(key, after[key]), []).append(key)

        for sig, old_keys in gone.items():
            new_keys = new.get(sig, [])
            if len(old_keys) != 1 or len(new_keys) != 1:
                continue
            old_key, new_key = old_keys[0], new_keys[0]
            if old_key[index] == new_key[index]:
                continue
            entry = describe(new_key, after[new_key])
            entry["renamed"] = field
            entry["was"] = old_key[index]
            if before[old_key]["more_info"] != after[new_key]["more_info"]:
                entry["fields"] = ["notes"]
            renames.append(entry)
            removed.discard(old_key)
            added.discard(new_key)
    return renames


def extract_renames(added: set, removed: set, before: dict, after: dict) -> list[dict]:
    """Fold same-commit removal/addition pairs back into renames.

    Two passes, strictest first. The first demands every field match byte for
    byte. The second retries only what is left over while ignoring `more_info`,
    because a country rename usually rewrites the prose that names the country
    too ("China's Great Firewall…" became "People's Republic of China's…"), and
    a rename that also touched the notes is still a rename. Both passes require
    a unique match, so relaxing the signature widens what can be recognised
    without ever letting an ambiguous pair through.
    """
    renames = _pair_on(added, removed, before, after, TRACKED)
    renames += _pair_on(added, removed, before, after,
                        tuple(f for f in TRACKED if f != "more_info"))
    return renames


def diff(before: dict, after: dict) -> dict:
    added_keys = set(after) - set(before)
    removed_keys = set(before) - set(after)
    renamed = extract_renames(added_keys, removed_keys, before, after)

    added = [describe(k, after[k]) for k in added_keys]
    removed = [describe(k, before[k]) for k in removed_keys]
    changed = []
    for key in before.keys() & after.keys():
        fields = [f for f in TRACKED if before[key][f] != after[key][f]]
        if not fields:
            continue
        entry = describe(key, after[key])
        entry["fields"] = [FIELD_LABEL[f] for f in fields]
        # Carry the old and new date only — a full before/after of the notes
        # would make every card a wall of text.
        if "since" in fields:
            entry["since_was"] = before[key]["since"]
        changed.append(entry)
    sort = lambda items: sorted(items, key=lambda e: (e["country"].lower(), e["platform"].lower()))
    return {"added": sort(added), "removed": sort(removed),
            "changed": sort(changed), "renamed": sort(renamed)}


def build() -> list[dict]:
    history = commits()
    if not history:
        return []
    events: list[dict] = []
    before: dict = {}
    for entry in history:
        after = snapshot(entry["sha"])
        delta = diff(before, after)
        before = after
        total = sum(len(delta[k]) for k in ("added", "removed", "changed", "renamed"))
        if not total:
            continue  # a commit that reformatted the file, not the data
        events.append({
            "id": entry["sha"][:10],
            "sha": entry["sha"],
            "date": entry["iso"][:10],
            "iso": entry["iso"],
            "subject": entry["subject"],
            "author": entry["author"],
            "total": total,
            **delta,
        })
    events.reverse()  # newest first, which is how anyone reads a changelog
    return events


def summarise(event: dict) -> str:
    bits = []
    for kind in ("added", "removed", "changed", "renamed"):
        n = len(event[kind])
        if n:
            bits.append(f"{n} {kind}")
    return ", ".join(bits)


def item_body(event: dict) -> str:
    lines = [f"<p>{escape(summarise(event))}.</p>"]
    for kind, verb in (("added", "Added"), ("removed", "Removed"),
                       ("changed", "Revised"), ("renamed", "Renamed")):
        rows = event[kind]
        if not rows:
            continue
        listed = "".join(
            "<li>{} — {} ({}){}</li>".format(
                escape(r["platform"]), escape(r["country"]), escape(r["type"]),
                ": " + escape(", ".join(r["fields"])) if r.get("fields")
                else (" — was " + escape(r["was"]) if r.get("was") else ""))
            for r in rows[:40])
        more = f"<li>+{len(rows) - 40} more</li>" if len(rows) > 40 else ""
        lines.append(f"<p><b>{verb}</b></p><ul>{listed}{more}</ul>")
    return "".join(lines)


def write_feed(events: list[dict]) -> None:
    now = datetime.now(timezone.utc)
    items = []
    for event in events[:60]:
        link = f"{SITE}/changes#{event['id']}"
        try:
            when = datetime.fromisoformat(event["iso"])
        except ValueError:
            when = now
        items.append(
            "    <item>\n"
            f"      <title>{escape(event['subject'])}</title>\n"
            f"      <link>{escape(link)}</link>\n"
            f"      <guid isPermaLink=\"false\">{event['sha']}</guid>\n"
            f"      <pubDate>{format_datetime(when)}</pubDate>\n"
            f"      <description>{escape(item_body(event))}</description>\n"
            "    </item>")
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        "  <channel>\n"
        f"    <title>{escape(FEED_TITLE)}</title>\n"
        f"    <link>{SITE}/changes</link>\n"
        f"    <description>{escape(FEED_DESC)}</description>\n"
        "    <language>en</language>\n"
        f"    <lastBuildDate>{format_datetime(now)}</lastBuildDate>\n"
        f'    <atom:link href="{SITE}/feed.xml" rel="self" type="application/rss+xml"/>\n'
        + "\n".join(items) + "\n"
        "  </channel>\n"
        "</rss>\n")
    OUT_FEED.write_text(xml, encoding="utf-8")


def main(argv: list[str]) -> int:
    limit = 0
    if "--limit" in argv:
        limit = int(argv[argv.index("--limit") + 1])

    events = build()
    if not events:
        print("no dataset history found — is this a git checkout?", file=sys.stderr)
        return 1
    if limit:
        events = events[:limit]

    OUT_JSON.write_text(json.dumps({
        "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "count": len(events),
        "latest": events[0]["date"],
        "events": events,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_feed(events)

    rows = sum(e["total"] for e in events)
    print(f"wrote {OUT_JSON.name} and {OUT_FEED.name}: "
          f"{len(events)} dated changes covering {rows} row edits")
    print(f"  newest: {events[0]['date']} — {events[0]['subject']} ({summarise(events[0])})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
