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
"""
from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timezone, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "censorship_data.csv"
JSON_PATHS = [ROOT / "vpn_data.json", ROOT / "age_verification_data.json"]
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

# Wikipedia stays banned as a source, with one carve-out. In the countries
# whose internet is restricted by default there is often no platform-specific
# reporting to cite at all: nobody writes "Tumblr is blocked in Turkmenistan",
# they write that almost everything is. For those rows the country-level
# Wikipedia article is the agreed last resort, better than the homepage links
# and catch-all reports it replaced. Everywhere else a Wikipedia citation is
# still a defect, and a row whose platform *is* Wikipedia may cite it freely
# (see README.md).
WIKI_EXEMPT_COUNTRIES = {"China", "Eritrea", "Iran", "North Korea", "Turkmenistan"}


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


def status(url: str) -> str:
    try:
        res = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "-L",
             "--max-time", "25", "-A", UA, url],
            capture_output=True, text=True, timeout=40)
        return res.stdout.strip() or "000"
    except Exception:
        return "000"


def main() -> int:
    where = collect()
    urls = sorted(where)
    print(f"checking {len(urls)} unique source URLs...")

    with ThreadPoolExecutor(max_workers=12) as pool:
        codes = dict(zip(urls, pool.map(status, urls)))

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
