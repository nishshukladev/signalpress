"""Reddit top-of-week via the public Atom feeds.

Decisions:
- Reddit blocks the JSON endpoints (403) for non-browser clients since the 2023
  API changes; the RSS/Atom endpoints remain open. Trade-off: we lose
  score/comment counts but keep titles, permalinks, and dates without OAuth.
- Unauthenticated RSS is rate-limited to roughly one request/minute per IP, so
  we fetch ALL subreddits in a single multireddit request (r/A+B/top.rss)
  instead of one request per sub. One retry on 429 after a pause.
"""

import asyncio
import re
from datetime import UTC, datetime

import feedparser
import httpx

from signalpress.config.schema import SourceConfig
from signalpress.sources.base import Candidate

_SNIPPET_CAP = 500
_TAG_RE = re.compile(r"<[^>]+>")


def _entry_subreddit(entry) -> str:
    for tag in getattr(entry, "tags", []) or []:
        if getattr(tag, "label", None):
            return tag.label
        if getattr(tag, "term", None):
            return tag.term
    return "reddit"


async def fetch(config: SourceConfig, client: httpx.AsyncClient) -> list[Candidate]:
    subs = config.subreddits or ["LocalLLaMA", "MachineLearning"]
    multi = "+".join(subs)
    url = f"https://www.reddit.com/r/{multi}/top.rss"
    params = {"t": config.time_window, "limit": config.limit}

    resp = await client.get(url, params=params)
    if resp.status_code == 429:  # per-IP throttle; one respectful retry
        await asyncio.sleep(15)
        resp = await client.get(url, params=params)
    resp.raise_for_status()

    parsed = await asyncio.to_thread(feedparser.parse, resp.text)
    candidates: list[Candidate] = []
    for entry in parsed.entries[: config.limit]:
        published = None
        if getattr(entry, "updated_parsed", None):
            published = datetime(*entry.updated_parsed[:6], tzinfo=UTC)
        raw = entry.content[0].value if getattr(entry, "content", None) else ""
        snippet = " ".join(_TAG_RE.sub(" ", raw).split())[:_SNIPPET_CAP]
        candidates.append(
            Candidate(
                source="reddit",
                title=entry.title.strip(),
                url=entry.link,
                published_at=published,
                snippet=snippet,
                stats=f"{_entry_subreddit(entry)} top/{config.time_window}",
            )
        )
    return candidates
