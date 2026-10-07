from types import SimpleNamespace

from decision_maker import features, jev, scoring, sheet


def test_read_new_channels_maps_url_and_views():
    csv_bytes = (
        "Past 60 Days New Channels Created,Avg Views in this Channel in Latest Section,Most Popular View in this Channel\n"
        "https://youtube.com/@a,9024,172847\n"
        "https://youtube.com/@b,3045,29496\n"
    ).encode()
    rows = sheet.read_new_channels(csv_bytes, "r.csv")
    assert [r["url"] for r in rows] == ["https://youtube.com/@a", "https://youtube.com/@b"]
    assert rows[0]["avg_views"] == 9024 and rows[0]["most_popular"] == 172847


def test_validate_niche_enter_and_skip():
    strong = [{"channel": f"C{i}", "avg_views": 26000, "subscribers": 1600,
               "rpm": 2.5, "monetization": "Monetized"} for i in range(4)]
    out = scoring.validate_niche(strong)
    assert out["verdict"] == "ENTER"
    weak = [{"channel": "W", "avg_views": 800, "subscribers": 90, "monetization": "Not Monetized"}]
    assert scoring.validate_niche(weak)["verdict"] == "SKIP"


def test_demand_vs_saturation_enter_and_skip():
    strong = [{"url": "x", "avg_views": 15000, "most_popular": 172000},
              {"url": "y", "avg_views": 9000, "most_popular": 95000}]
    assert scoring.demand_vs_saturation(strong)["verdict"] == "ENTER"
    weak = [{"url": "z", "avg_views": 500, "most_popular": 1000}]
    assert scoring.demand_vs_saturation(weak)["verdict"] == "SKIP"


def test_features_run_f1_rules():
    channels = [{"channel": f"C{i}", "avg_views": 26000, "subscribers": 1600,
                 "rpm": 2.5, "monetization": "Monetized"} for i in range(3)]
    csv = "channel name,avg views per video,subscribes,rpm,monetization status\n" + \
          "\n".join(f"{c['channel']},26000,1600,2.5,Monetized" for c in channels)
    out = features.run("p1", "f1_niche_validator", csv.encode(), "d.csv", "", None)
    assert out["verdict"] == "ENTER" and out["engine"] == "rules"


def test_features_run_f1_uses_jev_when_present():
    class FakeJev:
        def system_one(self, state, questions):
            return SimpleNamespace(choices={"verdict": SimpleNamespace(choice="skip", confidence=0.7)}, scores={})
    csv = "channel name,avg views per video,subscribes,rpm,monetization status\nA,26000,1600,2.5,Monetized"
    out = features.run("p1", "f1_niche_validator", csv.encode(), "d.csv", "", FakeJev())
    assert out["verdict"] == "SKIP" and out["engine"] == "jev" and out["confidence"] == 0.7


def test_features_run_unknown_feature():
    assert "error" in features.run("p2", "nope", b"", "", "", None)


def test_jev_niche_verdict_maps_choice():
    class FakeJev:
        def system_one(self, state, questions):
            return SimpleNamespace(choices={"verdict": SimpleNamespace(choice="enter", confidence=0.8)}, scores={})
    v = jev.niche_verdict(FakeJev(), {"Monetized": 3}, "decide")
    assert v["verdict"] == "ENTER" and v["confidence"] == 0.8
