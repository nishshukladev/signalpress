"""Generic RSS/Atom fetcher (practitioner blogs: Willison, Latent Space, Hamel, ...).

Uses feedparser for robustness across feed dialects; do not hand-parse XML.
"""

import asyncio
from datetime import UTC, datetime

import feedparser
import httpx

from signalpress.config.schema import SourceConfig
from signalpress.sources.base import Candidate

_SNIPPET_CAP = 500


def _entry_to_candidate(entry) -> Candidate | None:
    link = getattr(entry, "link", None)
    title = getattr(entry, "title", None)
    if not link or not title:
        return None
    published = None
    for attr in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            published = datetime(*parsed[:6], tzinfo=UTC)
            break
    snippet = getattr(entry, "summary", "") or ""
    return Candidate(
        source="rss",
        title=title.strip(),
        url=link,
        published_at=published,
        snippet=snippet.replace("\n", " ").strip()[:_SNIPPET_CAP],
    )


async def _fetch_feed(url: str, client: httpx.AsyncClient, per_feed_limit: int) -> list[Candidate]:
    resp = await client.get(url)
    resp.raise_for_status()
    parsed = await asyncio.to_thread(feedparser.parse, resp.text)
    candidates = [c for e in parsed.entries[:per_feed_limit] if (c := _entry_to_candidate(e))]
    return candidates


async def fetch(config: SourceConfig, client: httpx.AsyncClient) -> list[Candidate]:
    if not config.feeds:
        raise ValueError("rss source requires at least one feed URL in `feeds`")
    per_feed = max(1, config.limit // len(config.feeds))
    results = await asyncio.gather(
        *[_fetch_feed(str(url), client, per_feed) for url in config.feeds]
    )
    return [c for feed in results for c in feed]
