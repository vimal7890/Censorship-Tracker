// Shared behaviour for every page: freshness, citations, and the vocabulary
// used to describe how well a claim is evidenced.
//
// These three things have to say exactly the same thing on all four pages, so
// they live here rather than being pasted into each one. Everything is
// same-origin and static — no third-party request has ever been made from this
// site, and adding one would be a real cost to a visitor reading it from a
// network that watches them.
window.Site = (function () {
    'use strict';

    var meta = null;
    var sources = null;

    function escapeHTML(value) {
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;')
            .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    // "2026-06-12" -> "12 Jun 2026". Returns '' for anything unparseable, so a
    // missing date renders as nothing rather than as "Invalid Date".
    function fmtDate(iso, opts) {
        if (!iso) return '';
        var d = new Date(String(iso).slice(0, 10) + 'T00:00:00Z');
        if (isNaN(d)) return '';
        return d.toLocaleDateString('en-GB', {
            day: 'numeric',
            month: (opts && opts.long) ? 'long' : 'short',
            year: 'numeric',
            timeZone: 'UTC'
        });
    }

    // How many whole days ago, as a phrase. Used to make a freshness date
    // legible at a glance ("14 Jul 2026 · 18 days ago") — a bare date makes the
    // reader do the arithmetic, which is the whole problem with a stale
    // "DATA AS OF" stamp nobody notices has gone off.
    function relativeDays(iso) {
        if (!iso) return '';
        var then = new Date(String(iso).slice(0, 10) + 'T00:00:00Z');
        if (isNaN(then)) return '';
        var now = new Date();
        var days = Math.floor((Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate())
            - then.getTime()) / 86400000);
        if (days < 0) return '';
        if (days === 0) return 'today';
        if (days === 1) return 'yesterday';
        if (days < 45) return days + ' days ago';
        var months = Math.round(days / 30.4);
        if (months < 18) return months + ' month' + (months === 1 ? '' : 's') + ' ago';
        return Math.round(days / 365) + ' years ago';
    }

    /* ---------------- Freshness ----------------
       Every page states two dates and derives both from meta.json, which is
       generated from the data's own git history (build_meta.py). Nothing on
       this site types a freshness date by hand any more — the previous
       hand-written "DATA AS OF: JUL 2026" had already drifted a week away from
       the file that records when the sources were actually checked. */

    function paintMeta(info) {
        var values = {
            'data-updated': fmtDate(info.data_updated),
            'data-updated-rel': relativeDays(info.data_updated),
            'sources-checked': fmtDate(info.sources_checked),
            'sources-checked-rel': relativeDays(info.sources_checked),
            'sources-count': info.sources_count ? String(info.sources_count) : '',
            'entries': info.censorship ? String(info.censorship.entries) : '',
            'platforms': info.censorship ? String(info.censorship.platforms) : '',
            'territories': info.censorship ? String(info.censorship.territories) : ''
        };
        Object.keys(values).forEach(function (key) {
            var text = values[key];
            document.querySelectorAll('[data-meta="' + key + '"]').forEach(function (el) {
                // An unknown value hides its whole readout rather than showing
                // a dash: a freshness claim we cannot substantiate should not
                // occupy space pretending to be one.
                var host = el.closest('[data-meta-row]') || el;
                if (!text) { host.hidden = true; return; }
                el.textContent = text;
                host.hidden = false;
            });
        });
    }

    function loadMeta() {
        if (meta) return Promise.resolve(meta);
        return fetch('meta.json', { cache: 'no-cache' })
            .then(function (res) { return res.ok ? res.json() : null; })
            .then(function (info) {
                if (!info) return null;
                meta = info;
                paintMeta(info);
                return info;
            })
            .catch(function () { return null; });
    }

    /* ---------------- Citations ----------------
       A citation used to render as "[47]", which tells a reader nothing about
       what they are about to open or how much weight it carries. sources.json
       (build_sources.py) supplies a publisher, a date and an evidence kind for
       every URL, so a citation can say "Reuters · Reporting · 12 Jun 2026". */

    var KIND_LABEL = {
        primary: 'Primary',
        measurement: 'Measurement',
        research: 'Research',
        reporting: 'Reporting',
        reference: 'Reference'
    };

    function loadSources() {
        if (sources) return Promise.resolve(sources);
        return fetch('sources.json', { cache: 'no-cache' })
            .then(function (res) { return res.ok ? res.json() : null; })
            .then(function (data) {
                sources = (data && data.sources) || {};
                return sources;
            })
            .catch(function () { sources = {}; return sources; });
    }

    // What we know about one URL. Falls back to the bare hostname so a citation
    // added since the last build still renders as a link to somewhere named,
    // rather than disappearing or rendering as "[undefined]".
    function source(url) {
        if (!url) return null;
        var entry = sources && sources[url];
        if (entry) return entry;
        var host = '';
        try { host = new URL(url).hostname.replace(/^www\./, ''); } catch (e) { host = url; }
        return { url: url, domain: host, publisher: host, kind: '', date: '', title: '' };
    }

    // Screen-reader text for a citation link. The visible chip is a short
    // publisher name; this spells out what the link is and where it goes, which
    // is the whole point of replacing a bare footnote number.
    function sourceLabel(url) {
        var s = source(url);
        if (!s) return '';
        var bits = ['Source: ' + s.publisher];
        if (s.title) bits.push(s.title);
        if (KIND_LABEL[s.kind]) bits.push(KIND_LABEL[s.kind].toLowerCase());
        if (s.date) bits.push(fmtDate(s.date, { long: true }));
        // Two different archive facts: `archived` means the URL itself is a
        // Wayback link; `snapshot` means the Archive holds a confirmed copy of
        // this live URL, taken by the weekly check while the page still exists.
        if (s.archived) bits.push('archived copy');
        else if (s.snapshot) bits.push('archived copy available');
        return bits.join(', ') + ' (opens in a new tab)';
    }

    // Compact citation for dense rows — the publisher's name, colour-coded by
    // evidence kind.
    function sourceChip(url) {
        var s = source(url);
        if (!s) return '';
        return '<a class="src-chip kind-' + escapeHTML(s.kind || 'other') + '"'
            + ' href="' + escapeHTML(url) + '" target="_blank" rel="noopener"'
            + ' aria-label="' + escapeHTML(sourceLabel(url)) + '">'
            + escapeHTML(s.publisher) + '</a>';
    }

    // Full citation card for a case file: what it is, who published it, when.
    // The title line only appears once verify_links.py has fetched a real one —
    // a URL slug is not a headline and is never dressed up as one.
    //
    // When the weekly check has confirmed an Internet Archive copy of this
    // source, a second small link offers it: if the original ever dies, the
    // evidence stays reachable instead of vanishing with the citation.
    function sourceCard(url) {
        var s = source(url);
        if (!s) return '';
        var meta = [];
        if (s.date) meta.push(fmtDate(s.date));
        meta.push(s.domain);
        if (s.archived) meta.push('archived');
        var lead = s.title
            ? '<span class="src-title">' + escapeHTML(s.title) + '</span>'
              + '<span class="src-pub">' + escapeHTML(s.publisher) + '</span>'
            : '<span class="src-title">' + escapeHTML(s.publisher) + '</span>';
        var card = '<a class="src-card kind-' + escapeHTML(s.kind || 'other') + '"'
            + ' href="' + escapeHTML(url) + '" target="_blank" rel="noopener"'
            + ' aria-label="' + escapeHTML(sourceLabel(url)) + '">'
            + '<span class="src-kind" aria-hidden="true">' + escapeHTML(KIND_LABEL[s.kind] || 'Source') + '</span>'
            + '<span class="src-body">' + lead
            + '<span class="src-meta">' + escapeHTML(meta.join(' · ')) + '</span></span>'
            + '<span class="src-go" aria-hidden="true">&#8599;</span></a>';
        if (!s.snapshot) return card;
        return card
            + ' <a class="src-chip kind-other"'
            + ' href="' + escapeHTML(s.snapshot) + '" target="_blank" rel="noopener"'
            + ' aria-label="Archived copy of ' + escapeHTML(sourceLabel(url)) + '">'
            + 'ARCHIVE</a>';
    }

    /* ---------------- Status and coverage vocabulary ----------------
       "Age verification" and "partial" were carrying too much: a law adopted
       last week that bites next year, a block OONI has measured for a decade,
       and a single news report all looked identical. These two axes split that
       apart — what stage the restriction is at, and how well the row is
       evidenced. Both are derived in build_status.py and written into the CSV. */

    var STATUS = {
        scheduled: { label: 'Scheduled', blurb: 'Adopted, but does not take effect until a future date.' },
        enforced: { label: 'Enforced', blurb: 'In effect, and a network measurement confirms it bites.' },
        in_force: { label: 'In force', blurb: 'In effect, established by an official instrument or the operator&rsquo;s own notice.' },
        reported: { label: 'Reported', blurb: 'In effect according to reporting or monitoring, with no instrument or measurement behind it.' }
    };

    var EVIDENCE = {
        dedicated: { label: 'Dedicated source', blurb: 'Cites a source about this platform in this territory.' },
        'country-default': { label: 'Country-wide fallback', blurb: 'Rests on a country-wide fact rather than a platform-specific citation — used for states that block nearly everything.' },
        uncorroborated: { label: 'Needs corroboration', blurb: 'Listed, but without a source of its own. Help us fix these.' }
    };

    // `since` dates go stale on their own, so whether something is still
    // scheduled is decided here at render time rather than trusted from the
    // file — the CSV's baked value is only ever the starting point.
    function effectiveStatus(row, startDate) {
        var declared = row && row.status;
        if (startDate && startDate.getTime() > Date.now()) return 'scheduled';
        if (declared === 'scheduled') return 'reported';  // its date has passed
        return STATUS[declared] ? declared : 'reported';
    }

    return {
        escapeHTML: escapeHTML,
        fmtDate: fmtDate,
        relativeDays: relativeDays,
        loadMeta: loadMeta,
        loadSources: loadSources,
        source: source,
        sourceLabel: sourceLabel,
        sourceChip: sourceChip,
        sourceCard: sourceCard,
        KIND_LABEL: KIND_LABEL,
        STATUS: STATUS,
        EVIDENCE: EVIDENCE,
        effectiveStatus: effectiveStatus,
        get meta() { return meta; }
    };
})();
