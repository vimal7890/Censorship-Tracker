# Global Censorship Tracker

A live index of banned, restricted and age-gated platforms worldwide.

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
| `source`    | URL cited as the numbered reference                                      |

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
  clean pass** it writes [`verified.json`](verified.json) (date + source count);
  the homepage reads that file and shows a "Sources Verified: &lt;date&gt;"
  badge in the ticker. The badge only appears after a clean run, so it can never
  claim the citations were checked more recently than they actually were — if a
  single source is dead, no file is written and no badge shows.
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

## Age verification timeline

The timeline on [`age-verification.html`](age-verification.html) is driven by
`timeline` in [`age_verification_data.json`](age_verification_data.json). Each
entry carries a `status` of `implemented` or `scheduled` — but **the badge on
the page is not read straight from that field**. The page compares
`implementation_date` (ISO `YYYY-MM-DD`) against today in the viewer's own
timezone, so a scheduled law promotes itself to *Implemented* on the morning it
takes effect, with no edit and no redeploy. France's under-15 ban flips on
2026-09-01, Türkiye's on 2026-10-01, Gabon's in February 2027.

So `status` records what was legislated and the page works out whether that
date has arrived. Keep writing `scheduled` for a future law; there is no need
to go back and change it later.

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

All three pages follow the system light/dark preference automatically and have
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

The index can be narrowed three ways, and they compose: the **type filter**
(All / Complete / Partial / Age), a **country lens** (the `In:` dropdown, one
territory at a time) and free-text **search** (matches platform *and* country
names). All three, plus any open map dossier, are mirrored into the URL hash
(`#filter=age&in=France&q=…&country=FR`) so any view can be bookmarked and
shared. Case-file panels are rendered lazily — the grid ships as light shells
and a panel's markup is built the first time it is opened — so editing search
does not rebuild 450+ hidden panels on every keystroke.

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
