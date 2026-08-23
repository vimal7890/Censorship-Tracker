#!/usr/bin/env python3
"""Check every source URL in the tracker data.

Reports three classes of problem:

  dead        the URL does not resolve, so the claim cannot be checked
  wikipedia   banned as a source by README.md
  placeholder a search-engine URL left behind by a link-fixing script

Run it after editing sources:  python3 verify_links.py

A note on why this does what it does. An earlier attempt at link fixing used
`curl -I` (HEAD), which many CDNs answer with 403 or 405 even when the page is
fine, and treated those as dead. It then "repaired" the false positives by
substituting the first DuckDuckGo or Wikipedia hit for keywords guessed from
the URL slug, which silently replaced good citations with unrelated pages. So:
issue a real GET, follow redirects, send a browser User-Agent, and treat the
bot-protection codes as alive. A source that cannot be verified automatically
needs a human to look at it — never auto-replace one.

Since it already downloads every page, this also records each one's <title> into
sources.json, so citations can be shown as a real headline rather than a
footnote number. Titles are only ever taken from the page itself — never derived
from a URL slug — so a page that will not serve us simply keeps an empty title
and the card falls back to publisher and date.

"Will not serve us" has to include the pages that answer 200 with a challenge
instead of an article. A Cloudflare interstitial is a successful request whose
title is "Just a moment...", and storing that would put the CDN's furniture on a
citation card under the byline of a real publisher. CHALLENGE_TITLES below is
the list of titles that are not headlines; they are dropped on the way in, and
any that an earlier run already stored are cleared on the way out.

Since the check already reaches every live URL once a week, it also makes sure
each one has an Internet Archive snapshot taken while the page still exists —
so that when a citation later dies, the evidence does not die with it. See
WAYBACK below for the rules; the headline one is that a stored snapshot is only
ever one the Archive itself confirmed, never an assumption that a save request
worked, and archive trouble never fails the pass.
"""
from __future__ import annotations

import csv
import html
import json
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timezone, datetime
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "censorship_data.csv"
JSON_PATHS = [ROOT / "vpn_data.json", ROOT / "age_verification_data.json"]
# Citation cards (publisher, kind, date, title) — see build_sources.py.
SOURCES_PATH = ROOT / "sources.json"
# Written only on a fully clean pass, so its mere presence means "every source
# resolved and none tripped the Wikipedia/placeholder rules on this date". The
# homepage reads it to show visitors when the citations were last checked live.
VERIFIED_PATH = ROOT / "verified.json"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# Bot protection, rate limiting and "no HEAD please" all mean the page exists.
# 406 is in here because Time and Newsweek answer scripted requests with it:
# time.com/4642916 returns 406 to curl but has a Wayback snapshot from November
# 2025, so treating it as dead would resurrect exactly the false positives that
# caused the bad substitutions in the first place.
ALIVE = {"200", "301", "302", "303", "307", "308", "401", "403", "406", "429"}

# Codes that mean "ask again", not "this page is gone". Cloudflare answers 52x
# when it cannot reach the origin, and "000" is curl giving up on a slow DNS
# lookup or TLS handshake. journalismpakistan.com returned 522, 522, then 200 to
# three identical requests, which is the whole problem: one unlucky GET would
# have reported a live citation as dead, and a dead report is what invites
# somebody to "repair" a perfectly good source with a search hit. Retrying costs
# a couple of seconds on a run that already takes a minute.
TRANSIENT = {"000", "408", "425", "500", "502", "503", "504", "522", "523", "524"}
RETRIES = 2

# Wikipedia stays banned as a source, with one carve-out. In the countries
# whose internet is restricted by default there is often no platform-specific
# reporting to cite at all: nobody writes "Tumblr is blocked in Turkmenistan",
# they write that almost everything is. For those rows the country-level
# Wikipedia article is the agreed last resort, better than the homepage links
# and catch-all reports it replaced. Everywhere else a Wikipedia citation is
# still a defect, and a row whose platform *is* Wikipedia may cite it freely
# (see README.md).
WIKI_EXEMPT_COUNTRIES = {"People's Republic of China", "Eritrea", "Islamic Republic of Iran", "North Korea", "Turkmenistan"}


