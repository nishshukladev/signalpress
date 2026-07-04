from pathlib import Path

import pytest
from pydantic import ValidationError

from signalpress.config.loader import config_hash, load_config
from signalpress.config.schema import NewsletterConfig

EXAMPLE = Path(__file__).resolve().parents[1] / "src/signalpress/templates/newsletter.example.yaml"


def test_example_config_is_valid() -> None:
    config = load_config(EXAMPLE)
    assert config.name == "AI Engineering Signal"
    assert len(config.lanes) == 4
    assert {s.type.value for s in config.enabled_sources()} == {
        "hn",
        "arxiv",
        "hf_papers",
        "rss",
        "reddit",
    }


def test_disabled_source_excluded() -> None:
    config = load_config(EXAMPLE)
    all_types = {s.type.value for s in config.sources}
    assert "bluesky" in all_types  # present but disabled


def test_config_hash_is_stable(config: NewsletterConfig) -> None:
    assert config_hash(config) == config_hash(config)
    assert len(config_hash(config)) == 12


def test_invalid_recency_rejected() -> None:
    raw = load_config(EXAMPLE).model_dump()
    raw["rules"]["recency_days"] = 0
    with pytest.raises(ValidationError):
        NewsletterConfig.model_validate(raw)
