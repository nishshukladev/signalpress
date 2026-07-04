from signalpress.config.prompt_compiler import (
    compile_judge_prompt,
    compile_judgment_prompt,
    compile_synthesis_prompt,
)
from signalpress.config.schema import NewsletterConfig


def test_judgment_prompt_contains_policy(config: NewsletterConfig) -> None:
    prompt = compile_judgment_prompt(config)
    assert "Test Signal" in prompt
    assert "agents-evals" in prompt
    assert "last 30 days" in prompt
    assert "PRIOR-ART RULE" in prompt
    assert "at most 12 items" in prompt


def test_extra_instructions_escape_hatch(config: NewsletterConfig) -> None:
    config = config.model_copy(update={"extra_instructions": "Never mention crypto."})
    assert "Never mention crypto." in compile_judgment_prompt(config)


def test_prior_art_rule_toggle(config: NewsletterConfig) -> None:
    config.rules.prior_art_required = False
    assert "PRIOR-ART RULE" not in compile_judgment_prompt(config)


def test_judge_prompt_scores_not_gates(config: NewsletterConfig) -> None:
    prompt = compile_judge_prompt(config)
    assert "1-5" in prompt
    assert "HOT" in prompt and "DEEP" in prompt and "HIGH-VALUE" in prompt


def test_synthesis_prompt_names_tracker_rule(config: NewsletterConfig) -> None:
    prompt = compile_synthesis_prompt(config)
    assert "tracker" in prompt.lower()
    assert "build-of-the-week" in prompt.lower()
    assert "more than one source" in prompt
