"""Bluesky feed generators via the public AppView (unauthenticated).

https://public.api.bsky.app/xrpc/app.bsky.feed.getFeed?feed=<at-uri>
Configure feed_uris with at:// URIs of feed generators (e.g. curated AI feeds).
"""

import asyncio
from datetime import datetime

import httpx

from signalpress.config.schema import SourceConfig
from signalpress.sources.base import Candidate

API = "https://public.api.bsky.app/xrpc/app.bsky.feed.getFeed"
_SNIPPET_CAP = 500


def _post_to_candidate(feed_item: dict) -> Candidate | None:
    post = feed_item.get("post", {})
    record = post.get("record", {})
    text = (record.get("text") or "").strip()
    if not text:
        return None
    uri = post.get("uri", "")  # at://did/app.bsky.feed.post/rkey
    handle = post.get("author", {}).get("handle", "unknown")
    rkey = uri.rsplit("/", 1)[-1] if uri else ""
    web_url = f"https://bsky.app/profile/{handle}/post/{rkey}"
    created = record.get("createdAt")
    likes = post.get("likeCount", 0)
    reposts = post.get("repostCount", 0)
    # Prefer an outbound link if the post embeds one; the post itself is context.
    external = post.get("embed", {}).get("external", {})
    url = external.get("uri") or web_url
    title = external.get("title") or text[:120]
    return Candidate(
        source="bluesky",
        title=title,
        url=url,
        published_at=datetime.fromisoformat(created.replace("Z", "+00:00")) if created else None,
        snippet=text[:_SNIPPET_CAP],
        stats=f"@{handle}: {likes} likes, {reposts} reposts ({web_url})",
    )


async def _fetch_feed(uri: str, limit: int, client: httpx.AsyncClient) -> list[Candidate]:
    resp = await client.get(API, params={"feed": uri, "limit": limit})
    resp.raise_for_status()
    feed = resp.json().get("feed", [])
    return [c for item in feed if (c := _post_to_candidate(item))]


async def fetch(config: SourceConfig, client: httpx.AsyncClient) -> list[Candidate]:
    if not config.feed_uris:
        raise ValueError("bluesky source requires at least one at:// feed URI in `feed_uris`")
    per_feed = max(1, config.limit // len(config.feed_uris))
    results = await asyncio.gather(
        *[_fetch_feed(uri, per_feed, client) for uri in config.feed_uris]
    )
    return [c for feed in results for c in feed]
