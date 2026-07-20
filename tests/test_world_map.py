#!/usr/bin/env python3
"""World map integrity: every country in the data has an ISO mapping, and
every mapped ISO code is drawable — either as a path id in assets/world.svg or,
for microstates too small to have an outline, as a MICROSTATE_LATLON marker
that projects inside the viewBox."""
import csv
import json
import math
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


def parse_microstates(js_text):
    """Extract MICROSTATE_LATLON (ISO -> [lon, lat]) from assets/countries.js."""
    block = re.search(r"MICROSTATE_LATLON\s*=\s*\{(.*?)\}\s*;", js_text, re.S)
    if not block:
        return {}
    return {
        iso: (float(lon), float(lat))
        for iso, lon, lat in re.findall(
            r"([A-Z]{2}):\s*\[\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\]", block.group(1)
        )
    }


def project(lon, lat):
    """Mirror of window.projectLonLat in assets/countries.js."""
    k, x0, y0 = 160.58734, 475.1309, 463.6362
    while lon < -169.52:
        lon += 360
    while lon > 190.48:
        lon -= 360
    return (
        k * math.radians(lon) + x0,
        y0 - k * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)),
    )


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

    # Microstates have no outline in world.svg and are drawn as markers from
    # MICROSTATE_LATLON instead, so they satisfy the "is mappable" requirement
    # without being path ids.
    micro = parse_microstates(COUNTRIES_JS.read_text(encoding="utf-8"))
    assert micro, "MICROSTATE_LATLON not found in countries.js"

    clash = sorted(set(micro) & id_set)
    assert not clash, f"microstates that already have a world.svg path: {clash}"

    for iso, (lon, lat) in sorted(micro.items()):
        assert -180 <= lon <= 180, f"{iso}: longitude {lon} out of range"
        assert -85 <= lat <= 85, f"{iso}: latitude {lat} out of range"
        x, y = project(lon, lat)
        assert 0 <= x <= 1009, f"{iso}: projected x={x:.1f} outside the viewBox"
        assert 0 <= y <= 651, f"{iso}: projected y={y:.1f} outside the viewBox"

    mappable = id_set | set(micro)
    unmapped = sorted(iso for iso in set(mapping.values()) if iso not in mappable)
    assert not unmapped, (
        f"ISO codes with neither a world.svg path nor MICROSTATE_LATLON "
        f"coordinates: {unmapped}"
    )

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