def collect() -> dict[str, list[str]]:
    """Map each source URL to the rows that cite it."""
    where: dict[str, list[str]] = {}
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            url = (row.get("source") or "").strip()
            if url.startswith("http"):
                where.setdefault(url, []).append(f'{row["platform"]}/{row["country"]}')
    for path in JSON_PATHS:
        if not path.is_file():
            continue
        for url in re.findall(r'"(https?://[^"]+)"', path.read_text(encoding="utf-8")):
            where.setdefault(url, []).append(path.name)
    return where


def wiki_allowed(url: str, rows: list[str]) -> bool:
    """True when every row citing this Wikipedia URL is entitled to one.

    `rows` holds "Platform/Country" for CSV citations, so the country is
    recoverable. Entries from the JSON files are bare filenames with no
    country in them; those are never exempt, which is why the split below
    has to actually find a slash.
    """
    for row in rows:
        platform, _, country = row.partition("/")
        if not country:
            return False
        if platform == "Wikipedia":
            continue
        if country not in WIKI_EXEMPT_COUNTRIES:
            return False
    return True


TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")

# Titles that are the CDN's furniture rather than the page's headline.
#
# The bot-protection codes are treated as alive on purpose (see ALIVE above),
# but the interstitials that answer 200 slip past that entirely: the status says
# the page is fine and the <title> says "Just a moment...". Recording that as a
# headline would be inventing a citation out of a Cloudflare challenge, which is
# the failure mode this whole script exists to prevent. Same for the "page not
# found" bodies served with a 200 that README.md warns about.
#
# Matched against the *whole* title, never as substrings. This is a censorship
# tracker: "Access Denied" and "captcha" are things real headlines say here, and
# a story called "Access Denied: Internet Shutdowns in 2025 | Access Now" must
# survive. A challenge page's title is the entire title and carries no publisher
# suffix, so equality is both sufficient and much safer than containment.
CHALLENGE_TITLES = {
    "just a moment",
    "one moment please",
    "attention required",
    "checking your browser",
    "checking your browser before accessing",
    "checking if the site connection is secure",
    "security checkpoint",
    "vercel security checkpoint",
    "access denied",
    "access to this page has been denied",
    "forbidden",
    "403 forbidden",
    "you have been blocked",
    "request blocked",
    "too many requests",
    "rate limited",
    "are you a robot",
    "are you a human",
    "verify you are human",
    "verifying you are human",
    "human verification",
    "bot verification",
    "captcha",
    "captcha challenge",
    "please enable javascript",
    "please enable cookies",
    "javascript is required",
    "javascript is disabled",
    "page not found",
    "404 not found",
    "404 page not found",
    "not found",
    "error",
    "site unavailable",
    "service unavailable",
}

# Bot-protection vendors brand their interstitials ("Attention Required! |
# Cloudflare"). Stripping a trailing vendor name lets the phrase in front be
# matched on its own. Only these names are stripped — none of them is a
# publisher this dataset cites, so no real citation can lose its suffix here.
VENDOR_SUFFIX_RE = re.compile(
    r"\s*[|·:—–-]\s*(cloudflare|vercel|incapsula|imperva|akamai|fastly|sucuri|datadome)\s*$",
    re.I)


def is_challenge_title(title: str) -> bool:
    """True when a <title> is a challenge/error page rather than a headline."""
    text = re.sub(r"\s+", " ", (title or "")).strip()
    text = VENDOR_SUFFIX_RE.sub("", text)
    # Trailing ellipses and punctuation are decoration on these pages
    # ("Just a moment...", "Are you a robot?"), never meaning.
    return text.strip(" .!?…").lower() in CHALLENGE_TITLES


def clean_title(raw: str) -> str:
    """Collapse a raw <title> into one readable line.

    Kept deliberately dumb: unescape entities, strip any stray markup, squash
    whitespace, cap the length. No attempt to strip site-name suffixes — "…|
    Reuters" is honest, and guessing at which half is the headline is how you
    end up mangling titles that legitimately contain a pipe or a dash.
    """
    text = html.unescape(TAG_RE.sub(" ", raw))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:180]


