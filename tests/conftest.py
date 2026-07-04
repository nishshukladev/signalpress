from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from signalpress.config.schema import (
    Lane,
    NewsletterConfig,
    SourceConfig,
    SourceType,
)
from signalpress.store.db import make_engine, session_scope
from signalpress.store.models import Item


@pytest.fixture
def config() -> NewsletterConfig:
    return NewsletterConfig(
        name="Test Signal",
        persona="A test reader chasing staff-level AI engineering depth.",
        lanes=[
            Lane(id="agents-evals", label="AI agents + evals", weight=1.5),
            Lane(id="inference", label="LLM inference / serving", weight=1.5),
        ],
        sources=[
            SourceConfig(type=SourceType.HN, limit=5),
            SourceConfig(type=SourceType.ARXIV, limit=5, categories=["cs.LG"]),
        ],
        db_path=":memory:",
    )


@pytest.fixture
def session(tmp_path) -> Iterator[Session]:
    engine = make_engine(tmp_path / "test.db")
    with session_scope(engine) as s:
        yield s


def make_item(
    *,
    run_id: str,
    title: str = "A fine item",
    url: str = "https://example.com/post",
    lane: str = "agents-evals",
    tool: str = "Inspect AI",
    published_days_ago: int = 2,
    section: str = "repos",
) -> Item:
    return Item(
        run_id=run_id,
        source="hn",
        title=title,
        url=url,
        dedupe_key=url,
        published_at=datetime.now(UTC) - timedelta(days=published_days_ago),
        lane=lane,
        axes="hot,high_value",
        summary="Two sentences. Exactly two.",
        why_it_matters="Because tests.",
        apply_hook_effort="read",
        apply_hook_action="Read the docs.",
        apply_hook_tool=tool,
        section=section,
    )
