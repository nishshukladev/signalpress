"""Weekly run orchestrator: week's items + tracker -> synthesis -> tracker rows."""

import logging

from sqlalchemy.orm import Session

from signalpress.config.loader import config_hash
from signalpress.config.schema import NewsletterConfig
from signalpress.judgment.schemas import WeeklyReport
from signalpress.judgment.synthesis import run_synthesis
from signalpress.store import repo
from signalpress.store.models import EvalResult, Item, Run

logger = logging.getLogger(__name__)

WEEK_DAYS = 7


def _check_build_prior_art(report: WeeklyReport, config: NewsletterConfig) -> tuple[bool, str]:
    denylist = {t.lower() for t in config.rules.vague_tool_denylist}
    builds_on = report.build_of_week.builds_on.strip().lower()
    ok = bool(builds_on) and builds_on not in denylist
    return ok, report.build_of_week.builds_on


def run_weekly(
    session: Session, config: NewsletterConfig
) -> tuple[Run, WeeklyReport, dict[str, Item], str]:
    """Returns (run, report, items_by_id, warnings_block)."""
    run = repo.create_run(session, kind="weekly", config_hash=config_hash(config))

    items = repo.items_since(session, days=WEEK_DAYS)
    tracker = repo.tracker_entries(session)
    logger.info("synthesizing over %d items, %d tracker entries", len(items), len(tracker))

    report = run_synthesis(config, items, tracker)

    # Gate: build-of-week must name real prior art (the no-goose-chase rule as code).
    prior_art_ok, builds_on = _check_build_prior_art(report, config)
    session.add(
        EvalResult(
            run_id=run.id,
            check_name="build_prior_art",
            passed=prior_art_ok,
            detail=None if prior_art_ok else f"vague builds_on: {builds_on!r}",
        )
    )
    warnings = (
        ""
        if prior_art_ok
        else (
            "> ⚠️ 1 eval gate failure(s) this run:\n"
            f"> - `build_prior_art`: vague builds_on: {builds_on!r}"
        )
    )

    # Feed the output loop: build-of-week -> tracker idea; backlog ideas -> backlog.
    repo.add_tracker_entry(
        session,
        idea=report.build_of_week.title,
        lane=report.themes[0].title if report.themes else "",
        builds_on=report.build_of_week.builds_on,
        source_run_id=run.id,
        status="idea",
    )
    for idea in report.backlog_ideas:
        repo.add_tracker_entry(
            session, idea=idea, lane="", builds_on="", source_run_id=run.id, status="backlog"
        )

    items_by_id = {item.id: item for item in items}
    repo.finish_run(session, run=run, status="ok" if prior_art_ok else "gated", output_path=None)
    return run, report, items_by_id, warnings
