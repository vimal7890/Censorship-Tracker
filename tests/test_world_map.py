#!/usr/bin/env python3
"""World map integrity: every country in the data has an ISO mapping, and
every mapped ISO code exists as a path id in assets/world.svg."""
import csv
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SVG = ROOT / "assets" / "world.svg"
COUNTRIES_JS = ROOT / "assets" / "countries.js"
CSV_PATH = ROOT / "censorship_data.csv"
VPN_DATA = ROOT / "vpn_data.json"
INDEX = ROOT / "index.html"


def parse_country_map(js_text):
    """Extract the COUNTRY_TO_ISO mapping from assets/countries.js."""
    mapping = {}
    # "Name": "XX"
    for name, iso in re.findall(r'"([^"]+)":\s*"([A-Z]{2})"', js_text):
        mapping[name] = iso
    # "Name": { iso: "XX", subnational: true }
    for name, iso in re.findall(r'"([^"]+)":\s*\{\s*iso:\s*"([A-Z]{2})"', js_text):
        mapping[name] = iso
    return mapping


def main():
    assert SVG.is_file(), "missing assets/world.svg"
    assert COUNTRIES_JS.is_file(), "missing assets/countries.js"

    svg_text = SVG.read_text(encoding="utf-8")
    root = ET.fromstring(svg_text)
    assert root.get("viewBox"), "world.svg must declare a viewBox"

    ids = re.findall(r'id="([A-Z]{2})"', svg_text)
    assert len(ids) == len(set(ids)), "duplicate country ids in world.svg"
    id_set = set(ids)
    assert len(id_set) > 150, f"expected a full world map, got {len(id_set)} countries"

    mapping = parse_country_map(COUNTRIES_JS.read_text(encoding="utf-8"))
    assert mapping, "COUNTRY_TO_ISO not found in countries.js"

    with CSV_PATH.open(encoding="utf-8") as fh:
        csv_countries = {row["country"] for row in csv.DictReader(fh)}
    missing = sorted(c for c in csv_countries if c not in mapping)
    assert not missing, f"CSV countries missing from COUNTRY_TO_ISO: {missing}"

    vpn = json.loads(VPN_DATA.read_text(encoding="utf-8"))
    vpn_countries = {r["country"] for r in vpn.get("restrictions", [])}
    missing = sorted(c for c in vpn_countries if c not in mapping)
    assert not missing, f"vpn_data countries missing from COUNTRY_TO_ISO: {missing}"

    unmapped = sorted(iso for iso in set(mapping.values()) if iso not in id_set)
    assert not unmapped, f"ISO codes not present in world.svg: {unmapped}"

    index_html = INDEX.read_text(encoding="utf-8")
    for needle in (
        "assets/world.svg",
        "assets/countries.js",
        'id="mapSection"',
        'id="countryDossier"',
        'id="countryJump"',
        'id="statsSection"',
        'id="recentSection"',
    ):
        assert needle in index_html, f"index.html missing: {needle}"

    print("ok: world map assets, country mappings and map sections verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
