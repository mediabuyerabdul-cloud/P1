"""Local downloader bot.

Chalane ke liye (project folder se):  python src/downloader/app.py
Phir browser mein kholein:            http://127.0.0.1:5000
"""

from __future__ import annotations

import sys
import webbrowser
from pathlib import Path

from urllib.parse import urlsplit

from curl_cffi import requests
from flask import Flask, Response, jsonify, request, send_from_directory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from downloader import browser_fetch  # noqa: E402
from downloader.pdf_table import parse_pdf  # noqa: E402

STATIC = Path(__file__).parent / "static"

app = Flask(__name__, static_folder=None)
# Sirf PDF mein mile hue links hi download kiye ja sakte hain.
allowed_urls: set[str] = set()
browser = browser_fetch.BrowserFetcher()
# In jawabon par seedhi request ki jagah asli browser se dobara koshish hoti hai.
BLOCKED_STATUSES = {401, 403, 429}


def http_get(url: str):
    """File ko asli Chrome browser ki tarah maangta hai.

    Kai websites (jaise Lincoln Electric, loc.gov) aam Python requests ko
    HTTP 403 de deti hain, is liye Chrome jaisa connection istemaal hota hai.
    """
    parts = urlsplit(url)
    return requests.get(
        url,
        impersonate="chrome",
        headers={"Referer": f"{parts.scheme}://{parts.netloc}/"},
        timeout=(15, 120),
        allow_redirects=True,
    )


@app.get("/")
def index():
    return send_from_directory(STATIC, "index.html")


@app.post("/api/parse")
def parse():
    upload = request.files.get("pdf")
    if upload is None:
        return jsonify(error="PDF file nahi mili"), 400
    try:
        rows = parse_pdf(upload.read())
    except Exception as exc:  # noqa: BLE001 - user ko saaf error dikhana hai
        return jsonify(error=f"PDF parh nahi saka: {exc}"), 400
    if not rows:
        return jsonify(error="Is PDF mein Order/Chapter/Section/Visual/Source URL wala table nahi mila"), 400
    allowed_urls.update(r.url for r in rows)
    return jsonify(rows=[r.to_dict() for r in rows])


def download(url: str) -> tuple[int, bytes, str, str]:
    """Pehle seedhi request; website roke to asli browser se."""
    try:
        upstream = http_get(url)
        if upstream.status_code not in BLOCKED_STATUSES:
            content_type = upstream.headers.get("Content-Type") or "application/octet-stream"
            return upstream.status_code, upstream.content, content_type, upstream.url
    except requests.exceptions.RequestException:
        pass
    result = browser.get(url)
    return result.status_code, result.content, result.content_type, result.url


@app.get("/api/fetch")
def fetch():
    url = request.args.get("url", "")
    if url not in allowed_urls:
        return jsonify(error="Yeh link PDF mein nahi tha"), 403
    try:
        status, content, content_type, final_url = download(url)
    except Exception as exc:  # noqa: BLE001 - user ko saaf error dikhana hai
        return jsonify(error=f"Download fail: {exc}"), 502
    if status >= 400:
        return jsonify(error=f"Website ne mana kiya (HTTP {status})"), 502
    if "text/html" in content_type:
        return jsonify(error="Yeh web page hai, file nahi (khud khol kar dekhein)"), 422
    return Response(content, content_type=content_type, headers={"X-Final-Url": final_url})


def main() -> None:
    url = "http://127.0.0.1:5000"
    print(f"\n  Bot chal raha hai: {url}\n  Band karne ke liye is window mein Ctrl+C dabayein.\n")
    webbrowser.open(url)
    try:
        # threaded=False: browser (Playwright) ek hi thread se chalta hai.
        app.run(host="127.0.0.1", port=5000, threaded=False)
    finally:
        browser.close()


if __name__ == "__main__":
    main()
