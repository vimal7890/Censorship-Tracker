#!/usr/bin/env python3
"""Shared territory logic for the build scripts.

Grouping CSV rows into territories is done in two places with the same rules:
the browser does it to build the map and the dossiers (buildCountryIndex in
index.html), and the generators do it to build the static country pages and
the per-territory feeds. This module is the generators' single copy, so
build_pages.py and build_changelog.py cannot drift apart on what a slug or a
display name is — a feed URL baked into a page must keep resolving.

The name → ISO mapping itself comes from country_registry.json via
country_registry.py — the same canonical registry assets/countries.js is
generated from, so the pages and the browser cannot disagree on it.
"""
from __future__ import annotations

import csv
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

from country_registry import load_registry

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "censorship_data.csv"

# The four default-restricted countries and the shared sentence the homepage
# substitutes when a row there has nothing platform-specific to say. Mirrors
# HEAVY_CENSORSHIP in index.html; tests/test_static_pages.py asserts the two
# copies stay identical.
HEAVY_CENSORSHIP = {
    "People's Republic of China": "People's Republic of China's \"Great Firewall\" blocks most major foreign platforms by default. State-monitored domestic alternatives take their place, and unsanctioned VPN use is illegal.",
    "Eritrea": "Eritrea routes the whole country through EriTel, the sole state-owned ISP, and internet penetration sits near 1%. There is no independent domestic media, so foreign platforms are out of reach by default.",
    "North Korea": "North Korea has no public internet. Citizens can only reach the state-run Kwangmyong intranet, so every foreign platform is inaccessible by default.",
    "Turkmenistan": "Turkmenistan's state-monopoly ISP blocks most foreign platforms and roughly 75% of all IP addresses by default, and VPN use is actively suppressed.",
}


def slugify(name: str) -> str:
    """A URL path segment for a territory or platform name.

    ASCII-folded so "Türkiye" becomes "turkiye" — the slug is typed into
    address bars and cited in links, and a non-ASCII path would be
    percent-encoded into something nobody recognises.
    """
    ascii_name = (unicodedata.normalize("NFKD", name)
                  .encode("ascii", "ignore").decode("ascii"))
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")
    assert slug, f"name {name!r} produced an empty slug"
    return slug


def load_rows() -> list[dict]:
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        return [row for row in csv.DictReader(f)
                if (row.get("platform") or "").strip() and (row.get("country") or "").strip()]


def group_by_territory(rows: list[dict]) -> dict[str, dict]:
    """CSV rows grouped by ISO code, subnational rows under their parent.

    Returns iso -> {iso, display, slug, entries, subnational_names}. The
    display name is the registry's canonical name for the ISO code, so a
    country whose rows are all state-level is still titled after the country.
    Every entry keeps its own country string, so Texas stays named inside the
    United States group.
    """
    registry = load_registry()
    groups: dict[str, dict] = {}
    for row in rows:
        country = row["country"].strip()
        info = registry.resolve(country)
        if not info:
            continue  # unmapped name; tests/test_world_map.py rejects these
        iso = info["iso"]
        subnational = bool(info.get("subnational"))
        group = groups.setdefault(iso, {
            "iso": iso,
            "display": registry.canonical_name(iso) or country,
            "entries": [], "subnational_names": [],
        })
        if subnational and country not in group["subnational_names"]:
            group["subnational_names"].append(country)
        group["entries"].append({**{k: (row.get(k) or "").strip() for k in row},
                                 "subnational": subnational,
                                 "subnational_note": info.get("note", "")})
    for group in groups.values():
        group["slug"] = slugify(group["display"])
    return groups


def group_by_platform(rows: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        groups[row["platform"].strip()].append(
            {k: (row.get(k) or "").strip() for k in row})
    return dict(groups)
