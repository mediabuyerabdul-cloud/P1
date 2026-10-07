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


# --- Phase 1 features: deep-analysis verdicts (rule fallback) ---------------

def _mean(xs):
    xs = [x for x in xs if x]
    return sum(xs) / len(xs) if xs else 0


def validate_niche(channels: list[dict]) -> dict:
    """F1 - Niche Validator: ENTER / RISKY / SKIP from the competitor table."""
    decs = [classify_channel(c) for c in channels]
    n = len(decs)
    highs = [d for d in decs if d["relevance"] == "High"]
    monetized = [d for d in decs if d["monetized"]]
    leaders = [d for d in decs if d["stage"] == "Market Leader"]
    avg_demand = int(_mean([d["avg_views"] for d in decs]))
    good_rpm = [c for c in channels if (c.get("rpm") or 0) >= 2]

    if len(highs) >= 3 and len(monetized) >= 2:
        verdict = "ENTER"
        headline = (f"Proven, monetizable niche: {len(highs)} highly-relevant channels, "
                    f"{len(monetized)} monetized, {len(leaders)} market leader(s).")
    elif highs and (monetized or leaders):
        verdict = "RISKY"
        headline = (f"Some proof ({len(highs)} high-relevance, {len(monetized)} monetized) but thin - "
                    "enter only with a sharper angle than the leaders.")
    else:
        verdict = "SKIP"
        headline = "Weak signal: too few relevant, monetized, or leading channels to justify entry."

    analysis = [
        ("Channels analyzed", n),
        ("Highly relevant", len(highs)),
        ("Monetized", len(monetized)),
        ("Market leaders", len(leaders)),
        ("Channels with RPM >= 2", len(good_rpm)),
        ("Avg views across niche", f"{avg_demand:,}"),
    ]
    rank = {"High": 0, "Medium": 1, "Low": 2}
    decs.sort(key=lambda d: (rank[d["relevance"]], -d["avg_views"]))
    return {"verdict": verdict, "headline": headline, "analysis": analysis, "rows": decs,
            "columns": ["channel", "relevance", "stage", "tier", "avg_views", "subscribers", "reason"]}


def demand_vs_saturation(rows: list[dict]) -> dict:
    """F2 - Demand vs Saturation: from new channels (last 60 days)."""
    n = len(rows)
    avgs = [r.get("avg_views") or 0 for r in rows]
    pops = [r.get("most_popular") or 0 for r in rows]
    avg_demand = int(_mean(avgs))
    max_pop = int(max(pops) if pops else 0)
    breakout = sum(1 for p in pops if p >= 100000)
    pulling = sum(1 for a in avgs if a >= 10000)

    demand = "High" if (avg_demand >= 10000 or max_pop >= 100000) else "Moderate" if avg_demand >= 3000 else "Low"
    saturation = "High" if n >= 8 else "Moderate" if n >= 4 else "Low"

    if demand in ("High", "Moderate") and saturation != "High":
        verdict = "ENTER"
        headline = f"{demand} demand (avg {avg_demand:,} views, breakout {max_pop:,}) with {saturation.lower()} saturation - room to compete."
    elif demand == "High" and saturation == "High":
        verdict = "RISKY"
        headline = f"Demand is proven but {n} new channels already crowd it - enter only with a clear edge."
    else:
        verdict = "SKIP"
        headline = f"{demand} demand and {saturation.lower()} saturation - not worth a new channel now."

    analysis = [
        ("New channels (60 days)", n),
        ("Demand", demand),
        ("Saturation", saturation),
        ("Avg views (new channels)", f"{avg_demand:,}"),
        ("Biggest breakout view", f"{max_pop:,}"),
        ("Channels pulling >=10k avg", pulling),
        ("Channels with a 100k+ video", breakout),
    ]
    rows_sorted = sorted(rows, key=lambda r: -(r.get("most_popular") or 0))
    return {"verdict": verdict, "headline": headline, "analysis": analysis, "rows": rows_sorted,
            "columns": ["url", "avg_views", "most_popular"]}
