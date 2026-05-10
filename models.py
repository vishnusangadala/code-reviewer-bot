"""
Data contracts for the code-review loop.

Note the IterationRecord — it captures one full pass through the loop.
The pipeline accumulates a list of these so you can see the full history
of how the review evolved.
"""
from pydantic import BaseModel, Field
from typing import Literal, Optional, List


Severity = Literal["nit", "minor", "major", "critical"]


# ---------- Step: Generator output ----------

class ReviewComment(BaseModel):
    """A single review comment from the generator."""
    line_hint: str = Field(
        description="Approximate location: function name, line range, or 'overall'. "
                    "Not required to be exact — this is for human readability."
    )
    severity: Severity
    category: Literal[
        "bug", "performance", "readability", "naming",
        "style", "security", "testing", "documentation",
    ]
    issue: str = Field(description="What's wrong, in one or two sentences.")
    suggestion: str = Field(description="Concrete fix. Code snippet if helpful.")


class CodeReview(BaseModel):
    """The Generator's output — a full code review."""
    summary: str = Field(description="2-3 sentences: overall assessment of the code.")
    comments: List[ReviewComment]
    overall_recommendation: Literal[
        "approve", "approve_with_nits", "request_changes", "needs_major_rework"
    ]


# ---------- Step: Critic output ----------

class CritiqueAspect(BaseModel):
    aspect: Literal[
        "completeness",     # did the review cover all important issues?
        "accuracy",         # are the comments correct (no false positives)?
        "specificity",      # are issues specific or vague?
        "actionability",    # do suggestions help fix things?
        "severity_calibration",  # are severities sensible (no nit-marked-critical, etc.)?
    ]
    score: int = Field(ge=0, le=10)
    rationale: str = Field(description="Why this score. Specific examples from the review.")


class Critique(BaseModel):
    """The Critic's evaluation of the review."""
    aspects: List[CritiqueAspect] = Field(
        description="Score each of the 5 aspects. ALL FIVE must be present."
    )
    overall_score: int = Field(
        ge=0, le=10,
        description="Holistic quality. NOT a simple average — weight by how much each aspect mattered."
    )
    missed_issues: List[str] = Field(
        description="Important problems the review missed entirely. Empty list if none."
    )
    false_positives: List[str] = Field(
        description="Comments in the review that are wrong or overstated. Empty list if none."
    )
    feedback_for_next_iteration: str = Field(
        description="Specific guidance the generator should use on the next pass. "
                    "Empty string if the review is good enough already."
    )


# ---------- Per-iteration record ----------

class IterationRecord(BaseModel):
    iteration: int = Field(ge=1)
    review: CodeReview
    critique: Critique
    accepted: bool = Field(description="Whether this iteration's review met the quality bar.")


# ---------- Final pipeline result ----------

class PipelineResult(BaseModel):
    code: str
    final_review: CodeReview
    iterations: List[IterationRecord]
    converged: bool = Field(description="True if quality bar was met; False if we hit max iterations.")
    final_score: int = Field(ge=0, le=10)
    stop_reason: Literal["quality_met", "max_iterations", "no_progress"]
