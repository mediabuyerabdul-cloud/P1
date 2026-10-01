"""Chalane ke liye:  python src/main.py "Aapka price kya hai? Aaj hi order karna hai"
"""

import sys

from dotenv import load_dotenv
from typesafe_sdk import TypeSafeClient

from jev_integration import analyze_lead


def main() -> None:
    load_dotenv()  # .env file se TYPESAFE_API_KEY parhta hai
    message = " ".join(sys.argv[1:]) or "Hi, what is the price? I want to order today."

    with TypeSafeClient() as client:
        decision = analyze_lead(message, client)

    print(f"Message : {message}")
    print(f"Intent  : {decision.intent} ({decision.intent_confidence:.0%} confident)")
    print(f"Quality : {decision.quality:.1f} / 5")
    print(f"Urgent  : {'YES' if decision.is_urgent else 'no'} ({decision.urgent_probability:.0%})")


if __name__ == "__main__":
    main()
