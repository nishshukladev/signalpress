from signalpress.config.schema import NewsletterConfig
from signalpress.evals import invariants, report
from signalpress.sources import FetchOutcome
from signalpress.store import repo
from tests.conftest import make_item


def _run(session, config: NewsletterConfig):
    return repo.create_run(session, kind="daily", config_hash="abc123def456")


def test_recency_gate_fails_old_item(session, config) -> None:
    run = _run(session, config)
    fresh = make_item(run_id=run.id, published_days_ago=2)
    stale = make_item(run_id=run.id, url="https://example.com/old", published_days_ago=45)
    results = invariants.check_recency([fresh, stale], config)
    assert [r.passed for r in results] == [True, False]
    assert "45" not in (results[0].detail or "")


def test_recency_gate_fails_missing_date(session, config) -> None:
    run = _run(session, config)
    item = make_item(run_id=run.id)
    item.published_at = None
    (result,) = invariants.check_recency([item], config)
    assert not result.passed
    assert result.detail == "missing published_at"


def test_vague_tool_gate(session, config) -> None:
    run = _run(session, config)
    good = make_item(run_id=run.id, tool="Inspect AI")
    bad = make_item(run_id=run.id, url="https://example.com/2", tool="a tool")
    empty = make_item(run_id=run.id, url="https://example.com/3", tool="  ")
    results = invariants.check_apply_hook_tool([good, bad, empty], config)
    assert [r.passed for r in results] == [True, False, False]


def test_lane_validity_gate(session, config) -> None:
    run = _run(session, config)
    good = make_item(run_id=run.id, lane="agents-evals")
    bad = make_item(run_id=run.id, url="https://example.com/2", lane="made-up-lane")
    results = invariants.check_lane_validity([good, bad], config)
    assert [r.passed for r in results] == [True, False]


def test_source_coverage_gate() -> None:
    outcomes = [
        FetchOutcome(source="hn", ok=True, candidates=[]),
        FetchOutcome(source="arxiv", ok=False, candidates=[], error="HTTPError: boom"),
    ]
    results = invariants.check_source_coverage(outcomes)
    assert [r.passed for r in results] == [True, False]
    assert "arxiv" in (results[1].detail or "")


def test_dedupe_gate_catches_prior_and_intra_run(session, config) -> None:
    run = _run(session, config)
    a = make_item(run_id=run.id, url="https://example.com/a")
    b = make_item(run_id=run.id, url="https://example.com/a")  # intra-run dup
    c = make_item(run_id=run.id, url="https://example.com/seen-before")
    results = invariants.check_dedupe([a, b, c], prior_keys={"https://example.com/seen-before"})
    assert [r.passed for r in results] == [True, False, False]


def test_warnings_block_and_status(session, config) -> None:
    run = _run(session, config)
    stale = make_item(run_id=run.id, published_days_ago=45)
    results = invariants.check_recency([stale], config)
    block = report.warnings_block(results)
    assert "recency" in block and block.startswith("> ⚠️")
    assert report.run_status(results) == "gated"
    assert report.run_status([]) == "ok"
