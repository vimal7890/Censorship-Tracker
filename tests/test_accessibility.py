#!/usr/bin/env python3
"""Guard the accessibility fixes that are easy to undo by accident.

Each of these was a real defect, and each would come back the moment somebody
tidied the markup without knowing why it was written that way:

  * the homepage search field's visible "SEARCH_" was a decorative <span>, so
    the input had no accessible name at all
  * citations rendered as "[47]", which is not a description of anything
  * every form control needs a label, visible or otherwise
  * the region guess must stay client-side — no geolocation prompt, no lookup
    service, because either would tell somebody that this visitor is reading a
    censorship tracker
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ["index.html", "age-verification.html", "vpn-tracker.html", "changes.html"]
SITE_JS = ROOT / "assets" / "site.js"
TZ_JS = ROOT / "assets" / "timezones.js"

# Controls that need a name, and how they are allowed to get one.
LABEL_ATTRS = ("aria-label", "aria-labelledby", "id")


def labelled_controls(text: str, name: str) -> None:
    """Every <input>/<select> must resolve to a name somehow."""
    labels_for = set(re.findall(r'<label[^>]*\sfor="([^"]+)"', text))
    for tag in re.findall(r"<(?:input|select)\b[^>]*>", text):
        if 'type="hidden"' in tag:
            continue
        ident = re.search(r'\sid="([^"]+)"', tag)
        has_aria = "aria-label" in tag or "aria-labelledby" in tag
        has_label = bool(ident and ident.group(1) in labels_for)
        assert has_aria or has_label, (
            f"{name}: form control has no accessible name — add a <label for> "
            f"or an aria-label: {tag[:110]}")


def main() -> int:
    index = (ROOT / "index.html").read_text(encoding="utf-8")

    # The search field: a real <label for>, not a decorative span.
    assert '<label class="search-label" for="searchBox">' in index, (
        "index.html: the search field's SEARCH_ text must be a <label for=\"searchBox\">, "
        "not a <span> — otherwise the input has no accessible name")

    # Citations must describe themselves rather than render a footnote number.
    assert not re.search(r'>\s*\[\$\{sourceIndex', index), "index.html still renders [n] citations"
    assert "sourceIndex" not in index, (
        "index.html still builds a numeric source index; citations should come from "
        "Site.sourceChip / Site.sourceCard")

    site_js = SITE_JS.read_text(encoding="utf-8")
    assert "function sourceLabel" in site_js, "site.js lost its citation label builder"
    for phrase in ("'Source: '", "opens in a new tab"):
        assert phrase in site_js, f"site.js citation labels no longer include {phrase}"

    # Focus has to land somewhere after a dossier opens.
    assert 'id="dossierTitle" tabindex="-1"' in index, (
        "index.html: the dossier heading needs tabindex=\"-1\" so focus can move into it")
    assert "getElementById('dossierTitle').focus" in index, (
        "index.html: opening a dossier must move focus into it")

    # An empty result has to offer a way out of itself.
    assert "no-results-actions" in index, (
        "index.html: an empty result must suggest which filter to clear")

    # Region detection stays inside the browser.
    for banned, why in (
        ("navigator.geolocation", "a location prompt"),
        ("ipapi", "an IP lookup service"),
        ("ipinfo", "an IP lookup service"),
        ("geoip", "an IP lookup service"),
    ):
        assert banned not in index, (
            f"index.html uses {banned} — region detection must not depend on {why}. "
            "It reads the browser's own time zone; see build_timezones.py.")
    assert "resolvedOptions().timeZone" in index, "index.html lost its time-zone region guess"
    assert TZ_JS.is_file(), "assets/timezones.js missing (run: python3 build_timezones.py)"
    assert "window.TZ_TO_ISO" in TZ_JS.read_text(encoding="utf-8"), "timezones.js is malformed"

    for name in PAGES:
        text = (ROOT / name).read_text(encoding="utf-8")
        labelled_controls(text, name)
        assert 'lang="en"' in text, f"{name}: <html> has no lang"

    print(f"ok: search field labelled, citations described, focus managed, "
          f"region guess stays local, {len(PAGES)} pages' controls all named")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
