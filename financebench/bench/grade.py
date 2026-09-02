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
from typing import Literal

from loguru import logger
from pydantic import BaseModel

from financebench.bench._env import DEFAULT_JUDGE_LLM, FB_DIR, load_env
from financebench.bench.run_questions import RUNS_PATH

SCORES_PATH = FB_DIR / "scores.jsonl"


class JudgeVerdict(BaseModel):
    """Structured verdict returned by the LLM-as-judge."""

    correctness: Literal["correct", "partial", "incorrect"]
    numeric_match: bool | None = None
    groundedness: Literal["grounded", "partial", "ungrounded"] = "partial"
    rationale: str = ""


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


def _parse_verdict(content: str) -> JudgeVerdict:
    """Parse and strictly validate the judge JSON output into a JudgeVerdict."""
    raw_dict = _extract_json(content)

    # Normalize correctness
    raw_corr = str(raw_dict.get("correctness", "")).lower().strip()
    if raw_corr in ("correct", "exact", "true", "yes"):
        correctness: Literal["correct", "partial", "incorrect"] = "correct"
    elif raw_corr in ("partial", "partially_correct", "partially correct"):
        correctness = "partial"
    elif raw_corr in ("incorrect", "false", "no", "wrong"):
        correctness = "incorrect"
    elif "partial" in raw_corr:
        correctness = "partial"
    elif "correct" in raw_corr and raw_corr != "correctness":
        correctness = "correct"
    else:
        # If the model emitted a malformed or schema-echoed key, try to infer from rationale or fallback
        rat = str(raw_dict.get("rationale", "")).lower()
        if "correct" in rat and "incorrect" not in rat:
            correctness = "correct"
        elif "partial" in rat:
            correctness = "partial"
        else:
            correctness = "incorrect"

    # Normalize numeric_match
    num_m = raw_dict.get("numeric_match")
    if isinstance(num_m, str):
        if num_m.lower() in ("true", "yes", "1"):
            numeric_match: bool | None = True
        elif num_m.lower() in ("false", "no", "0"):
            numeric_match = False
        else:
            numeric_match = None
    elif isinstance(num_m, bool):
        numeric_match = num_m
    else:
        numeric_match = None

    # Normalize groundedness
    raw_ground = str(
        raw_dict.get("groundedness")
        or raw_dict.get("grounded")
        or ("grounded" if correctness == "correct" else "partial")
    ).lower().strip()
    if raw_ground in ("grounded", "true", "yes"):
        groundedness: Literal["grounded", "partial", "ungrounded"] = "grounded"
    elif raw_ground in ("partial", "partially_grounded", "partially grounded"):
        groundedness = "partial"
    elif raw_ground in ("ungrounded", "false", "no"):
        groundedness = "ungrounded"
    else:
        groundedness = "partial"

    rationale = str(raw_dict.get("rationale") or "").strip()
    if not rationale:
        rationale = "(no rationale provided)"

    return JudgeVerdict(
        correctness=correctness,
        numeric_match=numeric_match,
        groundedness=groundedness,
        rationale=rationale,
    )


