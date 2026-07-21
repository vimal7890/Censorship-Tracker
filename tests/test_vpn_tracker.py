#!/usr/bin/env python3
"""Validate VPN Tracker page structure and shipped data (no mocks)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
AGE = ROOT / "age-verification.html"
VPN = ROOT / "vpn-tracker.html"
DATA = ROOT / "vpn_data.json"


def main() -> int:
    assert INDEX.is_file() and AGE.is_file() and VPN.is_file() and DATA.is_file()

    for path, html in (
        (INDEX, INDEX.read_text(encoding="utf-8")),
        (AGE, AGE.read_text(encoding="utf-8")),
        (VPN, VPN.read_text(encoding="utf-8")),
    ):
        assert "VPN" in html, f"{path.name} missing VPN nav"
        assert 'href="/vpn-tracker"' in html, f"{path.name} missing vpn-tracker link"

    vpn_html = VPN.read_text(encoding="utf-8")
    assert "Global Censorship Tracker" in vpn_html
    assert "Age Verification" in vpn_html
    assert "Current Legislative Efforts" in vpn_html
    assert "vpn_data.json" in vpn_html

    data = json.loads(DATA.read_text(encoding="utf-8"))
    rows = data.get("restrictions") or []
    efforts = data.get("legislative_efforts") or []

    assert len(rows) >= 8, f"need ≥8 restriction rows, got {len(rows)}"
    severities = {r.get("severity") for r in rows}
    assert "complete" in severities and "restricted" in severities, severities

    for r in rows:
        assert r.get("country") and r.get("summary"), r
        assert r.get("severity") in ("complete", "restricted"), r
        assert str(r.get("source", "")).startswith("http"), r
        assert "wikipedia.org" not in r["source"] or True  # allow but prefer news

    assert len(efforts) >= 1, efforts

    # Russia's 2025–2026 crackdown is consolidated into its restrictions row
    # rather than duplicated as separate legislative-effort cards.
    russia_effort = [
        e for e in efforts
        if "Russia" in e.get("jurisdiction", "") or "Russia" in e.get("title", "")
    ]
    assert not russia_effort, f"Russia should not be duplicated in efforts: {russia_effort}"

    russia = next((r for r in rows if r["country"] == "Russia"), None)
    assert russia, "Russia restriction row missing"
    summary = russia["summary"].lower()
    for token in ("roskomnadzor", "advertis", "extremist"):
        assert token in summary, f"Russia row lost '{token}' detail: {russia['summary']}"

    for e in efforts:
        assert e.get("jurisdiction") and e.get("title") and e.get("status"), e
        assert str(e.get("source", "")).startswith("http"), e

    # App/website availability matrix
    matrix = data.get("app_matrix") or {}
    apps = matrix.get("apps") or []
    countries = matrix.get("countries") or []
    assert len(apps) == 15, f"expected 15 tracked VPN apps, got {len(apps)}"
    assert "matrix-section" in vpn_html and "appMatrixBody" in vpn_html

    codes = {c["code"] for c in countries}
    row_names = {r["country"] for r in rows}
    matrix_names = {c["name"] for c in countries}
    assert matrix_names == row_names, (
        f"matrix must cover exactly the restriction rows; "
        f"missing={row_names - matrix_names} extra={matrix_names - row_names}"
    )

    # One service-level verdict per country, not per app store: Pakistan leaves
    # the apps listed and blocks the connection, so store presence would not
    # answer whether the service actually works. "blocked" is the state
    # blocking it; "unavailable" is the provider withdrawing from the market.
    valid = {"available", "restricted", "blocked", "unavailable"}
    for c in countries:
        assert c.get("note"), c
        assert c.get("sources"), f"{c['name']} needs at least one source"
        assert all(str(s).startswith("http") for s in c["sources"]), c
        assert c.get("default") in valid, c

    for app in apps:
        assert app.get("name"), app
        for code, status in (app.get("overrides") or {}).items():
            assert code in codes, f"{app['name']} overrides unknown country {code}"
            assert status in valid, (app["name"], code, status)

    # Pakistan is the worked example of connection-level blocking: a restricted
    # baseline with the providers named in reporting overridden to blocked.
    pk = next(c for c in countries if c["code"] == "PK")
    assert pk["default"] == "restricted", pk
    pk_blocked = {a["name"] for a in apps if (a.get("overrides") or {}).get("PK") == "blocked"}
    assert {"NordVPN", "ExpressVPN", "Proton VPN"} <= pk_blocked, sorted(pk_blocked)

    # IPVanish withdrew from India outright (apps pulled from the Indian
    # stores, signups closed) and is barred from Iran by US sanctions. Both are
    # provider-side, so they must read unavailable rather than blocked.
    ipvanish = next(a for a in apps if a["name"] == "IPVanish")
    for code in ("IN", "IR"):
        assert ipvanish["overrides"].get(code) == "unavailable", ipvanish

    # India's baseline stays available — the withdrawal is IPVanish's alone,
    # not something the Indian state did to every provider.
    assert next(c for c in countries if c["code"] == "IN")["default"] == "available"

    # Every unavailable verdict must be a per-provider override; a country-wide
    # "unavailable" would be a category error (that would be state blocking).
    for c in countries:
        assert c["default"] != "unavailable", f"{c['name']} baseline cannot be unavailable"

    # The circumvention caveat must sit between the grid and the country notes.
    # Match the element, not the stylesheet rule of the same name.
    assert 'class="mx-caveat"' in vpn_html, "circumvention caveat missing from the page"
    assert (
        vpn_html.index('<tbody id="appMatrixBody">')
        < vpn_html.index('class="mx-caveat"')
        < vpn_html.index('id="matrixNotes"')
    ), "caveat must render below the matrix and above the country notes"

    # iCloud Private Relay box section
    assert 'id="icloud-relay-section"' in vpn_html, "iCloud Private Relay section missing"
    relay = data.get("icloud_private_relay") or {}
    assert relay.get("regions"), "iCloud Private Relay regions missing from vpn_data.json"
    relay_countries = [c for r in relay["regions"] for c in r.get("countries", [])]
    assert len(relay_countries) >= 30, f"expected ≥30 Private Relay countries, got {len(relay_countries)}"

    # Infobox check for countries where iCloud+ is not available
    no_icloud_countries = {c["name"] for c in relay_countries if c.get("icloud_plus_available") is False}
    assert {"Cuba", "North Korea", "Iran", "Syria", "Eritrea"} <= no_icloud_countries, no_icloud_countries
    for c in relay_countries:
        if c.get("icloud_plus_available") is False:
            assert c.get("note"), f"Missing infobox note for {c['name']}"

    print("OK: VPN Tracker nav on all pages")
    print("OK: restrictions:", [(r["country"], r["severity"]) for r in rows])
    print("OK: legislative:", [e["jurisdiction"] for e in efforts])
    print("OK: Russia crackdown consolidated into its restrictions row")
    print(f"OK: matrix {len(apps)} apps × {len(countries)} countries")
    print(f"OK: {len(rows)} table rows + {len(efforts)} efforts")
    print(f"OK: iCloud Private Relay {len(relay_countries)} countries across {len(relay['regions'])} regions")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        raise SystemExit(1)
