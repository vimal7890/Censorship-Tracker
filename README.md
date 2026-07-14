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
  (e.g. X in Malaysia has both a partial Grok block and an age rule).
- New platforms need an icon + brand colour added to `PLATFORM_ICONS` /
  `PLATFORM_COLORS` in `index.html`; otherwise the row renders without a logo.
- **New country names need an ISO mapping** in
  [`assets/countries.js`](assets/countries.js) (`COUNTRY_TO_ISO`) so the world
  map can shade them — `tests/test_world_map.py` enforces this. Subnational
  jurisdictions (e.g. US states) map to their parent country with
  `{ iso: "US", subnational: true }` and are aggregated under it on the map.

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
