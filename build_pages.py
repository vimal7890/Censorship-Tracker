#!/usr/bin/env python3
"""Generate a static page per territory and per platform, plus sitemap.xml.

The homepage is one URL wearing every hat: dossiers, filters and searches all
live in the hash, which a search engine never sees. So the question people
actually type — "is Telegram banned in Iran?" — had no page to land on, and
the sitemap honestly listed four URLs for a dataset covering ~78 territories
and ~49 platforms.

This writes real HTML — /country/<slug>/ and /platform/<slug>/ — from the same
CSV the app renders, each with its own title, description, canonical URL and
JSON-LD, linking back into the interactive dossier. The pages are generated
artifacts exactly like the prerender block: never edit one by hand, re-run
this after any data change (build.py does). Stale pages from renamed
territories are deleted on the way through, and sitemap.xml is derived here
too, so it can no longer claim the site is four URLs.

    python3 build_pages.py
"""
from __future__ import annotations

import html
import json
import re
import shutil
import sys
from datetime import datetime, date
from pathlib import Path
from urllib.parse import quote

from territories import (HEAVY_CENSORSHIP, group_by_platform,
                         group_by_territory, load_rows, slugify)

ROOT = Path(__file__).resolve().parent
SOURCES_PATH = ROOT / "sources.json"
SITEMAP = ROOT / "sitemap.xml"
SITE = "https://censorship.my"

COUNTRY_DIR = ROOT / "country"
PLATFORM_DIR = ROOT / "platform"

TYPE_ORDER = {"complete": 0, "partial": 1, "age": 2}
TYPE_LABEL = {"complete": "Complete ban", "partial": "Partial restriction",
              "age": "Age verification"}
STATUS_LABEL = {"scheduled": "Scheduled", "enforced": "Enforced",
                "in_force": "In force", "reported": "Reported"}
KIND_LABEL = {"primary": "primary source", "measurement": "network measurement",
              "research": "research", "reporting": "reporting",
              "reference": "reference"}


def esc(value: str) -> str:
    return html.escape(value or "", quote=True)


def fmt_date(iso: str) -> str:
    """"2026-06-12" -> "12 Jun 2026", or "" — same rendering as Site.fmtDate."""
    try:
        return datetime.strptime(iso[:10], "%Y-%m-%d").strftime("%-d %b %Y")
    except (ValueError, TypeError):
        return ""


def load_sources() -> dict[str, dict]:
    if not SOURCES_PATH.is_file():
        return {}
    try:
        return json.loads(SOURCES_PATH.read_text(encoding="utf-8")).get("sources", {})
    except json.JSONDecodeError:
        return {}


def source_chip(url: str, sources: dict[str, dict]) -> str:
    """The same compact citation Site.sourceChip renders, baked server-side."""
    if not url:
        return ""
    info = sources.get(url)
    if not info:
        domain = re.sub(r"^www\.", "", re.sub(r"^https?://", "", url).split("/")[0])
        info = {"publisher": domain, "kind": "", "date": "", "title": ""}
    label_bits = [f"Source: {info['publisher']}"]
    if info.get("title"):
        label_bits.append(info["title"])
    if KIND_LABEL.get(info.get("kind", "")):
        label_bits.append(KIND_LABEL[info["kind"]])
    if fmt_date(info.get("date", "")):
        label_bits.append(fmt_date(info["date"]))
    label = ", ".join(label_bits) + " (opens in a new tab)"
    return (f'<a class="src-chip kind-{esc(info.get("kind") or "other")}" '
            f'href="{esc(url)}" target="_blank" rel="noopener" '
            f'aria-label="{esc(label)}">{esc(info["publisher"])}</a>')


