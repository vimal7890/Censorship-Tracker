#!/usr/bin/env python3
"""Generate assets/countries.js from the canonical country registry.

Do not edit assets/countries.js by hand.  Human-readable names, aliases,
subnational notes, map-only territory aliases, microstate coordinates and the
projection constants all live in country_registry.json; this file is the
browser-shaped build artifact consumed by index.html.

    python3 build_countries.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from country_registry import CountryRegistry, load_registry

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "assets" / "countries.js"
VPN_PATH = ROOT / "vpn_data.json"
CSV_PATH = ROOT / "censorship_data.csv"


def quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def mapping_value(record: dict) -> str:
    if record.get("subnational"):
        note = record.get("note", "")
        return (
            '{ iso: ' + quote(record["iso"]) +
            ', subnational: true, note: ' + quote(note) + ' }'
        )
    return quote(record["iso"])


def write_mapping(registry: CountryRegistry) -> list[str]:
    lines = ["window.COUNTRY_TO_ISO = {"]
    for name, record in registry.records.items():
        lines.append(f"    {quote(name)}: {mapping_value(record)},")
    # Keep the final entry syntactically tidy without relying on a trailing
    # comma being accepted by an older browser.
    lines[-1] = lines[-1].rstrip(",")
    lines.append("};")
    return lines


def write_canonical_names(registry: CountryRegistry) -> list[str]:
    lines = ["window.COUNTRY_CANONICAL_NAMES = {"]
    for iso, name in registry.canonical_names.items():
        lines.append(f"    {iso}: {quote(name)},")
    lines[-1] = lines[-1].rstrip(",")
    lines.append("};")
    return lines


def write_map_aliases(registry: CountryRegistry) -> list[str]:
    aliases = registry.map.get("iso_aliases") or {}
    lines = ["window.MAP_ISO_ALIASES = {"]
    for child, parent in aliases.items():
        lines.append(f"    {child}: {quote(parent)},")
    if aliases:
        lines[-1] = lines[-1].rstrip(",")
    lines.append("};")
    return lines


def write_microstates(registry: CountryRegistry) -> list[str]:
    microstates = registry.map.get("microstates") or {}
    lines = ["window.MICROSTATE_LATLON = {"]
    for iso, coords in microstates.items():
        lon, lat = coords
        lines.append(f"    {iso}: [{lon:g}, {lat:g}],")
    if microstates:
        lines[-1] = lines[-1].rstrip(",")
    lines.append("};")
    return lines


def main() -> int:
    try:
        registry = load_registry()
        with CSV_PATH.open(newline="", encoding="utf-8") as fh:
            registry.validate_names(
                (row.get("country") or "" for row in csv.DictReader(fh)),
                "censorship_data.csv",
            )

        vpn = json.loads(VPN_PATH.read_text(encoding="utf-8"))
        vpn_names = [
            row.get("country", "") for row in vpn.get("restrictions", [])
        ]
        matrix_countries = (vpn.get("app_matrix") or {}).get("countries", [])
        vpn_names.extend(row.get("name", "") for row in matrix_countries)
        for row in matrix_countries:
            name = row.get("name", "")
            record = registry.resolve(name)
            if not record or record["iso"] != row.get("code"):
                raise ValueError(
                    f"vpn_data.json: matrix {name!r} has code {row.get('code')!r}, "
                    f"expected {record['iso'] if record else 'a registered ISO code'}"
                )
        vpn_names.extend(
            country.get("name", "")
            for region in (vpn.get("icloud_private_relay") or {}).get("regions", [])
            for country in region.get("countries", [])
        )
        registry.validate_names(vpn_names, "vpn_data.json")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    projection = registry.map.get("projection") or {}
    body = [
        "// Country names, aliases and map metadata generated from",
        "// country_registry.json by build_countries.py. The same registry is",
        "// validated against censorship_data.csv and vpn_data.json, and its",
        "// ISO codes are used by build_timezones.py.",
        "//",
        "// Every name in the source datasets must resolve here. Subnational",
        "// jurisdictions map to their parent ISO and are aggregated on the map.",
        *write_mapping(registry),
        "",
        *write_canonical_names(registry),
        "",
        "// Map-only territory aliases: data and dossiers stay keyed to the",
        "// sovereign country while the SVG may still paint a separate outline.",
        *write_map_aliases(registry),
        "",
        "window.mapIsoOf = function (iso) {",
        "    return (window.MAP_ISO_ALIASES || {})[iso] || iso;",
        "};",
        "",
        "window.mapPathsForIso = function (iso) {",
        "    const paths = [iso];",
        "    Object.entries(window.MAP_ISO_ALIASES || {}).forEach(([alias, parent]) => {",
        "        if (parent === iso) paths.push(alias);",
        "    });",
        "    return paths;",
        "};",
        "",
        "// Territories with no path in assets/world.svg are drawn as markers.",
        "// Coordinates are [longitude, latitude].",
        *write_microstates(registry),
        "",
        "// world.svg is a plain spherical Mercator on a 1009x651 viewBox.",
        "window.MAP_PROJECTION = { "
        f"k: {projection.get('k', 0)}, x0: {projection.get('x0', 0)}, "
        f"y0: {projection.get('y0', 0)} "
        "};",
        "",
        "window.projectLonLat = function (lon, lat) {",
        "    const { k, x0, y0 } = window.MAP_PROJECTION;",
        "    let l = lon;",
        "    while (l < -169.52) l += 360;",
        "    while (l > 190.48) l -= 360;",
        "    return {",
        "        x: k * (l * Math.PI / 180) + x0,",
        "        y: y0 - k * Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI / 180) / 2))",
        "    };",
        "};",
        "",
        "// Resolve a display name or alias to its ISO code.",
        "window.isoOf = function (name) {",
        "    const v = window.COUNTRY_TO_ISO[name];",
        "    return v && (v.iso || v);",
        "};",
        "",
        "// Resolve any recognized spelling to the registry's canonical display name.",
        "window.canonicalCountryName = function (name) {",
        "    const iso = window.isoOf(name);",
        "    return iso && window.COUNTRY_CANONICAL_NAMES[iso];",
        "};",
        "",
        "window.isSubnational = function (name) {",
        "    const v = window.COUNTRY_TO_ISO[name];",
        "    return !!(v && v.subnational);",
        "};",
        "",
        "window.subnationalNote = function (name) {",
        "    const v = window.COUNTRY_TO_ISO[name];",
        "    return (v && v.note) || '';",
        "};",
        "",
    ]
    OUT.write_text("\n".join(body), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(registry.records)} names, "
          f"{len(registry.canonical_names)} canonical ISO records")
    return 0


if __name__ == "__main__":
    sys.exit(main())
