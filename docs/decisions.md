# Decision Ledger

Every material decision, its alternatives, and the tradeoff taken. Newest last.

## D1 — OSS portfolio artifact, not SaaS
**Decision:** Ship as an open-source, BYOK, self-run tool. No hosted UI in v1.
**Alternatives:** Hosted SaaS with billing/auth; personal-only tool.
**Tradeoff:** Foregoes revenue path now; avoids the n8n-alike graveyard, credential custody,
and token-billing problems. The career leverage is the design + writeup, and a hosted door
stays open (SQLite → Postgres, config schema → UI form).

## D2 — Social layer degrades honestly; no credentialed scraping
**Decision:** Per-source `mode: api | scrape-local | search-fallback`. v1 implements `api` only.
X (login-gated) is out of scope for anything hosted; a local-browser mode is reserved.
**Alternatives:** Hold users' logins and scrape via hosted headless browsers.
**Tradeoff:** Loses X coverage in v1. Rejected credentialed scraping on three independent
grounds: credential/2FA custody liability, datacenter-IP bot detection banning *users'*
accounts, and platform ToS. Bluesky (public AT Protocol) and Reddit (public feeds) cover the
social beat without auth.

## D3 — Editorial policy as schema, prompts compiled
**Decision:** `newsletter.yaml` (Pydantic-validated) is the source of truth; all LLM
instructions are compiled from it (`config/prompt_compiler.py`). One `extra_instructions`
free-text escape hatch.
**Alternatives:** User-edited free-text prompt.
**Tradeoff:** Less prompt flexibility; in exchange, schema fields become checkable invariants
(recency_days, vague-tool denylist, max items) and the system is a product, not a prompt-runner.

## D4 — SQLite from day 1; markdown is a rendered artifact
**Decision:** Items, runs, eval results, judge scores, and the idea tracker are rows. Digests
are Jinja renders over rows, regeneratable at any time.
**Alternatives:** Repo-as-state (git-scraping pattern); items only as prose in markdown.
**Tradeoff:** Loses fork-and-go simplicity and free git diffing; gains SQL-powered weekly
synthesis, dedupe, and evals over structured rows, plus a clean Postgres migration path.
(User call, overriding the repo-as-state recommendation; accepted losses noted.)

## D5 — Pipeline, not agent
**Decision:** Deterministic fetchers (API/RSS) gather candidates; the LLM only judges,
tags, and writes via structured output. The LLM never browses.
**Alternatives:** Agentic browsing with web tools (how the original Claude prompt worked).
**Tradeoff:** Less flexibility for source-less beats; in exchange ~10x cheaper runs,
unit-testable fetchers, code-guaranteed beat coverage (the original prompt's "do NOT skip"
pleading is deleted as a problem class), and evals target one LLM step, not a trajectory.

## D6 — Python + Pydantic AI
**Decision:** Python 3.12, Pydantic AI (provider-agnostic model strings per stage),
SQLAlchemy 2 + SQLite, httpx, feedparser, Jinja2, typer, pytest + respx.
**Alternatives:** TypeScript + Vercel AI SDK; LiteLLM; LangChain.
**Tradeoff:** TS would ease a future web UI; Python wins on author fluency, Pydantic-native
structured output, and the eval-tooling ecosystem (Inspect AI, pydantic-evals) this project
speaks to. Provider switching is consumed off-the-shelf (Pydantic AI), not built.

## D7 — Evals: invariant gates + judge telemetry, asymmetric
**Decision:** Programmatic invariants (link resolves, recency, vague-tool denylist, lane
validity, dedupe, source coverage, weekly prior-art) fail *visibly* — run marked `gated`,
warnings block rendered atop the digest — but never block shipping. LLM lens-adherence judge
(cheap model, per-item, 1–5 + rationale) is recorded telemetry, never a gate.
**Alternatives:** Hard-fail gates; judge-as-gate; no evals.
**Tradeoff:** A flagged newsletter beats a silently missing one; judge scores are too noisy to
gate on but trend meaningfully (`signalpress trend`). Judge-vs-human agreement validation is
deliberately deferred to phase 2 (via pydantic-evals — extend, don't build).

## D8 — One batched judgment call per day, per-item judge calls
**Decision:** The daily keep/drop stage sees ALL candidates in one structured call; the judge
scores each kept item in separate cheap calls.
**Alternatives:** Per-candidate judgment calls; batched judge call.
**Tradeoff:** Ranking is relative — the model must see the pool to enforce `max_items_daily`
honestly. Judge is per-item to keep scores independent (no anchoring) and the rubric stable
across runs.

## D9 — Sync SQLAlchemy, async only at the fetch boundary
**Decision:** Fetchers run concurrently via asyncio/httpx; everything after gathering
(DB, LLM calls, render) is synchronous.
**Alternatives:** Async end-to-end.
**Tradeoff:** This is a daily batch job, not a server; async DB/LLM adds ceremony with zero
latency benefit at n=1 run.

## D10 — Dropped candidates are re-judged on later days
**Decision:** Only *kept* items enter the dedupe set. A candidate dropped yesterday reappears
in today's pool if still live on a source.
**Alternatives:** Persist drops and exclude them.
**Tradeoff:** Slight repeated-judgment cost (rides the same batched call, so ~zero marginal
tokens); in exchange, a story that was noise on day 1 can be promoted when it gains momentum —
which is exactly what the HOT axis is for. (Surfaced by a failing test; kept deliberately.)

## D11 — Reddit via multireddit Atom feed, not JSON
**Decision:** Fetch `r/A+B/top.rss` — one request for all subreddits, parsed with feedparser;
one retry on 429.
**Alternatives:** Public JSON endpoints (403 for non-browser clients since the 2023 API
changes); OAuth API (registration burden for every user).
**Tradeoff:** Loses score/comment counts as judge signal; keeps zero-auth setup. Live-tested:
unauthenticated RSS tolerates ~1 request/minute per IP, which forced the single-request design.

## D12 — Templates ship inside the package
**Decision:** `src/signalpress/templates/` (Jinja + example config) so wheel installs work.
**Alternatives:** Repo-root `templates/` (breaks on `uv tool install`).

## D13 — Scheduler-agnostic by design
**Decision:** No built-in scheduler. `signalpress daily|weekly` are idempotent commands; cron,
launchd, and GitHub Actions recipes are documented instead.
**Alternatives:** Built-in APScheduler/daemon.
**Tradeoff:** One less moving part to own; schedulers are a solved commodity and the "users
control the schedule" requirement is satisfied by *their* scheduler, not ours.
