"""Phase 1 rule-based Go/No-Go scoring: Demand vs. Saturation.

Honest heuristic, not a guarantee. Two numbers per idea:
  - avg_views        = avg views of recent top videos on the topic (DEMAND proxy)
  - competing_videos = how many videos already cover it (SATURATION proxy)

opportunity = demand spread across the competition = avg_views / competing_videos.
Thresholds are visible and tunable in the UI so you fit them to your own data.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

DEFAULT_THRESHOLDS = {
    "min_demand": 10000,  # avg_views below this = no proven audience → No-Go
    "go": 20000,          # opportunity >= this = Go
    "rework": 5000,       # opportunity >= this = Rework, below = No-Go
}


@dataclass
class Scored:
    topic: str
    niche: str
    competing_videos: int
    avg_views: int
    opportunity: int
    verdict: str
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


def score_idea(topic, niche, competing_videos, avg_views, thresholds=None) -> Scored:
    t = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    competing = max(int(competing_videos), 0)
    views = max(int(avg_views), 0)
    opportunity = views // max(competing, 1)

    if views < t["min_demand"]:
        verdict = "No-Go"
        reason = f"Demand too low: top videos average {views:,} views (< {t['min_demand']:,})."
    elif opportunity >= t["go"]:
        verdict = "Go"
        reason = f"Strong: {views:,} avg views across only {competing} competing video(s)."
    elif opportunity >= t["rework"]:
        verdict = "Rework"
        reason = f"Crowded: demand is there ({views:,}) but {competing} competitors — find a sharper angle."
    else:
        verdict = "No-Go"
        reason = f"Saturated: {competing} videos split {views:,} views (~{opportunity:,}/video)."

    return Scored(str(topic).strip(), str(niche).strip(), competing, views, opportunity, verdict, reason)


def score_all(ideas, thresholds=None) -> list[Scored]:
    scored = [
        score_idea(i["topic"], i.get("niche", ""), i.get("competing_videos", 0), i.get("avg_views", 0), thresholds)
        for i in ideas
        if str(i.get("topic", "")).strip()
    ]
    rank = {"Go": 0, "Rework": 1, "No-Go": 2}
    scored.sort(key=lambda s: (rank[s.verdict], -s.opportunity))
    return scored


# --- Channel-level decisions over a research sheet (rule fallback) ----------

def _monetized(rec) -> bool:
    s = str(rec.get("monetization", "")).lower()
    return "monet" in s and "not" not in s


def classify_channel(rec: dict) -> dict:
    """Rule fallback: judge one channel from the stats you provided."""
    avg = rec.get("avg_views") or 0
    subs = rec.get("subscribers") or 0
    rpm = rec.get("rpm") or 0
    monthly_views = rec.get("monthly_views") or 0
    monetized = _monetized(rec)

    if avg >= 25000 or subs >= 5000 or monthly_views >= 500000:
        stage, tier = "Market Leader", "Market Leader"
    elif avg >= 10000:
        stage, tier = "Close competitor", "Rising Challenger"
    else:
        stage, tier = "Moderate", "Early / Niche"

    if avg >= 15000 and (monetized or rpm >= 2):
        relevance = "High"
    elif avg >= 5000:
        relevance = "Medium"
    else:
        relevance = "Low"

    bits = [f"{int(avg):,} avg views", f"{int(subs):,} subs"]
    if rpm:
        bits.append(f"RPM {rpm}")
    bits.append("monetized" if monetized else "not monetized")
    return {
        "channel": rec.get("channel", ""),
        "relevance": relevance, "stage": stage, "tier": tier,
        "avg_views": int(avg), "subscribers": int(subs),
        "monthly_income": rec.get("monthly_income") or "", "rpm": rpm or "",
        "monetization": rec.get("monetization", ""), "monetized": monetized,
        "reason": ", ".join(bits) + ".",
    }


def recommend_niche(decisions: list[dict]) -> dict:
    highs = [d for d in decisions if d["relevance"] == "High"]
    monetized = [d for d in decisions if d.get("monetized")]
    leaders = [d for d in decisions if d["stage"] == "Market Leader"]
    follow = [d["channel"] for d in sorted(highs, key=lambda d: -d["avg_views"])[:4]]

    if len(highs) >= 3 and monetized:
        verdict = "Go"
        reason = (f"{len(highs)} highly-relevant channels, {len(monetized)} monetized, "
                  f"{len(leaders)} market leader(s) — proven, monetizable niche.")
    elif highs:
        verdict = "Rework"
        reason = (f"Some traction ({len(highs)} high-relevance) but thin monetization proof — "
                  "enter with a sharper angle.")
    else:
        verdict = "No-Go"
        reason = "No highly-relevant, proven channels — weak niche signal."
    return {"verdict": verdict, "reason": reason, "follow": follow}
