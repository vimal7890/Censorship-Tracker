#!/usr/bin/env python3
"""Run every generator, in order, then the tests.

The site now derives five files from the data instead of restating it by hand —
sources.json, the CSV's status/evidence columns, meta.json, changelog.json and
feed.xml, plus the prerendered index. They have to be regenerated after any data
change, and the order matters: statuses are graded from the source registry, and
meta.json counts the statuses.

    python3 build.py            # regenerate everything, then run the tests
    python3 build.py --check    # fail if anything is out of date, change nothing

Link checking is deliberately not part of this: verify_links.py fetches 170-odd
external URLs and belongs in a scheduled job, not in the loop between editing a
row and seeing it.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# (script, args, why it comes here)
STEPS = [
    ("build_sources.py", [], "publisher and evidence kind for every citation"),
    ("build_status.py", [], "grade each row's stage and coverage — needs sources.json"),
    ("build_timezones.py", [], "time zone to country, for the client-side region guess"),
    ("prerender.py", [], "bake the index for crawlers and no-JS visitors"),
    ("build_changelog.py", [], "changelog and RSS from the dataset's git history"),
    ("build_meta.py", [], "freshness and counts — needs the status columns"),
]


def run(script: str, args: list[str]) -> int:
    print(f"\n$ python3 {script} {' '.join(args)}".rstrip())
    return subprocess.run([sys.executable, str(ROOT / script), *args], cwd=ROOT).returncode


def main(argv: list[str]) -> int:
    check = "--check" in argv
    failed: list[str] = []

    for script, args, why in STEPS:
        # Only build_status.py has a --check mode; in check mode the rest are
        # run normally and git is asked afterwards whether anything moved.
        extra = args + (["--check"] if check and script == "build_status.py" else [])
        if run(script, extra) != 0:
            failed.append(script)

    if check:
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                               capture_output=True, text=True).stdout.strip()
        if dirty:
            print("\nGenerated files are out of date — run: python3 build.py\n" + dirty)
            failed.append("generated files")

    print("\n$ tests")
    for test in sorted((ROOT / "tests").glob("test_*.py")):
        result = subprocess.run([sys.executable, str(test)], cwd=ROOT,
                                capture_output=True, text=True)
        status = "ok  " if result.returncode == 0 else "FAIL"
        print(f"  {status} {test.name}")
        if result.returncode != 0:
            print((result.stdout + result.stderr).rstrip())
            failed.append(test.name)

    if failed:
        print(f"\n{len(failed)} step(s) failed: {', '.join(failed)}")
        return 1
    print("\nall generators ran and every test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
