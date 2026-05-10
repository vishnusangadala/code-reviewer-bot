"""
The evaluator-optimizer loop.

THE NEW PATTERN (vs Project 3's routing):

    [code]
       │
       ▼
    iter = 1
       │
       ├──────────────────────────────────┐
       ▼                                  │
   Generator produces review              │
       │                                  │
       ▼                                  │
   Critic evaluates → score, feedback     │
       │                                  │
       ▼                                  │
   ┌───────────────────────────────┐      │
   │ score >= threshold?  ─yes─→ accept   │
   │ iter >= max_iter?    ─yes─→ stop (max)
   │ no progress?         ─yes─→ stop (oscillation)
   │ otherwise            ─────→ iter+=1, regenerate with feedback ─┐
   └───────────────────────────────┘                                │
                                                                    │
                                                                    │
   loop back ←────────────────────────────────────────────────────┘

THREE EXIT CONDITIONS (this is the part you must internalize):

  1. quality_met       — score >= QUALITY_THRESHOLD
  2. max_iterations    — iter >= MAX_ITERATIONS (hard cap; non-negotiable)
  3. no_progress       — score didn't improve from last iteration by at
                         least MIN_PROGRESS_DELTA (oscillation guard)

Without exit conditions, this loop runs forever and burns money. With them,
the worst case is bounded and predictable.
"""
from typing import List
from models import (
    CodeReview, Critique, IterationRecord, PipelineResult,
)
from llm import call_llm
from prompts import (
    GENERATOR_SYSTEM, GENERATOR_USER_FIRST_PASS, GENERATOR_USER_REVISION,
    CRITIC_SYSTEM, CRITIC_USER,
)


# Tunable parameters — these are the dials that define the loop's behavior.
# Lower threshold = faster but lower quality.
# Higher max = more retries but more cost.
# These defaults work well for code review specifically.
QUALITY_THRESHOLD = 8        # Accept when Critic's overall_score >= this
MAX_ITERATIONS = 3           # Hard cap; never iterate more than this
MIN_PROGRESS_DELTA = 1       # If score doesn't improve by this much, stop


def _format_comments_brief(review: CodeReview) -> str:
    """Compact representation for feeding back into the Generator."""
    lines = []
    for i, c in enumerate(review.comments, 1):
        lines.append(f"  [{i}] {c.severity.upper()} {c.category} @ {c.line_hint}: {c.issue}")
    return "\n".join(lines) if lines else "  (no comments)"


def _format_comments_full(review: CodeReview) -> str:
    """Full representation for feeding to the Critic."""
    lines = []
    for i, c in enumerate(review.comments, 1):
        lines.append(
            f"  [{i}] {c.severity.upper()} | {c.category} | {c.line_hint}\n"
            f"       Issue: {c.issue}\n"
            f"       Suggestion: {c.suggestion}"
        )
    return "\n".join(lines) if lines else "  (no comments — review found nothing)"


def generate_review(
    code: str,
    language: str,
    previous_review: CodeReview | None = None,
    critique: Critique | None = None,
) -> CodeReview:
    """Run the Generator. First pass uses one prompt; revisions use another."""
    if previous_review is None:
        prompt = GENERATOR_USER_FIRST_PASS.format(language=language, code=code)
    else:
        assert critique is not None
        prompt = GENERATOR_USER_REVISION.format(
            language=language,
            code=code,
            previous_summary=previous_review.summary,
            n_previous_comments=len(previous_review.comments),
            previous_comments_brief=_format_comments_brief(previous_review),
            critic_feedback=critique.feedback_for_next_iteration,
            missed_issues="\n".join(f"  - {m}" for m in critique.missed_issues) or "  (none)",
            false_positives="\n".join(f"  - {f}" for f in critique.false_positives) or "  (none)",
        )

    return call_llm(
        prompt=prompt,
        schema=CodeReview,
        system=GENERATOR_SYSTEM,
        # Slightly higher temp on first pass for thoroughness; lower on revisions
        # because we want it to address feedback faithfully, not riff.
        temperature=0.4 if previous_review is None else 0.2,
    )


def critique_review(code: str, language: str, review: CodeReview) -> Critique:
    """Run the Critic on a given review."""
    return call_llm(
        prompt=CRITIC_USER.format(
            language=language,
            code=code,
            review_summary=review.summary,
            review_recommendation=review.overall_recommendation,
            n_comments=len(review.comments),
            review_comments=_format_comments_full(review),
        ),
        schema=Critique,
        system=CRITIC_SYSTEM,
        temperature=0.1,  # critique wants consistency
    )


def run_pipeline(code: str, language: str = "python", verbose: bool = True) -> PipelineResult:
    iterations: List[IterationRecord] = []
    previous_review: CodeReview | None = None
    previous_critique: Critique | None = None
    previous_score: int = -1

    for iter_num in range(1, MAX_ITERATIONS + 1):
        if verbose:
            print(f"\n→ Iteration {iter_num}/{MAX_ITERATIONS}")

        # --- Generator ---
        review = generate_review(code, language, previous_review, previous_critique)
        if verbose:
            print(f"  Generator: {len(review.comments)} comments, "
                  f"recommendation={review.overall_recommendation}")

        # --- Critic ---
        critique = critique_review(code, language, review)
        if verbose:
            print(f"  Critic: overall_score={critique.overall_score}/10, "
                  f"missed={len(critique.missed_issues)}, "
                  f"false_pos={len(critique.false_positives)}")
            for asp in critique.aspects:
                print(f"    - {asp.aspect}: {asp.score}/10")

        accepted = critique.overall_score >= QUALITY_THRESHOLD
        iterations.append(IterationRecord(
            iteration=iter_num,
            review=review,
            critique=critique,
            accepted=accepted,
        ))

        # --- Exit condition 1: quality met ---
        if accepted:
            if verbose:
                print(f"  ✓ Quality threshold met (score {critique.overall_score} "
                      f">= {QUALITY_THRESHOLD})")
            return PipelineResult(
                code=code,
                final_review=review,
                iterations=iterations,
                converged=True,
                final_score=critique.overall_score,
                stop_reason="quality_met",
            )

        # --- Exit condition 2: max iterations ---
        if iter_num >= MAX_ITERATIONS:
            if verbose:
                print(f"  ⚠ Hit max iterations without converging (score "
                      f"{critique.overall_score})")
            return PipelineResult(
                code=code,
                final_review=review,
                iterations=iterations,
                converged=False,
                final_score=critique.overall_score,
                stop_reason="max_iterations",
            )

        # --- Exit condition 3: no progress (oscillation guard) ---
        # Only check after iteration 2 — first iteration has no prior to compare.
        if iter_num >= 2 and critique.overall_score - previous_score < MIN_PROGRESS_DELTA:
            if verbose:
                print(f"  ⚠ No progress (score {previous_score} → "
                      f"{critique.overall_score}); stopping to avoid oscillation")
            return PipelineResult(
                code=code,
                final_review=review,
                iterations=iterations,
                converged=False,
                final_score=critique.overall_score,
                stop_reason="no_progress",
            )

        # Set up for next iteration
        previous_review = review
        previous_critique = critique
        previous_score = critique.overall_score

    # Defensive: shouldn't reach here because MAX_ITERATIONS check handles it,
    # but typing prefers explicit return.
    raise RuntimeError("Loop exited without producing a result; check exit conditions.")
