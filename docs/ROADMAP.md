# Decision Maker By A — Roadmap

Localhost tool for a faceless-YouTube agency. **Jev (typesafe.ai) is the decision
engine** for every verdict; a built-in rule scorer is the offline fallback.
YouTube data is read by browsing public pages (no API key, no login).
Stack: Python + Flask + a browser page, same pattern as the downloader tool.

## Phases

| # | Phase | Features | Needs |
|---|-------|----------|-------|
| 1 | Niche & Topic Vetting | Go/No-Go (Jev) · Demand vs. Saturation | YouTube (browser) · Jev |
| 2 | Competitor Profiling | Strategy mapping · Blueprint extraction | YouTube · Jev/LLM |
| 3 | Production & Prompts | Hook & outline prompts · Visual & thumbnail specs | LLM |
| 4 | Post-Production QA & Packaging | Title strength (virality+SEO) · Glitch pick on visuals · Licence ledger + pacing* · Workflow checker · Virality score · Backend tags · Description | LLM · YouTube · ffmpeg |
| 5 | Performance Feedback (Learn) | Title-repeat check · Script/character repetition risk · Winner → template · Views-drop pause flag | Catalog DB · YouTube · Jev/LLM |
| 6 | Uploading | Best upload-time window | YouTube (+ OAuth for audience hours) |
| 7 | Analysis | Prompt A/B comparison · Video analysis (timestamps, visual count) | LLM · ffmpeg |
| 8 | Creative Direction | Intro & hook pick · Retention map · Thumbnail direction · Best duration · Voice-over pick* | LLM · your voice set |
| 9 | Assets & Routing | Template pick · Font & typography pick* · Predict potential (range)** · Best tool/model per task | LLM · your asset lists |
| 10 | Risk & Compliance (cross-cutting) | Copyright/music-claim risk · reused-content risk · misleading title/thumb · guideline risk per niche | Jev/LLM · licence ledger |

\* reframed for safety: licence tracking, voices you own, not "safe seconds".
\*\* predictions shown as a range with confidence, never a guarantee.

## Input formats
One shared input layer; each phase plugs in only the readers it needs.
Now (Phase 1): typed/pasted ideas, CSV (export your Google Sheet as CSV), YouTube browsing.
Later: mp4 (Phase 7 video analysis), images (Phase 4 glitch check), mp3 (Phase 8 voice), pdf/doc where a phase needs them.

## Keys
- **Jev / TYPESAFE_API_KEY** — the decision engine (console.typesafe.ai). Put in `.env`.
- **LLM API key** (Claude/OpenAI) — text generation in later phases. Official APIs only.
- No login cookies for ChatGPT/Claude/Muse — ToS/ban risk.

## Status
- [x] Phase 1 built: Go/No-Go via Jev (rule fallback), YouTube browser reader, localhost UI, CSV export.
- [ ] Validate YouTube reader live on a real machine (blocked in cloud dev).
- [x] Phases 2-9 built as Jev decision presets (score / pick / classify) in one generic engine.
- [ ] Generative sub-features (Phase 3 prompts, Phase 4 description/tags, Phase 4 glitch, Phase 7 video) need an LLM/vision/ffmpeg key.
- [ ] Validate all phases live once a Jev key is added.

## Run
`start-decision-maker.bat` → opens http://127.0.0.1:5001
