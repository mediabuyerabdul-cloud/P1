"""Decision Maker By A — local server.

Run (from project folder):  python src/decision_maker/app.py
Then open:                  http://127.0.0.1:5001

UI is Phase -> Feature. You upload the data a feature expects; Jev decides
(the built-in rule engine runs when no Jev key is set).
"""

from __future__ import annotations

import os
import sys
import webbrowser
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, request, send_from_directory

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from decision_maker import features, jev, sheet  # noqa: E402

load_dotenv()  # read TYPESAFE_API_KEY from .env
STATIC = Path(__file__).parent / "static"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
app = Flask(__name__, static_folder=None)
_jev = jev.client_from_env()  # None when no key → rule fallback


@app.get("/")
def index():
    return send_from_directory(STATIC, "index.html")


@app.get("/api/features")
def list_features():
    return jsonify(phases=features.PHASES, engine="jev" if _jev is not None else "rules")


@app.post("/api/run-feature")
def run_feature():
    phase = request.form.get("phase", "")
    feature = request.form.get("feature", "")
    paste = request.form.get("paste", "")
    upload = request.files.get("file")
    data = upload.read() if upload is not None else b""
    filename = upload.filename if upload is not None else ""
    try:
        result = features.run(phase, feature, data, filename, paste, _jev)
    except Exception as exc:  # noqa: BLE001 - show a readable error
        return jsonify(error=str(exc)), 400
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


@app.post("/api/export-xlsx")
def export_xlsx():
    body = request.get_json(force=True)
    data = sheet.write_xlsx(body.get("rows", []), body.get("recommendation", {}))
    return Response(
        data,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=decisions.xlsx"},
    )


def _write_env_key(name: str, value: str) -> None:
    env = PROJECT_ROOT / ".env"
    lines = []
    if env.exists():
        lines = [ln for ln in env.read_text().splitlines() if not ln.startswith(name + "=")]
    lines.append(f"{name}={value}")
    env.write_text("\n".join(lines) + "\n")


@app.post("/api/set-key")
def set_key():
    global _jev
    key = (request.get_json(force=True).get("key") or "").strip()
    if not key:
        return jsonify(error="Paste your Jev API key first."), 400
    os.environ["TYPESAFE_API_KEY"] = key
    try:
        _write_env_key("TYPESAFE_API_KEY", key)  # persist so it survives restart
    except Exception:  # noqa: BLE001 - best-effort; key still works this session
        pass
    try:
        _jev = jev.client_from_env()
    except Exception as exc:  # noqa: BLE001
        return jsonify(error=f"Key set but Jev client failed: {exc}"), 500
    return jsonify(engine="jev" if _jev is not None else "rules", saved=True)


def main() -> None:
    url = "http://127.0.0.1:5001"
    print(f"\n  Decision Maker chal raha hai: {url}\n  Band karne ke liye Ctrl+C dabayein.\n")
    webbrowser.open(url)
    app.run(host="127.0.0.1", port=5001, threaded=False)


if __name__ == "__main__":
    main()
