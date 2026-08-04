#!/usr/bin/env python3
"""A citation's title must be a headline, never a CDN's challenge page.

verify_links.py records each source's <title> into sources.json so a citation
can show what the reader is about to open. Bot-protection interstitials break
that: they answer HTTP 200, so the status check passes, and their title is
"Just a moment...". A run in August 2026 filed seven of those as headlines —
Cloudflare challenges under the bylines of Eurasianet, Grindr and Computing,
and a "Vercel Security Checkpoint" under OONI's. A card claiming OONI published
"Vercel Security Checkpoint" is a fabricated citation, which is the one failure
mode this repo works hardest to prevent.

So this guards both ends of the rule:

  - the matcher rejects the challenge titles and keeps real headlines, including
    the ones that legitimately *contain* a challenge phrase. On a censorship
    tracker "Access Denied" and "captcha" are things headlines say, and short
    titles like "SB0142" are what legislatures actually call their bills.
  - no title already in sources.json is a challenge page.

Fix a failure by re-running:  python3 verify_links.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import verify_links  # noqa: E402

SOURCES_JSON = ROOT / "sources.json"

# Real interstitials seen in the wild, plus the casing and punctuation variants
# that must not be a way around the check.
CHALLENGE = [
    "Just a moment...",
    "JUST A MOMENT…",
    "  Just a moment.  ",
    "Vercel Security Checkpoint",
    "Access Denied",
    "Access to this page has been denied",
    "Attention Required! | Cloudflare",
    "Are you a robot?",
    "Verify you are human",
    "Please enable JavaScript",
    "Checking your browser before accessing",
    "One moment please",
    "403 Forbidden",
    "Too Many Requests",
    "Page not found",
]

# Titles that must survive. The last five are the trap: each contains a phrase
# from the reject list inside a real headline, which is why the matcher compares
# whole titles instead of looking for substrings.
HEADLINES = [
    "SB0142",
    "L15211",
    "Al Jazeera website becomes inaccessible in Pakistan | Journalism Pakistan",
    "89(R) History for SB 2420 | Texas Legislature Online",
    "Asia Chats: LINE and KakaoTalk Disruptions in China - The Citizen Lab",
    "Access Denied: Internet Shutdowns in 2025 | Access Now",
    "Why CAPTCHA is broken | The Guardian",
    "Just a moment in history: the 2011 blackout",
    "Error 404: how Russia rewrote its internet",
    "Page not found? Inside Turkmenistan's blocks | RFE/RL",
]


def main() -> int:
    missed = [t for t in CHALLENGE if not verify_links.is_challenge_title(t)]
    assert not missed, (
        f"{len(missed)} challenge page title(s) would be stored as headlines: {missed}")

    lost = [t for t in HEADLINES if verify_links.is_challenge_title(t)]
    assert not lost, (
        f"{len(lost)} real headline(s) would be thrown away as challenge pages: {lost}")

    assert not verify_links.is_challenge_title(""), "an empty title is absent, not a challenge"

    assert SOURCES_JSON.is_file(), "sources.json missing (run: python3 build_sources.py)"
    entries = json.loads(SOURCES_JSON.read_text(encoding="utf-8"))["sources"]
    stored = {
        url: entry["title"] for url, entry in entries.items()
        if verify_links.is_challenge_title(entry.get("title") or "")
    }
    assert not stored, (
        f"{len(stored)} citation(s) carry a challenge page as their headline "
        f"(run: python3 verify_links.py): {stored}")

    titled = sum(1 for e in entries.values() if (e.get("title") or "").strip())
    print(f"ok: {len(CHALLENGE)} challenge titles rejected, {len(HEADLINES)} headlines kept, "
          f"{titled}/{len(entries)} stored titles are real")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
