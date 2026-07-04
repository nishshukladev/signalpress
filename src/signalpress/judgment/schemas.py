"""Structured output contracts for all LLM stages.

Decision: the LLM never free-writes into the pipeline; every stage returns one
of these models (Pydantic AI `output_type`). Prose exists only inside fields.
"""

from pydantic import BaseModel, Field

from signalpress.config.schema import ApplyHookEffort, Section


class Axis(BaseModel):
    hot: bool = False
    deep: bool = False
    high_value: bool = False

    def as_csv(self) -> str:
        return ",".join(
            name
            for name, on in [
                ("hot", self.hot),
                ("deep", self.deep),
                ("high_value", self.high_value),
            ]
            if on
        )


class ApplyHook(BaseModel):
    effort: ApplyHookEffort
    action: str = Field(description="Concrete action for the reader, one sentence.")
    tool: str = Field(
        description="The named, existing tool/repo/paper/framework to use or extend. Never vague."
    )


class ItemVerdict(BaseModel):
    candidate_index: int = Field(description="Index into the provided candidate list.")
    keep: bool
    lane: str = Field(
        default="", description="Lane id from the configured lanes; required if kept."
    )
    axes: Axis = Field(default_factory=Axis)
    section: Section = Field(default=Section.REPOS)
    summary: str = Field(default="", description="Two tight sentences; required if kept.")
    why_it_matters: str = Field(default="", description="One line tied to the reader's goal.")
    apply_hook: ApplyHook | None = None
    drop_reason: str = Field(default="", description="One line; required if dropped.")


class DailyVerdicts(BaseModel):
    verdicts: list[ItemVerdict]
    pattern_watch: str = Field(
        description="1-2 sentences: what recurred across sources today, tagged by axis."
    )


class JudgeVerdict(BaseModel):
    score: int = Field(ge=1, le=5)
    rationale: str = Field(description="One line explaining the score.")


class Theme(BaseModel):
    title: str
    why_it_matters: str
    axes: Axis
    durability: str = Field(description="high | medium | low - 12-month relevance.")
    leverage: str = Field(description="high | medium | low - for the reader's lanes/goal.")
    item_ids: list[str] = Field(description="IDs of the week's items backing this theme.")


class BuildOfWeek(BaseModel):
    title: str
    description: str = Field(description="Weekend-sized, shippable scope; specific.")
    builds_on: str = Field(description="Named existing framework/harness/dataset it extends.")
    prior_art_checked: str = Field(description="What was searched/checked before proposing this.")
    result_to_publish: str = Field(description="The single number/result to feature.")
    draft_post_title: str


class WeeklyReport(BaseModel):
    themes: list[Theme]
    build_of_week: BuildOfWeek
    backlog_ideas: list[str] = Field(
        default_factory=list, description="Other strong apply-ideas worth tracking."
    )
    lane_check: str = Field(description="Stay the course or shift? One or two sentences.")
    noise_filtered: list[str] = Field(default_factory=list)
