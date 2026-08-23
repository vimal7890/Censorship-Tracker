#!/usr/bin/env python3
"""Smoke-run the homepage's JavaScript headlessly, so a runtime error in the
render path fails the suite instead of shipping.

The August 2026 outage ("Failed to load censorship_data.csv — infoId is not
defined") was invisible to every existing test: the CSV parsed, the build was
green, and the defect only fired when a browser executed renderPlatforms. This
test extracts index.html's inline scripts, runs them under node against a stub
DOM and the real generated assets served over localhost, then asserts the
platform grid actually rendered rows rather than the failure banner.

Skipped (reported as ok) when node is unavailable; enforced in CI, which has it.
An optional argv[1] points at an HTML file other than index.html, for checking
a candidate edit before it lands.
"""
from __future__ import annotations

import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# A deliberately permissive DOM: the point is to execute real app code paths
# (scope errors, typos, bad template references) — not to lay out pages.
# Anything the script writes is recorded so the assertions can inspect what
# renderPlatforms actually produced.
HARNESS = r"""
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const root = process.argv[2];
const inlinePath = process.argv[3];
const BASE = process.env.SMOKE_BASE;

function magic(id) {
  const target = function () { return magic(); };
  target.__id = id || '';
  return new Proxy(target, {
    get(t, prop) {
      if (prop === Symbol.toPrimitive) return () => '';
      if (prop === 'length') return 0;
      if (prop === 'classList') return { add(){}, remove(){}, toggle(){ return false; }, contains(){ return false; } };
      if (prop === 'dataset') return {};
      if (prop === 'style') return {};
      if (prop === 'value' || prop === 'hidden') return '';
      if (prop === 'textContent' || prop === 'innerHTML') return t['__' + String(prop)] || '';
      if (prop === 'then') return undefined;           // never look like a promise
      if (['forEach','map','filter','querySelectorAll'].includes(prop)) return () => [];
      if (['addEventListener','removeEventListener'].includes(prop)) return () => {};
      if (prop === 'setAttribute') return (k, v) => { t['attr:' + k] = v; };
      if (prop === 'getAttribute') return (k) => t['attr:' + k] ?? null;
      if (['appendChild','focus','scrollIntoView','click','remove','setAttribute','insertAdjacentHTML'].includes(prop)) return () => {};
      if (prop === 'closest') return () => null;
      // Inside an injected subtree a querySelector finds *something* — the
      // world-map code walks its SVG after setting innerHTML.
      if (prop === 'querySelector') return () => magic(String(t.__id) + ':q');
      if (prop === 'getTime') return () => Date.now();
      const v = t[prop];
      if (v !== undefined) return v;
      return magic(String(t.__id) + '.' + String(prop));
    },
    set(t, prop, value) {
      if (prop === 'innerHTML' || prop === 'textContent') t['__' + String(prop)] = String(value);
      else t[prop] = value;
      return true;
    }
  });
}

const elements = {};
function elementById(id) {
  if (!elements[id]) elements[id] = magic('#' + id);
  return elements[id];
}

// Node's own fetch, captured before the stub below shadows it on globalThis.
const realFetch = global.fetch;

const sandbox = {
  console,
  setTimeout, clearTimeout, setInterval, clearInterval,
  queueMicrotask,
  URL,
  fetch: (input, init) => {
    const href = typeof input === 'string'
      ? new URL(input, BASE).href
      : new URL(input.url, BASE).href;   // Request object
    return realFetch(href, init);
  },
  Intl, Date, Math, JSON, Promise, Error,
  document: {
    getElementById: elementById,
    querySelector: () => null,
    querySelectorAll: () => [],
    createElement: (tag) => magic('<' + tag + '>'),
    createElementNS: () => magic('ns-el'),
    addEventListener: () => {},
    body: magic('body'),
    documentElement: magic('html'),
    activeElement: null,
    contains: () => false,
  },
  history: { replaceState(){}, pushState(){} },
  addEventListener: () => {},
  removeEventListener: () => {},
  innerWidth: 1280,
  innerHeight: 800,
  location: { hash: '', pathname: '/', href: BASE + '/', origin: BASE, protocol: 'http:' },
  navigator: { userAgent: 'smoke', language: 'en-GB' },
  localStorage: { getItem: () => null, setItem(){}, removeItem(){} },
  matchMedia: () => ({ matches: false, addEventListener(){}, addListener(){} }),
  requestAnimationFrame: (fn) => setTimeout(fn, 0),
  scrollTo(){},
};
sandbox.window = globalThis;
sandbox.globalThis = globalThis;
// Publish the stubs on the real global so classic scripts share one scope,
// exactly as they do in a browser: window.X set by one file is readable as
// bare X by the next. Keys Node itself owns (e.g. navigator in newer
// runtimes) keep their built-ins, which answer what the app reads.
for (const [key, value] of Object.entries(sandbox)) {
  try { globalThis[key] = value; } catch (e) { /* Node-owned global */ }
}

// Load the shared assets exactly as the page does, then the inline scripts.
for (const asset of ['assets/countries.js', 'assets/icons.js', 'assets/site.js']) {
  vm.runInThisContext(fs.readFileSync(path.join(root, asset), 'utf8'), { filename: asset });
}
vm.runInThisContext(fs.readFileSync(inlinePath, 'utf8'), { filename: 'index.html:inline' });

// The page kicks off its own init at load; give the async chain a moment,
// then inspect what landed in the grid.
setTimeout(() => {
  const html = (elements['platformGrid'] && elements['platformGrid'].__innerHTML) || '';
  const failed = /Failed to load/.test(html);
  const rows = (html.match(/class="platform-row"/g) || []).length;
  const tags = (html.match(/country-tag/g) || []).length;
  if (failed || rows === 0) {
    console.error(`SMOKE FAIL: rendered ${rows} platform row(s), ${tags} country tag(s); `
      + `failure banner present=${failed}`);
    console.error('grid snippet:', html.slice(0, 300));
    process.exit(1);
  }
  const feed = (elements['changeFeed'] && elements['changeFeed'].__innerHTML) || '';
  if (!feed.includes('change-row')) {
    console.error('SMOKE FAIL: the change feed rendered no events');
    process.exit(1);
  }
  console.log(`SMOKE OK: ${rows} platform rows, ${tags} country tags, change feed filled`);
  process.exit(0);
}, 1500);
"""