# The palette and chrome every page carries (see changes.html for the original
# with commentary); pages generated here stay visually native to the site.
PAGE_CSS = """
        :root {
            color-scheme: light;
            --paper-white: #ffffff; --background: #f9f9f9;
            --surface-bright: #f9f9f9; --surface-container-low: #f3f3f3;
            --surface-container: #eeeeee; --surface-container-high: #e8e8e8;
            --primary: #1e1e1e; --redaction-black: #000000; --on-primary: #ffffff;
            --secondary: #b6152e; --alert-orange: #fd7e14; --age-purple: #7d3ac1;
            --age-purple-light: #d9c3f2; --tertiary-green: #35b14d;
            --muted-gray: #6c757d; --on-surface-variant: #444748;
            --outline-variant: #c4c7c7; --ticker-muted: #d0d0d0;
        }
        :root[data-theme="dark"] {
            color-scheme: dark;
            --paper-white: #161616; --background: #0d0d0d;
            --surface-bright: #1a1a1a; --surface-container-low: #212121;
            --surface-container: #282828; --surface-container-high: #303030;
            --primary: #e8e8e8; --redaction-black: #f2f2f2; --on-primary: #121212;
            --secondary: #ef4358; --alert-orange: #fd7e14; --age-purple: #a465e6;
            --age-purple-light: #503a6d; --tertiary-green: #3fc75a;
            --muted-gray: #98a0a7; --on-surface-variant: #c2c5c7;
            --outline-variant: #3a3d3e; --ticker-muted: #4f4f4f;
        }
        @media (prefers-color-scheme: dark) {
            :root:not([data-theme="light"]) {
                color-scheme: dark;
                --paper-white: #161616; --background: #0d0d0d;
                --surface-bright: #1a1a1a; --surface-container-low: #212121;
                --surface-container: #282828; --surface-container-high: #303030;
                --primary: #e8e8e8; --redaction-black: #f2f2f2; --on-primary: #121212;
                --secondary: #ef4358; --alert-orange: #fd7e14; --age-purple: #a465e6;
                --age-purple-light: #503a6d; --tertiary-green: #3fc75a;
                --muted-gray: #98a0a7; --on-surface-variant: #c2c5c7;
                --outline-variant: #3a3d3e; --ticker-muted: #4f4f4f;
            }
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html { -webkit-text-size-adjust: 100%; }
        body {
            font-family: 'Source Sans 3', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--background); color: var(--primary);
            min-height: 100vh; display: flex; flex-direction: column;
            -webkit-font-smoothing: antialiased;
        }
        .topbar { position: sticky; top: 0; z-index: 50; width: 100%;
            background: var(--paper-white); border-bottom: 2px solid var(--primary); }
        .topbar-inner { position: relative; max-width: 1472px; margin: 0 auto;
            display: flex; flex-direction: column; align-items: flex-start;
            padding: 14px 16px; gap: 10px; }
        .wordmark { font-family: 'Chivo', sans-serif; font-weight: 900; font-size: 20px;
            line-height: 1.1; letter-spacing: -0.02em; text-transform: uppercase;
            color: var(--redaction-black); padding-right: 30px; }
        .wordmark a { color: inherit; text-decoration: none; }
        .theme-toggle { position: absolute; top: 10px; right: 12px; display: inline-flex;
            align-items: center; justify-content: center; width: 34px; height: 34px;
            flex-shrink: 0; padding: 0; border: 1px solid var(--primary);
            background: var(--paper-white); color: var(--primary); cursor: pointer;
            transition: background 0.12s, color 0.12s; }
        .theme-toggle:hover { background: var(--primary); color: var(--paper-white); }
        .theme-toggle svg { width: 16px; height: 16px; display: block; }
        .theme-toggle .icon-sun { display: none; }
        :root[data-theme="dark"] .theme-toggle .icon-moon { display: none; }
        :root[data-theme="dark"] .theme-toggle .icon-sun { display: block; }
        @media (prefers-color-scheme: dark) {
            :root:not([data-theme="light"]) .theme-toggle .icon-moon { display: none; }
            :root:not([data-theme="light"]) .theme-toggle .icon-sun { display: block; }
        }
        .topnav { display: flex; align-items: center; gap: 10px; width: 100%;
            font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 700;
            letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted-gray);
            flex-wrap: wrap; }
        .site-nav-links { display: flex; align-items: center; gap: 6px 12px; flex-wrap: wrap; }
        .nav-link { color: var(--muted-gray); text-decoration: none;
            border-bottom: 2px solid transparent; padding: 4px 0 3px;
            transition: color 0.15s, border-color 0.15s; }
        .nav-link:hover { color: var(--primary); }
        .nav-link.active { color: var(--redaction-black); border-bottom-color: var(--tertiary-green); }
        .ticker { width: 100%; background: var(--redaction-black); color: var(--paper-white); }
        .ticker-inner { max-width: 1472px; margin: 0 auto; padding: 8px 16px;
            font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 500;
            letter-spacing: 0.08em; text-transform: uppercase; color: var(--ticker-muted);
            display: flex; flex-wrap: wrap; gap: 8px 20px; }
        .ticker-inner b { color: var(--paper-white); }
        .main-wrap { flex: 1 0 auto; width: 100%; max-width: 900px; margin: 0 auto;
            padding: 24px 16px 48px; }
        .crumb { font-family: 'JetBrains Mono', monospace; font-size: 12px;
            letter-spacing: 0.05em; text-transform: uppercase; margin-bottom: 18px; }
        .crumb a { color: var(--muted-gray); text-decoration: none; }
        .crumb a:hover { color: var(--primary); }
        h1 { font-family: 'Chivo', sans-serif; font-weight: 900; font-size: 32px;
            line-height: 1.15; letter-spacing: -0.01em; text-transform: uppercase;
            color: var(--redaction-black); margin-bottom: 10px; }
        .lede { font-size: 16px; line-height: 1.55; color: var(--on-surface-variant);
            max-width: 640px; margin-bottom: 6px; }
        .country-note { font-size: 14px; line-height: 1.5; color: var(--on-surface-variant);
            border-left: 3px solid var(--secondary); background: var(--surface-container-low);
            padding: 10px 12px; margin: 14px 0 0; max-width: 640px; }
        .actions { display: flex; flex-wrap: wrap; gap: 8px 18px; margin: 18px 0 26px;
            font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 700;
            letter-spacing: 0.05em; text-transform: uppercase; }
        .actions a { color: var(--primary); }
        .entry { border: 1px solid var(--outline-variant); border-left: 4px solid var(--muted-gray);
            background: var(--paper-white); padding: 14px 16px; margin-bottom: 12px; }
        .entry.complete { border-left-color: var(--secondary); }
        .entry.partial { border-left-color: var(--alert-orange); }
        .entry.age { border-left-color: var(--age-purple); }
        .entry h2 { font-family: 'Chivo', sans-serif; font-weight: 900; font-size: 18px;
            text-transform: uppercase; letter-spacing: 0; color: var(--redaction-black);
            margin-bottom: 4px; }
        .entry-meta { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 10px;
            font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700;
            letter-spacing: 0.05em; text-transform: uppercase; color: var(--muted-gray);
            margin-bottom: 8px; }
        .entry-meta .t-complete { color: var(--secondary); }
        .entry-meta .t-partial { color: var(--alert-orange); }
        .entry-meta .t-age { color: var(--age-purple); }
        .entry p { font-size: 14px; line-height: 1.55; color: var(--on-surface-variant);
            margin-bottom: 8px; max-width: 680px; }
        .index-list { columns: 2; column-gap: 40px; margin-top: 18px; }
        .index-list li { margin-bottom: 8px; font-size: 15px; line-height: 1.4;
            break-inside: avoid; }
        .index-list a { color: var(--primary); }
        .index-list .n { color: var(--muted-gray); font-size: 13px; }
        @media (max-width: 560px) { .index-list { columns: 1; } }
        .footer { flex-shrink: 0; background: var(--paper-white);
            border-top: 2px solid var(--primary); }
        .footer-inner { max-width: 1472px; margin: 0 auto; padding: 14px 16px;
            font-family: 'JetBrains Mono', monospace; font-size: 11px;
            letter-spacing: 0.05em; text-transform: uppercase; color: var(--muted-gray); }
        .freshness { margin-top: 26px; }
        @media (min-width: 768px) {
            .topbar-inner, .ticker-inner, .footer-inner { padding-left: 40px; padding-right: 40px; }
        }
"""

