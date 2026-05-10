# Code Review Bot — Project 4: Evaluator-Optimizer Loop

A code-review pipeline where a Generator LLM produces a review and a Critic
LLM evaluates it. If the Critic's score is below threshold, the Generator
revises using the Critic's feedback. Bounded by three exit conditions.

This is **Project 4** of an agentic-workflows course. The pattern is
**evaluator-optimizer** — your first real loop with explicit exit conditions.

```
[code]
   │
   ▼
 iter=1 ─────────────────────────────┐
   │                                 │
   ▼                                 │
Generator → review                   │
   │                                 │
   ▼                                 │
Critic → score, missed, feedback     │
   │                                 │
   ▼                                 │
score >= 8?      ─yes─→ accept       │
iter >= 3?       ─yes─→ stop (cap)   │
no improvement?  ─yes─→ stop (osc)   │
   │ no                              │
   └─────────────────────────────────┘
       (regenerate with feedback)
```

---

## Three Exit Conditions (the most important thing in this project)

Every loop needs exit conditions. This one has three:

| Exit | Trigger | Why |
|---|---|---|
| `quality_met` | Critic score ≥ 8 | The review is good enough |
| `max_iterations` | Iter count ≥ 3 | Hard cap; prevents infinite cost |
| `no_progress` | Score didn't improve by ≥ 1 | Oscillation guard |

**Always have all three.** Without `max_iterations` your loop can run forever. Without `no_progress` your loop can oscillate between two equivalent outputs. Without `quality_met` you have no way to actually succeed.

---

## What's new vs. Projects 1–3

- **A real `while`-style loop** (actually a `for` with breaks, but conceptually a while)
- **Two prompts that must be tuned against each other** — Generator and Critic
- **State carried across iterations** — Critic's feedback feeds into Generator's next prompt
- **Iteration audit trail** — every pass is logged so you can debug what improved (or didn't)

Everything else carries over: Pydantic schemas, the `call_llm` helper, structured outputs.

---

## Setup

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # paste OPENAI_API_KEY
export $(cat .env | xargs)
python main.py
```

The sample code (`inputs/sample.py`) is deliberately buggy — SQL injection, hardcoded password, MD5 for passwords, N+1 query, naming issues. The Critic should catch most of these even if the first-pass Generator misses some.

To review your own code:
```bash
python main.py path/to/your/file.py
```

---

## File map

| File | Role |
|------|------|
| `models.py` | Schemas: CodeReview, Critique, IterationRecord, PipelineResult |
| `prompts.py` | Generator + Critic prompts (tuned against each other) |
| `llm.py` | OpenAI structured-output helper (same as Projects 1–3) |
| `pipeline.py` | The loop itself — three exit conditions, feedback threading |
| `render.py` | Iteration trail + final review pretty-printer |
| `main.py` | Entry point with language detection |
| `inputs/sample.py` | Deliberately buggy code to exercise the loop |

---

## What this teaches

1. **Generator-Critic pattern.** Two LLMs with different roles produce better results than one combined prompt. Specialization, calibration, and observability all improve.
2. **Bounded iteration is non-negotiable.** Every loop must have a hard iteration cap. Always.
3. **Oscillation is real and silent.** Without a no-progress check, you can burn money on a loop that's just alternating between equivalent outputs.
4. **Feedback threading.** The Critic's specific output (missed issues, false positives, feedback string) feeds directly into the Generator's next prompt. This is what makes iterations actually improve — not just "try again," but "try again specifically addressing X, Y, Z."
5. **State across iterations is the foundation of memory.** This is the seed of what becomes Reflexion in Project 10. Memory is just iteration-state that persists across runs.

---

## Tuning Dials (in `pipeline.py`)

```python
QUALITY_THRESHOLD = 8        # Accept when overall_score >= this
MAX_ITERATIONS = 3           # Hard cap
MIN_PROGRESS_DELTA = 1       # Minimum improvement per iteration
```

These are the dials. Lower threshold = faster but lower quality. Higher max = more retries but more cost. Tighter progress delta = harder to oscillate but more likely to stop too early. Tune for your use case.

---

## Things to experiment with

- **Set `QUALITY_THRESHOLD = 10`.** Watch the loop hit `max_iterations` every time. This shows you what happens when the bar is unreachable.
- **Set `MAX_ITERATIONS = 10`.** See if the score ever actually reaches 10. (Usually no — there's a natural ceiling per task.)
- **Remove the no-progress guard.** Watch a borderline case oscillate. See how many iterations it takes before the max-iterations cap catches it.
- **Make the Critic prompt more lenient.** ("Be generous with scoring.") Watch the loop terminate on iteration 1 every time — and notice the final review is mediocre. This is what happens when the Critic isn't strict enough.
- **Make the Critic prompt stricter.** ("Be extremely critical.") Watch the loop never converge.

---

## Cost

Each iteration is 2 LLM calls (Generator + Critic). At max 3 iterations, the worst case is 6 calls. At GPT-5.4 mini pricing, roughly **$0.02–0.05 per review** for typical code files.

---

## Next (Phase 2 → Phase 3 transition)

Project 4.5 (Production Guardrails — middleware) is next in Phase 2. Then we cross into Phase 3, where LangGraph is introduced and the patterns from Phase 1–2 get expressed in a state-machine framework. The loop pattern from this project shows up directly in LangGraph as cyclic edges.
