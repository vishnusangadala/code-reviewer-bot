"""
Renderer for PipelineResult.

Two things to show:
  1. The full iteration trail — so you can see HOW the review improved
  2. The final accepted review

The iteration trail is what makes loop debugging tractable. Without it,
you can't tell whether the loop was actually improving or just oscillating.
"""
from models import PipelineResult

# ANSI colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
GRAY = "\033[90m"
BOLD = "\033[1m"
RESET = "\033[0m"

SEVERITY_COLOR = {
    "critical": RED + BOLD,
    "major": RED,
    "minor": YELLOW,
    "nit": GRAY,
}

STOP_REASON_COLOR = {
    "quality_met": GREEN,
    "max_iterations": YELLOW,
    "no_progress": YELLOW,
}


def render(result: PipelineResult):
    # ---- Iteration trail ----
    print(f"\n{BOLD}{'═' * 70}{RESET}")
    print(f"{BOLD}ITERATION TRAIL{RESET}")
    print(f"{BOLD}{'═' * 70}{RESET}")

    for it in result.iterations:
        accepted_marker = (f"{GREEN}✓ ACCEPTED{RESET}" if it.accepted
                           else f"{YELLOW}✗ rejected{RESET}")
        print(f"\n{BOLD}Iteration {it.iteration}{RESET}  {accepted_marker}  "
              f"score={it.critique.overall_score}/10")
        print(f"  Generator: {len(it.review.comments)} comments, "
              f"rec={it.review.overall_recommendation}")
        print(f"  Critic aspects:", end="")
        for asp in it.critique.aspects:
            color = GREEN if asp.score >= 8 else (YELLOW if asp.score >= 5 else RED)
            print(f"  {asp.aspect}={color}{asp.score}{RESET}", end="")
        print()
        if it.critique.missed_issues:
            print(f"  {YELLOW}Missed:{RESET}")
            for m in it.critique.missed_issues:
                print(f"    • {m}")
        if it.critique.false_positives:
            print(f"  {YELLOW}False positives:{RESET}")
            for f in it.critique.false_positives:
                print(f"    • {f}")
        if not it.accepted and it.critique.feedback_for_next_iteration:
            print(f"  {BLUE}Feedback for next pass:{RESET} "
                  f"{it.critique.feedback_for_next_iteration}")

    # ---- Stop reason ----
    stop_color = STOP_REASON_COLOR.get(result.stop_reason, "")
    print(f"\n{BOLD}{'─' * 70}{RESET}")
    print(f"{BOLD}Stop reason:{RESET} {stop_color}{result.stop_reason}{RESET}  "
          f"(final score {result.final_score}/10, "
          f"converged={'yes' if result.converged else 'no'})")

    # ---- Final review ----
    print(f"\n{BOLD}{'═' * 70}{RESET}")
    print(f"{BOLD}FINAL REVIEW{RESET}")
    print(f"{BOLD}{'═' * 70}{RESET}\n")

    fr = result.final_review
    print(f"{BOLD}Summary:{RESET} {fr.summary}\n")
    print(f"{BOLD}Recommendation:{RESET} {fr.overall_recommendation}\n")
    print(f"{BOLD}Comments ({len(fr.comments)}):{RESET}\n")
    for i, c in enumerate(fr.comments, 1):
        sev_color = SEVERITY_COLOR.get(c.severity, "")
        print(f"  {BOLD}[{i}]{RESET} {sev_color}{c.severity.upper()}{RESET} "
              f"{MAGENTA}{c.category}{RESET} @ {c.line_hint}")
        print(f"      Issue: {c.issue}")
        print(f"      Fix:   {c.suggestion}\n")

    print(f"{BOLD}{'═' * 70}{RESET}\n")
