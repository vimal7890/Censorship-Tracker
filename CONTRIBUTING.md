# Contributing

The tracker lives or dies on one thing: every row says something checkable,
and cites a page that actually checks it. Everything below follows from that.

## Reporting a restriction (no code needed)

Open a [restriction report](https://github.com/vimal7890/Censorship-Tracker/issues/new?template=report-restriction.yml)
with the platform, the territory, when it started, and — this is the part that
matters — a source you have personally opened that names **this platform in
this territory**. Reports without a usable source are welcome too (they become
leads), but they ship only once sourced.

To report something we got wrong — a lifted ban still listed, a wrong date, a
dead or unrelated citation — use the
[correction report](https://github.com/vimal7890/Censorship-Tracker/issues/new?template=report-error.yml).
Corrections are the most valuable contribution this project gets: a tracker
that only ever adds rows drifts into fiction.

## Editing the data directly

All restriction data is one CSV, [`censorship_data.csv`](censorship_data.csv);
the site derives everything else from it. The workflow:

1. Edit the CSV — columns are documented in [README.md](README.md) ("Editing
   the data"). Leave the derived `status` and `evidence` columns blank.
2. Run `python3 build.py`. It regenerates every derived file (status columns,
   prerender, static pages, feeds, changelog, meta) and runs the tests.
3. Open a PR. CI runs `python3 build.py --check` and fails if any generated
   file was forgotten.

## Source rules (the short version)

The full reasoning is in [README.md](README.md); the rules are:

- **A source must name this platform and this territory.** A country overview
  pasted across twenty rows evidences none of them.
- **Open the page yourself.** A 200 response is not a verification — plenty of
  sites answer missing pages with a success status.
- **Never invent or auto-substitute a URL.** No search-result links, no
  guessed slugs, no "close enough" articles. If you cannot find a real
  source, leave the field blank — an unsourced claim is recoverable, a
  confidently wrong citation is not.
- **No Wikipedia**, except a country's own internet-censorship article for
  rows in the five default-restricted countries (People's Republic of China,
  Eritrea, Islamic Republic of Iran, North Korea, Turkmenistan), and except
  when Wikipedia itself is the blocked platform.
- Good sources: government decrees and gazettes, court rulings, OONI
  measurements, Citizen Lab / Freedom House research, platform transparency
  or support pages, established news outlets.

## Licensing of contributions

By contributing you agree your changes ship under the repository's licenses:
code under [MIT](LICENSE), data under [CC BY 4.0](LICENSE-DATA).
