"""Fake client se test, is liye API key ki zaroorat nahi."""

from types import SimpleNamespace

from jev_integration import analyze_lead
from jev_integration.leads import QUESTIONS


class FakeClient:
    def __init__(self):
        self.calls = []

    def system_one(self, state, questions):
        self.calls.append((state, questions))
        return SimpleNamespace(
            choices={"intent": SimpleNamespace(choice="buy", confidence=0.92)},
            scores={"quality": SimpleNamespace(score=4.3)},
            nouls={"urgent": SimpleNamespace(noul=0.81)},
        )


def test_analyze_lead_maps_answers():
    client = FakeClient()
    decision = analyze_lead("Price? Order today.", client)

    assert client.calls == [({"message": "Price? Order today."}, QUESTIONS)]
    assert decision.intent == "buy"
    assert decision.intent_confidence == 0.92
    assert decision.quality == 4.3
    assert decision.is_urgent


def test_questions_serialize_to_valid_types():
    assert {name: q.type for name, q in QUESTIONS.items()} == {
        "intent": "choice",
        "quality": "score",
        "urgent": "noul",
    }
