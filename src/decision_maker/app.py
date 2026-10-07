"""Decision Maker By A — local server (Phase 1: Niche & Topic Vetting).

Run (from project folder):  python src/decision_maker/app.py
Then open:                  http://127.0.0.1:5001
"""

from __future__ import annotations

import sys
import webbrowser
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, request, send_from_directory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from decision_maker import jev, phases, sheet, youtube_scrape  # noqa: E402
from decision_maker.scoring import (  # noqa: E402
    DEFAULT_THRESHOLDS,
    classify_channel,
    recommend_niche,
    score_all,
)

load_dotenv()  # read TYPESAFE_API_KEY (and any YouTube key later) from .env
STATIC = Path(__file__).parent / "static"
app = Flask(__name__, static_folder=None)
_browser = None
_jev = jev.client_from_env()  # None when no key → rule fallback


def browser() -> youtube_scrape.YouTubeBrowser:
    global _browser
    if _browser is None:
        _browser = youtube_scrape.YouTubeBrowser()
    return _browser


@app.get("/")
def index():
    return send_from_directory(STATIC, "index.html")


@app.get("/api/defaults")
def defaults():
    return jsonify(thresholds=DEFAULT_THRESHOLDS, engine="jev" if _jev is not None else "rules")


@app.post("/api/vet")
def vet():
    body = request.get_json(force=True)
    mode = body.get("mode", "manual")
    niche = body.get("niche", "")
    thresholds = body.get("thresholds") or None
    ideas, errors, fetched = [], [], {}

    for row in body.get("rows", []):
        topic = str(row.get("topic", "")).strip()
        if not topic:
            continue
        if mode == "auto":
            try:
                st = browser().stats_for(topic)
            except Exception as exc:  # noqa: BLE001 - show the user a readable error
                errors.append(f"{topic}: {exc}")
                continue
            fetched[topic] = st
            ideas.append({"topic": topic, "niche": niche,
                          "competing_videos": st["competing_videos"], "avg_views": st["avg_views"]})
        else:
            ideas.append({"topic": topic, "niche": niche,
                          "competing_videos": row.get("competing_videos", 0),
                          "avg_views": row.get("avg_views", 0)})

    if _jev is not None:
        rows = []
        for idea in ideas:
            try:
                rows.append(jev.decide(_jev, **idea).to_dict())
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{idea['topic']}: Jev error: {exc}")
        rank = {"Go": 0, "Rework": 1, "No-Go": 2}
        rows.sort(key=lambda r: (rank.get(r["verdict"], 9), -(r.get("confidence") or 0)))
        engine = "jev"
    else:
        rows = [s.to_dict() for s in score_all(ideas, thresholds)]
        engine = "rules"
    return jsonify(rows=rows, errors=errors, fetched=fetched, engine=engine)


@app.post("/api/analyze-sheet")
def analyze_sheet():
    upload = request.files.get("sheet")
    if upload is None:
        return jsonify(error="No sheet uploaded"), 400
    try:
        channels = sheet.read_channels(upload.read(), upload.filename or "sheet.xlsx")
    except Exception as exc:  # noqa: BLE001
        return jsonify(error=f"Could not read sheet: {exc}"), 400
    if not channels:
        return jsonify(error="No channel rows found. Need a header row with Channel Name + stats."), 400

    errors = []
    if _jev is not None:
        rows = []
        for rec in channels:
            try:
                rows.append(jev.decide_channel(_jev, rec))
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{rec.get('channel', '?')}: Jev error: {exc}")
        engine = "jev"
    else:
        rows = [classify_channel(rec) for rec in channels]
        engine = "rules"

    rank = {"High": 0, "Medium": 1, "Low": 2}
    rows.sort(key=lambda r: (rank.get(r["relevance"], 9), -r["avg_views"]))
    return jsonify(rows=rows, recommendation=recommend_niche(rows), engine=engine, errors=errors)


@app.post("/api/export-xlsx")
def export_xlsx():
    body = request.get_json(force=True)
    data = sheet.write_xlsx(body.get("rows", []), body.get("recommendation", {}))
    return Response(
        data,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=decisions.xlsx"},
    )


@app.get("/api/phases")
def list_phases():
    return jsonify(phases=phases.LIST, pending=phases.PENDING_LIST,
                   engine="jev" if _jev is not None else "rules")


@app.post("/api/task")
def task():
    body = request.get_json(force=True)
    items = [x.strip() for x in str(body.get("items", "")).split("\n") if x.strip()]
    try:
        return jsonify(phases.run_task(body.get("phase"), items, body.get("context", ""), _jev))
    except Exception as exc:  # noqa: BLE001
        return jsonify(error=str(exc)), 400


def main() -> None:
    url = "http://127.0.0.1:5001"
    print(f"\n  Decision Maker chal raha hai: {url}\n  Band karne ke liye Ctrl+C dabayein.\n")
    webbrowser.open(url)
    try:
        app.run(host="127.0.0.1", port=5001, threaded=False)
    finally:
        if _browser is not None:
            _browser.close()


if __name__ == "__main__":
    main()