async def _grade_one(
    judge_llm_id: str,
    run: dict,
    *,
    max_retries: int = 3,
    retry_delay: float = 2.0,
) -> dict:
    """Grade one run with the judge LLM and return the score record."""
    from genai_tk.core.factories.llm_factory import get_llm

    judge = get_llm(llm=judge_llm_id, json_mode=True)
    messages = [
        {"role": "system", "content": _JUDGE_SYSTEM},
        {"role": "user", "content": _judge_prompt(run)},
    ]

    content: str = ""
    for attempt in range(max_retries):
        try:
            resp = await judge.ainvoke(messages)
            content = resp.content if isinstance(resp.content, str) else str(resp.content)
            break
        except Exception as exc:
            if attempt < max_retries - 1:
                logger.warning(
                    "[{}] Judge LLM invocation error (attempt {}/{}): {}; retrying in {}s...",
                    run.get("financebench_id"),
                    attempt + 1,
                    max_retries,
                    exc,
                    retry_delay * (attempt + 1),
                )
                await asyncio.sleep(retry_delay * (attempt + 1))
            else:
                logger.error(
                    "[{}] Judge LLM invocation failed after {} attempts: {}",
                    run.get("financebench_id"),
                    max_retries,
                    exc,
                )
                raise

    try:
        verdict = _parse_verdict(content)
        parsed_verdict = verdict.model_dump()
    except Exception as exc:  # noqa: BLE101
        parsed_verdict = {
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
        **parsed_verdict,
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


def generate_markdown_report(
    scores: list[dict],
    summary: dict,
    *,
    profile_name: str = "mistral_glm",
    agent_llm: str = "",
    judge_llm: str = "",
    report_path: Path | None = None,
) -> Path:
    """Generate a markdown evaluation report from scores and summary."""
    from collections import defaultdict
    from datetime import datetime, timezone
    from financebench.bench._env import REPORT_DIR

    target_path = report_path or (REPORT_DIR / f"{profile_name}_report.md")
    target_path.parent.mkdir(parents=True, exist_ok=True)

    n = summary.get("n", len(scores))
    acc_exact = f"{summary.get('accuracy_correct', 0) * 100:.1f}%"
    acc_lenient = f"{summary.get('accuracy_correct_or_partial', 0) * 100:.1f}%"
    groundedness = f"{summary.get('groundedness_rate', 0) * 100:.1f}%"
    num_match = (
        f"{summary.get('numeric_match_rate', 0) * 100:.1f}%"
        if summary.get("numeric_match_rate") is not None
        else "N/A"
    )

    lines: list[str] = [
        f"# FinanceBench Benchmark Report: `{profile_name}`",
        "",
        f"- **Date**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"- **Agent LLM**: `{agent_llm}`",
        f"- **Judge LLM**: `{judge_llm}`",
        f"- **Total Questions Evaluated**: {n}",
        "",
        "## Summary Metrics",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| **Exact Correct** | {summary.get('correct', 0)} ({acc_exact}) |",
        f"| **Correct or Partial** | {summary.get('correct', 0) + summary.get('partial', 0)} ({acc_lenient}) |",
        f"| **Incorrect** | {summary.get('incorrect', 0)} ({summary.get('incorrect', 0) / max(1, n) * 100:.1f}%) |",
        f"| **Groundedness Rate** | {summary.get('grounded', 0)} / {n} ({groundedness}) |",
        f"| **Numeric Match Rate** | {num_match} ({summary.get('numeric_questions', 0)} numeric questions) |",
        f"| **Avg Tool Calls / Question** | {summary.get('avg_tool_calls', 0)} |",
        f"| **Avg Input Tokens / Question** | {summary.get('avg_input_tokens', 0):,} |",
        f"| **Avg Output Tokens / Question** | {summary.get('avg_output_tokens', 0):,} |",
        "",
    ]

    # Breakdown by document
    by_doc: dict[str, list[dict]] = defaultdict(list)
    for s in scores:
        doc = s.get("doc_name") or "unknown"
        by_doc[doc].append(s)

    lines.extend([
        "## Results by Document",
        "",
        "| Document | Questions | Correct | Partial | Incorrect | Accuracy (Lenient) |",
        "|---|---|---|---|---|---|",
    ])
    for doc, doc_scores in sorted(by_doc.items()):
        d_n = len(doc_scores)
        d_c = sum(1 for s in doc_scores if s.get("correctness") == "correct")
        d_p = sum(1 for s in doc_scores if s.get("correctness") == "partial")
        d_i = sum(1 for s in doc_scores if s.get("correctness") == "incorrect")
        d_rate = f"{(d_c + d_p) / max(1, d_n) * 100:.1f}%"
        lines.append(f"| `{doc}` | {d_n} | {d_c} | {d_p} | {d_i} | {d_rate} |")

    lines.append("")

    # Breakdown by reasoning type
    by_reasoning: dict[str, list[dict]] = defaultdict(list)
    for s in scores:
        r_type = s.get("question_reasoning") or s.get("question_type") or "general"
        by_reasoning[r_type].append(s)

    if len(by_reasoning) > 1:
        lines.extend([
            "## Results by Question Type / Reasoning",
            "",
            "| Category | Questions | Correct | Partial | Incorrect | Accuracy (Lenient) |",
            "|---|---|---|---|---|---|",
        ])
        for cat, cat_scores in sorted(by_reasoning.items()):
            c_n = len(cat_scores)
            c_c = sum(1 for s in cat_scores if s.get("correctness") == "correct")
            c_p = sum(1 for s in cat_scores if s.get("correctness") == "partial")
            c_i = sum(1 for s in cat_scores if s.get("correctness") == "incorrect")
            c_rate = f"{(c_c + c_p) / max(1, c_n) * 100:.1f}%"
            lines.append(f"| {cat} | {c_n} | {c_c} | {c_p} | {c_i} | {c_rate} |")
        lines.append("")

    # Non-correct questions analysis
    non_correct = [s for s in scores if s.get("correctness") in ("partial", "incorrect")]
    if non_correct:
        lines.extend([
            "## Non-Perfect Questions Analysis",
            "",
        ])
        for s in non_correct:
            lines.extend([
                f"### `{s.get('financebench_id')}` — {s.get('doc_name')} ({s.get('correctness', '').upper()})",
                "",
                f"- **Question**: {s.get('question')}",
                f"- **Gold Answer**: {s.get('gold_answer')}",
                f"- **Agent Answer**: {s.get('agent_answer')}",
                f"- **Judge Rationale**: {s.get('rationale')}",
                f"- **Numeric Match**: {s.get('numeric_match')}",
                f"- **Groundedness**: {s.get('groundedness')}",
                "",
            ])

    target_path.write_text("\n".join(lines), encoding="utf-8")
    return target_path


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
