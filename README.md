# Global Censorship Tracker

A live index of banned, restricted and age-gated platforms worldwide.

## Building

Nothing about the site's own freshness, citation labels or change history is
written by hand — all of it is derived from the data and its git history. After
any data change, run:

```
python3 build.py
```

That regenerates everything in dependency order and then runs the tests.
`python3 build.py --check` verifies the generated files are current without
changing them, which is the right thing for CI. Individually:

| Script                | Generates                        | Why it exists                                                      |
|-----------------------|----------------------------------|--------------------------------------------------------------------|
| `build_sources.py`    | `sources.json`                   | Publisher, evidence kind and date for every cited URL              |
| `build_status.py`     | CSV `status` / `evidence` cols   | Grades each row's stage and how well it is sourced                 |
| `build_timezones.py`  | `assets/timezones.js`            | Time zone → country, for the client-side "use my region" guess     |
| `prerender.py`        | baked index in `index.html`      | Crawlers and no-JS visitors get the real list                      |
| `build_changelog.py`  | `changelog.json`, `feed.xml`     | Dated changelog and RSS, from the dataset's commits                |
| `build_meta.py`       | `meta.json`                      | The site's two freshness dates and its coverage counts             |

`verify_links.py` is deliberately *not* part of `build.py`: it fetches ~170
external URLs and belongs in a scheduled job, not in the loop between editing a
row and looking at it.

## Editing the data

All ban/restriction data lives in [`censorship_data.csv`](censorship_data.csv) —
the page loads it at runtime, so editing the CSV is all you need to do to
update the tracker. One row per platform+country entry:

| Column      | Meaning                                                                 |
|-------------|-------------------------------------------------------------------------|
| `platform`  | Platform name — must match a name in `PLATFORM_ICONS` for a logo to show |
| `country`   | Country name shown on the tag                                            |
| `since`     | Free-text date the restriction started                                   |
| `type`      | `complete` (red), `partial` (orange) or `age` (purple, age verification) |
| `more_info` | Case-file text shown when the tag is clicked                             |
| `source`    | URL cited as the reference                                               |
| `status`    | **Derived** — `scheduled`, `enforced`, `in_force` or `reported`          |
| `evidence`  | **Derived** — `dedicated`, `country-default` or `uncorroborated`         |

Leave the last two blank when adding a row; `build_status.py` fills them in.

Notes:

