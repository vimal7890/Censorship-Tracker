#!/usr/bin/env python3
"""Write a generated JSON file only when its content actually changed.

Every generator stamps its output with `generated_utc`, and that stamp used to
be its own change: regenerating an identical payload rewrote the file with a
fresh timestamp, so `python3 build.py --check` in a clean checkout always found
"drift" — four files different, none of them meaningfully. A check that always
fails protects nothing, and CI cannot run on it.

So generators route their writes through here. When everything except the
volatile timestamp keys is identical to what is already on disk, the file is
left byte-for-byte alone, timestamp included: the payload did not change, so
the claim about when it was generated should not move either. The stamp now
means "when this content last changed", which is the only reading of it a
visitor could ever check.
"""
from __future__ import annotations

import json
from pathlib import Path

# Keys that record when something was written rather than what was written.
# `generated_utc` is stamped by every generator; `titles_captured_utc` is
# stamped by verify_links.py into sources.json.
VOLATILE = ("generated_utc", "titles_captured_utc")


def write_json(path: Path, payload: dict, volatile: tuple[str, ...] = VOLATILE) -> bool:
    """Write `payload` to `path` unless only volatile keys differ.

    Returns True when the file was written, False when it was already current.
    """
    if path.is_file():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = None
        if isinstance(existing, dict):
            def stripped(d: dict) -> dict:
                return {k: v for k, v in d.items() if k not in volatile}
            if stripped(existing) == stripped(payload):
                return False
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return True
