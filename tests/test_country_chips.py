#!/usr/bin/env python3
"""The platform list must show every country chip without an overflow toggle."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"


def main() -> int:
    index = INDEX.read_text(encoding="utf-8")

    # A long platform row is intentionally allowed to grow; no country may be
    # hidden behind a "more" button or made visible only after a second click.
    for removed in ("CHIP_LIMIT", "chip-more", "toggleChipOverflow", "data-more"):
        assert removed not in index, f"index.html still contains the old chip overflow control: {removed}"
    assert "country-tag.overflow" not in index, "index.html still hides overflow country chips"

    # The renderer must map directly over every grouped country and emit the
    # ordinary visible chip class, without a hidden attribute or overflow suffix.
    assert "${groups.map(g => {" in index, "country renderer no longer maps every group"
    assert re.search(
        r'class="country-tag \$\{cls\}"\$\{style\} title=',
        index,
    ), "country chips are not rendered as visible buttons"

    print("ok: every country chip renders directly with no overflow control")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
