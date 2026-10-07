"""Read public YouTube search results with a real browser — no API key, no login.

Given a topic, open youtube.com/results, read the top videos' view counts and
ages from the page's embedded `ytInitialData`, and turn them into the two
numbers Phase 1 scores on:
  - avg_views        = median views of the top results  (DEMAND)
  - competing_videos = how many top results are recent   (SATURATION)

Figures are approximate: YouTube rounds "1.2M views" and may change its page,
so the parser is defensive and the numbers are overridable in the UI.
"""

from __future__ import annotations

import json
import re
import statistics

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

BROWSER_PATH_ENV = "DOWNLOADER_BROWSER"  # reuse the downloader's optional override


# ---- parsing (pure, unit-tested) -------------------------------------------

def _find_all(obj, key, out):
    """Collect every value stored under `key`, in document order."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                out.append(v)
            _find_all(v, key, out)
    elif isinstance(obj, list):
        for v in obj:
            _find_all(v, key, out)
    return out


def extract_initial_data(html: str) -> dict:
    m = re.search(r"ytInitialData\s*=\s*({.*?})\s*;\s*</script>", html, re.S)
    if not m:
        m = re.search(r"ytInitialData\s*=\s*({.*?})\s*;", html, re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return {}


def _text(node) -> str:
    if not isinstance(node, dict):
        return ""
    if "simpleText" in node:
        return node["simpleText"]
    if "runs" in node:
        return "".join(r.get("text", "") for r in node["runs"] if isinstance(r, dict))
    return ""


_VIEW_RE = re.compile(r"([\d.,]+)\s*([KMB]?)", re.I)
_MULT = {"": 1, "K": 1_000, "M": 1_000_000, "B": 1_000_000_000}


def parse_views(text: str) -> int:
    m = _VIEW_RE.search((text or "").replace(",", ""))
    if not m:
        return 0
    return int(float(m.group(1)) * _MULT[m.group(2).upper()])


_AGE_RE = re.compile(r"(\d+)\s*(second|minute|hour|day|week|month|year)", re.I)
_PER_MONTH = {"second": 0, "minute": 0, "hour": 0, "day": 1 / 30, "week": 1 / 4.3, "month": 1, "year": 12}


def parse_age_months(text: str):
    m = _AGE_RE.search(text or "")
    return int(m.group(1)) * _PER_MONTH[m.group(2).lower()] if m else None


def parse_search(html: str) -> list[dict]:
    items = []
    for vr in _find_all(extract_initial_data(html), "videoRenderer", []):
        if not isinstance(vr, dict):
            continue
        title = _text(vr.get("title", {}))
        if title:
            items.append({
                "title": title,
                "views": parse_views(_text(vr.get("viewCountText", {}))),
                "age_months": parse_age_months(_text(vr.get("publishedTimeText", {}))),
            })
    return items


def topic_stats(items: list[dict], top: int = 10, recent_months: int = 6) -> dict:
    top_items = items[:top]
    views = [i["views"] for i in top_items if i["views"] > 0]
    recent = sum(1 for i in top_items if i["age_months"] is not None and i["age_months"] <= recent_months)
    return {
        "avg_views": int(statistics.median(views)) if views else 0,
        "competing_videos": max(recent, 1),
        "sample": len(top_items),
    }


# ---- live fetch (needs a browser; runs on the user's machine) --------------

class YouTubeBrowser:
    def __init__(self):
        self._pw = None
        self._page = None

    def _launch(self):
        import os
        self._pw = sync_playwright().start()
        path = os.environ.get(BROWSER_PATH_ENV)
        attempts = [{"executable_path": path}] if path else [{"channel": "chrome"}, {"channel": "msedge"}]
        last = None
        for opts in attempts:
            try:
                browser = self._pw.chromium.launch(headless=True, **opts)
                break
            except PlaywrightError as exc:
                last = exc
        else:
            raise RuntimeError("Chrome ya Edge nahi mila. Google Chrome install karein.") from last
        ctx = browser.new_context(locale="en-US")
        # Skip the EU consent interstitial so ytInitialData is on the first page.
        ctx.add_cookies([{"name": "SOCS", "value": "CAI", "domain": ".youtube.com", "path": "/"}])
        self._page = ctx.new_page()

    def search(self, query: str) -> str:
        if self._page is None or self._page.is_closed():
            self._launch()
        url = "https://www.youtube.com/results?search_query=" + query.replace(" ", "+") + "&hl=en&gl=US"
        self._page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        return self._page.content()

    def stats_for(self, query: str) -> dict:
        return topic_stats(parse_search(self.search(query)))

    def close(self):
        try:
            if self._page is not None:
                self._page.context.browser.close()
            if self._pw is not None:
                self._pw.stop()
        except PlaywrightError:
            pass
        self._pw = self._page = None
