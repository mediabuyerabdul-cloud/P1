"""Phases 2-9 as Jev decision presets.

Same pattern as Phase 1: you provide the options/data, Jev decides. Each preset
is one of three ops — score each item, pick the best, or classify each into a
category. Generative work (writing prompts/descriptions) is out of scope for
Jev and marked needs-llm.
"""

from __future__ import annotations

from decision_maker import jev

PHASES = {
    "p2_template": {
        "title": "Phase 2 — Template fit", "op": "classify",
        "hint": "One channel or video title per line.",
        "context_label": "Your templates (comma separated), e.g. A: reversal, B: underdog, C: discovery",
        "instructions": "Classify this channel/video into the closest title+thumbnail template.",
    },
    "p4_title": {
        "title": "Phase 4 — Title strength", "op": "score",
        "hint": "One title per line.",
        "context_label": "Niche (optional)",
        "instructions": "Rate this YouTube title's strength (click-pull + SEO) for a faceless channel.",
        "levels": ["very weak", "weak", "average", "strong", "excellent"],
    },
    "p4_virality": {
        "title": "Phase 4 — Virality score", "op": "score",
        "hint": "One video concept or title per line.",
        "context_label": "Niche (optional)",
        "instructions": "Rate this video's viral potential for a faceless channel.",
        "levels": ["very low", "low", "moderate", "high", "very high"],
    },
    "p5_winner": {
        "title": "Phase 5 — Winner → template", "op": "classify",
        "hint": "One winning video title per line.",
        "context_label": "Your templates (comma separated)",
        "instructions": "Which of our templates does this winning video follow, so we can repeat it?",
    },
    "p6_time": {
        "title": "Phase 6 — Best upload time", "op": "pick",
        "hint": "One time slot per line, e.g. 'Sat 6pm EST'.",
        "context_label": "Audience / niche (optional)",
        "instructions": "Pick the best upload time window for this faceless channel's audience.",
    },
    "p7_prompt": {
        "title": "Phase 7 — Compare prompts", "op": "pick",
        "hint": "One prompt per line (2 or more).",
        "context_label": "What the prompt is for (e.g. image gen, script)",
        "instructions": "Pick the stronger prompt for the stated task.",
    },
    "p8_hook": {
        "title": "Phase 8 — Pick best intro/hook", "op": "pick",
        "hint": "One hook/intro option per line.",
        "context_label": "Video topic (optional)",
        "instructions": "Pick the strongest opening hook for a faceless YouTube video.",
    },
    "p8_voice": {
        "title": "Phase 8 — Pick best voice-over", "op": "pick",
        "hint": "One of YOUR licensed voices per line (name + tone/accent).",
        "context_label": "Video mood / niche",
        "instructions": "Pick the voice that best fits this video from the ones provided.",
    },
    "p8_duration": {
        "title": "Phase 8 — Best duration fit", "op": "score",
        "hint": "One candidate length per line, e.g. '8 min', '18 min'.",
        "context_label": "Niche / format",
        "instructions": "Rate how well this length fits the niche for watch-time and retention.",
        "levels": ["poor", "weak", "ok", "good", "ideal"],
    },
    "p9_template": {
        "title": "Phase 9 — Pick best template", "op": "pick",
        "hint": "One template option per line.",
        "context_label": "Video / niche",
        "instructions": "Pick the best video+thumbnail template for this video.",
    },
    "p9_tool": {
        "title": "Phase 9 — Pick best tool/model", "op": "pick",
        "hint": "One tool/model option per line (e.g. ChatGPT, Claude, Muse).",
        "context_label": "The task (e.g. scripting, image creation, prompting)",
        "instructions": "Pick the best tool/model for the stated task.",
    },
    "p9_predict": {
        "title": "Phase 9 — Predict potential", "op": "score",
        "hint": "One video concept per line.",
        "context_label": "Niche / competitor context",
        "instructions": "Estimate this video's view potential (a rough range signal, never a promise).",
        "levels": ["very low", "low", "moderate", "high", "very high"],
    },
}

# Features that need generation/vision/ffmpeg, not a Jev decision — surfaced so
# they're visible but honestly marked instead of faked.
PENDING = {
    "p3_prompts": "Phase 3 — Generate hook/outline prompts (needs an LLM key)",
    "p4_description": "Phase 4 — Write description/tags (needs an LLM key)",
    "p4_glitch": "Phase 4 — Glitch pick on visuals (needs a vision model)",
    "p7_video": "Phase 7 — Video analysis / timestamps (needs ffmpeg + video file)",
}

LIST = [{"id": k, "title": v["title"], "hint": v["hint"],
         "context_label": v["context_label"], "op": v["op"]} for k, v in PHASES.items()]
PENDING_LIST = [{"id": k, "title": v} for k, v in PENDING.items()]


def run_task(phase_id, items, context, client):
    p = PHASES.get(phase_id)
    if p is None:
        return {"error": f"Unknown phase {phase_id}"}
    if client is None:
        return {"engine": "needs-jev",
                "note": "Add your Jev key (TYPESAFE_API_KEY) to .env to run this decision."}
    if not items:
        return {"error": "Add at least one line."}

    op = p["op"]
    if op == "score":
        rows = jev.score_each(client, p["instructions"], p["levels"], items, context)
        return {"engine": "jev", "op": op, "rows": rows, "best": rows[0]["item"] if rows else ""}
    if op == "pick":
        r = jev.pick_best(client, p["instructions"], items, context)
        rows = [{"item": o, "pick": o == r["best"]} for o in r["ranked"]]
        return {"engine": "jev", "op": op, "rows": rows, "best": r["best"], "confidence": r["confidence"]}
    if op == "classify":
        cats = [c.strip() for c in context.split(",") if c.strip()]
        if not cats:
            return {"error": "Enter your categories/templates in the context box (comma separated)."}
        rows = jev.classify_into(client, p["instructions"], cats, items, context)
        return {"engine": "jev", "op": op, "rows": rows}
    return {"error": f"Unknown op {op}"}
