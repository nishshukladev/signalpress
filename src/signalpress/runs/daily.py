"""Daily run orchestrator: fetch -> dedupe -> judge -> store -> gates -> render."""

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from signalpress.config.loader import config_hash
from signalpress.config.schema import NewsletterConfig
from signalpress.evals import invariants, report
from signalpress.judgment.judge import build_judge_agent, score_item
from signalpress.judgment.ranker import run_judgment
from signalpress.sources import FetchOutcome, fetch_all_sync
from signalpress.sources.base import Candidate, normalize_url
from signalpress.store import repo
from signalpress.store.models import EvalResult, Item, JudgeScore, Run

logger = logging.getLogger(__name__)


def _dedupe_candidates(candidates: list[Candidate], prior_keys: set[str]) -> list[Candidate]:
    seen: set[str] = set()
    fresh = []
    for c in candidates:
        key = normalize_url(c.url)
        if key in prior_keys or key in seen:
            continue
        seen.add(key)
        fresh.append(c)
    return fresh


def _store_kept_items(
    session: Session, *, run: Run, candidates: list[Candidate], verdicts
) -> list[Item]:
    items = []
    for verdict in verdicts.verdicts:
        if not verdict.keep or verdict.apply_hook is None:
            continue
        if not 0 <= verdict.candidate_index < len(candidates):
            logger.warning("verdict references invalid candidate index %s", verdict.candidate_index)
            continue
        c = candidates[verdict.candidate_index]
        item = Item(
            run_id=run.id,
            source=c.source,
            title=c.title,
            url=c.url,
            dedupe_key=normalize_url(c.url),
            published_at=c.published_at,
            lane=verdict.lane,
            axes=verdict.axes.as_csv(),
            summary=verdict.summary,
            why_it_matters=verdict.why_it_matters,
            apply_hook_effort=verdict.apply_hook.effort.value,
            apply_hook_action=verdict.apply_hook.action,
            apply_hook_tool=verdict.apply_hook.tool,
            section=verdict.section.value,
        )
        session.add(item)
        items.append(item)
    session.flush()
    return items


def run_daily(
    session: Session,
    config: NewsletterConfig,
    *,
    check_links: bool = True,
    with_judge: bool = True,
) -> tuple[Run, list[Item], str, str]:
    """Returns (run, kept_items, pattern_watch, warnings_block). Render happens in CLI."""
    run = repo.create_run(session, kind="daily", config_hash=config_hash(config))

    outcomes: list[FetchOutcome] = fetch_all_sync(config.enabled_sources())
    all_candidates: list[Candidate] = []
    for outcome in outcomes:
        repo.log_fetch(
            session,
            run_id=run.id,
            source=outcome.source,
            ok=outcome.ok,
            count=len(outcome.candidates),
            error=outcome.error,
        )
        all_candidates.extend(outcome.candidates)

    prior_keys = repo.recent_dedupe_keys(session, days=config.rules.recency_days)
    candidates = _dedupe_candidates(all_candidates, prior_keys)
    logger.info("fetched %d candidates, %d after dedupe", len(all_candidates), len(candidates))

    verdicts = run_judgment(config, candidates)
    items = _store_kept_items(session, run=run, candidates=candidates, verdicts=verdicts)

    gate_results = invariants.run_all_gates(
        items=items,
        config=config,
        outcomes=outcomes,
        prior_keys=prior_keys,
        check_links=check_links,
    )
    for r in gate_results:
        session.add(
            EvalResult(
                run_id=run.id,
                check_name=r.check_name,
                item_id=r.item_id,
                passed=r.passed,
                detail=r.detail,
            )
        )

    if with_judge:
        judge_agent = build_judge_agent(config)
        for item in items:
            verdict = score_item(config, item, judge_agent)
            if verdict is not None:
                session.add(
                    JudgeScore(
                        run_id=run.id,
                        item_id=item.id,
                        score=verdict.score,
                        rationale=verdict.rationale,
                        model=config.models.judge,
                    )
                )

    warnings = report.warnings_block(gate_results)
    repo.finish_run(session, run=run, status=report.run_status(gate_results), output_path=None)
    run.finished_at = datetime.now(UTC)
    return run, items, verdicts.pattern_watch, warnings