- **High quality source requirement:** Every source URL must be a high-quality, primary or reputable secondary reference (e.g., official government decrees, OONI network measurements, Citizen Lab reports, Freedom House / Freedom on the Net research, established news outlets like BBC, Reuters, AP, TechCrunch, or official platform support/transparency pages).
- **No Wikipedia, search-engine placeholders, or catch-all report spam:**
  - Do not use Wikipedia as a source unless Wikipedia itself is the platform being blocked.
  - **One narrow exception:** rows in the default-restricted countries — People's Republic of China,
    Eritrea, Islamic Republic of Iran, North Korea and Turkmenistan — may fall back to that
    country's own Wikipedia article (`Internet censorship in People's Republic of China`,
    `Internet in Turkmenistan`, …) when no platform-specific reporting exists.
    Nobody publishes "Tumblr is blocked in Turkmenistan"; they publish that
    almost everything is. Reach for it only after looking: Freedom House's
    *Freedom on the Net* country reports name platforms individually and are
    the better citation wherever they do. `verify_links.py` enforces exactly
    this — a Wikipedia URL cited by any row outside those five countries is
    still reported as a defect.
  - Do not copy-paste generic overview reports (e.g., CPJ's "10 Most Censored Countries" list) across dozens of unrelated platform rows. Each source MUST specifically document or verify the restriction for that specific platform and country.
  - If a platform in a default-restricted nation (e.g., North Korea, Turkmenistan, Eritrea, People's Republic of China) lacks a specific, dedicated high-quality source, leave `source` empty and let the country fallback system handle it — never attach generic drivel or catch-all URLs to pad rows.
- **Never invent a source URL, and never auto-replace one.** A batch of rows
  once cited plausible-looking articles — right domain, right slug style — that
  had never existed; the Wayback Machine had no snapshot of any of them. A
  later script "repaired" them with the first search-engine hit for keywords
  guessed from the URL, which attached real but unrelated pages to the claims.
  A source must be a page you have actually opened, that actually supports the
  specific row it sits on. If you cannot find one, leave the `source` field blank — an unsourced claim is recoverable, a confidently wrong citation is not.
- **Re-run [`prerender.py`](prerender.py) after editing the CSV.** The homepage
  renders its list from the CSV at runtime, but it also carries a *baked* copy
  of that list (between the `PRERENDER` markers in `index.html`) so crawlers and
  no-JS visitors get the full platform→countries index — the app overwrites it
  on load, and it doubles as the pre-hydration paint. `prerender.py` regenerates
  that block; `tests/test_prerender.py` fails if the CSV and the baked block
  drift, so a forgotten run is caught.
- Run [`verify_links.py`](verify_links.py) after editing sources. It reports
  dead URLs, Wikipedia citations and leftover search-engine placeholders, with
  the rows that cite each, and exits non-zero if any are found. On a **fully
  clean pass** it writes [`verified.json`](verified.json) (date + source count),
  which `build_meta.py` turns into the "Sources checked" date every page shows.
  The date only moves after a clean run, so it can never claim the citations
  were checked more recently than they actually were — if a single source is
  dead, no file is written and the old date stands.
- Since it already downloads every page, `verify_links.py` also records each
  one's `<title>` into `sources.json`, which is the **only** way a citation
  gains a headline. Titles are never derived from a URL slug: a slug is not a
  headline, and dressing one up as if it were would be inventing a citation in
  the least detectable way possible. A page that will not serve us keeps an
  empty title and its card falls back to publisher, kind and date.
- **A challenge page is not a headline either.** Cloudflare and friends answer
  with HTTP 200 and a page of their own, so the status check passes and the
  `<title>` reads `Just a moment...`. One run filed seven of those as headlines,
  including a "Vercel Security Checkpoint" under OONI's byline — a fabricated
  citation by any other name. `CHALLENGE_TITLES` in `verify_links.py` lists the
  titles that are not headlines; they are dropped on the way in and cleared from
  `sources.json` on the way out. It matches whole titles, never substrings,
  because on this site *Access Denied* and *captcha* are things real headlines
  say. `tests/test_source_titles.py` enforces both halves of that.
- **A 200 is not a verification.** The checker answers "does this URL resolve?"
  and nothing more, and a surprising number of sites answer a missing page with
  a 200: Intercom, Quartz, Reuters, Newsweek and Zoom's knowledge base all
  serve "page not found" bodies with a success status, and Moscow Times,
  Egypt Today and LSM article IDs get reassigned so the old link quietly lands
  on an unrelated story. Before trusting a source, open it and confirm it names
  this platform and this country.
- **People's Republic of China, Eritrea, North Korea and Turkmenistan** rows can leave `more_info`
  empty — the page substitutes a shared boilerplate about their
  default-restricted internet (see `HEAVY_CENSORSHIP` in `index.html`). The
  boilerplate is a **fallback**, not an override: a row that has something
  specific to say keeps its own text, and only empty rows borrow the shared
  sentence. So write `more_info` when the platform's situation differs from
  the country-wide default — that Zoom is throttled in People's Republic of China rather than
  outright banned, or that Spotify never listed Turkmenistan as a market —
  and leave it empty when the country default is the whole story.
- Wrap fields containing commas or quotes in `"double quotes"` (standard CSV).
- A country may appear twice for one platform with different `type`s
  (e.g. X in Türkiye has both a partial Grok block and an age rule). On the
  homepage those rows render as **one country label** with diagonal stripes
  mixing both type colours (purple age + orange partial), and a combined
  case file listing each restriction.
- New platforms need an icon + brand colour added to `PLATFORM_ICONS` /
  `PLATFORM_COLORS` in `index.html`; otherwise the row renders without a logo.
- **New country names need an ISO mapping** in
  [`assets/countries.js`](assets/countries.js) (`COUNTRY_TO_ISO`) so the world
  map can shade them — `tests/test_world_map.py` enforces this, and also
  enforces that the ISO code is actually drawable: either a path in
  `world.svg` or a `MICROSTATE_LATLON` entry that projects inside the viewBox.
  Subnational
  jurisdictions (e.g. US states) map to their parent country with
  `{ iso: "US", subnational: true }` and are aggregated under it on the map.

## Citations

Every source URL is classified by [`sources.py`](sources.py) into a publisher
and an evidence kind, written to `sources.json` by `build_sources.py`, and
rendered by `Site.sourceCard` / `Site.sourceChip`
([`assets/site.js`](assets/site.js)) as a card naming who published it rather
than a footnote number. `[47]` told a reader nothing about what they were about
to open, and hid the most useful distinction in the dataset: whether a row rests
on the law itself, on a network measurement, or on somebody reporting a block.

| Kind          | What it means                                                                   |
|---------------|---------------------------------------------------------------------------------|
| `primary`     | The instrument itself — decree, act, regulator decision, or the platform's notice |
| `measurement` | Somebody probed the network and recorded what happened (OONI, Citizen Lab)        |
| `research`    | Sustained monitoring or legal analysis (Freedom House, HRW, CPJ, EFF, law firms)  |
| `reporting`   | Journalism                                                                       |
| `reference`   | Encyclopedic — Wikipedia, only for the default-restricted countries              |

**Adding a citation from a new outlet means adding its domain to
`sources.REGISTRY`.** `tests/test_sources.py` fails otherwise: an unregistered
domain still renders, degraded to a bare hostname, which is exactly the kind of
quiet shabbiness that survives forever unless something fails.

Two things are derived and never guessed. **Dates** come out of the URL path
(`/2024/06/12/`) and are simply absent when the path has none. **Wayback links**
are unwrapped, so an archived Reuters story reads as Reuters with the snapshot
date, not as `web.archive.org`.

## Status and coverage

Three restriction types were doing too much work. A scheduled law with a future
start date, a Chinese block OONI has measured weekly for
a decade, and one news story saying a country started throttling something all
rendered identically. `build_status.py` splits that across two derived columns:

- **`status`** — what stage the restriction is at. `scheduled` (dated in the
  future), `enforced` (a measurement source), `in_force` (a primary source),
  `reported` (everything else).
- **`evidence`** — how well the row is covered. `dedicated` (a
  platform-specific source), `country-default` (rests on a country-wide fact:
  either the `HEAVY_CENSORSHIP` boilerplate or a country article cited in place
  of a real source), `uncorroborated` (no source at all).

Both are written into the CSV rather than computed in the browser, so they are
diffable, auditable and correctable — overwrite a cell by hand and the script
leaves it alone (`--force` re-derives everything). The one exception is
`scheduled`: the pages recompute it from the date at render time, because "is
this date in the future?" goes stale on its own.

`evidence` is what the coverage panel in Methodology counts. Showing that 38% of
the index rests on a country-wide fallback is more useful than implying all of
it is equally sourced, and the 22 rows marked `uncorroborated` are one click
away on the homepage — a tracker that hides its thin rows is asking to be
trusted on faith.

## What changed

[`changes.html`](changes.html) renders `changelog.json`, which
`build_changelog.py` derives by replaying the CSV commit by commit. Each change
has a stable anchor (`/changes#<short sha>`) so a single edit can be cited, and
`feed.xml` is an RSS feed of the same thing — followable without an account or
an email address.