def fetch(url: str) -> tuple[str, str]:
    """(HTTP status code, page title), retrying while the failure looks transient."""
    code, title = "000", ""
    for attempt in range(RETRIES + 1):
        code, title = fetch_once(url)
        if code not in TRANSIENT:
            break
        if attempt < RETRIES:
            time.sleep(1 + attempt)
    return code, title


def fetch_once(url: str) -> tuple[str, str]:
    """One GET. (HTTP status code, page title); title is "" when unreadable."""
    try:
        res = subprocess.run(
            ["curl", "-s", "-w", "\n%{http_code}", "-L",
             "--max-time", "25", "-A", UA, url],
            capture_output=True, text=True, timeout=40, errors="replace")
    except Exception:
        return "000", ""
    body, _, code = res.stdout.rpartition("\n")
    code = code.strip() or "000"
    m = TITLE_RE.search(body)
    title = clean_title(m.group(1)) if m else ""
    # A challenge page is "cannot be read" as far as titles go, so it falls back
    # to the documented empty title rather than becoming a fake headline.
    return code, "" if is_challenge_title(title) else title


def write_sources(titles: dict[str, str], snapshots: dict[str, dict] | None = None) -> None:
    """Merge freshly fetched titles and confirmed snapshots into sources.json.

    build_sources.py owns the file's shape; this only fills the fields that
    need a live fetch. A page that answered without a usable title keeps
    whatever title was recorded before rather than being blanked, so one bad
    day for a CDN does not erase good data. The same carry-forward rule covers
    snapshots: this script only ever overwrites them with a *newer* confirmed
    snapshot, never with nothing.

    The one thing that *is* blanked is a stored challenge-page title, which
    earlier runs of this script recorded before they knew to reject them. Only
    known-bad values are cleared, so the rule above still holds: this erases a
    CDN's furniture, never a headline.
    """
    if not SOURCES_PATH.is_file():
        print(f"note: {SOURCES_PATH.name} missing — run build_sources.py to create it")
        return
    payload = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    entries = payload.get("sources", {})
    added = 0
    cleared = 0
    for entry in entries.values():
        if is_challenge_title(entry.get("title") or ""):
            entry["title"] = ""
            cleared += 1
    for url, title in titles.items():
        entry = entries.get(url)
        if entry is None or not title or entry.get("title") == title:
            continue
        entry["title"] = title
        added += 1
    snapshotted = 0
    for url, snap in (snapshots or {}).items():
        entry = entries.get(url)
        if entry is None or not snap.get("snapshot"):
            continue
        if entry.get("snapshot") == snap["snapshot"] \
                and entry.get("snapshot_date", "") == snap.get("snapshot_date", ""):
            continue
        entry["snapshot"] = snap["snapshot"]
        entry["snapshot_date"] = snap.get("snapshot_date", "")
        snapshotted += 1
    payload["titles_captured_utc"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    SOURCES_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    have = sum(1 for e in entries.values() if e.get("title"))
    snaps = sum(1 for e in entries.values() if e.get("snapshot"))
    note = f", {cleared} challenge page(s) left untitled" if cleared else ""
    print(f"{SOURCES_PATH.name}: {added} title(s) updated, "
          f"{have}/{len(entries)} now titled{note}")
    print(f"{SOURCES_PATH.name}: {snapshotted} snapshot(s) newly confirmed, "
          f"{snaps}/{len(entries)} archived")


# --- Wayback preservation ----------------------------------------------------
#
# A citation that dies takes its evidence with it: the row keeps pointing at a
# URL that no longer says what it said. This script already reaches every live
# URL once a week, so it also makes sure each one has a copy on the Internet
# Archive's servers — taken while the original still exists. The rules:
#
#   * A stored snapshot is only ever one the availability API CONFIRMED. A save
#     request is queued server-side and can fail quietly; assuming it worked
#     would store a link nobody ever verified, which is the exact sin the rest
#     of this file exists to prevent.
#   * A save whose confirmation has not landed yet is simply retried next run.
#     Saves usually become visible within minutes; a weekly cadence converges.
#   * Anonymous saves are rate-limited, so there is a per-run budget and a
#     politeness pause between requests. URLs beyond the budget wait a week.
#   * Every archive problem is a printed note, never a failed pass: archiving
#     is preservation layered on top of the check, not part of it.

WAYBACK_AVAILABLE = "https://archive.org/wayback/available?url="
WAYBACK_SAVE = "https://web.archive.org/save/"
# Re-request after a year so a living page's copy does not go stale.
SNAPSHOT_MAX_AGE_DAYS = 365
# How long to wait before asking whether a just-requested save has appeared.
SAVE_SETTLE_SECONDS = 20
# Anonymous saves are rate-limited per IP; stay well inside that.
MAX_SAVES_PER_RUN = 30
AVAILABILITY_PAUSE_SECONDS = 0.4


def iso_from_timestamp(ts: str) -> str:
    """Wayback timestamp "YYYYMMDD[hhmmss]" -> "YYYY-MM-DD"; "" when malformed."""
    ts = (ts or "").strip()
    if not re.fullmatch(r"\d{8}(\d{6})?", ts):
        return ""
    try:
        date(int(ts[:4]), int(ts[4:6]), int(ts[6:8]))
    except ValueError:
        return ""
    return f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"


def snapshot_age_days(iso_date: str, today: date) -> int | None:
    """Whole days since a stored snapshot date; None when unusable."""
    try:
        then = date.fromisoformat((iso_date or "")[:10])
    except ValueError:
        return None
    days = (today - then).days
    return days if days >= 0 else None


def parse_availability(text: str) -> tuple[str, str]:
    """(snapshot URL, raw timestamp) from an availability API response."""
    try:
        data = json.loads(text)
    except ValueError:
        return "", ""
    closest = ((data.get("archived_snapshots") or {}).get("closest")) or {}
    # A non-200 stored capture (redirects, DNS errors) is not evidence of the
    # page's content, so it does not count as archived.
    if str(closest.get("status") or "") != "200" or not closest.get("url"):
        return "", ""
    return closest["url"], str(closest.get("timestamp") or "")


def availability(url: str) -> tuple[str, str]:
    """Ask the Archive what its newest usable capture of `url` is."""
    try:
        res = subprocess.run(
            ["curl", "-s", "--max-time", "20", WAYBACK_AVAILABLE + quote(url, safe="")],
            capture_output=True, text=True, timeout=30)
        snap_url, ts = parse_availability(res.stdout)
        # The API answers with plain http; store the https form so every
        # snapshot link the site ships is same-scheme with the rest.
        return snap_url.replace("http://web.archive.org", "https://web.archive.org", 1), ts
    except Exception:
        return "", ""


def request_save(url: str) -> None:
    """Fire one anonymous save request; the result is checked separately."""
    try:
        subprocess.run(
            ["curl", "-s", "-L", "--max-time", "60", "-A", UA, WAYBACK_SAVE + url],
            capture_output=True, text=True, timeout=70)
    except Exception:
        pass  # judged by the follow-up availability check, never by this


def ensure_snapshots(urls: list[str], entries: dict[str, dict]) -> dict[str, dict]:
    """{url: {snapshot, snapshot_date}} for every URL worth archiving this run.

    `entries` holds the current sources.json records, so a URL whose stored
    snapshot is young enough skips the network entirely — after the first few
    runs this makes the steady-state cost one cheap API call per stale URL,
    not one per source. URLs that are themselves Wayback links are skipped:
    they are already archived by definition, and the availability API does not
    index captures of captures.

    A confirmed capture is always kept even when it is older than the
    freshness bar — a two-year-old copy beats no copy — but a stale one also
    earns its URL a save request, so living pages converge toward a current
    capture instead of resting on whatever the Archive happened to have.
    """
    today = date.today()
    found: dict[str, dict] = {}
    saves_tried = checked = 0

    def record(url: str, snap_url: str, ts: str) -> None:
        if snap_url:
            found[url] = {"snapshot": snap_url, "snapshot_date": iso_from_timestamp(ts)}

    for i, url in enumerate(urls):
        if url.startswith(("http://web.archive.org/", "https://web.archive.org/")):
            continue
        stored = entries.get(url) or {}
        age = snapshot_age_days(stored.get("snapshot_date") or "", today)
        if age is not None and age <= SNAPSHOT_MAX_AGE_DAYS:
            continue
        time.sleep(AVAILABILITY_PAUSE_SECONDS)
        checked += 1
        snap_url, ts = availability(url)
        if snap_url:
            record(url, snap_url, ts)
            fresh = snapshot_age_days(found[url]["snapshot_date"], today)
            if fresh is not None and fresh <= SNAPSHOT_MAX_AGE_DAYS:
                continue
            print(f"  archive: newest capture of {url} is {fresh} days old "
                  "- keeping it, requesting a fresh one")

        if saves_tried >= MAX_SAVES_PER_RUN:
            print(f"  archive: save budget reached ({MAX_SAVES_PER_RUN}); "
                  f"{len(urls) - i} URL(s) wait for the next run")
            break
        saves_tried += 1
        request_save(url)
        time.sleep(SAVE_SETTLE_SECONDS)
        snap_url, ts = availability(url)
        if snap_url:
            record(url, snap_url, ts)
            print(f"  archived: {url}")
        else:
            print(f"  archive: save requested, not yet visible — {url}")
    print(f"archive: {checked} URL(s) needed a look, {saves_tried} save(s) requested")
    return found


def main() -> int:
    no_archive = "--no-archive" in sys.argv[1:]
    where = collect()
    urls = sorted(where)
    print(f"checking {len(urls)} unique source URLs...")

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = dict(zip(urls, pool.map(fetch, urls)))
    codes = {u: r[0] for u, r in results.items()}
    write_sources({u: r[1] for u, r in results.items()})

    # Preservation pass: make sure every live URL has a fresh-enough Wayback
    # copy. Only alive URLs are offered to the Archive (it cannot fetch a dead
    # one either), and any archive failure is non-fatal by design.
    if not no_archive and SOURCES_PATH.is_file():
        try:
            stored = json.loads(SOURCES_PATH.read_text(encoding="utf-8")).get("sources", {})
            alive = sorted(u for u in urls if codes[u] in ALIVE)
            snapshots = ensure_snapshots(alive, stored)
            write_sources({}, snapshots)
        except Exception as exc:  # never let preservation break verification
            print(f"note: snapshotting skipped after an error ({exc})")

    dead = {u: c for u, c in codes.items() if c not in ALIVE}
    wiki = [u for u in urls if "wikipedia.org" in u and not wiki_allowed(u, where[u])]
    placeholder = [u for u in urls if "duckduckgo.com" in u or "google.com/search" in u]

    for label, items in (("dead", dead), ("wikipedia", wiki), ("placeholder", placeholder)):
        if not items:
            continue
        print(f"\n{label.upper()} ({len(items)} URLs, "
              f"{sum(len(where[u]) for u in items)} rows)")
        for url in sorted(items, key=lambda u: -len(where[u])):
            note = f"[{dead[url]}] " if label == "dead" else ""
            rows = where[url]
            shown = ", ".join(rows[:4]) + (f" +{len(rows) - 4} more" if len(rows) > 4 else "")
            print(f"  {note}{url}\n      {shown}")

    print(f"\n{len(urls) - len(dead)}/{len(urls)} URLs alive.")
    if dead or placeholder:
        print("Fix by finding a real source for each claim — never substitute a search hit.")
        return 1
    if wiki:
        print("Wikipedia sources present; README.md disallows them.")
        return 1
    # Clean pass: stamp verified.json so the homepage can show the check date.
    VERIFIED_PATH.write_text(json.dumps({
        "date": date.today().isoformat(),
        "checked_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "sources": len(urls),
    }, indent=2) + "\n", encoding="utf-8")
    print(f"ALL URLs OK — wrote {VERIFIED_PATH.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
