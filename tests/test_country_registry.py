#!/usr/bin/env python3
"""The canonical country registry must be the common resolver for every data surface."""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from country_registry import load_registry  # noqa: E402

CSV_PATH = ROOT / "censorship_data.csv"
VPN_PATH = ROOT / "vpn_data.json"
COUNTRIES_JS = ROOT / "assets" / "countries.js"
TIMEZONES_JS = ROOT / "assets" / "timezones.js"
INDEX = ROOT / "index.html"
VPN_PAGE = ROOT / "vpn-tracker.html"


def vpn_names(data: dict) -> set[str]:
    names = {row.get("country", "") for row in data.get("restrictions", [])}
    matrix = data.get("app_matrix") or {}
    names |= {row.get("name", "") for row in matrix.get("countries", [])}
    names |= {
        country.get("name", "")
        for region in (data.get("icloud_private_relay") or {}).get("regions", [])
        for country in region.get("countries", [])
    }
    return {name for name in names if name}


def parse_json_asset(text: str, variable: str) -> dict:
    match = re.search(rf"window\.{variable}\s*=\s*(\{{.*?\}});", text, re.S)
    assert match, f"{variable} missing from generated timezone asset"
    return json.loads(match.group(1))


def main() -> int:
    registry = load_registry()
    assert registry.version == 1
    assert registry.resolve("United Kingdom")["iso"] == "GB"
    assert registry.canonical_name("GB") == "United Kingdom of Great Britain and Northern Ireland"
    assert registry.resolve("Greenland")["iso"] == "DK"
    assert registry.map["iso_aliases"]["GL"] == "DK"

    with CSV_PATH.open(newline="", encoding="utf-8") as fh:
        csv_names = {row["country"] for row in csv.DictReader(fh)}
    registry.validate_names(csv_names, "censorship_data.csv")

    vpn = json.loads(VPN_PATH.read_text(encoding="utf-8"))
    registry.validate_names(vpn_names(vpn), "vpn_data.json")
    for country in (vpn.get("app_matrix") or {}).get("countries", []):
        record = registry.resolve(country["name"])
        assert record and record["iso"] == country["code"], country

    countries_js = COUNTRIES_JS.read_text(encoding="utf-8")
    assert "generated from" in countries_js and "country_registry.json" in countries_js
    assert "window.COUNTRY_TO_ISO" in countries_js
    assert "window.COUNTRY_CANONICAL_NAMES" in countries_js
    assert '"United Kingdom": "GB"' in countries_js
    assert '"Greenland": "DK"' in countries_js
    assert "window.canonicalCountryName" in countries_js

    timezones_js = TIMEZONES_JS.read_text(encoding="utf-8")
    assert "country_registry.json" in timezones_js
    iso_map = parse_json_asset(timezones_js, "TZ_TO_ISO")
    name_map = parse_json_asset(timezones_js, "TZ_TO_COUNTRY")
    assert iso_map and name_map
    assert "America/New_York" in iso_map
    for zone, name in name_map.items():
        iso = iso_map[zone]
        canonical_iso = registry.map["iso_aliases"].get(iso, iso)
        assert name == registry.canonical_name(canonical_iso), (zone, iso, name)

    index = INDEX.read_text(encoding="utf-8")
    assert '<script src="assets/countries.js"></script>' in index
    assert "canonicalCountryName" in index
    vpn_page = VPN_PAGE.read_text(encoding="utf-8")
    assert '<script src="assets/countries.js"></script>' in vpn_page
    assert "function displayCountry" in vpn_page

    print(
        f"ok: {len(registry.records)} registry names resolve across "
        f"{len(csv_names)} CSV countries, {len(vpn_names(vpn))} VPN names, "
        f"and {len(name_map)} named time zones"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, KeyError, TypeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