Rows are keyed on (platform, country, type), so a partial block hardening into a
complete one shows as a removal plus an addition: that is a different
restriction, not an edited one. **Renames are pulled back out of that churn**,
because this repo's history is full of them ("Turkey" → "Türkiye", "China" →
"People's Republic of China") and left alone they read as 39 restrictions
appearing and 39 vanishing on the same day — alarming, and false. A removal and
an addition pair into a rename only when they differ in exactly one of platform
or country, agree on everything else, and the match is unambiguous. Anything
short of that stays reported as a removal and an addition: a wrong pairing would
misreport a real change as cosmetic.

## Freshness

Nothing states a date. All three pages once carried the string
`Data As Of: JUL 2026`, typed by hand into three files, and it had already
drifted a week from `verified.json`. `build_meta.py` writes `meta.json` with two
separate dates, and `Site.loadMeta` fills them into any element carrying
`data-meta`:

- **Data updated** — the newest commit touching any dataset file, or today when
  a dataset has uncommitted edits.
- **Sources checked** — when `verify_links.py` last confirmed every URL
  resolves.

They answer different questions ("we edited the data" and "we re-opened every
citation" are different promises) so they are shown as two lines.
`tests/test_freshness.py` fails if a hand-typed currency date reappears on any
page.

## Age verification timeline

The timeline on [`age-verification.html`](age-verification.html) is driven by
`timeline` in [`age_verification_data.json`](age_verification_data.json). Each
entry carries a `status` of `implemented` or `scheduled` — but **the badge on
the page is not read straight from that field**. The page compares
`implementation_date` (ISO `YYYY-MM-DD`) against today in the viewer's own
timezone, so a scheduled law promotes itself to *Implemented* on the morning it
takes effect, with no edit and no redeploy. Türkiye's under-15 ban flips in
late 2026 and Gabon's in February 2027.

So `status` records what was legislated and the page works out whether that
date has arrived. Keep writing `scheduled` for a future law; there is no need
to go back and change it later. Do remove an entry if the underlying law is
struck down before it can take effect.

One escape hatch: set `"auto_advance": false` on an entry whose date should not
be trusted to arrive on time — one still facing a court challenge, or where
implementation has visibly slipped — and it stays *Scheduled* until a human
says otherwise. Leave it off in the normal case.

## VPN service availability matrix

`app_matrix` in [`vpn_data.json`](vpn_data.json) drives the grid under the VPN
restrictions table: 15 providers (rows) × the restricted countries (columns),
each cell carrying one verdict — `available`, `restricted`, `blocked` or
`unavailable`.

`blocked` and `unavailable` are both red because the service is equally
unusable either way, but they have different causes and different fixes:
`blocked` is the state filtering the service, `unavailable` is the provider
withdrawing from the market. IPVanish is the worked example — it pulled its
apps from the Indian stores and closed Indian signups after CERT-In, and as a
US company it is barred from selling to Islamic Republic of Iran by sanctions. Because
`unavailable` is always provider-side, it may only appear as a per-provider
override, never as a country baseline; the test enforces that.

The verdict is about **whether the service works**, not whether the app is
listed in a store. Those are different questions and the store answer is the
less useful one: Pakistan leaves every VPN app in both stores and blocks the
tunnels at connection level instead.

Each country carries a `default` verdict plus a sourced `note`; a provider only
needs an `overrides` entry when reporting names it specifically, keyed by
country `code`:

```json
{ "name": "NordVPN", "overrides": { "PK": "blocked" } }
```

Country defaults exist because most regimes restrict circumvention tools
wholesale rather than provider-by-provider — the default expresses that
baseline, and per-provider evidence overrides it. Pakistan is the worked
example: a `restricted` baseline with the six providers named in reporting
overridden to `blocked`.

A `blocked` rating describes official standing and default-connection
behaviour, not a claim that access is impossible — the caveat rendered between
the grid and the country notes says so on the page, and the legal risk of
circumventing a block often exceeds the technical difficulty.

`tests/test_vpn_tracker.py` enforces that the matrix covers exactly the
countries in `restrictions`, that every verdict is one of the three valid
values, that no `overrides` key names an unknown country, and that the caveat
renders between the grid and the notes.

## Dark mode

All four pages follow the system light/dark preference automatically and have
a moon/sun toggle in the top bar ([`assets/theme.js`](assets/theme.js)). A
manual choice is saved to `localStorage` and shared across pages; picking the
theme that matches the system again returns to auto-sync. Styling rules:

- Every colour must be a CSS variable — no hardcoded hex in rules or in
  JS-generated SVG (use `var(--…)` in `fill`/`stroke` attributes).
- Dark values live in **two identical blocks** per page: `[data-theme="dark"]`
  (manual toggle) and the `prefers-color-scheme: dark` media query (system
  auto). Keep them in sync when adding a variable.
- Near-black brand colours in `PLATFORM_COLORS` are auto-swapped to the
  foreground colour in dark mode (`isDarkBrand` in `index.html`).

## Shared components

Citation cards, status and coverage badges, and the freshness
readout live in [`assets/site.css`](assets/site.css) and
[`assets/site.js`](assets/site.js) rather than being pasted into each page,
because they must say exactly the same thing everywhere. `site.css` may only use
CSS variables the pages already define, so it never needs a dark-mode copy of
its own.

## Fonts

The three families (Chivo, Source Sans 3, JetBrains Mono) are **self-hosted**
from [`assets/fonts/`](assets/fonts/) rather than fetched from Google Fonts.
That removes a third-party request on every page load — which matters for a
censorship tracker whose visitors may be on monitored networks — and the
render-blocking round-trip that came with it. Only the `latin` and `latin-ext`
subsets are vendored (the data is Latin script); the `@font-face` rules keep
their `unicode-range`s, so a face is only downloaded when a matching glyph is
actually used. To change weights or families, regenerate `fonts.css` and the
`.woff2` files together and keep every rule pointing at a file that exists.

## Homepage controls

The index can be narrowed four ways, and they compose: the **type filter**
(All / Complete / Partial / Age), a **saved view** (New in last 90 days,
Scheduled, Measured as blocking, Needs corroboration), a **country lens** (the
`In:` dropdown, one territory at a time) and free-text **search** (matches
platform *and* country names). It can also be **sorted** alphabetically, by most
territories, or by most recent. All of that, plus any open map dossier, is
mirrored into the URL hash (`#filter=age&view=new90&sort=recent&in=France&q=…`)
so any view can be bookmarked and shared.

Case-file panels are rendered lazily — the grid ships as light shells and a
panel's markup is built the first time it is opened — so editing search does not
rebuild 450+ hidden panels on every keystroke. Long rows collapse past 14
country chips (Russia Today alone spans 37, which buried everything under it),
and **Compact list** collapses every row to its heading so 49 platform names fit
on a screen or two. Deep links open whatever is hiding their target first.

An empty result offers to undo whichever narrowing actually caused it, rather
than leaving the visitor to guess which of four to clear.

### Country-first lookup

The question most visitors arrive with is "what applies where I am?", which used
to need a scroll to the map or a hunt through the filter row. The lookup block
sits above the search box and opens a territory's full dossier.

**Use my region** guesses from `Intl.DateTimeFormat().resolvedOptions().timeZone`
and a generated lookup table (`build_timezones.py`). Every other way of doing
this is wrong for this audience: the Geolocation API throws a permission prompt
and returns coordinates that then need a reverse-geocoding request, and IP
lookup services are a third-party request that tells someone else you were
reading a censorship tracker. Both leak. Reading the clock runs entirely inside
the page, with no prompt and no request. It is a guess — a VPN or a manually set
clock will fool it — so it fills the selector in rather than navigating, and
says what it guessed and from what.

## Accessibility

Things that were broken, are fixed, and are pinned by
`tests/test_accessibility.py` because they are easy to undo while tidying:

- The search field's visible `SEARCH_` is a real `<label for="searchBox">`, not
  a decorative `<span>` — the input previously had no accessible name at all.
- Citations carry a full description ("Source: Reuters, reporting, 12 June 2026,
  opens in a new tab") instead of the number `[47]`.
- Opening a country dossier moves focus to its heading, which takes
  `tabindex="-1"`. Clicking a country on the map used to leave a keyboard
  visitor parked on the map while the answer rendered somewhere below them.
- Revealing a case file from a dossier or the recent list focuses the chip it
  opened, expanding any collapsed row or chip overflow hiding it.
- Every form control on every page resolves to a name.

## VPN matrix on a small screen

15 providers against a dozen jurisdictions is a wide table anywhere and an
unusable one on a phone. Two ways out, neither of which hides data: narrow to a
single jurisdiction, or **Flip axes** so the long list runs down the page rather
than across it. Narrowing the table never narrows the country notes below it —
that is a way to read the data, not a claim the rest stopped applying.

## World map & derived sections

The homepage renders three derived views of the same CSV (no separate data):

- **Global Restriction Map** — [`assets/world.svg`](assets/world.svg)
  (amCharts worldLow outline, path ids are ISO 3166-1 alpha-2 codes) is
  fetched and inlined at runtime, then shaded by restriction count. Clicking
  a territory opens its dossier; if the SVG can't load, a country-card list
  renders instead.
  - The outline drops anything under roughly 1,000 km², so microstates and
    small island nations (Malta, Singapore, Bahrain, the Caribbean and Pacific
    states, Hong Kong, Macau) have **no path to shade**. Those are listed in
    `MICROSTATE_LATLON` in [`assets/countries.js`](assets/countries.js) as
    `[longitude, latitude]` and drawn at runtime as circular markers, projected
    with the same Mercator as the SVG (`window.projectLonLat`). A marker is
    only drawn for a territory that actually has data — rendering all of them
    would crowd the eastern Caribbean into an unreadable smear. To add one,
    put its coordinates in that table; no change to `world.svg` is needed.
- **By the Numbers** — hand-rolled SVG charts (per-platform stacked bars,
  type breakdown, per-year chart, top territories).
- **Most Recent Restrictions** — latest dated entries, parsed leniently from
  the free-text `since` column (undated values like "Forever" are skipped).
