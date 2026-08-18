#!/usr/bin/env python3
"""Regenerating unchanged data must not rewrite the generated files.

`build.py --check` works by running every generator and asking git whether
anything moved. That is only a usable check if a generator whose inputs did
not change leaves its output byte-for-byte alone — the first version of the
generators stamped a fresh generated_utc on every run, so the check always
found "drift" and could never pass in CI.

This runs the cheap generators twice and asserts the second run changes
nothing. (build_changelog.py is exercised the same way by build.py --check
itself; it is left out here only because replaying the CSV's history is slow.)
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# generator -> the files it owns
GENERATORS = {
    "build_sources.py": ["sources.json"],
    "build_meta.py": ["meta.json"],
    "build_timezones.py": ["assets/timezones.js"],
}


def run(script: str) -> None:
    res = subprocess.run([sys.executable, str(ROOT / script)], cwd=ROOT,
                         capture_output=True, text=True)
    assert res.returncode == 0, f"{script} failed:\n{res.stdout}{res.stderr}"


def main() -> int:
    for script, outputs in GENERATORS.items():
        run(script)
        before = {name: (ROOT / name).read_bytes() for name in outputs}
        run(script)
        for name in outputs:
            assert (ROOT / name).read_bytes() == before[name], (
                f"{script} rewrote {name} although nothing changed — "
                "a volatile field (generated_utc?) is being restamped, which "
                "makes build.py --check fail forever. Route the write through "
                "stable_write.write_json.")

    print(f"ok: {len(GENERATORS)} generators leave their output alone when nothing changed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
