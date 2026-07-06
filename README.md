# signalpress

**A config-driven, stateful newsletter agent — with output evals.**

Most "scheduled AI digest" setups are a cron job firing a prompt: stateless, unverifiable, and
prone to silently degrading. signalpress is the pipeline version:

```
deterministic fetchers ──► LLM judgment (structured output) ──► SQLite items
        │                                                          │
        └── every source guaranteed by code, not prompt pleading   ├──► rendered markdown digest
                                                                   ├──► eval gates (visible failures)
                                                                   └──► weekly cross-run synthesis
                                                                        + build-of-the-week + tracker
```

**This repo runs itself.** GitHub Actions executes the pipeline daily and commits the results
back — so the repo is the live demo:

- [`newsletter.yaml`](newsletter.yaml) — the editorial policy producing everything below
- [`digests/`](digests/) — the daily digests and weekly pattern reports, as they land
- [Actions](../../actions) — every run, its gate results, and its logs, in public

## What makes it different

1. **Editorial policy as schema, not prompt.** `newsletter.yaml` defines the reader persona,
   lanes, distillation lens (hot / deep / high-value), recency rule, and prior-art rule. Prompts
   are *compiled* from the schema — one free-text `extra_instructions` escape hatch. Swap the
   lanes and persona and the same machine becomes a biotech digest, a legal-AI digest, a
   design-tools digest.
2. **Compounding state.** Daily runs store items as structured rows in SQLite. The weekly run
   synthesizes across the week ("what appeared more than once, across more than one source?"),
   proposes one weekend-sized build-of-the-week that must name the existing project it extends,
   and records it in a tracker so it never re-suggests what you've already shipped.
3. **Output evals.** Programmatic gates on every run — links resolve, items within
   `recency_days`, every apply-hook names a real tool, no dupes, every source fetched. Failures
   flag the digest, they never block it. On top: an LLM lens-adherence judge (a different,
   cheaper model that audits but never picks) whose 1–5 scores are recorded as telemetry and
   trended with `signalpress trend`.
4. **Pipeline, not agent.** The LLM never browses; fetchers are deterministic API/RSS code.
   Cheap, testable, and no source can be silently skipped.

## Get your own

### Fork-and-go (recommended — no server, no laptop)

1. Fork this repo and enable Actions in your fork (scheduled workflows are off by default).
2. Clone your fork, then:
   ```bash
   uv sync
   uv run signalpress init        # writes newsletter.yaml
   # edit newsletter.yaml: your field, your lanes, your definition of high-value
   git add -f newsletter.yaml && git commit -m "my editorial policy" && git push
   ```
3. Add `ANTHROPIC_API_KEY` as a repo secret (Settings → Secrets and variables → Actions).
   Or use `OPENAI_API_KEY` and change the `models:` block in your config.

The shipped workflow ([`.github/workflows/signalpress.yml`](.github/workflows/signalpress.yml))
runs the daily digest at 07:00 UTC and the weekly report Saturday 08:00 UTC, committing the
digests and SQLite state back to your fork. Trigger ad-hoc runs from the Actions tab. Details
and cron/launchd alternatives: [`docs/scheduling.md`](docs/scheduling.md).

### Run locally

```bash
git clone https://github.com/nishshukladev/signalpress && cd signalpress
uv sync
uv run signalpress init        # writes newsletter.yaml + creates signalpress.db
export ANTHROPIC_API_KEY=...
uv run signalpress daily       # fetch -> judge -> gates -> digests/digest-YYYY-MM-DD.md
uv run signalpress weekly      # week's items -> pattern report + build-of-the-week
uv run signalpress trend       # judge-score & gate-failure trends across runs
```

## Sources — no code required

Built-in fetchers: Hacker News (Algolia API) · arXiv (export API) · Hugging Face daily papers ·
RSS/Atom · Reddit (public feeds) · Bluesky feed generators (public AppView) · **any JSON API**
via the config-only `json_api` type.

Adding your own source is a config edit, not a Python file:

- **Anything with an RSS/Atom feed** — blogs, Substacks, YouTube channels, GitHub releases —
  is a URL under `type: rss`.
- **Sites without feeds:** generate one with [RSSHub](https://docs.rsshub.app),
  [openrss.org](https://openrss.org), or [Kill the Newsletter](https://kill-the-newsletter.com)
  (email newsletters → feeds).
- **Public JSON APIs:** declare the endpoint and field paths under `type: json_api`:
  ```yaml
  - type: json_api
    name: lobsters
    url: https://lobste.rs/hottest.json
    items_path: ""            # dot-path to the item list ('' = response root)
    field_map:
      title: title
      url: url
      published_at: created_at   # epoch seconds/millis or ISO 8601, auto-detected
      snippet: description_plain
  ```

The annotated template lives at
[`src/signalpress/templates/newsletter.example.yaml`](src/signalpress/templates/newsletter.example.yaml)
(inside the package so `signalpress init` works from any install); this repo's live
[`newsletter.yaml`](newsletter.yaml) is a working example.

Each source declares a mode: `api` (v1), while `scrape-local` and `search-fallback` are
reserved for sources without public APIs (e.g. X requires a local browser session and is
deliberately out of scope for anything hosted).

## Models

Any [Pydantic AI](https://ai.pydantic.dev) model string works, per stage:

```yaml
models:
  judgment: "anthropic:claude-sonnet-4-5"   # keep/drop + tagging (one batched call/day)
  judge: "anthropic:claude-haiku-4-5"       # cheap lens-adherence telemetry
  synthesis: "anthropic:claude-sonnet-4-5"  # weekly pattern report
```

A daily run costs roughly one frontier-model call plus ~a dozen cheap judge calls — cents, not
dollars. Set a spend cap on the API key you put in a public fork's secrets.

## Development

```bash
uv sync
uv run pytest -q
uv run ruff check .
```

Design notes and every architectural decision with its tradeoffs:
[`docs/decisions.md`](docs/decisions.md).
