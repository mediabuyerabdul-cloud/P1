"""Lead/message ko Jev se analyze karna.

Jev chat nahi karta. Hum use "state" (text) aur typed "questions" bhejte hain,
aur woh har sawal ka typed jawab probability ke saath deta hai:
  - Choice: options mein se ek chunna
  - Score:  levels par rating (1, 2, 3 ...)
  - Noul:   haan/nahi ki probability (0 se 1)
"""

from __future__ import annotations

from dataclasses import dataclass

from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

QUESTIONS = {
    "intent": Choice(
        instructions="What does the sender want?",
        criteria={
            "buy": "Wants to purchase or asks about price/ordering",
            "question": "Has a general question about the product or service",
            "complaint": "Is unhappy or reports a problem",
            "spam": "Irrelevant, promotional, or automated message",
        },
    ),
    "quality": Score(
        instructions="How likely is this lead to become a paying customer?",
        criteria=[
            "Very unlikely",
            "Unlikely",
            "Possible",
            "Likely",
            "Very likely",
        ],
    ),
    "urgent": Noul(instructions="The message needs a reply within the hour."),
}


@dataclass(frozen=True)
class LeadDecision:
    intent: str
    intent_confidence: float
    quality: float
    urgent_probability: float

    @property
    def is_urgent(self) -> bool:
        return self.urgent_probability >= 0.5


def analyze_lead(message: str, client: TypeSafeClient) -> LeadDecision:
    """Ek lead message Jev ko bhej kar typed decision wapas lein."""
    response = client.system_one(state={"message": message}, questions=QUESTIONS)
    intent = response.choices["intent"]
    return LeadDecision(
        intent=intent.choice,
        intent_confidence=intent.confidence,
        quality=response.scores["quality"].score,
        urgent_probability=response.nouls["urgent"].noul,
    )
