"""Daily judgment stage: candidates -> keep/drop verdicts via one structured call.

Decision: one batched call over all candidates (not per-item calls). Ranking is
relative - the model must see the whole pool to enforce max_items_daily and
compare items against each other. Cost: one large call/day vs N small ones.
"""

import json

from pydantic_ai import Agent

from signalpress.config.prompt_compiler import compile_judgment_prompt
from signalpress.config.schema import NewsletterConfig
from signalpress.judgment.schemas import DailyVerdicts
from signalpress.sources.base import Candidate


def _candidates_payload(candidates: list[Candidate]) -> str:
    rows = [
        {
            "index": i,
            "source": c.source,
            "title": c.title,
            "url": c.url,
            "published_at": c.published_at.isoformat() if c.published_at else None,
            "snippet": c.snippet,
            "stats": c.stats,
        }
        for i, c in enumerate(candidates)
    ]
    return json.dumps(rows, ensure_ascii=False)


def build_judgment_agent(config: NewsletterConfig) -> Agent[None, DailyVerdicts]:
    return Agent(
        config.models.judgment,
        output_type=DailyVerdicts,
        instructions=compile_judgment_prompt(config),
    )


def run_judgment(
    config: NewsletterConfig,
    candidates: list[Candidate],
    agent: Agent[None, DailyVerdicts] | None = None,
) -> DailyVerdicts:
    agent = agent or build_judgment_agent(config)
    lanes = ", ".join(lane.id for lane in config.lanes)
    prompt = (
        f"Valid lane ids: {lanes}.\n"
        f"Keep at most {config.rules.max_items_daily} items total.\n"
        f"CANDIDATES (JSON):\n{_candidates_payload(candidates)}"
    )
    return agent.run_sync(prompt).output
