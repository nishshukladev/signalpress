"""Hacker News front page via the Algolia API (no key needed).

https://hn.algolia.com/api/v1/search?tags=front_page
"""

from datetime import UTC, datetime

import httpx

from signalpress.config.schema import SourceConfig
from signalpress.sources.base import Candidate

API = "https://hn.algolia.com/api/v1/search"


async def fetch(config: SourceConfig, client: httpx.AsyncClient) -> list[Candidate]:
    resp = await client.get(API, params={"tags": "front_page", "hitsPerPage": config.limit})
    resp.raise_for_status()
    candidates: list[Candidate] = []
    for hit in resp.json().get("hits", []):
        title = hit.get("title") or ""
        story_id = hit.get("objectID")
        url = hit.get("url") or f"https://news.ycombinator.com/item?id={story_id}"
        created = hit.get("created_at_i")
        candidates.append(
            Candidate(
                source="hn",
                title=title,
                url=url,
                published_at=datetime.fromtimestamp(created, tz=UTC) if created else None,
                stats=f"{hit.get('points', 0)} points, {hit.get('num_comments', 0)} comments "
                f"(https://news.ycombinator.com/item?id={story_id})",
            )
        )
    return candidates