TOGGLE_SVG = ('<svg class="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
              'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
              '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>'
              '<svg class="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
              'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
              '<circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line>'
              '<line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>'
              '<line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line>'
              '<line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>'
              '<line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>')


def page_shell(*, title: str, description: str, canonical: str, body: str,
               jsonld: dict, feed: tuple[str, str] | None = None) -> str:
    """The chrome every generated page shares. `feed` is (title, href)."""
    feed_link = (f'\n    <link rel="alternate" type="application/rss+xml" '
                 f'title="{esc(feed[0])}" href="{esc(feed[1])}">' if feed else "")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="theme-color" content="#ffffff">
    <title>{esc(title)}</title>
    <meta name="description" content="{esc(description)}">
    <link rel="canonical" href="{esc(canonical)}">
    <base href="/">
    <meta property="og:type" content="website">
    <meta property="og:site_name" content="Global Censorship Tracker">
    <meta property="og:title" content="{esc(title)}">
    <meta property="og:description" content="{esc(description)}">
    <meta property="og:url" content="{esc(canonical)}">
    <meta property="og:image" content="{SITE}/og-image.png">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    <meta property="og:image:alt" content="Global Censorship Tracker — banned, restricted and age-gated platforms worldwide.">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{esc(title)}">
    <meta name="twitter:description" content="{esc(description)}">
    <meta name="twitter:image" content="{SITE}/og-image.png">
    <link rel="icon" href="favicon.svg" type="image/svg+xml">
    <link rel="icon" href="favicon.ico" sizes="any">
    <link rel="apple-touch-icon" href="favicon-32.png">
    <link rel="preload" href="assets/fonts/Chivo-latin.woff2" as="font" type="font/woff2" crossorigin>
    <link rel="preload" href="assets/fonts/SourceSans3-latin.woff2" as="font" type="font/woff2" crossorigin>
    <link rel="stylesheet" href="assets/fonts/fonts.css">
    <link rel="stylesheet" href="assets/site.css">{feed_link}
    <script src="assets/theme.js"></script>
    <script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>
    <style>{PAGE_CSS}    </style>