def extract_inline_scripts(text: str) -> str:
    """All classic <script> blocks without src=, concatenated in document order."""
    scripts = re.findall(r"(<script\b[^>]*>)(.*?)</script>", text, re.S | re.I)
    keep = []
    for open_tag, body in scripts:
        if re.search(r'\bsrc\s*=', open_tag, re.I):
            continue
        if re.search(r'<script\s+type\s*=', open_tag, re.I):
            continue  # JSON-LD and friends are data, not code
        keep.append(body)
    assert keep, "no inline script blocks found"
    return "\n;\n".join(keep)


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def main(argv: list[str]) -> int:
    node = shutil.which("node")
    if not node:
        print("ok-skipped: node not available; frontend smoke not exercised here")
        return 0

    # argv[0], if given, is an alternative HTML file (e.g. a candidate edit or
    # a known-bad checkout used to validate this checker itself).
    page = Path(argv[0]) if argv else ROOT / "index.html"
    html = page.read_text(encoding="utf-8")

    with tempfile.TemporaryDirectory() as tmp:
        inline = Path(tmp) / "inline.js"
        inline.write_text(extract_inline_scripts(html), encoding="utf-8")
        harness = Path(tmp) / "harness.js"
        harness.write_text(HARNESS, encoding="utf-8")

        port = free_port()
        server = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
            cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.6)
        try:
            result = subprocess.run(
                [node, str(harness), str(ROOT), str(inline)],
                capture_output=True, text=True, timeout=60,
                env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
                     "SMOKE_BASE": f"http://127.0.0.1:{port}"})
            print((result.stdout + result.stderr).strip())
            return result.returncode
        finally:
            server.terminate()
            server.wait()


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
