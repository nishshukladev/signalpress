"""Weekly synthesis stage: a week of stored items + tracker -> WeeklyReport."""

import json

from pydantic_ai import Agent

from signalpress.config.prompt_compiler import compile_synthesis_prompt
from signalpress.config.schema import NewsletterConfig
from signalpress.judgment.schemas import WeeklyReport
from signalpress.store.models import Item, TrackerEntry


def _items_payload(items: list[Item]) -> str:
    rows = [
        {
            "id": item.id,
            "source": item.source,
            "title": item.title,
            "url": item.url,
            "lane": item.lane,
            "axes": item.axes,
            "section": item.section,
            "summary": item.summary,
            "apply_hook_tool": item.apply_hook_tool,
            "created_at": item.created_at.isoformat(),
        }
        for item in items
    ]
    return json.dumps(rows, ensure_ascii=False)


def _tracker_payload(entries: list[TrackerEntry]) -> str:
    rows = [
        {"idea": e.idea, "status": e.status, "lane": e.lane, "builds_on": e.builds_on}
        for e in entries
    ]
    return json.dumps(rows, ensure_ascii=False)


def build_synthesis_agent(config: NewsletterConfig) -> Agent[None, WeeklyReport]:
    return Agent(
        config.models.synthesis,
        output_type=WeeklyReport,
        instructions=compile_synthesis_prompt(config),
    )


def run_synthesis(
    config: NewsletterConfig,
    items: list[Item],
    tracker: list[TrackerEntry],
    agent: Agent[None, WeeklyReport] | None = None,
) -> WeeklyReport:
    agent = agent or build_synthesis_agent(config)
    prompt = (
        f"THE WEEK'S KEPT ITEMS (JSON):\n{_items_payload(items)}\n\n"
        f"EXISTING TRACKER (never re-propose these):\n{_tracker_payload(tracker)}"
    )
    return agent.run_sync(prompt).output
