"""Jinja2 rendering of digests/reports from stored rows. Markdown is an output
artifact only - regeneratable from SQLite at any time."""

from datetime import UTC, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from signalpress.config.schema import NewsletterConfig, Section
from signalpress.judgment.schemas import WeeklyReport
from signalpress.store.models import Item

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"

SECTION_TITLES: dict[str, str] = {
    Section.TOP3: "Top 3 — what's worth your attention today",
    Section.MODELS: "New & notable models",
    Section.REPOS: "Trending repos & tools",
    Section.DX_PRACTICES: "Dev-experience & practices",
    Section.PAPERS: "Papers worth a skim",
    Section.EVALS_WATCH: "Eval-methodology watch",
    Section.SOCIAL: "From the social layer",
    Section.PATTERN_WATCH: "Pattern watch",
}


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _group_by_section(items: list[Item], config: NewsletterConfig) -> list[dict]:
    groups = []
    for section in config.sections:
        if section is Section.PATTERN_WATCH:
            continue  # rendered from run-level prose, not items
        section_items = [i for i in items if i.section == section.value]
        if section_items:
            groups.append({"title": SECTION_TITLES[section], "entries": section_items})
    return groups


def render_digest(
    *,
    config: NewsletterConfig,
    items: list[Item],
    pattern_watch: str,
    warnings_block: str,
    date: datetime | None = None,
) -> str:
    date = date or datetime.now(UTC)
    return (
        _env()
        .get_template("digest.md.j2")
        .render(
            config=config,
            date=date.strftime("%Y-%m-%d"),
            sections=_group_by_section(items, config),
            pattern_watch=pattern_watch,
            warnings_block=warnings_block,
        )
    )


def render_weekly(
    *,
    config: NewsletterConfig,
    report: WeeklyReport,
    items_by_id: dict[str, Item],
    warnings_block: str,
    date: datetime | None = None,
) -> str:
    date = date or datetime.now(UTC)
    return (
        _env()
        .get_template("weekly.md.j2")
        .render(
            config=config,
            date=date.strftime("%Y-%m-%d"),
            report=report,
            items_by_id=items_by_id,
            warnings_block=warnings_block,
        )
    )


def write_output(content: str, *, output_dir: str, filename: str) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / filename
    path.write_text(content)
    return path
