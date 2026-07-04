"""Hugging Face daily papers via the public API.

https://huggingface.co/api/daily_papers
"""

from datetime import datetime

import httpx

from signalpress.config.schema import SourceConfig
from signalpress.sources.base import Candidate

API = "https://huggingface.co/api/daily_papers"
_SNIPPET_CAP = 500


async def fetch(config: SourceConfig, client: httpx.AsyncClient) -> list[Candidate]:
    resp = await client.get(API, params={"limit": config.limit})
    resp.raise_for_status()
    candidates: list[Candidate] = []
    for entry in resp.json():
        paper = entry.get("paper", {})
        paper_id = paper.get("id")
        if not paper_id:
            continue
        published_raw = paper.get("publishedAt") or entry.get("publishedAt")
        published = (
            datetime.fromisoformat(published_raw.replace("Z", "+00:00")) if published_raw else None
        )
        candidates.append(
            Candidate(
                source="hf_papers",
                title=paper.get("title", "").replace("\n", " ").strip(),
                url=f"https://arxiv.org/abs/{paper_id}",
                published_at=published,
                snippet=(paper.get("summary") or "").replace("\n", " ").strip()[:_SNIPPET_CAP],
                stats=f"{entry.get('numComments', 0)} HF comments, "
                f"{paper.get('upvotes', 0)} upvotes",
            )
        )
    return candidates
