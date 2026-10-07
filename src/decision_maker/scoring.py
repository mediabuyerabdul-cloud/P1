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
