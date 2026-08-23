#!/usr/bin/env python3
"""Who published a citation, and what kind of evidence is it?

Every claim on the site carries a source URL, which the pages used to render as
a bare footnote marker — `[47]`. That tells a reader nothing about what they are
about to open, and it hides the single most useful distinction in this dataset:
whether a row rests on the law itself, on a network measurement, or on somebody
reporting that a block happened.

This module turns a URL into three facts the pages can show:

  publisher   who put it out, in plain words ("Council of the European Union")
  kind        primary | measurement | research | reporting | reference
  date        publication date, only when the URL actually encodes one

Nothing here is invented. Publisher names come from the registry below, which
was written by hand against the domains the datasets actually cite. Dates are
read out of the URL path and are omitted when the path has none, rather than
guessed from anything else. Titles are not derived at all — a slug is not a
headline — so the `title` field stays empty until verify_links.py fetches the
real one from the page (it already issues a GET for every URL; see that script).

The kinds, and why the split matters:

  primary      the instrument or the operator's own notice — a decree, an act,
               a regulator's decision, a platform's help/transparency page. The
               strongest evidence that a restriction exists as a rule.
  measurement  somebody actually probed the network (OONI, Citizen Lab). The
               strongest evidence that a restriction is enforced in practice.
  research     sustained monitoring by an NGO or institute (Freedom House, HRW,
               CPJ, RSF, EFF, Access Now, Article 19).
  reporting    journalism.
  reference    encyclopedic. Wikipedia only, and only for the handful of
               countries whose internet is restricted by default (see README).
"""
from __future__ import annotations

import re
from datetime import date
from urllib.parse import unquote, urlparse

