# CONTINUITY — signalpress

Living briefing for this workspace. Read before acting; update on meaningful deltas.

## [PLANS]
- 2026-07-04T19:30Z [USER] Goal: OSS portfolio artifact — "config-driven, stateful newsletter
  agent with output evals." Writeup planned once v1 is exercised on real runs.
- 2026-07-04T19:30Z [ASSUMPTION] Phase 2 candidates (not started): judge-vs-human agreement
  validation via pydantic-evals; email delivery (Buttondown/Resend); `search-fallback` and
  `scrape-local` source modes; Postgres migration if ever hosted.

## [DECISIONS]
- 2026-07-04T19:30Z [USER]+[ASSUMPTION] All architectural decisions with tradeoffs live in
  `docs/decisions.md` (D1–D13). Headlines: OSS+BYOK, schema-compiled prompts, SQLite as source
  of truth, pipeline-not-agent, Pydantic AI, gates-visible-but-non-blocking, judge-as-telemetry.

## [PROGRESS]
- 2026-07-04T20:10Z [CODE] v1 implemented: config schema+loader+prompt compiler; 6 fetchers
  (hn, arxiv, hf_papers, rss, bluesky, reddit); store (runs/items/eval_results/judge_scores/
  tracker); judgment stages (ranker, judge, synthesis) via Pydantic AI structured output;
  invariant gates + warnings block; Jinja render; daily/weekly orchestrators; typer CLI
  (init/daily/weekly/trend). 27 tests green, ruff clean.
- 2026-07-04T20:10Z [TOOL] Live smoke: hn/arxiv/hf_papers/rss/reddit all fetch real data.
  Reddit needed two redesigns (JSON 403 → RSS; per-sub requests 429 → single multireddit
  request). Bluesky implemented but ships disabled (needs user-chosen feed URIs).

## [DISCOVERIES]
- 2026-07-04T19:50Z [TOOL] Reddit public JSON returns 403 for non-browser UAs; `.rss` Atom
  works but tolerates only ~1 unauthenticated request/minute/IP → multireddit single-request
  design (decisions.md D11).
- 2026-07-04T19:55Z [CODE] Jinja gotcha: `dict.items` attribute access resolves the builtin
  method, not the key — grouped-section dicts use key `entries`.
- 2026-07-04T20:00Z [CODE] Dedupe intentionally covers kept items only; dropped candidates are
  re-judged on later days so momentum can promote them (D10; asserted by test).

## [OUTCOMES]
- 2026-07-04T20:15Z [CODE] v1 ready: installable package, green suite, live fetchers.
  UNCONFIRMED: full LLM run end-to-end (needs ANTHROPIC_API_KEY at runtime).
