from decision_maker.scoring import score_all, score_idea


def test_go_when_demand_high_and_few_competitors():
    s = score_idea("AI cat compilation", "compilations", competing_videos=2, avg_views=100000)
    assert s.verdict == "Go" and s.opportunity == 50000


def test_no_go_when_demand_below_min():
    assert score_idea("obscure topic", "ai images", 1, 500).verdict == "No-Go"


def test_rework_when_crowded_but_demand_exists():
    # 50000 views / 8 competitors = 6250 opportunity: between rework(5000) and go(20000)
    assert score_idea("welding shorts", "compilations", 8, 50000).verdict == "Rework"


def test_no_go_when_saturated():
    # 30000 / 20 = 1500 opportunity, below rework
    assert score_idea("news recap", "compilations", 20, 30000).verdict == "No-Go"


def test_score_all_ranks_go_first_and_drops_blank_topics():
    rows = score_all([
        {"topic": "", "avg_views": 99999, "competing_videos": 1},
        {"topic": "weak", "niche": "x", "competing_videos": 1, "avg_views": 100},
        {"topic": "winner", "niche": "x", "competing_videos": 1, "avg_views": 100000},
    ])
    assert [r.topic for r in rows] == ["winner", "weak"]
    assert rows[0].verdict == "Go"


def test_thresholds_are_tunable():
    low = score_idea("t", "n", 1, 12000, thresholds={"min_demand": 1000, "go": 10000})
    assert low.verdict == "Go"


# --- YouTube reader parsing (no network) ---
import json as _json

from decision_maker import youtube_scrape as ys


def _fixture_html():
    data = {"contents": [
        {"videoRenderer": {"title": {"runs": [{"text": "Vid A"}]},
                           "viewCountText": {"simpleText": "1.2M views"},
                           "publishedTimeText": {"simpleText": "2 months ago"}}},
        {"videoRenderer": {"title": {"simpleText": "Vid B"},
                           "viewCountText": {"simpleText": "500,000 views"},
                           "publishedTimeText": {"simpleText": "3 years ago"}}},
    ]}
    return "<script>var ytInitialData = " + _json.dumps(data) + ";</script>"


def test_parse_views_units():
    assert ys.parse_views("1.2M views") == 1_200_000
    assert ys.parse_views("500,000 views") == 500_000
    assert ys.parse_views("No views") == 0


def test_parse_age_months():
    assert ys.parse_age_months("2 months ago") == 2
    assert ys.parse_age_months("3 years ago") == 36
    assert ys.parse_age_months("") is None


def test_parse_search_and_stats():
    items = ys.parse_search(_fixture_html())
    assert [i["title"] for i in items] == ["Vid A", "Vid B"]
    stats = ys.topic_stats(items)
    assert stats["avg_views"] == 850_000          # median of the two
    assert stats["competing_videos"] == 1         # only the 2-month one is recent


# --- Jev decision engine (fake client, no network) ---
from types import SimpleNamespace

from decision_maker import jev


class _FakeJevClient:
    def __init__(self, choice, conf, demand, sat):
        self._r = SimpleNamespace(
            choices={"verdict": SimpleNamespace(choice=choice, confidence=conf)},
            scores={"demand": SimpleNamespace(score=demand), "saturation": SimpleNamespace(score=sat)},
        )
    def system_one(self, state, questions):
        self.state, self.questions = state, questions
        return self._r


def test_jev_decide_maps_choice_and_labels():
    c = _FakeJevClient("go", 0.84, 5, 2)
    d = jev.decide(c, "AI cat compilation", "Compilations", 6, 120000)
    assert d.verdict == "Go" and d.confidence == 0.84
    assert d.demand == "very strong" and d.saturation == "some"
    assert c.state["avg_views_of_top_results"] == 120000
    assert "Jev: Go" in d.reason


# --- Research-sheet flow (reader + channel decisions, no network) ---
from decision_maker import sheet
from decision_maker.scoring import classify_channel, recommend_niche


def test_read_channels_from_csv_maps_headers_and_numbers():
    csv_bytes = (
        "Categories,Channel Name,Subscribes,Avg. Views Per Video,Monetization Status,RPM,Top Gender\n"
        "Farm,CountyHonor,1 560,26 159,Monetized,2.66,Male75.4%\n"
        "Farm,Weak One,120,900,Not Monetized,,Male\n"
    ).encode()
    recs = sheet.read_channels(csv_bytes, "r.csv")
    assert [r["channel"] for r in recs] == ["CountyHonor", "Weak One"]
    assert recs[0]["subscribers"] == 1560 and recs[0]["avg_views"] == 26159
    assert recs[0]["rpm"] == 2.66 and recs[0]["gender"] == "Male75.4%"


def test_classify_channel_and_recommend():
    leader = classify_channel({"channel": "A", "avg_views": 26000, "subscribers": 1560,
                               "rpm": 2.66, "monetization": "Monetized"})
    assert leader["relevance"] == "High" and leader["stage"] == "Market Leader"
    weak = classify_channel({"channel": "B", "avg_views": 900, "subscribers": 120,
                             "monetization": "Not Monetized"})
    assert weak["relevance"] == "Low"
    rec = recommend_niche([leader, leader, leader, weak])
    assert rec["verdict"] == "Go" and "A" in rec["follow"]


def test_write_xlsx_roundtrips():
    rows = [classify_channel({"channel": "A", "avg_views": 26000, "subscribers": 1560,
                              "rpm": 2.66, "monetization": "Monetized"})]
    data = sheet.write_xlsx(rows, recommend_niche(rows))
    assert data[:2] == b"PK"  # a valid .xlsx (zip) was produced


# --- Generic phase engine (fake Jev client, no network) ---
from decision_maker import phases


class _FakeScoreClient:
    def system_one(self, state, questions):
        return SimpleNamespace(scores={"score": SimpleNamespace(score=4.0, confidence=0.7)}, choices={})


class _FakePickClient:
    def system_one(self, state, questions):
        return SimpleNamespace(choices={"best": SimpleNamespace(
            choice="opt1", confidence=0.66, probabilities={"opt0": 0.2, "opt1": 0.8})}, scores={})


class _FakeClassifyClient:
    def system_one(self, state, questions):
        return SimpleNamespace(choices={"cat": SimpleNamespace(choice="A", confidence=0.9)}, scores={})


def test_phase_score_ranks_items():
    out = phases.run_task("p4_title", ["title one", "title two"], "farm", _FakeScoreClient())
    assert out["engine"] == "jev" and out["op"] == "score"
    assert out["rows"][0]["label"] == "strong"


def test_phase_pick_returns_best():
    out = phases.run_task("p8_hook", ["hook a", "hook b"], "", _FakePickClient())
    assert out["best"] == "hook b" and out["rows"][0]["item"] == "hook b"


def test_phase_classify_needs_categories():
    assert "error" in phases.run_task("p2_template", ["Chan X"], "", _FakeClassifyClient())
    out = phases.run_task("p2_template", ["Chan X"], "A, B, C", _FakeClassifyClient())
    assert out["rows"][0]["category"] == "A"


def test_phase_without_client_is_honest():
    out = phases.run_task("p4_title", ["t"], "", None)
    assert out["engine"] == "needs-jev" and "Jev key" in out["note"]
