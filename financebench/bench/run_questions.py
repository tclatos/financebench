"""Run each FinanceBench question through the docgraph agent and record results.

For every question in ``data/financebench/questions.jsonl`` this:
- builds the ``docgraph`` deep agent via ``create_docgraph_agent`` (Document
  Graph navigation tools + the ``financebench-qa`` skill injected at runtime);
- streams one turn and captures the trajectory directly from harness events
  (answer text, tool calls + results, token usage);
- appends one JSONL row per question to ``data/financebench/runs.jsonl``.

The LangChainHarness also auto-attaches the NeMo Relay callback, so each run is
recorded in the global ``TrajectoryStore`` (inspect with ``cli trajectory list``)
and flushed on ``aclose()``.

Usage:
```bash
uv run python -m financebench.bench.run_questions
uv run python -m financebench.bench.run_questions --limit 1
uv run python -m financebench.bench.run_questions --llm deepseek_v4flash@openrouter
```
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from financebench.bench._env import (
    DEFAULT_AGENT_LLM,
    FB_DIR,
    KG_DB,
    load_env,
)
from financebench.bench.load_dataset import QUESTIONS_PATH

RUNS_PATH = FB_DIR / "runs.jsonl"
DOCGRAPH_PROFILE = "docgraph"


def _load_questions(path: Path) -> list[dict]:
    """Read the per-question JSONL rows."""
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


async def _run_one(harness: object, q: dict, llm: str) -> dict:
    """Stream one question through *harness* and return the run record."""
    from genai_tk.agents.harness import (
        EndEvent,
        ErrorEvent,
        TokenEvent,
        ToolCallEvent,
        ToolResultEvent,
        UsageEvent,
    )

    thread_id = q["financebench_id"]
    answer_parts: list[str] = []
    tool_calls: list[dict] = []
    tool_results: list[dict] = []
    input_tokens = 0
    output_tokens = 0
    error: str | None = None

    async for event in harness.astream(q["question"], thread_id=thread_id):
        if isinstance(event, TokenEvent):
            answer_parts.append(event.text)
        elif isinstance(event, ToolCallEvent):
            tool_calls.append({"tool": event.tool_name, "args": event.args})
        elif isinstance(event, ToolResultEvent):
            tool_results.append(
                {"tool": event.tool_name, "content": (event.content or "")[:1500]}
            )
        elif isinstance(event, UsageEvent):
            input_tokens += event.input_tokens
            output_tokens += event.output_tokens
        elif isinstance(event, ErrorEvent):
            error = event.message
        elif isinstance(event, EndEvent):
            pass

    return {
        "financebench_id": q["financebench_id"],
        "doc_name": q["doc_name"],
        "company": q["company"],
        "question_type": q.get("question_type"),
        "question_reasoning": q.get("question_reasoning"),
        "question": q["question"],
        "gold_answer": q["answer"],
        "justification": q.get("justification"),
        "evidence": q.get("evidence"),
        "agent_answer": "".join(answer_parts).strip(),
        "tool_calls": tool_calls,
        "tool_results": tool_results,
        "n_tool_calls": len(tool_calls),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "error": error,
        "thread_id": thread_id,
        "llm": llm,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }


async def _run_all(
    questions: list[dict],
    llm: str,
    db_path: str,
    *,
    folder_id: str | None = None,
    profile_name: str = DOCGRAPH_PROFILE,
    runs_path: Path | None = None,
    embeddings_id: str | None = None,
) -> list[dict]:
    """Build the agent once and run every question on its own thread.

    *folder_id* scopes the agent to one folder (None = whole corpus).
    *profile_name* selects the agent profile (default ``docgraph``).
    *runs_path* overrides where JSONL rows are appended (default ``RUNS_PATH``).
    *embeddings_id* enables the hybrid (vector + BM25) ``search_sections`` mode.
    """
    from genai_tk.agents.harness.profiles import load_langchain_profiles

    from genai_graph.agent import create_docgraph_agent

    out_path = runs_path or RUNS_PATH
    profiles = load_langchain_profiles()
    if profile_name not in profiles:
        raise SystemExit(
            f"Agent profile {profile_name!r} not found. Available: {sorted(profiles)}"
        )
    profile = profiles[profile_name]

    logger.info(
        "Building docgraph agent (profile={}, llm={}, db={}, folder={}, embeddings={})",
        profile_name,
        llm,
        db_path,
        folder_id,
        embeddings_id or "off",
    )
    harness = create_docgraph_agent(
        profile, llm=llm, db_path=db_path, folder_id=folder_id, embeddings_id=embeddings_id
    )

    records: list[dict] = []
    try:
        for i, q in enumerate(questions, 1):
            logger.info(
                "[{}/{}] {} — {}",
                i,
                len(questions),
                q["financebench_id"],
                q["question"][:80],
            )
            record = await _run_one(harness, q, llm)
            records.append(record)
            with out_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            status = "ERROR" if record["error"] else "ok"
            logger.info(
                "  → {} ({} tool calls, {} in/{} out tok) [{}]",
                status,
                record["n_tool_calls"],
                record["input_tokens"],
                record["output_tokens"],
                (record["agent_answer"][:90] + "…")
                if len(record["agent_answer"]) > 90
                else record["agent_answer"],
            )
    finally:
        await harness.aclose()
    return records


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run FinanceBench questions through the docgraph agent."
    )
    parser.add_argument(
        "--llm", default=DEFAULT_AGENT_LLM, help="LLM identifier for the agent."
    )
    parser.add_argument(
        "--db", default=str(KG_DB), help="Ladybug Document Graph DB path."
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Run only the first N questions."
    )
    parser.add_argument(
        "--questions",
        default=str(QUESTIONS_PATH),
        help="Path to questions.jsonl (default: the selected target doc's).",
    )
    args = parser.parse_args(argv)

    load_env()
    questions = _load_questions(Path(args.questions))
    if args.limit:
        questions = questions[: args.limit]
    logger.info("Running {} question(s) from {}", len(questions), args.questions)

    # Truncate previous runs file for a clean, reproducible run.
    RUNS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RUNS_PATH.write_text("", encoding="utf-8")

    asyncio.run(_run_all(questions, args.llm, args.db))
    print(f"runs={RUNS_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
