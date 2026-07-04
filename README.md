# signalpress

**A config-driven, stateful newsletter agent — with output evals.**

Most "scheduled AI digest" setups are a cron job firing a prompt: stateless, unverifiable, and
prone to silently degrading. signalpress is the pipeline version:

```
deterministic fetchers ──► LLM judgment (structured output) ──► SQLite items
        │                                                          │
        └── every beat guaranteed by code, not prompt pleading     ├──► rendered markdown digest
                                                                   ├──► eval gates (visible failures)
                                                                   └──► weekly cross-run synthesis
                                                                        + build-of-the-week + tracker
```

## What makes it different

1. **Editorial policy as schema, not prompt.** `newsletter.yaml` defines the reader persona,
   lanes, distillation lens (hot / deep / high-value), recency rule, and prior-art rule. Prompts
   are *compiled* from the schema. One free-text `extra_instructions` escape hatch.
2. **Compounding state.** Daily runs store items as structured rows in SQLite. The weekly run
   synthesizes across the week, proposes one build-of-the-week, and records it in a tracker so
   it never re-suggests what you've already shipped.
3. **Output evals.** Programmatic gates on every run — links resolve, items within
   `recency_days`, every apply-hook names a real tool, no dupes, every source fetched — plus an
   LLM lens-adherence judge whose scores are recorded as telemetry and trended (`signalpress trend`).
4. **Pipeline, not agent.** The LLM never browses; fetchers are deterministic API/RSS code.
   Cheap, testable, and beats can't be silently skipped.

## Quickstart

```bash
uv tool install signalpress   # or: uv sync inside the repo
signalpress init              # writes newsletter.yaml + creates signalpress.db
# edit newsletter.yaml; export ANTHROPIC_API_KEY (or OPENAI_API_KEY + change models)
signalpress daily             # fetch -> judge -> gates -> digests/digest-YYYY-MM-DD.md
signalpress weekly            # week's items -> pattern report + build-of-the-week
signalpress trend             # judge-score & gate-failure trends across runs
```

Schedule it with cron / launchd / GitHub Actions — the tool is scheduler-agnostic by design.

## Sources (v1)

Hacker News (Algolia API) · arXiv (export API) · Hugging Face daily papers · RSS/Atom (any
practitioner blog) · Reddit (public JSON) · Bluesky feed generators (public AppView).

Each source declares a mode: `api` (v1), `scrape-local` and `search-fallback` are reserved for
sources without public APIs (e.g. X requires a local browser session and is deliberately out of
scope for anything hosted).

## Models

Any [Pydantic AI](https://ai.pydantic.dev) model string works, per stage:

```yaml
models:
  judgment: "anthropic:claude-sonnet-4-5"   # keep/drop + tagging (one batched call/day)
  judge: "anthropic:claude-haiku-4-5"       # cheap lens-adherence telemetry
  synthesis: "anthropic:claude-sonnet-4-5"  # weekly pattern report
```

## Development

```bash
uv sync
uv run pytest -q
uv run ruff check .
```

Design notes and every architectural decision with tradeoffs: [`docs/decisions.md`](docs/decisions.md).
