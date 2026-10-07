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
