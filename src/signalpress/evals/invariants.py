"""Programmatic invariant gates over a run's output.

Decision: gates FAIL VISIBLY but never block shipping - the digest renders with
a warnings block. Rationale: a newsletter that silently doesn't arrive is worse
than one that arrives flagged; the eval rows exist to be trended and fixed.
"""

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx

from signalpress.config.schema import NewsletterConfig
from signalpress.sources import FetchOutcome
from signalpress.store.models import Item


@dataclass
class CheckResult:
    check_name: str
    passed: bool
    item_id: str | None = None
    detail: str | None = None


def check_recency(items: list[Item], config: NewsletterConfig) -> list[CheckResult]:
    cutoff = datetime.now(UTC) - timedelta(days=config.rules.recency_days)
    results = []
    for item in items:
        if item.published_at is None:
            results.append(CheckResult("recency", False, item.id, "missing published_at"))
            continue
        published = item.published_at
        if published.tzinfo is None:
            published = published.replace(tzinfo=UTC)
        ok = published >= cutoff
        detail = None if ok else f"published {published.date()} > {config.rules.recency_days}d ago"
        results.append(CheckResult("recency", ok, item.id, detail))
    return results


def check_apply_hook_tool(items: list[Item], config: NewsletterConfig) -> list[CheckResult]:
    denylist = {t.lower() for t in config.rules.vague_tool_denylist}
    results = []
    for item in items:
        tool = item.apply_hook_tool.strip().lower()
        ok = bool(tool) and tool not in denylist
        detail = None if ok else f"vague/missing tool: {item.apply_hook_tool!r}"
        results.append(CheckResult("apply_hook_tool", ok, item.id, detail))
    return results


def check_lane_validity(items: list[Item], config: NewsletterConfig) -> list[CheckResult]:
    valid = {lane.id for lane in config.lanes}
    return [
        CheckResult(
            "lane_validity",
            item.lane in valid,
            item.id,
            None if item.lane in valid else f"unknown lane {item.lane!r}",
        )
        for item in items
    ]


def check_source_coverage(outcomes: list[FetchOutcome]) -> list[CheckResult]:
    return [
        CheckResult("source_coverage", o.ok, None, None if o.ok else f"{o.source}: {o.error}")
        for o in outcomes
    ]


def check_dedupe(items: list[Item], prior_keys: set[str]) -> list[CheckResult]:
    seen: set[str] = set()
    results = []
    for item in items:
        dup = item.dedupe_key in prior_keys or item.dedupe_key in seen
        seen.add(item.dedupe_key)
        results.append(
            CheckResult("dedupe", not dup, item.id, "duplicate of prior item" if dup else None)
        )
    return results


async def _resolve(url: str, client: httpx.AsyncClient) -> bool:
    try:
        resp = await client.head(url)
        if resp.status_code in (405, 403):  # some hosts reject HEAD; retry GET
            resp = await client.get(url)
        return resp.status_code < 400
    except httpx.HTTPError:
        return False


async def check_links_async(items: list[Item]) -> list[CheckResult]:
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        oks = await asyncio.gather(*[_resolve(item.url, client) for item in items])
    return [
        CheckResult("link_resolves", ok, item.id, None if ok else f"unreachable: {item.url}")
        for item, ok in zip(items, oks, strict=True)
    ]


def run_all_gates(
    *,
    items: list[Item],
    config: NewsletterConfig,
    outcomes: list[FetchOutcome],
    prior_keys: set[str],
    check_links: bool = True,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    results += check_recency(items, config)
    results += check_apply_hook_tool(items, config)
    results += check_lane_validity(items, config)
    results += check_source_coverage(outcomes)
    results += check_dedupe(items, prior_keys)
    if check_links:
        results += asyncio.run(check_links_async(items))
    return results
