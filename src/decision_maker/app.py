"""Decision Maker By A — local server (Phase 1: Niche & Topic Vetting).

Run (from project folder):  python src/decision_maker/app.py
Then open:                  http://127.0.0.1:5001
"""

from __future__ import annotations

import sys
import webbrowser
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from decision_maker import jev, youtube_scrape  # noqa: E402
from decision_maker.scoring import DEFAULT_THRESHOLDS, score_all  # noqa: E402

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
