"""Orchestration tests: LLM stages stubbed (TestModel / monkeypatch), everything
else real - store, dedupe, gates, render. No network, no API keys."""

from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from signalpress.config.prompt_compiler import compile_judgment_prompt
from signalpress.judgment.ranker import run_judgment
from signalpress.judgment.schemas import (
    ApplyHook,
    Axis,
    BuildOfWeek,
    DailyVerdicts,
    ItemVerdict,
    WeeklyReport,
)
from signalpress.render.renderer import render_digest
from signalpress.runs import daily as daily_mod
from signalpress.runs import weekly as weekly_mod
from signalpress.sources import FetchOutcome
from signalpress.sources.base import Candidate
from signalpress.store import repo

CANDIDATES = [
    Candidate(
        source="hn",
        title="Inspect AI ships agent evals",
        url="https://example.com/inspect",
        published_at=None,
        stats="400 points",
    ),
    Candidate(source="hn", title="Celebrity gossip", url="https://example.com/gossip"),
]

VERDICTS = DailyVerdicts(
    verdicts=[
        ItemVerdict(
            candidate_index=0,
            keep=True,
            lane="agents-evals",
            axes=Axis(hot=True, high_value=True),
            section="top3",
            summary="Inspect AI added agent eval support. It matters.",
            why_it_matters="Direct lane hit.",
            apply_hook=ApplyHook(
                effort="read", action="Read the release notes.", tool="Inspect AI"
            ),
        ),
        ItemVerdict(candidate_index=1, keep=False, drop_reason="noise"),
    ],
    pattern_watch="Evals tooling recurred across sources.",
)


def test_run_judgment_with_test_model(config) -> None:
    agent = Agent(
        TestModel(custom_output_args=VERDICTS.model_dump(mode="json")),
        output_type=DailyVerdicts,
        instructions=compile_judgment_prompt(config),
    )
    out = run_judgment(config, CANDIDATES, agent)
    assert len(out.verdicts) == 2
    assert out.verdicts[0].keep and out.verdicts[0].apply_hook.tool == "Inspect AI"


def _patch_daily(monkeypatch) -> None:
    monkeypatch.setattr(
        daily_mod,
        "fetch_all_sync",
        lambda sources: [FetchOutcome(source="hn", ok=True, candidates=list(CANDIDATES))],
    )
    monkeypatch.setattr(daily_mod, "run_judgment", lambda config, candidates: VERDICTS)


def test_run_daily_end_to_end(session, config, monkeypatch) -> None:
    _patch_daily(monkeypatch)
    run, items, pattern_watch, warnings = daily_mod.run_daily(
        session, config, check_links=False, with_judge=False
    )
    assert len(items) == 1  # gossip dropped
    assert items[0].lane == "agents-evals"
    assert pattern_watch.startswith("Evals tooling")
    # gates ran: recency fails (published_at None) -> gated status + warning block
    assert run.status == "gated"
    assert "recency" in warnings
    # eval rows persisted
    checks = {r.check_name for r in repo.eval_results_for_run(session, run_id=run.id)}
    assert {"recency", "apply_hook_tool", "lane_validity", "source_coverage", "dedupe"} <= checks
    # digest renders with warning block and item
    content = render_digest(
        config=config, items=items, pattern_watch=pattern_watch, warnings_block=warnings
    )
    assert "Inspect AI ships agent evals" in content
    assert "⚠️" in content


def test_daily_dedupes_against_prior_run(session, config, monkeypatch) -> None:
    _patch_daily(monkeypatch)
    daily_mod.run_daily(session, config, check_links=False, with_judge=False)

    # second run: the KEPT item is deduped away; the dropped one is re-judged by
    # design (yesterday's noise may gain momentum; it rides the same batched call).
    def judgment_second_day(config, candidates):
        assert [c.title for c in candidates] == ["Celebrity gossip"]
        return DailyVerdicts(verdicts=[], pattern_watch="Quiet day.")

    monkeypatch.setattr(daily_mod, "run_judgment", judgment_second_day)
    _, items, _, _ = daily_mod.run_daily(session, config, check_links=False, with_judge=False)
    assert items == []


WEEKLY = WeeklyReport(
    themes=[],
    build_of_week=BuildOfWeek(
        title="Reproduce SWE-bench-lite scoring with Inspect AI",
        description="Weekend-sized.",
        builds_on="Inspect AI",
        prior_art_checked="Searched Inspect AI docs and SWE-bench harness.",
        result_to_publish="Agreement rate vs official harness.",
        draft_post_title="I re-scored SWE-bench with Inspect AI",
    ),
    backlog_ideas=["Trend judge scores publicly"],
    lane_check="Stay the course.",
)


def test_run_weekly_feeds_tracker(session, config, monkeypatch) -> None:
    monkeypatch.setattr(weekly_mod, "run_synthesis", lambda c, i, t: WEEKLY)
    run, report, _, warnings = weekly_mod.run_weekly(session, config)
    assert run.status == "ok" and warnings == ""
    entries = repo.tracker_entries(session)
    assert {e.status for e in entries} == {"idea", "backlog"}
    assert entries[0].builds_on == "Inspect AI"


def test_weekly_gates_vague_prior_art(session, config, monkeypatch) -> None:
    vague = WEEKLY.model_copy(deep=True)
    vague.build_of_week.builds_on = "a tool"
    monkeypatch.setattr(weekly_mod, "run_synthesis", lambda c, i, t: vague)
    run, _, _, warnings = weekly_mod.run_weekly(session, config)
    assert run.status == "gated"
    assert "build_prior_art" in warnings
