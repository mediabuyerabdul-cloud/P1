# JEV Integration

[TypeSafe AI](https://typesafe.ai) ke **Jev** model ka integration. Jev chat nahi karta:
aap use text/state aur typed sawal bhejte hain, aur woh typed jawab probability ke saath deta hai.

Pehla feature: **lead analyzer**. Ek customer message ke liye Jev batata hai:
- `intent`: buy / question / complaint / spam (Choice)
- `quality`: customer banne ka chance, 1 se 5 (Score)
- `urgent`: ek ghante mein reply chahiye? (Noul, haan ki probability)

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env        # phir .env mein apni TYPESAFE_API_KEY daalein
python src/main.py "Price kya hai? Aaj hi order karna hai"
pytest                      # tests (API key ki zaroorat nahi)
```

API key yahan se banayein: https://console.typesafe.ai/keys

Sawal (questions) aur unke options ek hi jagah hain: `src/jev_integration/leads.py` mein `QUESTIONS`.

## Claude Code skill

Official TypeSafe skill install karne ke liye apne terminal mein chalayein:

```bash
claude plugin marketplace add typesafe-ai/skills
claude plugin install typesafe@typesafe-ai
```

## Status

- [x] Step 1: Repository create ho gayi (GitHub: `mediabuyerabdul-cloud/P1`)
- [x] Step 2: Starter files (README, .gitignore)
- [x] Step 3: TypeSafe Jev SDK add kiya
- [x] Step 4: Pehla feature: lead analyzer
- [ ] Step 5: Apni API key se asal test chalana

## Folder structure

```
P1/
├── README.md    # Project ki maloomat
├── .gitignore   # Woh files jo Git save nahi karega
├── src/jev_integration/  # Jev ka code
├── src/main.py  # Chalane wali file
├── tests/       # Tests
└── docs/        # Notes aur documentation
```
