#!/usr/bin/env python3
"""Turn the git history of the datasets into a changelog and an RSS feed.

A censorship tracker that only ever shows the current state answers "what is
blocked?" but not "what changed?" — which is the question anyone following this
subject actually has. The answer already exists: every edit to the datasets is
a commit, with a date and a message. It just was not readable by anybody who
was not going to run `git log`.

This replays the three datasets (the main CSV plus the VPN and age-verification
JSON files) commit by commit and records, per commit, which rows were added,
removed, or had their date / notes / source changed. Output:

  changelog.json   what changes.html renders
  changelog-latest.json
                   a small slice of the same events for the homepage's
                   "what changed" panel, so visitors do not download the
                   whole history to read six lines
  feed.xml         RSS 2.0, one item per dated change, so the tracker can be
                   followed in a reader without an account or an email address
  feed/<slug>.xml  the same events filtered to one territory — "what changed
                   in Iran?" is the question a person actually following one
                   place has, and the global feed buries it

Rows are keyed on (platform, country, type), which is what makes an entry the
same entry across commits. A row that changes type — a partial block hardened
into a complete one — therefore shows as a removal plus an addition, which is
the honest reading: that is a different restriction, not an edited one.

The two JSON datasets are flattened into that same shape before diffing, under
pseudo-platform names ("VPNs", "Age verification") so one differ serves all
three files. Their prose fields are folded into `more_info`, so any material
edit registers as a revision even when it touches a field the main CSV does
not have.

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

from stable_write import write_json

ROOT = Path(__file__).resolve().parent
CSV_NAME = "censorship_data.csv"
# Every dataset whose history belongs in the changelog. A subscriber following
# the feed cares about the age-verification law moving too, not only about new
# blocks appearing in the main index.
DATASET_FILES = [CSV_NAME, "vpn_data.json", "age_verification_data.json"]
OUT_JSON = ROOT / "changelog.json"
OUT_LATEST = ROOT / "changelog-latest.json"
OUT_FEED = ROOT / "feed.xml"
FEED_DIR = ROOT / "feed"

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

# How many events the RSS feeds carry. Readers only surface the newest few, so
# this is generous headroom against silent truncation, not a display setting.
FEED_ITEM_CAP = 200


def git(*args: str) -> str:
    res = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return res.stdout if res.returncode == 0 else ""


def commits() -> list[dict]:
    """Every commit that touched any dataset file, oldest first."""
    out = git("log", "--reverse", "--format=%H%x1f%cI%x1f%an%x1f%s", "--", *DATASET_FILES)
    entries = []
    for line in out.splitlines():
        parts = line.split("\x1f")
        if len(parts) == 4:
            entries.append({"sha": parts[0], "iso": parts[1], "author": parts[2], "subject": parts[3]})
    return entries


def _clean(value) -> str:
    return (value or "").strip() if isinstance(value, str) else str(value or "").strip()


def fold_vpn(data: dict) -> dict:
    """Flatten vpn_data.json into the differ's (platform, country, type) shape.

    Restrictions become "VPNs" rows keyed by their severity; policy efforts
    carry their title inside `type` because jurisdiction alone is not an
    identity. `status` — which is where these entries keep their stage and,
    usually, their dates — maps onto `since`.
    """
    rows: dict[tuple[str, str, str], dict] = {}
    for r in data.get("restrictions", []):
        key = ("VPNs", _clean(r.get("country")), _clean(r.get("severity")) or "restricted")
        rows[key] = {"since": _clean(r.get("since")),
                     "more_info": _clean(r.get("summary")),
                     "source": _clean(r.get("source"))}
    for section, label in (("legislative_efforts", "bill"), ("rejected_efforts", "rejected bill")):
        for r in data.get(section, []):
            title = _clean(r.get("title"))
            key = ("VPNs", _clean(r.get("jurisdiction")), f"{label}: {title}" if title else label)
            rows[key] = {"since": _clean(r.get("status")),
                         "more_info": _clean(r.get("summary")),
                         "source": _clean(r.get("source"))}
    return rows


def fold_age(data: dict) -> dict:
    """Flatten age_verification_data.json into the differ's shape.

    Timeline laws are keyed by (country, law name); the prose fields that have
    no CSV equivalent (pass date, implementation label, threshold) are folded
    into `more_info` so editing any of them registers as a revision rather
    than slipping past a differ that only knows three fields.
    """
    rows: dict[tuple[str, str, str], dict] = {}
    for r in data.get("timeline", []):
        key = ("Age verification", _clean(r.get("country")), _clean(r.get("law")))
        prose = " · ".join(filter(None, (_clean(r.get("passed_label")),
                                         _clean(r.get("implementation_label")),
                                         _clean(r.get("threshold")),
                                         _clean(r.get("summary")))))
        rows[key] = {"since": _clean(r.get("implementation_date")),
                     "more_info": prose,
                     "source": _clean(r.get("source"))}
    for r in data.get("legislative_efforts", []):
        key = ("Age verification", _clean(r.get("country")), _clean(r.get("title")))
        rows[key] = {"since": _clean(r.get("status")),
                     "more_info": _clean(r.get("summary")),
                     "source": _clean(r.get("source"))}
    return rows


def snapshot(sha: str) -> dict[tuple[str, str, str], dict]:
    """All three datasets at one commit, keyed by (platform, country, type).

    A file that did not exist yet simply contributes no rows; history before
    the JSON datasets arrived stays exactly as informative as it was.
    """
    rows: dict[tuple[str, str, str], dict] = {}
    text = git("show", f"{sha}:{CSV_NAME}")
    for row in csv.DictReader(io.StringIO(text)):
        platform = (row.get("platform") or "").strip()
        country = (row.get("country") or "").strip()
        if not platform or not country:
            continue
        key = (platform, country, (row.get("type") or "complete").strip())
        rows[key] = {f: (row.get(f) or "").strip() for f in TRACKED}
    for name, folder in (("vpn_data.json", fold_vpn), ("age_verification_data.json", fold_age)):
        blob = git("show", f"{sha}:{name}")
        if blob.strip():
            try:
                rows.update(folder(json.loads(blob)))
            except json.JSONDecodeError:
                pass  # a commit that left the file unparseable contributes nothing
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
    # The key includes type: two rows can differ only by it (X — Malaysia has
    # both a partial and an age row), and a (country, platform) sort leaves
    # their order to set-iteration luck, which flips run to run and makes the
    # build check see phantom changes.
    sort = lambda items: sorted(items, key=lambda e: (
        e["country"].lower(), e["platform"].lower(), e.get("type", "")))
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


def feed_xml(*, title: str, link: str, self_href: str, description: str,
             events: list[dict], build_date: datetime) -> str:
    items = []
    for event in events[:FEED_ITEM_CAP]:
        permalink = f"{SITE}/changes#{event['id']}"
        try:
            when = datetime.fromisoformat(event["iso"])
        except ValueError:
            when = build_date
        items.append(
            "    <item>\n"
            f"      <title>{escape(event['subject'])}</title>\n"
            f"      <link>{escape(permalink)}</link>\n"
            f"      <guid isPermaLink=\"false\">{event['sha']}</guid>\n"
            f"      <pubDate>{format_datetime(when)}</pubDate>\n"
            f"      <description>{escape(item_body(event))}</description>\n"
            "    </item>")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        "  <channel>\n"
        f"    <title>{escape(title)}</title>\n"
        f"    <link>{escape(link)}</link>\n"
        f"    <description>{escape(description)}</description>\n"
        "    <language>en</language>\n"
        f"    <lastBuildDate>{format_datetime(build_date)}</lastBuildDate>\n"
        f'    <atom:link href="{escape(self_href)}" rel="self" type="application/rss+xml"/>\n'
        + "\n".join(items) + "\n"
        "  </channel>\n"
        "</rss>\n")


def write_feed(events: list[dict]) -> None:
    OUT_FEED.write_text(
        feed_xml(title=FEED_TITLE, link=f"{SITE}/changes",
                 self_href=f"{SITE}/feed.xml", description=FEED_DESC,
                 events=events, build_date=datetime.now(timezone.utc)),
        encoding="utf-8")


def country_rename_chain(events: list[dict]) -> dict[str, str]:
    """old country name -> the name that replaced it, from the events themselves.

    The registry only knows current names, but the feed filter below has to
    place "Kingdom of Saudi Arabia" rows from 2026 history under today's
    Saudi Arabia. The changelog already extracts country renames explicitly,
    so the chain is derived from the same events rather than hand-typed.
    """
    chain: dict[str, str] = {}
    for event in reversed(events):  # oldest first
        for entry in event.get("renamed", []):
            if entry.get("renamed") == "country":
                chain[entry["was"]] = entry["country"]
    return chain


def follow(name: str, chain: dict[str, str]) -> str:
    seen = set()
    while name in chain and name not in seen:
        seen.add(name)
        name = chain[name]
    return name


def write_territory_feeds(events: list[dict]) -> tuple[int, int]:
    """One filtered feed per territory, feed/<slug>.xml. -> (written, kept).

    Content is deterministic — lastBuildDate is the newest included event, not
    now() — so an unchanged territory keeps a byte-identical feed and the
    build check stays quiet. Feeds for territories that left the dataset are
    deleted; a stale feed asserting "nothing since June" would be a claim
    nobody is maintaining.
    """
    from territories import group_by_territory, load_rows
    from country_registry import load_registry

    registry = load_registry()
    chain = country_rename_chain(events)

    def iso_of(country: str) -> str:
        info = registry.resolve(follow(country, chain))
        return info["iso"] if info else ""

    groups = group_by_territory(load_rows())
    FEED_DIR.mkdir(exist_ok=True)
    expected: set[Path] = set()
    written = kept = 0
    for group in groups.values():
        iso = group["iso"]
        filtered_events = []
        for event in events:
            parts = {}
            for kind in ("added", "removed", "changed", "renamed"):
                parts[kind] = [r for r in event[kind]
                               if iso_of(r["country"]) == iso
                               or (r.get("renamed") == "country"
                                   and iso_of(r["was"]) == iso)]
            total = sum(len(v) for v in parts.values())
            if total:
                filtered_events.append({**event, **parts, "total": total})
        if not filtered_events:
            continue
        target = FEED_DIR / f"{group['slug']}.xml"
        expected.add(target)
        try:
            newest = datetime.fromisoformat(filtered_events[0]["iso"])
        except ValueError:
            newest = datetime.now(timezone.utc)
        name = group["display"]
        xml = feed_xml(
            title=f"Global Censorship Tracker — what changed in {name}",
            link=f"{SITE}/country/{group['slug']}/",
            self_href=f"{SITE}/feed/{group['slug']}.xml",
            description=(f"Every addition, removal and revision to the tracked "
                         f"restrictions in {name}, straight from the dataset's history."),
            events=filtered_events, build_date=newest)
        if target.is_file() and target.read_text(encoding="utf-8") == xml:
            kept += 1
            continue
        target.write_text(xml, encoding="utf-8")
        written += 1
    for stale in FEED_DIR.glob("*.xml"):
        if stale not in expected:
            stale.unlink()
    return written, kept


def latest_slice(events: list[dict], keep: int = 10) -> dict:
    """The homepage-sized projection: newest few events, counts only.

    The full changelog.json passed 260 KB because every event carries every
    touched row's prose. The homepage panel needs none of that — a subject, a
    date and how many rows moved — so it gets a file of its own rather than
    asking every visitor to download the archive.
    """
    slim = []
    for event in events[:keep]:
        slim.append({
            "id": event["id"],
            "date": event["date"],
            "subject": event["subject"],
            "total": event["total"],
            "added": len(event["added"]),
            "removed": len(event["removed"]),
            "changed": len(event["changed"]),
            "renamed": len(event["renamed"]),
        })
    return {
        "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "count": len(events),
        "latest": events[0]["date"] if events else "",
        "events": slim,
    }


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

    wrote = write_json(OUT_JSON, {
        "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "count": len(events),
        "latest": events[0]["date"],
        "events": events,
    })
    # The slice is derived from the same events; rewrite it under the same
    # condition so the two files never disagree about what happened.
    wrote_slice = write_json(OUT_LATEST, latest_slice(events))
    # The feed is a projection of the same events, so it only needs rewriting
    # when they changed — its lastBuildDate would otherwise be the sole diff.
    if wrote or wrote_slice or not OUT_FEED.is_file():
        write_feed(events)
    fw, fk = write_territory_feeds(events)

    rows = sum(e["total"] for e in events)
    print(f"{'wrote' if wrote else 'unchanged'} {OUT_JSON.name} and {OUT_FEED.name}: "
          f"{len(events)} dated changes covering {rows} row edits")
    print(f"{'wrote' if wrote_slice else 'unchanged'} {OUT_LATEST.name}: "
          f"newest {len(latest_slice(events)['events'])} event(s) as counts")
    print(f"feed/: {fw + fk} territory feeds ({fw} written, {fk} unchanged)")
    print(f"  newest: {events[0]['date']} — {events[0]['subject']} ({summarise(events[0])})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
