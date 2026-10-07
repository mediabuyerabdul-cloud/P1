"""Phase -> Feature structure and the run dispatcher.

Phase 1 is fully specified (F1 Niche Validator, F2 Demand vs Saturation).
Later phases are listed but hold no features until you share their spec.
Each feature: you provide a data sheet, Jev (or the rule fallback) decides.
"""

from __future__ import annotations

from decision_maker import jev, scoring, sheet

PHASES = [
    {
        "id": "p1",
        "title": "Phase 1 - Niche & Topic Vetting",
        "features": [
            {
                "id": "f1_niche_validator",
                "title": "F1 - Niche Validator",
                "about": "Upload your competitor table. Decides ENTER or SKIP this niche with deep analysis.",
                "input_hint": "Competitor table (.xlsx/.csv): Channel Name, Subscribers, Avg Views, Monetization, RPM, etc.",
            },
            {
                "id": "f2_demand_saturation",
                "title": "F2 - Demand vs Saturation",
                "about": "Upload the new-channels-in-60-days table. Judges demand vs saturation.",
                "input_hint": "Table (.xlsx/.csv): channel URL, Avg Views in latest section, Most Popular View.",
            },
        ],
    },
    {"id": "p2", "title": "Phase 2 - Competitor Profiling", "features": []},
    {"id": "p3", "title": "Phase 3 - Production & Prompts", "features": []},
    {"id": "p4", "title": "Phase 4 - Post-Production QA & Packaging", "features": []},
    {"id": "p5", "title": "Phase 5 - Performance Feedback", "features": []},
    {"id": "p6", "title": "Phase 6 - Uploading", "features": []},
    {"id": "p7", "title": "Phase 7 - Analysis", "features": []},
    {"id": "p8", "title": "Phase 8 - Creative Direction", "features": []},
    {"id": "p9", "title": "Phase 9 - Assets & Routing", "features": []},
    {"id": "p10", "title": "Phase 10 - Risk & Compliance", "features": []},
]

_NICHE_INSTRUCTIONS = (
    "You are a faceless-YouTube strategist. From these niche signals (relevant, "
    "monetized, market-leader counts, avg views, RPM), decide whether to ENTER "
    "this niche with a new channel, treat it as RISKY, or SKIP it."
)
_DEMAND_INSTRUCTIONS = (
    "From these signals about channels created in the last 60 days (how many, "
    "their average views, biggest breakout), decide whether demand is strong "
    "enough and saturation low enough to ENTER, or to treat as RISKY or SKIP."
)


def _read(data, filename, paste, reader):
    if data:
        return reader(data, filename)
    if paste and paste.strip():
        return reader(paste.encode("utf-8"), "paste.csv")
    return []


def run(phase_id, feature_id, data, filename, paste, client):
    if feature_id == "f1_niche_validator":
        channels = _read(data, filename, paste, sheet.read_channels)
        if not channels:
            return {"error": "No channel rows found. Need a header row with Channel Name + stats."}
        result = scoring.validate_niche(channels)
        if client is not None:
            summary = {label: value for label, value in result["analysis"]}
            v = jev.niche_verdict(client, summary, _NICHE_INSTRUCTIONS)
            result.update(verdict=v["verdict"], confidence=v["confidence"], engine="jev")
        else:
            result["engine"] = "rules"
        return result

    if feature_id == "f2_demand_saturation":
        rows = _read(data, filename, paste, sheet.read_new_channels)
        if not rows:
            return {"error": "No rows found. Need columns: channel URL, Avg Views, Most Popular View."}
        result = scoring.demand_vs_saturation(rows)
        if client is not None:
            summary = {label: value for label, value in result["analysis"]}
            v = jev.niche_verdict(client, summary, _DEMAND_INSTRUCTIONS)
            result.update(verdict=v["verdict"], confidence=v["confidence"], engine="jev")
        else:
            result["engine"] = "rules"
        return result

    return {"error": f"Feature not built yet: {feature_id}. Share its spec and I'll add it."}
