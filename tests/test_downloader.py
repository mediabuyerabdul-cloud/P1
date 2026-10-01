import io

import pymupdf
import pytest

from downloader import app as app_module
from downloader.pdf_table import parse_pdf

HEADER = ["Order", "Chapter", "Section", "Visual #", "Asset", "Source URL"]
HEADER_X = [50, 70, 95, 120, 150, 210]
ROWS = [
    ("1", "1", "1.1", "1", "https://www.shutterstock.com/video/clip-1", True),
    ("2", "1", "1.1", "2", "https://example.com/a/135.jpg", False),
    ("3", "2", "2.1", "7", "https://example.com/page", False),
]


def make_pdf(rows=ROWS) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=792, height=612)
    for x, text in zip(HEADER_X, HEADER):
        page.insert_text((x, 58), text, fontsize=4)
    y = 63.0
    for order, ch, sec, vis, url, red in rows:
        if red:
            page.draw_rect(pymupdf.Rect(210, y - 4, 527, y + 1), color=None, fill=(1, 0, 0))
        for x, text in zip(HEADER_X, [order, ch, sec, vis, "x", url]):
            page.insert_text((x + 1, y), text, fontsize=3)
        page.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(211, y - 3.5, 400, y + 0.5), "uri": url})
        y += 5
    return doc.tobytes()


def test_parse_pdf_reads_columns_and_red_rows():
    rows = parse_pdf(make_pdf())
    assert [(r.order, r.chapter, r.section, r.visual, r.url, r.red) for r in rows] == list(ROWS)


@pytest.fixture
def client():
    app_module.allowed_urls.clear()
    return app_module.app.test_client()


class FakeResponse:
    def __init__(self, content=b"", content_type="image/jpeg", status_code=200, url=""):
        self.content, self.status_code, self.url = content, status_code, url
        self.headers = {"Content-Type": content_type}


def test_parse_endpoint_returns_rows(client):
    res = client.post("/api/parse", data={"pdf": (io.BytesIO(make_pdf()), "t.pdf")})
    assert res.status_code == 200
    assert [r["red"] for r in res.get_json()["rows"]] == [True, False, False]


def test_fetch_refuses_urls_not_in_pdf(client):
    assert client.get("/api/fetch?url=http://127.0.0.1/secret").status_code == 403


def test_fetch_returns_file_and_rejects_html(client, monkeypatch):
    client.post("/api/parse", data={"pdf": (io.BytesIO(make_pdf()), "t.pdf")})

    def fake_get(url):
        if url.endswith(".jpg"):
            return FakeResponse(b"JPEGDATA", "image/jpeg", url=url)
        return FakeResponse(b"<html>", "text/html; charset=utf-8", url=url)

    monkeypatch.setattr(app_module, "http_get", fake_get)
    ok = client.get("/api/fetch?url=https://example.com/a/135.jpg")
    assert ok.status_code == 200 and ok.data == b"JPEGDATA"
    assert client.get("/api/fetch?url=https://example.com/page").status_code == 422
