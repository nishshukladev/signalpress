"""SQLAlchemy ORM models. SQLite is the source of truth for structured state;
markdown digests are rendered artifacts, never storage."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    kind: Mapped[str] = mapped_column(String(16))  # daily | weekly
    started_at: Mapped[datetime] = mapped_column(default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(default=None)
    config_hash: Mapped[str] = mapped_column(String(12))
    status: Mapped[str] = mapped_column(String(16), default="running")  # running|ok|gated|failed
    output_path: Mapped[str | None] = mapped_column(Text, default=None)


class FetchLog(Base):
    __tablename__ = "fetch_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"))
    source: Mapped[str] = mapped_column(String(32))
    ok: Mapped[bool] = mapped_column(default=True)
    candidate_count: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(Text, default=None)


class Item(Base):
    __tablename__ = "items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"))
    source: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    dedupe_key: Mapped[str] = mapped_column(String(256), index=True)
    published_at: Mapped[datetime | None] = mapped_column(default=None)
    lane: Mapped[str] = mapped_column(String(64))
    axes: Mapped[str] = mapped_column(String(64))  # csv of hot,deep,high_value
    summary: Mapped[str] = mapped_column(Text)
    why_it_matters: Mapped[str] = mapped_column(Text)
    apply_hook_effort: Mapped[str] = mapped_column(String(16))
    apply_hook_action: Mapped[str] = mapped_column(Text)
    apply_hook_tool: Mapped[str] = mapped_column(Text)
    section: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(default=_now)


class EvalResult(Base):
    __tablename__ = "eval_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"))
    check_name: Mapped[str] = mapped_column(String(64))
    item_id: Mapped[str | None] = mapped_column(ForeignKey("items.id"), default=None)
    passed: Mapped[bool] = mapped_column(default=True)
    detail: Mapped[str | None] = mapped_column(Text, default=None)


class JudgeScore(Base):
    __tablename__ = "judge_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"))
    item_id: Mapped[str] = mapped_column(ForeignKey("items.id"))
    rubric: Mapped[str] = mapped_column(String(32), default="lens_adherence")
    score: Mapped[int] = mapped_column()
    rationale: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(64))


class TrackerEntry(Base):
    __tablename__ = "tracker"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    idea: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="idea")  # idea|backlog|active|shipped
    lane: Mapped[str] = mapped_column(String(64))
    builds_on: Mapped[str] = mapped_column(Text, default="")  # named prior art
    source_run_id: Mapped[str | None] = mapped_column(ForeignKey("runs.id"), default=None)
    created_at: Mapped[datetime] = mapped_column(default=_now)
