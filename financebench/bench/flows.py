"""Prefect-orchestrated flows and tasks for the FinanceBench evaluation pipeline.

Provides parallelized, resilient workflow steps with automatic retries,
in-process concurrency (safe for Ladybug single-process constraints), and
fine-grained stage control (fetch, markdownize, build, run, grade).

Usage:
```bash
uv run cli bench run
uv run cli bench run --profile mistral_glm
uv run cli bench run --step run --limit 1
```
"""

from __future__ import annotations

import asyncio
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger
from prefect import flow, task

from financebench.bench._env import ensure_dirs, load_env
from financebench.bench.run import BenchConfig, configure_bench_monitoring

_RUNS_WRITE_LOCK = threading.Lock()
_SCORES_WRITE_LOCK = threading.Lock()
_QUESTION_SEMAPHORES: dict[int, threading.Semaphore] = {}
_JUDGE_SEMAPHORES: dict[int, threading.Semaphore] = {}


def _get_semaphore(cache: dict[int, threading.Semaphore], capacity: int) -> threading.Semaphore:
    if capacity not in cache:
        cache[capacity] = threading.Semaphore(max(1, capacity))
    return cache[capacity]


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


@task(retries=3, retry_delay_seconds=2, task_run_name="fetch-pdf-{doc_name}")
def fetch_doc_task(doc_name: str, pdfs_dir: str) -> str:
    """Download one document's PDF with automatic retries."""
    from financebench.bench.fetch_pdf import fetch_pdf

    return fetch_pdf(doc_name, pdfs_dir=Path(pdfs_dir))


@task(retries=2, retry_delay_seconds=2, task_run_name="markdownize-{doc_name}")
def markdownize_doc_task(
    doc_name: str,
    *,
    force: bool,
    pdfs_dir: str,
    onedrive_markdown_dir: str,
    markdownize_profile: str,
    markdown_dir: str,
    skip_ocr: bool,
) -> str:
    """Convert/OCR one document PDF to Markdown and copy into the project markdown directory."""
    from financebench.bench.build_graph import (
        MD_FILENAME_SUFFIX,
        copy_markdown_to_project,
        markdownize_target,
    )

    pdfs = Path(pdfs_dir)
    onedrive = Path(onedrive_markdown_dir)
    md_dir = Path(markdown_dir)
    md_dir.mkdir(parents=True, exist_ok=True)

    if skip_ocr:
        md_path = onedrive / f"{doc_name}{MD_FILENAME_SUFFIX}"
        if not md_path.exists():
            raise FileNotFoundError(
                f"--skip-ocr set but markdown not found: {md_path}; run without --skip fetch first."
            )
    else:
        md_path = markdownize_target(
            doc_name,
            force=False,
            pdfs_dir=pdfs,
            onedrive_markdown_dir=onedrive,
            markdownize_profile=markdownize_profile,
        )
    dest = copy_markdown_to_project(md_path, markdown_dir=md_dir)
    return str(dest)


@task(task_run_name="build-document-graph")
def build_graph_task(
    docs: list[str],
    *,
    markdown_dir: str,
    kg_db: str,
    force: bool,
    build_llm: str | None,
    structure_strategy: str = "auto",
    generate_summaries: bool = True,
    workers: int = 4,
    summary_min_tokens: int = 800,
    context_safety_ratio: float = 0.9,
    embeddings_id: str | None = None,
    fts: bool = True,
    chunk_size_tokens: int = 1500,
) -> dict[str, Any]:
    """Build the Ladybug Document Graph in-process (using worker threads for outline extraction)."""
    from financebench.bench.build_graph import build_document_graph

    md_dir = Path(markdown_dir)
    Path(kg_db).parent.mkdir(parents=True, exist_ok=True)

    result = build_document_graph(
        docs[0] if docs else "",
        force=force,
        llm=build_llm,
        structure_strategy=structure_strategy,
        generate_summaries=generate_summaries,
        workers=workers,
        summary_min_tokens=summary_min_tokens,
        context_safety_ratio=context_safety_ratio,
        markdown_dir=md_dir,
        kg_db=Path(kg_db),
        embeddings_id=embeddings_id,
        fts=fts,
        chunk_size_tokens=chunk_size_tokens,
    )
    logger.success(
        "Graph built: {} sections, {} summarized, {} doc(s) ({} degraded)",
        result.get("sections_created"),
        result.get("sections_summarized"),
        result.get("documents_processed"),
        result.get("files_degraded"),
    )
    return result


