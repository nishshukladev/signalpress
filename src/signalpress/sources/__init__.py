"""Source registry + concurrent fetch orchestration with per-source error capture."""

import asyncio
from dataclasses import dataclass

import httpx

from signalpress.config.schema import SourceConfig, SourceMode, SourceType
from signalpress.sources import arxiv, bluesky, hf_papers, hn, json_api, reddit, rss
from signalpress.sources.base import DEFAULT_HEADERS, Candidate, Fetcher

REGISTRY: dict[SourceType, Fetcher] = {
    SourceType.HN: hn.fetch,
    SourceType.ARXIV: arxiv.fetch,
    SourceType.HF_PAPERS: hf_papers.fetch,
    SourceType.RSS: rss.fetch,
    SourceType.BLUESKY: bluesky.fetch,
    SourceType.REDDIT: reddit.fetch,
    SourceType.JSON_API: json_api.fetch,
}


@dataclass
class FetchOutcome:
    source: str
    ok: bool
    candidates: list[Candidate]
    error: str | None = None


async def _run_one(config: SourceConfig, client: httpx.AsyncClient) -> FetchOutcome:
    name = config.name or config.type.value
    if config.mode is not SourceMode.API:
        return FetchOutcome(
            source=name, ok=False, candidates=[], error=f"mode {config.mode} not supported in v1"
        )
    try:
        candidates = await REGISTRY[config.type](config, client)
        return FetchOutcome(source=name, ok=True, candidates=candidates)
    except Exception as exc:  # noqa: BLE001 - one bad source must not kill the run
        return FetchOutcome(
            source=name, ok=False, candidates=[], error=f"{type(exc).__name__}: {exc}"
        )


async def fetch_all(sources: list[SourceConfig]) -> list[FetchOutcome]:
    async with httpx.AsyncClient(
        headers=DEFAULT_HEADERS, timeout=30, follow_redirects=True
    ) as client:
        return list(await asyncio.gather(*[_run_one(s, client) for s in sources]))


def fetch_all_sync(sources: list[SourceConfig]) -> list[FetchOutcome]:
    return asyncio.run(fetch_all(sources))
