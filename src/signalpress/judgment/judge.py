"""Lens-adherence judge: telemetry, never a gate.

Decision: per-item calls with a cheap model (config.models.judge). Per-item
keeps scores independent (no anchoring on neighbors) and lets us trend a stable
rubric across runs. Failures are recorded, not raised - telemetry must not
break the pipeline.
"""

import logging

from pydantic_ai import Agent

from signalpress.config.prompt_compiler import compile_judge_prompt
from signalpress.config.schema import NewsletterConfig
from signalpress.judgment.schemas import JudgeVerdict
from signalpress.store.models import Item


def build_judge_agent(config: NewsletterConfig) -> Agent[None, JudgeVerdict]:
    return Agent(
        config.models.judge,
        output_type=JudgeVerdict,
        instructions=compile_judge_prompt(config),
    )


def score_item(
    config: NewsletterConfig, item: Item, agent: Agent[None, JudgeVerdict] | None = None
) -> JudgeVerdict | None:
    agent = agent or build_judge_agent(config)
    prompt = (
        f"ITEM\ntitle: {item.title}\nurl: {item.url}\nlane: {item.lane}\n"
        f"claimed axes: {item.axes}\nsummary: {item.summary}\n"
        f"why it matters: {item.why_it_matters}\n"
        f"apply hook: [{item.apply_hook_effort}] {item.apply_hook_action} "
        f"(tool: {item.apply_hook_tool})"
    )
    try:
        return agent.run_sync(prompt).output
    except Exception as exc:  # noqa: BLE001 - telemetry must never break the run
        logging.getLogger(__name__).warning("judge scoring failed for item %s: %s", item.id, exc)
        return None
