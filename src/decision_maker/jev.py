"""Jev (typesafe.ai) is the decision engine.

We hand Jev the topic plus its demand/saturation numbers as typed questions and
it returns a typed verdict with calibrated confidence — a `choice` for Go /
Rework / No-Go, and `score`s for demand and saturation. No prose, no parsing.

Needs TYPESAFE_API_KEY in the environment (put it in .env). When the key is
absent, the app falls back to the built-in rule scorer instead.
"""

from __future__ import annotations

import dataclasses
import os
from dataclasses import dataclass

VERDICT_MAP = {"go": "Go", "rework": "Rework", "no_go": "No-Go"}
DEMAND_LEVELS = ["none", "weak", "moderate", "strong", "very strong"]
SATURATION_LEVELS = ["open", "some", "crowded", "saturated", "oversaturated"]


@dataclass
class Decision:
    topic: str
    niche: str
    competing_videos: int
    avg_views: int
    verdict: str
    confidence: float
    demand: str
    saturation: str
    reason: str

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


def _label(score: float, levels: list[str]) -> str:
    i = min(max(round(score) - 1, 0), len(levels) - 1)
    return levels[i]


def client_from_env():
    """A TypeSafeClient if TYPESAFE_API_KEY is set, else None."""
    if not os.environ.get("TYPESAFE_API_KEY"):
        return None
    from typesafe_sdk import TypeSafeClient

    return TypeSafeClient()


def decide(client, topic, niche, competing_videos, avg_views) -> Decision:
    from typesafe_sdk import Choice, Score

    resp = client.system_one(
        state={
            "topic": topic,
            "niche": niche,
            "avg_views_of_top_results": int(avg_views),
            "recent_competitors": int(competing_videos),
        },
        questions={
            "verdict": Choice(
                instructions=(
                    "You are a faceless-YouTube strategist. Weighing demand "
                    "(avg views of top results) against saturation (recent "
                    "competitors), should we produce this video now?"
                ),
                criteria={
                    "go": "Clear opportunity — produce now",
                    "rework": "Demand exists but the angle or sub-niche needs sharpening first",
                    "no_go": "Skip — weak demand or too saturated",
                },
            ),
            "demand": Score(instructions="Viewer demand for this topic.", criteria=DEMAND_LEVELS),
            "saturation": Score(instructions="How crowded/competitive this topic is.", criteria=SATURATION_LEVELS),
        },
    )
    v = resp.choices["verdict"]
    verdict = VERDICT_MAP.get(v.choice, v.choice)
    demand = _label(resp.scores["demand"].score, DEMAND_LEVELS)
    saturation = _label(resp.scores["saturation"].score, SATURATION_LEVELS)
    reason = f"Jev: {verdict} ({v.confidence:.0%} confident) — demand {demand}, saturation {saturation}."
    return Decision(topic, niche, int(competing_videos), int(avg_views),
                    verdict, round(float(v.confidence), 3), demand, saturation, reason)


# --- Channel decisions via Jev (over a research sheet) ----------------------

RELEVANCE_CHOICES = {
    "high": "Core archetype worth modelling closely",
    "medium": "Adjacent — overlapping audience but a different angle",
    "low": "Weak fit — different market, language, or demographic",
}
STAGE_CHOICES = {
    "market_leader": "Dominant scale and/or revenue in the niche",
    "close_competitor": "Direct competitor, growing, same format",
    "moderate": "Early-stage or loosely related",
}
STAGE_LABEL = {"market_leader": "Market Leader", "close_competitor": "Close competitor", "moderate": "Moderate"}
TIER_FOR_STAGE = {"Market Leader": "Market Leader", "Close competitor": "Rising Challenger", "Moderate": "Early / Niche"}


def decide_channel(client, rec: dict) -> dict:
    from typesafe_sdk import Choice

    resp = client.system_one(
        state={k: rec.get(k, "") for k in (
            "channel", "category", "subscribers", "avg_views", "monthly_views", "monthly_income",
            "rpm", "total_views", "total_videos", "uploads_per_month", "video_length",
            "monetization", "country", "geo", "gender", "age")},
        questions={
            "relevance": Choice(
                instructions="How relevant is this channel as a competitor to model for our faceless agency in this niche?",
                criteria=RELEVANCE_CHOICES),
            "stage": Choice(
                instructions="What competitor stage is this channel at?",
                criteria=STAGE_CHOICES),
        },
    )
    relevance = resp.choices["relevance"].choice
    stage = STAGE_LABEL.get(resp.choices["stage"].choice, resp.choices["stage"].choice)
    return {
        "channel": rec.get("channel", ""),
        "relevance": relevance.capitalize(),
        "stage": stage,
        "tier": TIER_FOR_STAGE.get(stage, stage),
        "confidence": round(float(resp.choices["relevance"].confidence), 3),
        "avg_views": int(rec.get("avg_views") or 0),
        "subscribers": int(rec.get("subscribers") or 0),
        "monthly_income": rec.get("monthly_income") or "",
        "rpm": rec.get("rpm") or "",
        "monetization": rec.get("monetization", ""),
        "monetized": "monet" in str(rec.get("monetization", "")).lower()
                     and "not" not in str(rec.get("monetization", "")).lower(),
        "reason": f"Jev: {relevance} relevance, {stage} ({resp.choices['relevance'].confidence:.0%} conf).",
    }
