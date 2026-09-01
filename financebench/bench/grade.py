"""Grade agent answers against FinanceBench gold answers with an LLM-as-judge.

For each run in ``data/financebench/runs.jsonl`` the judge LLM compares the
agent's answer to the gold answer (and the gold evidence / justification) and
returns a JSON verdict:

- ``correctness``: ``correct`` | ``partial`` | ``incorrect``
- ``numeric_match``: ``true`` | ``false`` | ``null`` (when no number is expected)
- ``groundedness``: ``grounded`` | ``partial`` | ``ungrounded``
- ``rationale``: one-sentence justification

Verdicts are written to ``data/financebench/scores.jsonl`` (one row per
question, joined with the run's trajectory summary).

Usage:
```bash
uv run cli bench run --step grade
uv run cli bench run --step grade -p deepseek_flash
```
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

from loguru import logger

from financebench.bench._env import DEFAULT_JUDGE_LLM, FB_DIR, load_env
from financebench.bench.run_questions import RUNS_PATH

SCORES_PATH = FB_DIR / "scores.jsonl"

_JUDGE_SYSTEM = """\
You are a strict-but-fair grader for FinanceBench, a financial QA benchmark.
Compare the agent's answer to the gold answer using the gold evidence and
justification. Financial answers are often a number or a short factual claim.

Return ONLY a JSON object with exactly these keys:
{
  "correctness": "correct" | "partial" | "incorrect",
  "numeric_match": true | false | null,
  "groundedness": "grounded" | "partial" | "ungrounded",
  "rationale": "<one sentence>"
}

Equivalence rules (adopted from Mafin2.5):
- Numerical accuracy: rounding differences are IGNORED when they do not change
  the conclusion. Allow flexibility: 1.2 is similar to 1.23 (one rounds to the
  other). Fractions, percentages, and decimals can be equivalent: "11 of 14" is
  equivalent to 79% and to 0.79.
- The agent answer is CORRECT if the gold answer, or any of its equivalences,
  can be INFERRED or generated from the agent's answer, or implicitly exists in
  it.
- If the agent answer is a SUPERSET of the gold answer, it is correct.
- If the agent answer conveys the same or similar meaning, conclusion, or
  rationale as the gold, it is correct.
- A reasonable alternative interpretation (justifiable vs the gold) is correct.
- Otherwise it is incorrect.

Tiers:
- "correct" = the agent answer matches the gold answer's substance under the
  equivalence rules above (number within rounding/fraction equivalence, or same
  factual claim). "partial" = right direction but wrong value/units, incomplete,
  or only partly substantiated. "incorrect" = wrong or missing.
- "numeric_match" = true if a number was expected and the agent's number matches
  the gold under the equivalence rules (rounding/fraction/percent); false if a
  number was expected and it does not match; null if no specific number expected.
- "groundedness" = whether the agent's answer is supported by the cited/source
  text rather than invented. "ungrounded" if it states facts not in the filing.
- Ignore any reasoning preamble in the agent's answer (e.g. "Now let me check
  ..."); grade only the substantive answer.
"""


def _evidence_text(run: dict) -> str:
    """Return a compact view of the gold evidence for the judge prompt."""
    evs = run.get("evidence") or []
    parts: list[str] = []
    for ev in evs[:2]:
        t = (ev.get("evidence_text") or "").strip()
        if t:
            parts.append(t[:600])
    return "\n".join(parts) if parts else "(no evidence provided)"


def _judge_prompt(run: dict) -> str:
    """Build the user message for the judge."""
    return (
        f"QUESTION:\n{run['question']}\n\n"
        f"GOLD ANSWER:\n{run['gold_answer']}\n\n"
        f"GOLD JUSTIFICATION:\n{run.get('justification') or '(none)'}\n\n"
        f"GOLD EVIDENCE:\n{_evidence_text(run)}\n\n"
        f"AGENT ANSWER:\n{run['agent_answer']}\n\n"
        "Return the JSON verdict now."
    )


def _extract_json(text: str) -> dict:
    """Parse the judge's JSON reply, tolerating code fences or stray prose."""
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else text
    match = re.search(r"\{.*\}", candidate, re.DOTALL)
    if match:
        candidate = match.group(0)
    return json.loads(candidate)


