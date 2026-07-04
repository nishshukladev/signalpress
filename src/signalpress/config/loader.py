"""Load and validate newsletter.yaml into a NewsletterConfig."""

from pathlib import Path

import yaml

from signalpress.config.schema import NewsletterConfig


def load_config(path: str | Path) -> NewsletterConfig:
    raw = yaml.safe_load(Path(path).read_text())
    return NewsletterConfig.model_validate(raw)


def config_hash(config: NewsletterConfig) -> str:
    """Stable hash of the config, recorded per run for reproducibility."""
    import hashlib

    return hashlib.sha256(config.model_dump_json().encode()).hexdigest()[:12]
