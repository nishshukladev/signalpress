"""Generic JSON API fetcher: any public JSON endpoint becomes a source via
config alone - url, a dot-path to the item list, and a field map. No code.

Example (lobste.rs):
  - type: json_api
    url: https://lobste.rs/hottest.json
    items_path: ""            # "" = the response root is the list
    field_map:
      title: title
      url: url
      published_at: created_at
      snippet: description_plain
"""

from datetime import UTC, datetime
from typing import Any

import httpx

from signalpress.config.schema import SourceConfig
from signalpress.sources.base import Candidate

_SNIPPET_CAP = 500


def resolve_path(data: Any, path: str) -> Any:
    """Resolve a dot-path like 'data.children' or 'paper.title'. '' = identity."""
    if not path:
        return data
    current = data
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            index = int(part)
            current = current[index] if index < len(current) else None
        else:
            return None
        if current is None:
            return None
    return current


def parse_date(value: Any) -> datetime | None:
    """Auto-detect epoch seconds/millis or ISO 8601 strings."""
    if value is None:
        return None
    if isinstance(value, int | float):
        seconds = value / 1000 if value > 1e11 else value  # millis vs seconds
        return datetime.fromtimestamp(seconds, tz=UTC)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


async def fetch(config: SourceConfig, client: httpx.AsyncClient) -> list[Candidate]:
    if not config.url:
        raise ValueError("json_api source requires `url`")
    if "title" not in config.field_map or "url" not in config.field_map:
        raise ValueError("json_api source requires field_map with at least `title` and `url`")

    resp = await client.get(config.url)
    resp.raise_for_status()
    items = resolve_path(resp.json(), config.items_path)
    if not isinstance(items, list):
        raise ValueError(
            f"items_path {config.items_path!r} did not resolve to a list "
            f"(got {type(items).__name__})"
        )

    fm = config.field_map
    candidates: list[Candidate] = []
    for item in items[: config.limit]:
        title = resolve_path(item, fm["title"])
        url = resolve_path(item, fm["url"])
        if not title or not url:
            continue  # unmappable row; skip rather than fail the source
        snippet = resolve_path(item, fm["snippet"]) if "snippet" in fm else ""
        candidates.append(
            Candidate(
                source=config.name or "json_api",
                title=str(title).strip(),
                url=str(url),
                published_at=parse_date(resolve_path(item, fm.get("published_at", ""))),
                snippet=str(snippet or "")[:_SNIPPET_CAP],
            )
        )
    return candidates