@task(retries=2, retry_delay_seconds=3, task_run_name="run-question-{q[financebench_id]}")
def run_question_task(
    q: dict[str, Any],
    *,
    llm: str,
    db_path: str,
    folder_id: str | None = None,
    profile_name: str = "default",
    embeddings_id: str | None = None,
    runs_path: str | None = None,
    concurrency: int = 10,
) -> dict[str, Any]:
    """Execute one question against the Document Graph deep agent and record trajectory."""
    from genai_tk.agents.harness.profiles import load_langchain_profiles

    from genai_graph.agent import create_docgraph_agent
    from financebench.bench.run_questions import _run_one

    sem = _get_semaphore(_QUESTION_SEMAPHORES, concurrency)

    async def _execute() -> dict[str, Any]:
        profiles = load_langchain_profiles()
        if profile_name not in profiles:
            raise KeyError(
                f"Agent profile '{profile_name}' not found. Available: {sorted(profiles)}"
            )
        profile = profiles[profile_name]
        harness = create_docgraph_agent(
            profile,
            llm=llm,
            db_path=db_path,
            folder_id=folder_id,
            embeddings_id=embeddings_id,
        )
        try:
            return await _run_one(harness, q, llm)
        finally:
            await harness.aclose()

    try:
        with sem:
            record = asyncio.run(_execute())
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "[{}] Exception during question run: {}",
            q.get("financebench_id"),
            exc,
        )
        record = {
            "financebench_id": q.get("financebench_id"),
            "doc_name": q.get("doc_name", ""),
            "company": q.get("company", ""),
            "question_type": q.get("question_type"),
            "question_reasoning": q.get("question_reasoning"),
            "question": q.get("question", ""),
            "gold_answer": q.get("answer", ""),
            "justification": q.get("justification"),
            "evidence": q.get("evidence"),
            "agent_answer": f"Execution error: {exc}",
            "tool_calls": [],
            "tool_results": [],
            "n_tool_calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "error": str(exc),
            "thread_id": q.get("financebench_id"),
            "llm": llm,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

    if record.get("error"):
        logger.warning(
            "[{}] Agent turn completed with error: {}",
            q["financebench_id"],
            record["error"],
        )
    else:
        logger.info(
            "[{}] → ok ({} tool calls, {} in/{} out tok)",
            q["financebench_id"],
            record.get("n_tool_calls", 0),
            record.get("input_tokens", 0),
            record.get("output_tokens", 0),
        )

    if runs_path:
        with _RUNS_WRITE_LOCK:
            out_p = Path(runs_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            with out_p.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    return record


@task(retries=5, retry_delay_seconds=3, task_run_name="grade-run-{run[financebench_id]}")
def grade_run_task(
    run: dict[str, Any],
    *,
    judge_llm: str,
    scores_path: str | None = None,
    concurrency: int = 5,
) -> dict[str, Any]:
    """Grade one question run using the LLM-as-judge."""
    from financebench.bench.grade import _grade_one

    sem = _get_semaphore(_JUDGE_SEMAPHORES, concurrency)

    with sem:
        score = asyncio.run(_grade_one(judge_llm, run))

    if scores_path:
        with _SCORES_WRITE_LOCK:
            out_p = Path(scores_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            with out_p.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(score, ensure_ascii=False) + "\n")

    logger.info(
        "[{}] Judge verdict: {} (numeric={}, groundedness={}) — {}",
        run["financebench_id"],
        score.get("correctness"),
        score.get("numeric_match"),
        score.get("groundedness"),
        score.get("rationale"),
    )
    return score


# ---------------------------------------------------------------------------
# Sub-flows
# ---------------------------------------------------------------------------


@flow(name="financebench-fetch")
def fetch_flow(cfg: BenchConfig) -> list[str]:
    """Fetch PDFs in parallel across configured documents."""
    logger.info("Fetching {} PDF document(s) in parallel...", len(cfg.docs))
    futures = [fetch_doc_task.submit(doc, pdfs_dir=cfg.pdfs_dir) for doc in cfg.docs]
    return [f.result() for f in futures]


@flow(name="financebench-markdownize")
def markdownize_flow(cfg: BenchConfig) -> list[str]:
    """Convert/OCR PDFs to Markdown in parallel."""
    logger.info("Markdownizing {} document(s) in parallel...", len(cfg.docs))
    futures = [
        markdownize_doc_task.submit(
            doc,
            force=cfg.build_force,
            pdfs_dir=cfg.pdfs_dir,
            onedrive_markdown_dir=cfg.onedrive_markdown_dir,
            markdownize_profile=cfg.markdownize_profile,
            markdown_dir=cfg.markdown_dir,
            skip_ocr=cfg.skip_ocr,
        )
        for doc in cfg.docs
    ]
    return [f.result() for f in futures]


@flow(name="financebench-build-graph")
def build_graph_flow(cfg: BenchConfig) -> dict[str, Any]:
    """Build the Ladybug Document Graph from the ingested Markdown files."""
    llm_arg = cfg.build_llm if cfg.build_llm_enabled else None
    logger.info(
        "Building Document Graph (db={}, llm={}, strategy={}, summaries={}, workers={})...",
        cfg.kg_db,
        llm_arg or "algorithmic",
        cfg.structure_strategy,
        cfg.generate_summaries,
        cfg.workers,
    )
    future = build_graph_task.submit(
        cfg.docs,
        markdown_dir=cfg.markdown_dir,
        kg_db=cfg.kg_db,
        force=cfg.build_force,
        build_llm=llm_arg,
        structure_strategy=cfg.structure_strategy,
        generate_summaries=cfg.generate_summaries,
        workers=cfg.workers,
        summary_min_tokens=cfg.summary_min_tokens,
        context_safety_ratio=cfg.context_safety_ratio,
        embeddings_id=cfg.embeddings,
        fts=cfg.fts,
        chunk_size_tokens=cfg.chunk_size_tokens,
    )
    return future.result()


@flow(name="financebench-run-questions")
def run_questions_flow(
    cfg: BenchConfig, questions: list[dict[str, Any]] | None = None
) -> list[dict[str, Any]]:
    """Run questions in parallel through the docgraph agent."""
    from financebench.bench.load_dataset import load_financebench, write_questions

    configure_bench_monitoring(cfg.monitoring, project_name=f"financebench-{cfg.profile_name}")

    if questions is None:
        df = load_financebench()
        questions = write_questions(df, cfg.docs)
        if cfg.limit:
            questions = questions[: cfg.limit]

    runs_path = Path(cfg.runs)
    runs_path.parent.mkdir(parents=True, exist_ok=True)

    existing_records: dict[str, dict[str, Any]] = {}
    if runs_path.exists():
        for line in runs_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    rec = json.loads(line)
                    if rec.get("financebench_id") and not rec.get("error"):
                        existing_records[rec["financebench_id"]] = rec
                except Exception:
                    pass

    pending_questions = [
        q for q in questions if q.get("financebench_id") not in existing_records
    ]

    if existing_records:
        logger.info(
            "Resuming: found {} completed question run(s); executing {} remaining question(s)",
            len(existing_records),
            len(pending_questions),
        )

    logger.info(
        "Running {} question(s) in parallel (agent={}, db={}, folder={}, embeddings={}, concurrency={})",
        len(pending_questions),
        cfg.agent_llm,
        cfg.kg_db,
        cfg.folder_id,
        cfg.embeddings or "off",
        cfg.question_concurrency,
    )

    if pending_questions:
        futures = [
            run_question_task.submit(
                q,
                llm=cfg.agent_llm,
                db_path=cfg.kg_db,
                folder_id=cfg.folder_id,
                profile_name=cfg.agent_profile,
                embeddings_id=cfg.embeddings,
                runs_path=str(runs_path),
                concurrency=cfg.question_concurrency,
            )
            for q in pending_questions
        ]
        new_records = [f.result() for f in futures]
        for r in new_records:
            if r.get("financebench_id"):
                existing_records[r["financebench_id"]] = r

    records = [
        existing_records[q["financebench_id"]]
        for q in questions
        if q.get("financebench_id") in existing_records
    ]
    with runs_path.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    logger.success("Completed {} question run(s) → {}", len(records), runs_path)
    return records


@flow(name="financebench-grade")
def grade_flow(
    cfg: BenchConfig, runs: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Grade question runs in parallel using LLM-as-judge."""
    from financebench.bench.grade import _summarize, generate_markdown_report

    runs_path = Path(cfg.runs)
    scores_path = Path(cfg.scores)
    summary_path = Path(cfg.scores_summary)

    if runs is None:
        if not runs_path.exists():
            logger.warning("Runs file {} does not exist. Skipping grade.", runs_path)
            return {}
        runs = [
            json.loads(line)
            for line in runs_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    scores_path.parent.mkdir(parents=True, exist_ok=True)
    existing_scores: dict[str, dict[str, Any]] = {}
    if scores_path.exists():
        for line in scores_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    sc = json.loads(line)
                    if sc.get("financebench_id") and not sc.get("error"):
                        existing_scores[sc["financebench_id"]] = sc
                except Exception:
                    pass

    pending_runs = [
        r for r in runs if r.get("financebench_id") not in existing_scores
    ]

    if existing_scores:
        logger.info(
            "Resuming: found {} completed score(s); grading {} remaining run(s)",
            len(existing_scores),
            len(pending_runs),
        )

    logger.info(
        "Grading {} run(s) in parallel with judge={} (concurrency={})",
        len(pending_runs),
        cfg.judge_llm,
        cfg.judge_concurrency,
    )

    if pending_runs:
        futures = [
            grade_run_task.submit(
                run,
                judge_llm=cfg.judge_llm,
                scores_path=str(scores_path),
                concurrency=cfg.judge_concurrency,
            )
            for run in pending_runs
        ]
        new_scores: list[dict[str, Any]] = []
        for f, run in zip(futures, pending_runs, strict=False):
            try:
                s = f.result()
                new_scores.append(s)
            except Exception as exc:
                logger.error("[{}] All grading retries failed: {}", run["financebench_id"], exc)
                fallback = {
                    "financebench_id": run["financebench_id"],
                    "doc_name": run["doc_name"],
                    "question_type": run.get("question_type"),
                    "question_reasoning": run.get("question_reasoning"),
                    "question": run["question"],
                    "gold_answer": run.get("gold_answer", ""),
                    "agent_answer": run.get("agent_answer", ""),
                    "n_tool_calls": run.get("n_tool_calls", 0),
                    "input_tokens": run.get("input_tokens", 0),
                    "output_tokens": run.get("output_tokens", 0),
                    "error": str(exc),
                    "judge_llm": cfg.judge_llm,
                    "correctness": "incorrect",
                    "numeric_match": None,
                    "groundedness": "ungrounded",
                    "rationale": f"Grading error: {exc}",
                }
                new_scores.append(fallback)
        for s in new_scores:
            if s.get("financebench_id"):
                existing_scores[s["financebench_id"]] = s

    scores = [
        existing_scores[r["financebench_id"]]
        for r in runs
        if r.get("financebench_id") in existing_scores
    ]
    with scores_path.open("w", encoding="utf-8") as fh:
        for s in scores:
            fh.write(json.dumps(s, ensure_ascii=False) + "\n")
    summary = _summarize(scores)

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    report_path = generate_markdown_report(
        scores,
        summary,
        profile_name=cfg.profile_name,
        agent_llm=cfg.agent_llm,
        judge_llm=cfg.judge_llm,
    )

    logger.success(
        "Grading complete → scores={}, summary={}, report={}",
        scores_path,
        summary,
        report_path,
    )
    return summary


# ---------------------------------------------------------------------------
# Master Pipeline Flow
# ---------------------------------------------------------------------------


@flow(name="financebench-pipeline")
def bench_flow(
    cfg: BenchConfig,
    *,
    steps: list[str] | None = None,
) -> dict[str, Any]:
    """Master Prefect flow orchestrating the end-to-end FinanceBench evaluation pipeline.

    Args:
        cfg: The loaded and resolved :class:`BenchConfig`.
        steps: Selected steps to execute (default: fetch, build, run, grade).
    """
    from genai_tk.utils.prefect_logging import install_loguru_prefect_bridge

    install_loguru_prefect_bridge()
    configure_bench_monitoring(cfg.monitoring, project_name=f"financebench-{cfg.profile_name}")
    load_env()
    ensure_dirs()

    active_steps = steps or ["fetch", "build", "run", "grade"]
    logger.info(
        "Executing FinanceBench pipeline (profile='{}', steps={}, docs={}, monitoring={})",
        cfg.profile_name,
        active_steps,
        len(cfg.docs),
        cfg.monitoring or "none",
    )

    results: dict[str, Any] = {}

    if "fetch" in active_steps:
        results["fetch"] = fetch_flow(cfg)

    if "build" in active_steps:
        results["markdownize"] = markdownize_flow(cfg)
        results["graph"] = build_graph_flow(cfg)

    if "run" in active_steps:
        results["runs"] = run_questions_flow(cfg)

    if "grade" in active_steps and cfg.judge_enabled:
        results["summary"] = grade_flow(cfg, runs=results.get("runs"))

    return results
