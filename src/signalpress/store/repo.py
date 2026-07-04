"""Query/write functions over the store. Kept as plain functions (no repository
class) - the surface is small and functions are easier to test."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from signalpress.store.models import EvalResult, FetchLog, Item, JudgeScore, Run, TrackerEntry


def create_run(session: Session, *, kind: str, config_hash: str) -> Run:
    run = Run(kind=kind, config_hash=config_hash)
    session.add(run)
    session.flush()
    return run


def finish_run(session: Session, *, run: Run, status: str, output_path: str | None) -> None:
    run.finished_at = datetime.now(UTC)
    run.status = status
    run.output_path = output_path


def log_fetch(
    session: Session, *, run_id: str, source: str, ok: bool, count: int, error: str | None = None
) -> None:
    session.add(FetchLog(run_id=run_id, source=source, ok=ok, candidate_count=count, error=error))


def recent_dedupe_keys(session: Session, *, days: int) -> set[str]:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    stmt = select(Item.dedupe_key).where(Item.created_at >= cutoff)
    return set(session.scalars(stmt).all())


def items_for_run(session: Session, *, run_id: str) -> list[Item]:
    return list(session.scalars(select(Item).where(Item.run_id == run_id)).all())


def items_since(session: Session, *, days: int) -> list[Item]:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    stmt = select(Item).where(Item.created_at >= cutoff).order_by(Item.created_at)
    return list(session.scalars(stmt).all())


def fetch_logs_for_run(session: Session, *, run_id: str) -> list[FetchLog]:
    return list(session.scalars(select(FetchLog).where(FetchLog.run_id == run_id)).all())


def eval_results_for_run(session: Session, *, run_id: str) -> list[EvalResult]:
    return list(session.scalars(select(EvalResult).where(EvalResult.run_id == run_id)).all())


def judge_scores_for_run(session: Session, *, run_id: str) -> list[JudgeScore]:
    return list(session.scalars(select(JudgeScore).where(JudgeScore.run_id == run_id)).all())


def tracker_entries(session: Session) -> list[TrackerEntry]:
    return list(session.scalars(select(TrackerEntry).order_by(TrackerEntry.created_at)).all())


def add_tracker_entry(
    session: Session, *, idea: str, lane: str, builds_on: str, source_run_id: str, status: str
) -> TrackerEntry:
    entry = TrackerEntry(
        idea=idea, lane=lane, builds_on=builds_on, source_run_id=source_run_id, status=status
    )
    session.add(entry)
    session.flush()
    return entry
