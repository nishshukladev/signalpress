"""signalpress CLI: init | daily | weekly | trend."""

import logging
from datetime import UTC, datetime
from pathlib import Path

import typer

from signalpress.config.loader import load_config

app = typer.Typer(help="Config-driven newsletter agent with output evals.")

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

CONFIG_OPT = typer.Option("newsletter.yaml", "--config", "-c", help="Path to newsletter.yaml")


@app.command()
def init(path: str = "newsletter.yaml") -> None:
    """Write a starter newsletter.yaml (from the packaged example) and create the DB."""
    example = Path(__file__).resolve().parent / "templates" / "newsletter.example.yaml"
    target = Path(path)
    if target.exists():
        typer.echo(f"{target} already exists; not overwriting.")
        raise typer.Exit(1)
    target.write_text(example.read_text())
    config = load_config(target)
    from signalpress.store.db import make_engine

    make_engine(config.db_path)
    typer.echo(f"Wrote {target} and created {config.db_path}. Edit the config, then run:")
    typer.echo("  signalpress daily")


@app.command()
def daily(
    config_path: str = CONFIG_OPT,
    check_links: bool = typer.Option(True, help="Run the link-resolution gate (network)."),
    judge: bool = typer.Option(True, help="Run lens-adherence judge telemetry (LLM calls)."),
) -> None:
    """Run the daily pipeline: fetch -> judge -> store -> gates -> render digest."""
    from signalpress.render.renderer import render_digest, write_output
    from signalpress.runs.daily import run_daily
    from signalpress.store.db import make_engine, session_scope

    config = load_config(config_path)
    engine = make_engine(config.db_path)
    with session_scope(engine) as session:
        run, items, pattern_watch, warnings = run_daily(
            session, config, check_links=check_links, with_judge=judge
        )
        content = render_digest(
            config=config, items=items, pattern_watch=pattern_watch, warnings_block=warnings
        )
        filename = f"digest-{datetime.now(UTC):%Y-%m-%d}.md"
        path = write_output(content, output_dir=config.output_dir, filename=filename)
        run.output_path = str(path)
    typer.echo(f"[{run.status}] {len(items)} items -> {path}")
    if warnings:
        typer.echo(warnings)


@app.command()
def weekly(config_path: str = CONFIG_OPT) -> None:
    """Run the weekly synthesis: week's items + tracker -> pattern report + build-of-week."""
    from signalpress.render.renderer import render_weekly, write_output
    from signalpress.runs.weekly import run_weekly
    from signalpress.store.db import make_engine, session_scope

    config = load_config(config_path)
    engine = make_engine(config.db_path)
    with session_scope(engine) as session:
        run, report, items_by_id, warnings = run_weekly(session, config)
        content = render_weekly(
            config=config, report=report, items_by_id=items_by_id, warnings_block=warnings
        )
        filename = f"weekly-{datetime.now(UTC):%Y-%m-%d}.md"
        path = write_output(content, output_dir=config.output_dir, filename=filename)
        run.output_path = str(path)
    typer.echo(f"[{run.status}] build-of-week: {report.build_of_week.title} -> {path}")


@app.command()
def trend(config_path: str = CONFIG_OPT) -> None:
    """Show judge-score and gate-failure trends across runs (the eval telemetry)."""
    from sqlalchemy import func, select

    from signalpress.store.db import make_engine, session_scope
    from signalpress.store.models import EvalResult, JudgeScore, Run

    config = load_config(config_path)
    engine = make_engine(config.db_path)
    with session_scope(engine) as session:
        rows = session.execute(
            select(
                Run.started_at,
                Run.kind,
                Run.status,
                func.avg(JudgeScore.score),
                func.count(JudgeScore.id),
            )
            .outerjoin(JudgeScore, JudgeScore.run_id == Run.id)
            .group_by(Run.id)
            .order_by(Run.started_at)
        ).all()
        typer.echo("date        kind    status  avg_judge  n_scored  gate_failures")
        for started, kind, status, avg_score, n_scored in rows:
            failures = session.scalar(
                select(func.count(EvalResult.id)).where(
                    EvalResult.passed.is_(False),
                    EvalResult.run_id.in_(select(Run.id).where(Run.started_at == started)),
                )
            )
            avg_repr = f"{avg_score:.2f}" if avg_score else "-"
            typer.echo(
                f"{started:%Y-%m-%d}  {kind:<7}{status:<8}{avg_repr:<11}{n_scored:<10}{failures}"
            )


if __name__ == "__main__":
    app()
