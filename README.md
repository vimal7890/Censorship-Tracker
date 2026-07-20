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

- **China, North Korea and Turkmenistan** rows can leave `more_info` empty —
  the page substitutes a shared boilerplate about their default-restricted
  internet (see `HEAVY_CENSORSHIP` in `index.html`).
- Wrap fields containing commas or quotes in `"double quotes"` (standard CSV).
- A country may appear twice for one platform with different `type`s
  (e.g. X in Turkey has both a partial Grok block and an age rule). On the
  homepage those rows render as **one country label** with diagonal stripes
  mixing both type colours (purple age + orange partial), and a combined
  case file listing each restriction.
- New platforms need an icon + brand colour added to `PLATFORM_ICONS` /
  `PLATFORM_COLORS` in `index.html`; otherwise the row renders without a logo.
- **New country names need an ISO mapping** in
  [`assets/countries.js`](assets/countries.js) (`COUNTRY_TO_ISO`) so the world
  map can shade them — `tests/test_world_map.py` enforces this. Subnational
  jurisdictions (e.g. US states) map to their parent country with
  `{ iso: "US", subnational: true }` and are aggregated under it on the map.

## VPN service availability matrix

`app_matrix` in [`vpn_data.json`](vpn_data.json) drives the grid under the VPN
restrictions table: 15 providers (rows) × the restricted countries (columns),
each cell carrying one verdict — `available`, `restricted` or `blocked`.

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

## World map & derived sections

The homepage renders three derived views of the same CSV (no separate data):

- **Global Restriction Map** — [`assets/world.svg`](assets/world.svg)
  (amCharts worldLow outline, path ids are ISO 3166-1 alpha-2 codes) is
  fetched and inlined at runtime, then shaded by restriction count. Clicking
  a territory opens its dossier; if the SVG can't load, a country-card list
  renders instead.
- **By the Numbers** — hand-rolled SVG charts (per-platform stacked bars,
  type breakdown, per-year chart, top territories).
- **Most Recent Restrictions** — latest dated entries, parsed leniently from
  the free-text `since` column (undated values like "Forever" are skipped).