</head>
<body>
    <header class="topbar">
        <div class="topbar-inner">
            <div class="wordmark"><a href="/">Global Censorship Tracker</a></div>
            <nav class="topnav" aria-label="Site">
                <div class="site-nav-links">
                    <a href="/" class="nav-link">Blocked Websites</a>
                    <a href="/age-verification" class="nav-link">Age Verification</a>
                    <a href="/vpn-tracker" class="nav-link">VPN</a>
                    <a href="/changes" class="nav-link">What Changed</a>
                </div>
                <button class="theme-toggle" id="themeToggle" type="button" aria-label="Switch to dark theme">{TOGGLE_SVG}</button>
            </nav>
        </div>
    </header>

    <div class="ticker">
        <div class="ticker-inner">
            <span>&#9632;&nbsp; Global Digital Ban Index</span>
            <span data-meta-row hidden>Data updated: <b data-meta="data-updated"></b></span>
            <span data-meta-row hidden>Sources checked: <b data-meta="sources-checked"></b></span>
        </div>
    </div>

    <main class="main-wrap">
{body}
        <div class="freshness">
            <span data-meta-row hidden>Data updated: <b data-meta="data-updated"></b> <span class="rel" data-meta="data-updated-rel"></span></span>
            <span data-meta-row hidden>Sources checked: <b data-meta="sources-checked"></b> <span class="rel" data-meta="sources-checked-rel"></span></span>
        </div>
    </main>

    <footer class="footer">
        <div class="footer-inner">&copy; 2026 Censorship_Tracker &mdash; data CC BY 4.0</div>
    </footer>

    <script src="assets/site.js"></script>
    <script>Site.loadMeta();</script>
