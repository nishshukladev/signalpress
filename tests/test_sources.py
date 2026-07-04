"""Fetcher tests against respx-mocked HTTP - no live network in CI."""

import httpx
import pytest
import respx

from signalpress.config.schema import SourceConfig, SourceType
from signalpress.sources import fetch_all
from signalpress.sources.base import normalize_url
from signalpress.sources.hn import fetch as hn_fetch

HN_FIXTURE = {
    "hits": [
        {
            "objectID": "1",
            "title": "Show HN: Foo",
            "url": "https://foo.dev/launch?utm_source=hn",
            "points": 412,
            "num_comments": 208,
            "created_at_i": 1900000000,
        },
        {
            "objectID": "2",
            "title": "Ask HN: Bar",
            "url": None,
            "points": 10,
            "num_comments": 3,
            "created_at_i": 1900000100,
        },
    ]
}


def test_normalize_url_strips_tracking_and_case() -> None:
    assert (
        normalize_url("HTTPS://Foo.dev/Launch/?utm_source=hn&x=1#frag")
        == "https://foo.dev/Launch?x=1"
    )
    # idempotent
    key = normalize_url("https://foo.dev/a")
    assert normalize_url(key) == key


@respx.mock
async def test_hn_fetch_parses_hits() -> None:
    respx.get("https://hn.algolia.com/api/v1/search").mock(
        return_value=httpx.Response(200, json=HN_FIXTURE)
    )
    async with httpx.AsyncClient() as client:
        candidates = await hn_fetch(SourceConfig(type=SourceType.HN, limit=5), client)
    assert len(candidates) == 2
    assert candidates[0].title == "Show HN: Foo"
    assert "412 points" in candidates[0].stats
    assert candidates[1].url == "https://news.ycombinator.com/item?id=2"  # Ask HN fallback
    assert candidates[0].published_at is not None


@respx.mock
async def test_fetch_all_isolates_source_failure() -> None:
    respx.get("https://hn.algolia.com/api/v1/search").mock(
        return_value=httpx.Response(200, json=HN_FIXTURE)
    )
    respx.get("https://export.arxiv.org/api/query").mock(return_value=httpx.Response(500))
    outcomes = await fetch_all(
        [
            SourceConfig(type=SourceType.HN, limit=5),
            SourceConfig(type=SourceType.ARXIV, limit=5),
        ]
    )
    by_source = {o.source: o for o in outcomes}
    assert by_source["hn"].ok and len(by_source["hn"].candidates) == 2
    assert not by_source["arxiv"].ok
    assert "HTTPStatusError" in (by_source["arxiv"].error or "")


REDDIT_ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>top scoring links : x</title>
  <entry>
    <title>Real post</title>
    <link href="https://www.reddit.com/r/x/comments/2/real_post/"/>
    <updated>2030-03-17T12:00:00+00:00</updated>
    <content type="html">&lt;p&gt;body text &lt;a href="https://ext.example"&gt;link&lt;/a&gt;&lt;/p&gt;</content>
  </entry>
</feed>"""


@respx.mock
async def test_reddit_fetch_parses_atom() -> None:
    respx.get(url__regex=r"https://www\.reddit\.com/r/.*/top\.rss.*").mock(
        return_value=httpx.Response(200, text=REDDIT_ATOM)
    )
    outcomes = await fetch_all([SourceConfig(type=SourceType.REDDIT, limit=10, subreddits=["x"])])
    (outcome,) = outcomes
    assert outcome.ok
    (candidate,) = outcome.candidates
    assert candidate.title == "Real post"
    assert candidate.url == "https://www.reddit.com/r/x/comments/2/real_post/"
    assert candidate.snippet == "body text link"
    assert candidate.published_at is not None


async def test_scrape_local_mode_rejected_in_v1() -> None:
    from signalpress.config.schema import SourceMode

    outcomes = await fetch_all([SourceConfig(type=SourceType.HN, mode=SourceMode.SCRAPE_LOCAL)])
    (outcome,) = outcomes
    assert not outcome.ok
    assert "not supported in v1" in (outcome.error or "")


@pytest.mark.anyio
async def test_rss_requires_feeds() -> None:
    outcomes = await fetch_all([SourceConfig(type=SourceType.RSS, feeds=[])])
    (outcome,) = outcomes
    assert not outcome.ok
    assert "requires at least one feed" in (outcome.error or "")
