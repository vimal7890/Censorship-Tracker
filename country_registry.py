#!/usr/bin/env python3
"""Load and validate the canonical country-name registry.

The data files keep human-readable country names because those names are part
of the public CSV/JSON exports.  This module is the single resolver behind
those names: the browser map, the VPN data checks, and the timezone generator
all consume the same ISO/canonical-name records.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent
REGISTRY_PATH = ROOT / "country_registry.json"
ISO_RE = re.compile(r"^[A-Z]{2}$")


class CountryRegistry:
    def __init__(self, payload: dict, path: Path = REGISTRY_PATH):
        self.path = path
        self.version = payload.get("version")
        self.entries = list(payload.get("entries") or [])
        self.aliases = list(payload.get("aliases") or [])
        self.map = dict(payload.get("map") or {})

        self._records: dict[str, dict] = {}
        self._canonical_by_iso: dict[str, dict] = {}
        self._load_records()
        self._validate_map()

    def _load_records(self) -> None:
        if self.version != 1:
            raise ValueError(f"{self.path.name}: unsupported registry version {self.version!r}")

        for entry in self.entries:
            self._add_record(entry, alias=False)
        for alias in self.aliases:
            self._add_record(alias, alias=True)

    def _add_record(self, raw: dict, *, alias: bool) -> None:
        if not isinstance(raw, dict):
            raise ValueError(f"{self.path.name}: registry records must be objects")
        name = raw.get("name")
        iso = raw.get("iso")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"{self.path.name}: every registry record needs a name")
        if not isinstance(iso, str) or not ISO_RE.fullmatch(iso):
            raise ValueError(f"{self.path.name}: {name!r} has invalid ISO code {iso!r}")
        name = name.strip()
        if name in self._records:
            raise ValueError(f"{self.path.name}: duplicate country name {name!r}")

        record = {"name": name, "iso": iso}
        if raw.get("subnational"):
            record["subnational"] = True
            if raw.get("note"):
                record["note"] = str(raw["note"])
        if alias:
            record["alias"] = True
        if alias and iso not in self._canonical_by_iso:
            raise ValueError(f"{self.path.name}: alias {name!r} points to unknown ISO {iso}")
        if not alias and not record.get("subnational") and iso in self._canonical_by_iso:
            previous = self._canonical_by_iso[iso]["name"]
            raise ValueError(
                f"{self.path.name}: ISO {iso} has multiple canonical names "
                f"({previous!r}, {name!r}); make one an alias"
            )

        self._records[name] = record

        # A subnational name intentionally shares its parent's ISO. The first
        # ordinary entry remains the display name for that ISO.
        if not alias and not record.get("subnational"):
            self._canonical_by_iso[iso] = record

    def _validate_map(self) -> None:
        map_aliases = self.map.get("iso_aliases") or {}
        if not isinstance(map_aliases, dict):
            raise ValueError(f"{self.path.name}: map.iso_aliases must be an object")
        for child, parent in map_aliases.items():
            if not ISO_RE.fullmatch(child) or not ISO_RE.fullmatch(parent):
                raise ValueError(f"{self.path.name}: invalid map ISO alias {child!r}: {parent!r}")
            if parent not in self._canonical_by_iso:
                raise ValueError(f"{self.path.name}: map alias parent {parent} is not registered")
            if child == parent:
                raise ValueError(f"{self.path.name}: map alias {child} points to itself")

        microstates = self.map.get("microstates") or {}
        if not isinstance(microstates, dict):
            raise ValueError(f"{self.path.name}: map.microstates must be an object")
        for iso, coords in microstates.items():
            if not ISO_RE.fullmatch(iso) or iso not in self._canonical_by_iso:
                raise ValueError(f"{self.path.name}: invalid or unregistered microstate {iso!r}")
            if not isinstance(coords, list) or len(coords) != 2:
                raise ValueError(f"{self.path.name}: invalid microstate {iso!r}")
            if not all(isinstance(v, (int, float)) for v in coords):
                raise ValueError(f"{self.path.name}: {iso} coordinates must be numeric")

    @property
    def records(self) -> dict[str, dict]:
        return dict(self._records)

    @property
    def canonical_names(self) -> dict[str, str]:
        return {iso: record["name"] for iso, record in self._canonical_by_iso.items()}

    @property
    def iso_codes(self) -> set[str]:
        return set(self._canonical_by_iso)

    @property
    def names(self) -> set[str]:
        return set(self._records)

    def resolve(self, name: str) -> dict | None:
        """Return the registry record for a canonical name or alias."""
        return self._records.get((name or "").strip())

    def canonical_name(self, iso: str) -> str | None:
        record = self._canonical_by_iso.get((iso or "").strip())
        return record["name"] if record else None

    def validate_names(self, names: Iterable[str], source: str) -> None:
        missing = sorted({(name or "").strip() for name in names if (name or "").strip()} - self.names)
        if missing:
            raise ValueError(
                f"{source}: country names missing from {self.path.name}: {missing}"
            )


def load_registry(path: Path = REGISTRY_PATH) -> CountryRegistry:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"{path.name} is missing") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path.name} is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name}: top level must be an object")
    return CountryRegistry(payload, path)