# --- Publisher registry -----------------------------------------------------
# domain -> (publisher, kind). Domains are stored bare (no scheme, no "www.").
# A missing domain is not an error: classify() falls back to the heuristics
# below and, failing those, to the domain itself as the publisher, so a newly
# cited outlet degrades to something honest rather than breaking the build.
REGISTRY: dict[str, tuple[str, str]] = {
    # -- Governments, legislatures and regulators (the instrument itself) -----
    "consilium.europa.eu": ("Council of the European Union", "primary"),
    "eur-lex.europa.eu": ("EUR-Lex (Official Journal of the EU)", "primary"),
    "planalto.gov.br": ("Presidency of the Republic (Brazil)", "primary"),
    "alusra.gov.ae": ("Government of the United Arab Emirates", "primary"),
    "pib.gov.in": ("Press Information Bureau (India)", "primary"),
    "capitol.texas.gov": ("Texas Legislature", "primary"),
    "legislation.gov.uk": ("UK legislation", "primary"),
    "gov.uk": ("UK Government", "primary"),
    "ofcom.org.uk": ("Ofcom", "primary"),
    "crtc.gc.ca": ("CRTC (Canada)", "primary"),
    "neplp.lv": ("NEPLP (Latvia)", "primary"),
    "flsenate.gov": ("Florida Senate", "primary"),
    "le.utah.gov": ("Utah Legislature", "primary"),
    "leg.colorado.gov": ("Colorado General Assembly", "primary"),
    "lis.virginia.gov": ("Virginia Legislative Information System", "primary"),
    "scstatehouse.gov": ("South Carolina Legislature", "primary"),
    "ag.ny.gov": ("New York Attorney General", "primary"),
    "oag.ca.gov": ("California Attorney General", "primary"),
    "legislature.idaho.gov": ("Idaho Legislature", "primary"),
    "esafety.gov.au": ("eSafety Commissioner (Australia)", "primary"),

    # -- Platforms' own notices (first-party, so also primary) ---------------
    "about.fb.com": ("Meta newsroom", "primary"),
    "help.grindr.com": ("Grindr support", "primary"),
    "help.netflix.com": ("Netflix help centre", "primary"),
    "help.openai.com": ("OpenAI help centre", "primary"),
    "support.spotify.com": ("Spotify support", "primary"),
    "newsroom.spotify.com": ("Spotify newsroom", "primary"),
    "support.apple.com": ("Apple support", "primary"),
    "docs.github.com": ("GitHub docs", "primary"),
    "github.blog": ("GitHub blog", "primary"),
    "blog.twitch.tv": ("Twitch blog", "primary"),
    "on.substack.com": ("Substack", "primary"),
    "protonvpn.com": ("Proton VPN", "primary"),
    "windscribe.com": ("Windscribe", "primary"),

    # -- Network measurement -------------------------------------------------
    "ooni.org": ("OONI", "measurement"),
    "explorer.ooni.org": ("OONI Explorer", "measurement"),
    "citizenlab.ca": ("Citizen Lab", "measurement"),

    # -- Sustained monitoring and legal research -----------------------------
    "freedomhouse.org": ("Freedom House", "research"),
    "hrw.org": ("Human Rights Watch", "research"),
    "cpj.org": ("Committee to Protect Journalists", "research"),
    "rsf.org": ("Reporters Without Borders", "research"),
    "eff.org": ("Electronic Frontier Foundation", "research"),
    "accessnow.org": ("Access Now", "research"),
    "article19.org": ("Article 19", "research"),
    "europeanjournalists.org": ("European Federation of Journalists", "research"),
    "business-humanrights.org": ("Business & Human Rights Resource Centre", "research"),
    "aclund.org": ("ACLU of North Dakota", "research"),
    "netchoice.org": ("NetChoice", "research"),
    "avpassociation.com": ("Age Verification Providers Association", "research"),
    "iapp.org": ("IAPP", "research"),
    "interface-eu.org": ("interface (Stiftung Neue Verantwortung)", "research"),
    "leave-russia.org": ("Leave Russia (KSE Institute)", "research"),
    "loeb.com": ("Loeb & Loeb", "research"),
    "troutmanprivacy.com": ("Troutman Pepper privacy blog", "research"),
    "sanctionsnews.bakermckenzie.com": ("Baker McKenzie sanctions news", "research"),
    "scotusblog.com": ("SCOTUSblog", "research"),
    "comparitech.com": ("Comparitech", "research"),
    "proprivacy.com": ("ProPrivacy", "research"),

    # -- Journalism ----------------------------------------------------------
    "reuters.com": ("Reuters", "reporting"),
    "apnews.com": ("Associated Press", "reporting"),
    "bbc.com": ("BBC News", "reporting"),
    "cnn.com": ("CNN", "reporting"),
    "theguardian.com": ("The Guardian", "reporting"),
    "washingtonpost.com": ("The Washington Post", "reporting"),
    "thegazette.com": ("The Gazette", "reporting"),
    "time.com": ("TIME", "reporting"),
    "variety.com": ("Variety", "reporting"),
    "deadline.com": ("Deadline", "reporting"),
    "techcrunch.com": ("TechCrunch", "reporting"),
    "techradar.com": ("TechRadar", "reporting"),
    "tomsguide.com": ("Tom's Guide", "reporting"),
    "bleepingcomputer.com": ("BleepingComputer", "reporting"),
    "therecord.media": ("The Record", "reporting"),
    "searchengineland.com": ("Search Engine Land", "reporting"),
    "computing.co.uk": ("Computing", "reporting"),
    "devactivity.com": ("DevActivity", "reporting"),
    "404media.co": ("404 Media", "reporting"),
    "reclaimthenet.org": ("Reclaim The Net", "reporting"),
    "courthousenews.com": ("Courthouse News Service", "reporting"),
    "aljazeera.com": ("Al Jazeera", "reporting"),
    "arabnews.com": ("Arab News", "reporting"),
    "malaymail.com": ("Malay Mail", "reporting"),
    "themoscowtimes.com": ("The Moscow Times", "reporting"),
    "meduza.io": ("Meduza", "reporting"),
    "en.zona.media": ("Mediazona", "reporting"),
    "rferl.org": ("Radio Free Europe / Radio Liberty", "reporting"),
    "rfa.org": ("Radio Free Asia", "reporting"),
    "voanews.com": ("Voice of America", "reporting"),
    "eurasianet.org": ("Eurasianet", "reporting"),
    "balkaninsight.com": ("Balkan Insight", "reporting"),
    "kathmandupost.com": ("The Kathmandu Post", "reporting"),
    "journalismpakistan.com": ("JournalismPakistan", "reporting"),
    "business-standard.com": ("Business Standard", "reporting"),
    "vietnamnet.vn": ("VietNamNet", "reporting"),
    "coconuts.co": ("Coconuts", "reporting"),
    "kun.uz": ("Kun.uz", "reporting"),
    "turkiyetoday.com": ("Türkiye Today", "reporting"),
    "aa.com.tr": ("Anadolu Agency", "reporting"),
    "en.royanews.tv": ("Roya News", "reporting"),
    "manassa.news": ("Al-Manassa", "reporting"),
    "dabangasudan.org": ("Radio Dabanga", "reporting"),
    "biometricupdate.com": ("Biometric Update", "reporting"),
    "loveingroup.com": ("Lovein Group", "reporting"),
    "mississippifreepress.org": ("Mississippi Free Press", "reporting"),
    "arkansasadvocate.com": ("Arkansas Advocate", "reporting"),
    "nebraskapublicmedia.org": ("Nebraska Public Media", "reporting"),
    "stlpr.org": ("St. Louis Public Radio", "reporting"),
    "xinhuanet.com": ("Xinhua (Chinese state media)", "reporting"),
    "observer.ug": ("The Observer (Uganda)", "reporting"),

    # -- Encyclopedic --------------------------------------------------------
    "en.wikipedia.org": ("Wikipedia", "reference"),
}