async def _grade_one(judge_llm_id: str, run: dict) -> dict:
    """Grade one run with the judge LLM and return the score record."""
    from genai_tk.core.factories.llm_factory import get_llm

    judge = get_llm(llm=judge_llm_id, json_mode=True)
    messages = [
        {"role": "system", "content": _JUDGE_SYSTEM},
        {"role": "user", "content": _judge_prompt(run)},
    ]
    resp = await judge.ainvoke(messages)
    content = resp.content if isinstance(resp.content, str) else str(resp.content)
    try:
        verdict = _extract_json(content)
        if "groundedness" not in verdict:
            if "grounded" in verdict:
                g_val = verdict.pop("grounded")
                verdict["groundedness"] = "grounded" if g_val is True else "ungrounded"
            else:
                verdict["groundedness"] = "grounded" if verdict.get("correctness") == "correct" else "partial"
    except Exception as exc:  # noqa: BLE101
        verdict = {
            "correctness": "incorrect",
            "numeric_match": None,
            "groundedness": "ungrounded",
            "rationale": f"judge parse error: {exc}; raw={content[:200]}",
        }

    return {
        "financebench_id": run["financebench_id"],
        "doc_name": run["doc_name"],
        "question_type": run.get("question_type"),
        "question_reasoning": run.get("question_reasoning"),
        "question": run["question"],
        "gold_answer": run["gold_answer"],
        "agent_answer": run["agent_answer"],
        "n_tool_calls": run["n_tool_calls"],
        "input_tokens": run["input_tokens"],
        "output_tokens": run["output_tokens"],
        "error": run.get("error"),
        "judge_llm": judge_llm_id,
        **verdict,
    }


async def _grade_all(
    runs: list[dict],
    judge_llm_id: str,
    *,
    scores_path: Path | None = None,
) -> list[dict]:
    """Grade every run sequentially (deterministic, rate-limit friendly).

    *scores_path* overrides where JSONL verdicts are appended (default ``SCORES_PATH``).
    """
    out_path = scores_path or SCORES_PATH
    scores: list[dict] = []
    for i, run in enumerate(runs, 1):
        logger.info("[{}/{}] grading {}", i, len(runs), run["financebench_id"])
        score = await _grade_one(judge_llm_id, run)
        scores.append(score)
        with out_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(score, ensure_ascii=False) + "\n")
        logger.info(
            "  → {} (numeric={}) [{}]",
            score["correctness"],
            score["numeric_match"],
            (score["rationale"][:90] + "…")
            if len(score["rationale"]) > 90
            else score["rationale"],
        )
    return scores


def _summarize(scores: list[dict]) -> dict:
    """Aggregate accuracy stats over the scored runs."""
    n = len(scores)
    if not n:
        return {"n": 0}
    correct = sum(1 for s in scores if s.get("correctness") == "correct")
    partial = sum(1 for s in scores if s.get("correctness") == "partial")
    incorrect = sum(1 for s in scores if s.get("correctness") == "incorrect")
    grounded = sum(
        1 for s in scores if s.get("groundedness") == "grounded" or s.get("grounded") is True
    )
    numeric = [s for s in scores if s.get("numeric_match") is not None]
    numeric_ok = sum(1 for s in numeric if s.get("numeric_match") is True)
    return {
        "n": n,
        "correct": correct,
        "partial": partial,
        "incorrect": incorrect,
        "accuracy_correct": round(correct / n, 3),
        "accuracy_correct_or_partial": round((correct + partial) / n, 3),
        "grounded": grounded,
        "groundedness_rate": round(grounded / n, 3),
        "numeric_questions": len(numeric),
        "numeric_match_rate": round(numeric_ok / len(numeric), 3) if numeric else None,
        "avg_tool_calls": round(sum(s.get("n_tool_calls", 0) for s in scores) / n, 2),
        "avg_input_tokens": round(sum(s.get("input_tokens", 0) for s in scores) / n),
        "avg_output_tokens": round(sum(s.get("output_tokens", 0) for s in scores) / n),
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Grade FinanceBench runs with an LLM-as-judge."
    )
    parser.add_argument(
        "--judge", default=DEFAULT_JUDGE_LLM, help="LLM identifier for the judge."
    )
    parser.add_argument("--runs", default=str(RUNS_PATH), help="Path to runs.jsonl.")
    args = parser.parse_args(argv)

    load_env()
    runs = [
        json.loads(line)
        for line in Path(args.runs).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    logger.info("Grading {} run(s) with judge={}", len(runs), args.judge)

    SCORES_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCORES_PATH.write_text("", encoding="utf-8")

    scores = asyncio.run(_grade_all(runs, args.judge))
    summary = _summarize(scores)
    (FB_DIR / "scores_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    print(f"scores={SCORES_PATH}")
    print(f"summary={json.dumps(summary)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
