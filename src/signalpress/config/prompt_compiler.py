"""Compile the editorial policy (NewsletterConfig) into LLM instructions.

Decision: prompts are *compiled from schema*, never hand-edited. The schema is
the source of truth; `extra_instructions` is the only free-text escape hatch.
"""

from signalpress.config.schema import NewsletterConfig


def _lens_block(config: NewsletterConfig) -> str:
    lens = config.lens
    return (
        "THE DISTILLATION LENS - every kept item must clear at least one axis; "
        "the best clear 2-3:\n"
        f"- HOT: {lens.hot}\n"
        f"- DEEP: {lens.deep}\n"
        f"- HIGH-VALUE: {lens.high_value}"
    )


def _lanes_block(config: NewsletterConfig) -> str:
    lines = [f"- {lane.id}: {lane.label} (weight {lane.weight})" for lane in config.lanes]
    return "LANES (higher weight = deeper priority):\n" + "\n".join(lines)


def _rules_block(config: NewsletterConfig) -> str:
    r = config.rules
    rules = [
        f"RECENCY (hard): only items published within the last {r.recency_days} days.",
        f"Keep at most {r.max_items_daily} items; fewer sharp items beat many weak ones.",
        "Every apply hook must name a concrete, existing tool/repo/paper to use or extend.",
    ]
    if r.prior_art_required:
        rules.append(
            "PRIOR-ART RULE (hard): before suggesting building anything, name the "
            "off-the-shelf option; prefer use/extend/reproduce over build-from-scratch."
        )
    return "\n".join(rules)


def compile_judgment_prompt(config: NewsletterConfig) -> str:
    """Instructions for the daily keep/drop + tag + apply-hook stage."""
    parts = [
        f"You are the editor of '{config.name}'.",
        f"READER: {config.persona.strip()}",
        _lanes_block(config),
        _lens_block(config),
        _rules_block(config),
        "You will receive candidate items fetched from configured sources. For each, "
        "decide keep/drop, assign exactly one lane, tag the axes it clears, write a "
        "2-sentence summary + one-line why-it-matters for the reader, and produce an "
        "apply hook (effort: read | micro-exp | weekend-build) naming the tool to use.",
        "Ruthlessly filter noise: politics, drama, memes, funding fluff, generic "
        "listicles, leaderboard one-upmanship between comparable models, and anything "
        "that only touches a keyword.",
    ]
    if config.extra_instructions.strip():
        parts.append(f"ADDITIONAL EDITOR INSTRUCTIONS:\n{config.extra_instructions.strip()}")
    return "\n\n".join(parts)


def compile_judge_prompt(config: NewsletterConfig) -> str:
    """Instructions for the lens-adherence telemetry judge (scores, never gates)."""
    return "\n\n".join(
        [
            f"You are a strict quality auditor for the newsletter '{config.name}'.",
            f"READER: {config.persona.strip()}",
            _lens_block(config),
            "Score how well a single kept item adheres to the lens for this reader, "
            "1-5 (5 = clearly clears 2+ axes with evidence; 1 = keyword-adjacent noise). "
            "Give a one-line rationale. Judge the item on its merits; do not reward "
            "confident phrasing.",
        ]
    )


def compile_synthesis_prompt(config: NewsletterConfig) -> str:
    """Instructions for the weekly cross-run synthesis stage."""
    r = config.rules
    return "\n\n".join(
        [
            f"You are writing the weekly pattern report for '{config.name}'.",
            f"READER: {config.persona.strip()}",
            _lanes_block(config),
            _lens_block(config),
            f"You will receive the week's kept items (structured) and the reader's "
            f"artifact tracker. Cluster into at most {r.max_themes_weekly} themes. "
            "KEY QUESTION: what showed up more than once, across more than one source? "
            "Rank themes by durability (12-month relevance) and leverage for the reader.",
            "Propose ONE build-of-the-week: weekend-sized, shippable, tied to the top "
            "theme. It MUST name the existing framework/harness/dataset it builds on "
            "(use/extend, never reinvent) and state what prior art was checked. "
            "NEVER propose anything already present in the tracker.",
            _rules_block(config),
        ]
    )
