"""Source fetcher contract.

Decision: fetchers are deterministic code (API/RSS), never agentic browsing.
Each fetcher returns Candidates; the LLM never fetches. Beats are guaranteed by
code, not by prompt pleading.
"""

from collections.abc import Awaitable, Callable
from datetime import datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from pydantic import BaseModel

from signalpress.config.schema import SourceConfig

_TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "ref"}


class Candidate(BaseModel):
    """A raw fetched item, pre-judgment."""

    source: str
    title: str
    url: str
    published_at: datetime | None = None
    snippet: str = ""  # abstract/selftext/first paragraph; capped by fetchers
    stats: str = ""  # e.g. "412 points, 208 comments" - signal for the judge


def normalize_url(url: str) -> str:
    """Dedupe key: lowercase host, strip tracking params + fragment + trailing slash."""
    scheme, netloc, path, query, _ = urlsplit(url.strip())
    kept = [(k, v) for k, v in parse_qsl(query) if k.lower() not in _TRACKING_PARAMS]
    path = path.rstrip("/") or "/"
    return urlunsplit((scheme.lower(), netloc.lower(), path, urlencode(kept), ""))


# A fetcher takes its SourceConfig and a shared AsyncClient, returns candidates.
Fetcher = Callable[[SourceConfig, httpx.AsyncClient], Awaitable[list[Candidate]]]

DEFAULT_HEADERS = {"User-Agent": "signalpress/0.1 (+https://github.com/nishshukladev/signalpress)"}
