"""Read a research sheet (.xlsx/.csv) of competitor channels and write decisions back.

You provide the data (stats, demographics, monetization — whatever you've
collected). This maps your columns to known fields; unknown columns are ignored
for scoring but you keep them in your own sheet.
"""

from __future__ import annotations

import csv
import io
import re

import openpyxl

# header (lowercased) -> canonical field name
ALIASES = {
    "channel name": "channel", "channel": "channel",
    "subscribes": "subscribers", "subscribers": "subscribers", "subs": "subscribers",
    "avg. views per video": "avg_views", "avg views per video": "avg_views", "avg views": "avg_views",
    "monthly views": "monthly_views",
    "monthly income": "monthly_income",
    "rpm": "rpm",
    "total views": "total_views", "total videos": "total_videos",
    "avg. monthly uploads": "uploads_per_month", "avg monthly uploads": "uploads_per_month",
    "avg. video length": "video_length", "avg video length": "video_length",
    "monetization status": "monetization", "monetization": "monetization",
    "relevance level": "relevance_given", "competitor stages": "stage_given", "competitor stage": "stage_given",
    "top geographies": "geo", "top gender": "gender", "top age": "age",
    "channel creation country": "country", "categories": "category", "category": "category",
}
NUMERIC = {"subscribers", "avg_views", "monthly_views", "monthly_income", "rpm",
           "total_views", "total_videos", "uploads_per_month"}


def _num(v):
    if v is None:
        return None
    s = re.sub(r"[^\d.]", "", str(v).replace(" ", ""))
    try:
        return float(s) if s else None
    except ValueError:
        return None


def _canon(header):
    return ALIASES.get(str(header or "").strip().lower())


def _table_from_bytes(data: bytes, filename: str):
    if filename.lower().endswith(".csv"):
        text = data.decode("utf-8-sig", errors="replace")
        return [list(r) for r in csv.reader(io.StringIO(text))]
    wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
    ws = wb.worksheets[0]  # first sheet = the master table (your "Cap")
    return [list(r) for r in ws.iter_rows(values_only=True)]


def read_channels(data: bytes, filename: str) -> list[dict]:
    table = _table_from_bytes(data, filename)
    header_idx, colmap = None, {}
    for i, row in enumerate(table[:12]):
        mapped = [_canon(c) for c in row]
        if sum(1 for m in mapped if m) >= 3:
            header_idx = i
            for j, m in enumerate(mapped):
                if m and m not in colmap:
                    colmap[m] = j
            break
    if header_idx is None:
        return []

    records = []
    for row in table[header_idx + 1:]:
        if not any(c not in (None, "") for c in row):
            continue
        rec = {}
        for field, j in colmap.items():
            val = row[j] if j < len(row) else None
            rec[field] = _num(val) if field in NUMERIC else ("" if val is None else str(val).strip())
        if rec.get("channel"):
            records.append(rec)
    return records


def write_xlsx(rows: list[dict], recommendation: dict) -> bytes:
    """rows = decided channels; recommendation = niche verdict. Returns .xlsx bytes."""
    wb = openpyxl.Workbook()
    dec = wb.active
    dec.title = "Decisions"
    cols = ["channel", "relevance", "stage", "tier", "avg_views", "subscribers",
            "monthly_income", "rpm", "monetization", "reason"]
    dec.append([c.replace("_", " ").title() for c in cols])
    for r in rows:
        dec.append([r.get(c, "") for c in cols])

    summ = wb.create_sheet("Best Decision")
    summ.append(["Niche verdict", recommendation.get("verdict", "")])
    summ.append(["Why", recommendation.get("reason", "")])
    summ.append([])
    summ.append(["Follow these channels (template to copy):"])
    for name in recommendation.get("follow", []):
        summ.append(["", name])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