KIND_LABEL = {
    "primary": "Primary",
    "measurement": "Measurement",
    "research": "Research",
    "reporting": "Reporting",
    "reference": "Reference",
}

# What each badge means, shown in the pages' source legend.
KIND_BLURB = {
    "primary": "The instrument itself — a law, decree, regulator decision or the platform's own notice.",
    "measurement": "Network measurement: somebody probed the connection and recorded what happened.",
    "research": "Sustained monitoring or legal analysis by an NGO, institute or law firm.",
    "reporting": "Journalism.",
    "reference": "Encyclopedic. Used only for countries whose internet is restricted by default.",
}

# Ranked strongest-first, for picking the best source among several.
KIND_RANK = ["primary", "measurement", "research", "reporting", "reference"]

ARCHIVE_RE = re.compile(r"^https?://web\.archive\.org/web/(\d{4})(\d{2})(\d{2})\d*(?:\w+)?/(?P<url>https?://.+)$")

# Dates as they appear in URL paths: /2024/06/12/, /2024/06/, /2024-06-12-,
# /20240612/. Anything else is left undated rather than guessed at.
_DATE_PATTERNS = (
    re.compile(r"/(?P<y>20\d{2})/(?P<m>0[1-9]|1[0-2])/(?P<d>0[1-9]|[12]\d|3[01])(?:[/_-]|$)"),
    re.compile(r"[/_-](?P<y>20\d{2})-(?P<m>0[1-9]|1[0-2])-(?P<d>0[1-9]|[12]\d|3[01])(?:[/_.-]|$)"),
    re.compile(r"/(?P<y>20\d{2})(?P<m>0[1-9]|1[0-2])(?P<d>0[1-9]|[12]\d|3[01])(?:[/_-]|$)"),
    re.compile(r"/(?P<y>20\d{2})/(?P<m>0[1-9]|1[0-2])/(?:[^/]*)$"),
)


def domain_of(url: str) -> str:
    """Bare hostname, lowercased, without a leading www."""
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host.split(":")[0]


def unwrap_archive(url: str) -> tuple[str, str]:
    """Split a Wayback URL into (original URL, snapshot date).

    An archived page is still whatever it was before it was archived, so a
    Wayback link to a Reuters story should read as Reuters, not as
    "web.archive.org". Returns the URL unchanged and an empty date when it is
    not an archive link.
    """
    m = ARCHIVE_RE.match(url)
    if not m:
        return url, ""
    return unquote(m.group("url")), f"{m.group(1)}-{m.group(2)}-{m.group(3)}"


def date_from_url(url: str) -> str:
    """ISO date encoded in the URL path, or "" when it encodes none."""
    path = urlparse(url).path
    for pattern in _DATE_PATTERNS:
        m = pattern.search(path)
        if not m:
            continue
        y, mo = int(m.group("y")), int(m.group("m"))
        d = int(m.group("d")) if "d" in m.groupdict() and m.group("d") else 1
        try:
            parsed = date(y, mo, d)
        except ValueError:
            continue
        # A "date" from the future is a version number or an id, not a date.
        if parsed.year > date.today().year + 1:
            continue
        return parsed.isoformat()
    return ""


def _fallback_kind(host: str) -> str | None:
    """Classify an unregistered domain from its suffix, or give up.

    Only the government suffixes are safe to infer: a `.gov`, `.gov.xx` or
    `.gouv.fr` really is the state publishing its own instrument. Everything
    else needs a human to add a registry entry.
    """
    if host.endswith(".gov") or ".gov." in host or host.endswith(".gouv.fr"):
        return "primary"
    if host.endswith(".parliament.uk") or host.endswith(".europa.eu"):
        return "primary"
    return None


def classify(url: str) -> dict:
    """Everything the pages need to render one citation.

    Keys: url, domain, publisher, kind, date, archived, registered.
    `registered` is False when the publisher had to be guessed from the domain,
    which is what tests/test_sources.py asserts against so new citations do not
    quietly ship as bare hostnames. `archived` is True when the URL itself is a
    Wayback link (unwrap_archive above); verify_links.py additionally stores a
    `snapshot` / `snapshot_date` pair on entries it has confirmed a fresh
    Internet Archive copy of, which the citation cards offer as a fallback.
    """
    target, snapshot = unwrap_archive(url)
    host = domain_of(target)
    entry = REGISTRY.get(host)
    if entry:
        publisher, kind = entry
        registered = True
    else:
        kind = _fallback_kind(host) or "reporting"
        publisher = host
        registered = False
    return {
        "url": url,
        "domain": host,
        "publisher": publisher,
        "kind": kind,
        "date": date_from_url(target) or snapshot,
        "archived": bool(snapshot),
        "registered": registered,
    }
