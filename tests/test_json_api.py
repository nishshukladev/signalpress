"""The config-only source type: any JSON endpoint, zero code."""

import httpx
import pytest
import respx

from signalpress.config.schema import SourceConfig, SourceType
from signalpress.sources import fetch_all
from signalpress.sources.json_api import parse_date, resolve_path

LOBSTERS = [
    {
        "title": "A fine post",
        "url": "https://example.com/post",
        "created_at": "2030-03-17T12:00:00.000-05:00",
        "description_plain": "body",
    },
    {"title": "", "url": "https://example.com/skip"},  # unmappable -> skipped
]

NESTED = {
    "data": {
        "children": [{"post": {"t": "Nested", "u": "https://example.com/n", "ts": 1900000000}}]
    }
}


def _config(**overrides) -> SourceConfig:
    base = dict(
        type=SourceType.JSON_API,
        url="https://api.example.com/items.json",
        items_path="",
        field_map={
            "title": "title",
            "url": "url",
            "published_at": "created_at",
            "snippet": "description_plain",
        },
    )
    base.update(overrides)
    return SourceConfig(**base)


def test_resolve_path() -> None:
    assert resolve_path({"a": {"b": [{"c": 1}]}}, "a.b.0.c") == 1
    assert resolve_path({"a": 1}, "") == {"a": 1}
    assert resolve_path({"a": 1}, "missing.deep") is None


def test_parse_date_variants() -> None:
    assert parse_date(1900000000).year == 2030
    assert parse_date(1900000000000).year == 2030  # millis
    assert parse_date("2030-03-17T12:00:00Z") is not None
    assert parse_date("not a date") is None
    assert parse_date(None) is None


@respx.mock
async def test_root_list_endpoint() -> None:
    respx.get("https://api.example.com/items.json").mock(
        return_value=httpx.Response(200, json=LOBSTERS)
    )
    (outcome,) = await fetch_all([_config(name="lobsters")])
    assert outcome.ok and outcome.source == "lobsters"
    (candidate,) = outcome.candidates  # empty-title row skipped
    assert candidate.title == "A fine post"
    assert candidate.snippet == "body"
    assert candidate.published_at is not None


@respx.mock
async def test_nested_items_path() -> None:
    respx.get("https://api.example.com/items.json").mock(
        return_value=httpx.Response(200, json=NESTED)
    )
    (outcome,) = await fetch_all(
        [
            _config(
                items_path="data.children",
                field_map={"title": "post.t", "url": "post.u", "published_at": "post.ts"},
            )
        ]
    )
    assert outcome.ok
    assert outcome.candidates[0].title == "Nested"
    assert outcome.candidates[0].published_at.year == 2030


async def test_missing_required_mapping_fails_cleanly() -> None:
    (outcome,) = await fetch_all([_config(field_map={"title": "title"})])
    assert not outcome.ok
    assert "field_map" in (outcome.error or "")


@respx.mock
async def test_items_path_not_a_list_fails_cleanly() -> None:
    respx.get("https://api.example.com/items.json").mock(
        return_value=httpx.Response(200, json={"data": {"x": 1}})
    )
    (outcome,) = await fetch_all([_config(items_path="data")])
    assert not outcome.ok
    assert "did not resolve to a list" in (outcome.error or "")


@pytest.mark.anyio
async def test_config_requires_url() -> None:
    (outcome,) = await fetch_all([_config(url="")])
    assert not outcome.ok
    assert "requires `url`" in (outcome.error or "")
