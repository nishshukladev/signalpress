"""arXiv recent submissions via the export API (Atom XML, parsed with feedparser).

http://export.arxiv.org/api/query
"""

from datetime import UTC, datetime

import feedparser
import httpx

from signalpress.config.schema import SourceConfig
from signalpress.sources.base import Candidate

API = "https://export.arxiv.org/api/query"
_SNIPPET_CAP = 500


async def fetch(config: SourceConfig, client: httpx.AsyncClient) -> list[Candidate]:
    categories = config.categories or ["cs.LG", "cs.CL"]
    query = " OR ".join(f"cat:{c}" for c in categories)
    resp = await client.get(
        API,
        params={
            "search_query": query,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": config.limit,
        },
    )
    resp.raise_for_status()
    parsed = feedparser.parse(resp.text)
    candidates: list[Candidate] = []
    for entry in parsed.entries:
        published = None
        if getattr(entry, "published_parsed", None):
            published = datetime(*entry.published_parsed[:6], tzinfo=UTC)
        candidates.append(
            Candidate(
                source="arxiv",
                title=entry.title.replace("\n", " ").strip(),
                url=entry.link,
                published_at=published,
                snippet=entry.summary.replace("\n", " ").strip()[:_SNIPPET_CAP],
            )
        )
    return candidates