</body>
</html>
"""


def breadcrumbs(*trail: tuple[str, str]) -> dict:
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": name, "item": url}
            for i, (name, url) in enumerate(trail)
        ],
    }


def entry_html(row: dict, *, heading: str, anchor: str,
               sources: dict[str, dict], state_note: str = "") -> str:
    btype = row.get("type") or "complete"
    status = row.get("status", "")
    prefix = "From" if status == "scheduled" else "Since"
    since = row.get("since", "")
    meta_bits = [f'<span class="t-{esc(btype)}">{TYPE_LABEL.get(btype, btype)}</span>']
    if since:
        meta_bits.append(f"<span>{prefix}: {esc(since)}</span>")
    if STATUS_LABEL.get(status):
        meta_bits.append(f'<span class="tag-status {esc(status)}">{STATUS_LABEL[status]}</span>')
    if state_note:
        meta_bits.append(f"<span>{esc(state_note)}</span>")
    chip = source_chip(row.get("source", ""), sources)
    if chip:
        meta_bits.append(chip)
    notes = row.get("more_info", "")
    notes_html = f"        <p>{esc(notes)}</p>\n" if notes else ""
    return (f'        <article class="entry {esc(btype)}" id="{esc(anchor)}">\n'
            f"        <h2>{esc(heading)}</h2>\n"
            f'        <div class="entry-meta">{" ".join(meta_bits)}</div>\n'
            f"{notes_html}"
            "        </article>")


def describe_types(entries: list[dict]) -> str:
    counts = {"complete": 0, "partial": 0, "age": 0}
    for e in entries:
        counts[e.get("type") or "complete"] = counts.get(e.get("type") or "complete", 0) + 1
    bits = []
    if counts["complete"]:
        bits.append(f"{counts['complete']} complete ban{'s' if counts['complete'] != 1 else ''}")
    if counts["partial"]:
        bits.append(f"{counts['partial']} partial restriction{'s' if counts['partial'] != 1 else ''}")
    if counts["age"]:
        bits.append(f"{counts['age']} age-verification requirement{'s' if counts['age'] != 1 else ''}")
    if len(bits) > 1:
        return ", ".join(bits[:-1]) + " and " + bits[-1]
    return bits[0] if bits else "no tracked restrictions"


def country_page(group: dict, sources: dict[str, dict]) -> str:
    name = group["display"]
    entries = sorted(group["entries"],
                     key=lambda e: (TYPE_ORDER.get(e.get("type"), 9),
                                    e["platform"].lower()))
    n = len(entries)
    canonical = f"{SITE}/country/{group['slug']}/"
    platforms = sorted({e["platform"] for e in entries}, key=str.lower)
    sample = ", ".join(platforms[:3])
    title = f"Websites blocked in {name} — {n} tracked restriction{'s' if n != 1 else ''}"
    description = (f"{name}: {describe_types(entries)} tracked, including {sample}. "
                   "Every entry dated and cited — from the Global Censorship Tracker.")[:300]

    jsonld = {
        "@context": "https://schema.org",
        "@graph": [
            breadcrumbs(("Global Censorship Tracker", f"{SITE}/"), (name, canonical)),
            {
                "@type": "ItemList",
                "name": f"Platforms blocked or restricted in {name}",
                "numberOfItems": n,
                "itemListElement": [
                    {"@type": "ListItem", "position": i + 1,
                     "name": f"{e['platform']} — {TYPE_LABEL.get(e.get('type'), e.get('type'))}"
                             + (f" since {e['since']}" if e.get("since") else "")}
                    for i, e in enumerate(entries)
                ],
            },
        ],
    }

    note_html = ""
    if name in HEAVY_CENSORSHIP:
        note_html = f'        <p class="country-note">{esc(HEAVY_CENSORSHIP[name])}</p>\n'
    state_line = ""
    if group["subnational_names"]:
        names = ", ".join(group["subnational_names"])
        plural = "s" if len(group["subnational_names"]) != 1 else ""
        state_line = (f'        <p class="lede">Includes state-level '
                      f"jurisdiction{plural}: {esc(names)}.</p>\n")

    rows = "\n".join(
        entry_html(e, heading=e["platform"],
                   anchor=slugify(e["platform"]) + ("-" + e["type"] if
                       sum(1 for x in entries if x["platform"] == e["platform"]) > 1 else ""),
                   sources=sources,
                   state_note=(e["country"] if e.get("subnational") else ""))
        for e in entries)

    body = (
        f'        <nav class="crumb" aria-label="Breadcrumb">'
        f'<a href="/">&larr; All countries &amp; platforms</a></nav>\n'
        f"        <h1>Blocked in {esc(name)}</h1>\n"
        f'        <p class="lede">The tracker lists {describe_types(entries)} '
        f"in {esc(name)}.</p>\n"
        + state_line + note_html +
        f'        <div class="actions">\n'
        f'            <a href="/#country={group["iso"]}">Open the interactive dossier &rarr;</a>\n'
        f'            <a href="/feed/{group["slug"]}.xml">Follow changes in {esc(name)} (RSS)</a>\n'
        f"        </div>\n"
        + rows + "\n")
    return page_shell(title=title, description=description, canonical=canonical,
                      body=body, jsonld=jsonld,
                      feed=(f"What changed in {name} — Global Censorship Tracker",
                            f"/feed/{group['slug']}.xml"))


def platform_page(name: str, rows: list[dict], sources: dict[str, dict],
                  territory_slugs: dict[str, str]) -> str:
    entries = sorted(rows, key=lambda e: (e["country"].lower(),
                                          TYPE_ORDER.get(e.get("type"), 9)))
    n = len(entries)
    countries = []
    for e in entries:
        if e["country"] not in countries:
            countries.append(e["country"])
    slug = slugify(name)
    canonical = f"{SITE}/platform/{slug}/"
    sample = ", ".join(countries[:4])
    title = (f"Where is {name} blocked? — "
             f"{len(countries)} countr{'ies' if len(countries) != 1 else 'y'} and territories")
    description = (f"{name} is blocked, restricted or age-gated in {len(countries)} "
                   f"countries and territories, including {sample}. "
                   "Dates, status and a cited source for each.")[:300]

    jsonld = {
        "@context": "https://schema.org",
        "@graph": [
            breadcrumbs(("Global Censorship Tracker", f"{SITE}/"), (name, canonical)),
            {
                "@type": "ItemList",
                "name": f"Countries and territories restricting {name}",
                "numberOfItems": n,
                "itemListElement": [
                    {"@type": "ListItem", "position": i + 1,
                     "name": f"{e['country']} — {TYPE_LABEL.get(e.get('type'), e.get('type'))}"
                             + (f" since {e['since']}" if e.get("since") else "")}
                    for i, e in enumerate(entries)
                ],
            },
        ],
    }

    def anchor_for(e: dict) -> str:
        base = slugify(e["country"])
        if sum(1 for x in entries if x["country"] == e["country"]) > 1:
            return f"{base}-{e['type']}"
        return base

    def heading_link(e: dict) -> str:
        return e["country"]

    rows_html = "\n".join(
        entry_html(e, heading=heading_link(e), anchor=anchor_for(e), sources=sources)
        for e in entries)

    body = (
        f'        <nav class="crumb" aria-label="Breadcrumb">'
        f'<a href="/">&larr; All countries &amp; platforms</a></nav>\n'
        f"        <h1>Where is {esc(name)} blocked?</h1>\n"
        f'        <p class="lede">{esc(name)} is blocked, restricted or age-gated in '
        f"{len(countries)} countr{'ies' if len(countries) != 1 else 'y'} and territories "
        f"— {describe_types(entries)} in total.</p>\n"
        f'        <div class="actions">\n'
        f'            <a href="/#q={quote(name)}">See it in the interactive index &rarr;</a>\n'
        f"        </div>\n"
        + rows_html + "\n")
    return page_shell(title=title, description=description, canonical=canonical,
                      body=body, jsonld=jsonld)


def hub_page(kind: str, items: list[tuple[str, str, int]]) -> str:
    """Index page for /country/ or /platform/ — internal links plus a human landing."""
    noun = "countries and territories" if kind == "country" else "platforms"
    title = f"All {noun} in the tracker — Global Censorship Tracker"
    canonical = f"{SITE}/{kind}/"
    description = (f"Every {'territory' if kind == 'country' else 'platform'} in the "
                   f"Global Censorship Tracker's index of blocked, restricted and "
                   f"age-gated apps and websites, with a page per entry.")
    lis = "\n".join(
        f'            <li><a href="/{kind}/{slug}/">{esc(name)}</a> '
        f'<span class="n">({n} restriction{"s" if n != 1 else ""})</span></li>'
        for name, slug, n in items)
    jsonld = {
        "@context": "https://schema.org",
        "@graph": [
            breadcrumbs(("Global Censorship Tracker", f"{SITE}/"),
                        (f"All {noun}", canonical)),
            {"@type": "ItemList", "numberOfItems": len(items),
             "itemListElement": [
                 {"@type": "ListItem", "position": i + 1, "name": name,
                  "url": f"{SITE}/{kind}/{slug}/"}
                 for i, (name, slug, _) in enumerate(items)]},
        ],
    }
    body = (
        f'        <nav class="crumb" aria-label="Breadcrumb">'
        f'<a href="/">&larr; Back to the tracker</a></nav>\n'
        f"        <h1>All {esc(noun)}</h1>\n"
        f'        <p class="lede">One page per {"territory" if kind == "country" else "platform"}, '
        f"listing every tracked restriction with its date, status and source.</p>\n"
        f'        <ul class="index-list">\n{lis}\n        </ul>\n')
    return page_shell(title=title, description=description, canonical=canonical,
                      body=body, jsonld=jsonld)


def write_tree(root: Path, pages: dict[str, str]) -> tuple[int, int]:
    """Write `slug -> html` under root, delete anything else. -> (written, kept)."""
    expected = {root / slug / "index.html" if slug else root / "index.html"
                for slug in pages}
    if root.is_dir():
        for child in root.iterdir():
            if child.is_dir() and (child / "index.html") not in expected:
                shutil.rmtree(child)
            elif child.is_file() and child not in expected:
                child.unlink()
    written = kept = 0
    for slug, content in pages.items():
        target = (root / slug / "index.html") if slug else (root / "index.html")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_file() and target.read_text(encoding="utf-8") == content:
            kept += 1
            continue
        target.write_text(content, encoding="utf-8")
        written += 1
    return written, kept


def write_sitemap(urls: list[tuple[str, str]]) -> None:
    """(loc, priority) pairs -> sitemap.xml. lastmod deliberately absent: a
    sitemap that stamps every URL with today is asserting freshness it has not
    checked, and the pages carry their real dates."""
    entries = "\n".join(
        "  <url>\n"
        f"    <loc>{esc(loc)}</loc>\n"
        "    <changefreq>weekly</changefreq>\n"
        f"    <priority>{priority}</priority>\n"
        "  </url>"
        for loc, priority in urls)
    SITEMAP.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + entries + "\n</urlset>\n", encoding="utf-8")


def main() -> int:
    rows = load_rows()
    sources = load_sources()
    territories_map = group_by_territory(rows)
    platforms_map = group_by_platform(rows)
    territory_slugs = {g["display"]: g["slug"] for g in territories_map.values()}

    country_pages: dict[str, str] = {}
    country_items: list[tuple[str, str, int]] = []
    for group in sorted(territories_map.values(), key=lambda g: g["display"].lower()):
        country_pages[group["slug"]] = country_page(group, sources)
        country_items.append((group["display"], group["slug"], len(group["entries"])))
    country_pages[""] = hub_page("country", country_items)

    platform_pages: dict[str, str] = {}
    platform_items: list[tuple[str, str, int]] = []
    for name in sorted(platforms_map, key=str.lower):
        entries = platforms_map[name]
        platform_pages[slugify(name)] = platform_page(name, entries, sources,
                                                      territory_slugs)
        platform_items.append((name, slugify(name), len(entries)))
    platform_pages[""] = hub_page("platform", platform_items)

    cw, ck = write_tree(COUNTRY_DIR, country_pages)
    pw, pk = write_tree(PLATFORM_DIR, platform_pages)

    urls: list[tuple[str, str]] = [
        (f"{SITE}/", "1.0"),
        (f"{SITE}/age-verification", "0.8"),
        (f"{SITE}/vpn-tracker", "0.8"),
        (f"{SITE}/changes", "0.6"),
        (f"{SITE}/country/", "0.6"),
        (f"{SITE}/platform/", "0.6"),
    ]
    urls += [(f"{SITE}/country/{slug}/", "0.7")
             for _, slug, _ in country_items]
    urls += [(f"{SITE}/platform/{slug}/", "0.7")
             for _, slug, _ in platform_items]
    write_sitemap(urls)

    print(f"country/: {len(country_pages)} pages ({cw} written, {ck} unchanged)")
    print(f"platform/: {len(platform_pages)} pages ({pw} written, {pk} unchanged)")
    print(f"sitemap.xml: {len(urls)} URLs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
