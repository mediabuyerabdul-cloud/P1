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
