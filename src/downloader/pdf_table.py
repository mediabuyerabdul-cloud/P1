"""PDF table se rows nikalna: Order, Chapter, Section, Visual # aur Source URL.

Har row ka Source URL ek clickable link hota hai. Agar us row ke Source URL
cell ke peeche laal (red) rang bhara ho to row "red" mani jati hai aur skip hoti hai.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import pymupdf

COLUMNS = ("Order", "Chapter", "Section", "Visual", "Source")


@dataclass
class Row:
    order: str
    chapter: str
    section: str
    visual: str
    url: str
    red: bool

    def to_dict(self) -> dict:
        return asdict(self)


def _is_red(color) -> bool:
    if not color:
        return False
    r, g, b = color[:3]
    return r > 0.8 and g < 0.3 and b < 0.3


def _header_positions(page) -> dict[str, float] | None:
    found = {}
    header_y = None
    words = page.get_text("words")
    for x0, y0, x1, y1, text, *_ in words:
        word = text.strip().rstrip("#")
        if word in COLUMNS and word not in found:
            found[word] = x0
            header_y = y0
    if len(found) != len(COLUMNS):
        return None
    # "Visual #" column ka end: header line par Visual ke baad wala pehla column.
    after = [w[0] for w in words if abs(w[1] - header_y) < 1 and w[0] > found["Visual"] and w[4] != "#"]
    found["VisualEnd"] = min(after, default=found["Source"])
    return found


def _cell(words, y_mid: float, x_from: float, x_to: float) -> str:
    parts = [w[4] for w in words if w[1] <= y_mid <= w[3] and x_from - 1 <= w[0] < x_to - 1]
    return " ".join(parts).strip()


def parse_pdf(data: bytes) -> list[Row]:
    rows: list[Row] = []
    header = None
    with pymupdf.open(stream=data, filetype="pdf") as doc:
        for page in doc:
            header = _header_positions(page) or header
            if header is None:
                continue
            words = page.get_text("words")
            red_boxes = [d["rect"] for d in page.get_drawings() if _is_red(d.get("fill"))]
            src_x = header["Source"]
            links = [
                l for l in page.get_links()
                if l.get("uri") and abs(l["from"].x0 - src_x) < 5
            ]
            for link in sorted(links, key=lambda l: l["from"].y0):
                box = link["from"]
                y_mid = (box.y0 + box.y1) / 2
                rows.append(
                    Row(
                        order=_cell(words, y_mid, header["Order"], header["Chapter"]),
                        chapter=_cell(words, y_mid, header["Chapter"], header["Section"]),
                        section=_cell(words, y_mid, header["Section"], header["Visual"]),
                        visual=_cell(words, y_mid, header["Visual"], header["VisualEnd"]),
                        url=link["uri"],
                        red=any(r.y0 <= y_mid <= r.y1 and r.x1 > src_x for r in red_boxes),
                    )
                )
    return rows
