"""Editorial policy schema: the newsletter.yaml contract.

This is the product surface. Every field here either (a) compiles into the
judgment/synthesis prompts, or (b) is enforced as a programmatic invariant.
"""

from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl


class SourceMode(StrEnum):
    API = "api"  # deterministic fetcher against a public API/feed
    SCRAPE_LOCAL = "scrape-local"  # local-only browser scrape (reserved; not in v1)
    SEARCH_FALLBACK = "search-fallback"  # web-search proxy (reserved; not in v1)


class SourceType(StrEnum):
    HN = "hn"
    ARXIV = "arxiv"
    HF_PAPERS = "hf_papers"
    RSS = "rss"
    BLUESKY = "bluesky"
    REDDIT = "reddit"


class SourceConfig(BaseModel):
    type: SourceType
    mode: SourceMode = SourceMode.API
    enabled: bool = True
    limit: int = Field(default=25, ge=1, le=100)
    # type-specific knobs (validated by each fetcher, not here, to keep schema stable)
    categories: list[str] = Field(default_factory=list)  # arxiv
    feeds: list[HttpUrl] = Field(default_factory=list)  # rss
    subreddits: list[str] = Field(default_factory=list)  # reddit
    feed_uris: list[str] = Field(default_factory=list)  # bluesky at:// feed URIs
    time_window: str = "week"  # reddit top window


class Lane(BaseModel):
    id: str
    label: str
    weight: float = Field(default=1.0, ge=0.0, le=2.0, description="ranking weight; core lanes > 1")


class Lens(BaseModel):
    """The distillation lens: every kept item must clear at least one axis."""

    hot: str = "Real cross-source momentum in the last ~30 days (more than one loud post)."
    deep: str = "Still matters in 12 months; worth genuine study."
    high_value: str = (
        "Moves the reader toward their stated goal "
        "(depth in a lane, a publishable artifact, a scarce skill)."
    )


class ApplyHookEffort(StrEnum):
    READ = "read"
    MICRO_EXP = "micro-exp"
    WEEKEND_BUILD = "weekend-build"


class Rules(BaseModel):
    recency_days: int = Field(default=30, ge=1, le=90)
    prior_art_required: bool = True
    max_items_daily: int = Field(default=12, ge=3, le=30)
    max_themes_weekly: int = Field(default=6, ge=1, le=10)
    vague_tool_denylist: list[str] = Field(
        default_factory=lambda: ["", "n/a", "unknown", "a tool", "some tool", "custom script"]
    )


class ModelsConfig(BaseModel):
    """Pydantic AI model strings, e.g. 'anthropic:claude-sonnet-4-5' or 'openai:gpt-5.2'."""

    judgment: str = "anthropic:claude-sonnet-4-5"
    judge: str = "anthropic:claude-haiku-4-5"
    synthesis: str = "anthropic:claude-sonnet-4-5"


class Section(StrEnum):
    TOP3 = "top3"
    MODELS = "models"
    REPOS = "repos"
    DX_PRACTICES = "dx_practices"
    PAPERS = "papers"
    EVALS_WATCH = "evals_watch"
    SOCIAL = "social"
    PATTERN_WATCH = "pattern_watch"


class NewsletterConfig(BaseModel):
    name: str
    persona: str = Field(description="Who the reader is and what they are optimizing for.")
    lanes: list[Lane]
    lens: Lens = Field(default_factory=Lens)
    rules: Rules = Field(default_factory=Rules)
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    sources: list[SourceConfig]
    sections: list[Section] = Field(default_factory=lambda: list(Section))
    extra_instructions: str = ""
    output_dir: str = "digests"
    db_path: str = "signalpress.db"

    def enabled_sources(self) -> list[SourceConfig]:
        return [s for s in self.sources if s.enabled]
