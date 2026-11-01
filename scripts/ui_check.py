"""Crawl the logged-in app at 1280px and 390px and fail on UI regressions.

Fails on: non-200 response, horizontal scroll, unlabelled form inputs and
WCAG AA contrast failures. Run via ``make ui-check`` (starts the container).
"""

from __future__ import annotations

import os
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ.get("UI_CHECK_URL", "http://localhost:8000")
USER = os.environ.get("UI_CHECK_USER", "demo")
PASSWORD = os.environ.get("UI_CHECK_PASSWORD", "DemoPass123!")
CHANNEL = os.environ.get("UI_CHECK_CHANNEL", "chrome")  # "" = bundled chromium
VIEWPORTS = {"desktop": (1280, 900), "mobile": (390, 844)}
PAGES = [
    "/",
    "/portfolio/",
    "/pipeline/",
    "/pipeline/kanban/",
    "/pipeline/list/",
    "/properties/",
    "/properties/compare/?ids=1&ids=2",
    "/properties/1/",
    "/analyze/1/",
    "/leasing/",
    "/vrm-properties/",
    "/hud-properties/",
    "/growth-explorer/",
    "/onboard/",
    "/brrrr/",
    "/markets/",
]

CHECKS = r"""() => {
  const out = {};
  out.hscroll = document.documentElement.scrollWidth > window.innerWidth + 1;
  out.unlabelled = [...document.querySelectorAll('input:not([type=hidden]):not([type=submit]):not([type=button]), select, textarea')]
    .filter(e => !(e.labels && e.labels.length) && !e.getAttribute('aria-label') && !e.getAttribute('aria-labelledby'))
    .map(e => e.name || e.id || e.type).slice(0, 15);
  function lum(c) { const m = c.match(/\d+(\.\d+)?/g); if (!m) return null; const [r,g,b] = m.slice(0,3).map(v => { v = v/255; return v <= 0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055, 2.4); }); return 0.2126*r + 0.7152*g + 0.0722*b; }
  function bg(el) { while (el) { const c = getComputedStyle(el).backgroundColor; if (c && !c.endsWith(', 0)') && c !== 'transparent') return c; el = el.parentElement; } return 'rgb(255,255,255)'; }
  const lows = new Map();
  [...document.querySelectorAll('body *')].filter(e => [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())).slice(0, 1500).forEach(e => {
    const s = getComputedStyle(e); if (s.visibility === 'hidden' || s.display === 'none') return;
    const a = lum(s.color), b = lum(bg(e)); if (a == null || b == null) return;
    const ratio = (Math.max(a,b)+0.05)/(Math.min(a,b)+0.05);
    const size = parseFloat(s.fontSize); const large = size >= 24 || (size >= 18.66 && +s.fontWeight >= 700);
    if (ratio < (large ? 3 : 4.5)) { const k = s.color + ' on ' + bg(e) + ' ' + ratio.toFixed(2); lows.set(k, (lows.get(k)||[]).concat([e.innerText.trim().slice(0,30)])); }
  });
  out.lowContrast = [...lows.entries()].slice(0, 8).map(([k, v]) => k + ' x' + v.length + ' e.g. "' + v[0] + '"');
  return out;
}"""


def check_page(page, path: str) -> list[str]:
    """Return the failures for one path; an unreachable page is a failure, not a crash."""
    try:
        resp = page.goto(BASE + path, wait_until="networkidle", timeout=30000)
    except Exception as exc:
        return [f"navigation failed: {str(exc)[:160]}"]
    failures = []
    if resp is None or resp.status != 200:
        failures.append(f"status {resp.status if resp else 'none'}")
    data = page.evaluate(CHECKS)
    if data["hscroll"]:
        failures.append("horizontal scroll")
    if data["unlabelled"]:
        failures.append("unlabelled inputs: " + ", ".join(data["unlabelled"]))
    failures += [f"contrast {c}" for c in data["lowContrast"]]
    return failures


def main() -> int:
    failed = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=CHANNEL or None)
        for label, (width, height) in VIEWPORTS.items():
            page = browser.new_context(
                viewport={"width": width, "height": height}
            ).new_page()
            page.goto(BASE + "/accounts/login/")
            page.fill("input[name=username]", USER)
            page.fill("input[name=password]", PASSWORD)
            page.locator(
                "form button[type=submit], form input[type=submit]"
            ).first.click()
            page.wait_for_load_state("networkidle")
            for path in PAGES:
                for failure in check_page(page, path):
                    failed += 1
                    print(f"FAIL {label} {path}: {failure}")
        browser.close()
    print(
        f"ui-check: {failed} failure(s) across {len(PAGES)} routes x {len(VIEWPORTS)} viewports"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
