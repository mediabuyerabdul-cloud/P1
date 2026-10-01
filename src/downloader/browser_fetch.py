"""Asli browser (Chrome ya Edge) se file download karna.

Kuch websites (jaise Lincoln Electric) Python ki request ko HTTP 403 deti hain,
lekin browser mein wahi link khul jata hai. Is liye jab seedhi request fail ho,
bot computer par installed Chrome/Edge khol kar wahi link us mein kholta hai
aur jo file aati hai woh save kar leta hai.

Playwright ka sync API ek hi thread se chalna chahiye, is liye Flask server
threaded=False chalta hai (downloads waise bhi ek ek kar ke hote hain).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

# Test ya khaas setup ke liye browser ka poora path yahan diya ja sakta hai.
BROWSER_PATH_ENV = "DOWNLOADER_BROWSER"


@dataclass
class BrowserResponse:
    status_code: int
    content: bytes
    content_type: str
    url: str


class BrowserFetcher:
    def __init__(self) -> None:
        self._playwright = None
        self._context = None
        self._page = None

    def _launch(self):
        self._playwright = sync_playwright().start()
        chromium = self._playwright.chromium
        path = os.environ.get(BROWSER_PATH_ENV)
        attempts = [{"executable_path": path}] if path else [{"channel": "chrome"}, {"channel": "msedge"}]
        last_error = None
        for options in attempts:
            try:
                browser = chromium.launch(headless=False, **options)
                break
            except PlaywrightError as exc:
                last_error = exc
        else:
            raise RuntimeError("Chrome ya Edge nahi mila. Google Chrome install karein.") from last_error
        self._context = browser.new_context(accept_downloads=False)
        self._page = self._context.new_page()

    def get(self, url: str) -> BrowserResponse:
        if self._page is None or self._page.is_closed():
            if self._playwright is not None:
                self.close()
            self._launch()
        response = self._page.goto(url, wait_until="commit", timeout=120_000)
        if response is None:
            raise RuntimeError("Browser ko jawab nahi mila")
        return BrowserResponse(
            status_code=response.status,
            content=response.body(),
            content_type=response.headers.get("content-type", "application/octet-stream"),
            url=response.url,
        )

    def close(self) -> None:
        try:
            if self._context is not None:
                self._context.browser.close()
            if self._playwright is not None:
                self._playwright.stop()
        except PlaywrightError:
            pass
        self._playwright = self._context = self._page = None
