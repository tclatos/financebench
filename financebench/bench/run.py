"""Config-driven bench orchestrator: fetch -> markdownize -> build -> run -> grade.

Reads a YAML config (default ``config/bench.yaml``) and runs the full FinanceBench
pipeline for the configured docs into the configured paths, so evaluating a new
set of filings is one command. Individual steps stay available via the other
``financebench.bench.*`` modules (fetch_pdf, load_dataset, build_graph,
run_questions, grade).

Usage:
```bash
uv run python -m financebench.bench.run
uv run python -m financebench.bench.run --config config/bench.yaml
uv run python -m financebench.bench.run --docs A,B --skip fetch
uv run python -m financebench.bench.run --step run --limit 1
```
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import yaml
from loguru import logger
from pydantic import BaseModel

from financebench.bench._env import PROJECT_ROOT, ensure_dirs, load_env

ALL_STEPS = ("fetch", "build", "run", "grade")


class BenchConfig(BaseModel):
    """Flat bench config loaded from YAML; paths resolved to absolute."""

    pdfs_dir: str = "data/pdfs"
    markdown_dir: str = "data/markdown_multi"
    kg_db: str = "data/kg/financebench_multi.db"
    onedrive_markdown_dir: str = "~/OneDrive/prj/financebench/markdown"
    runs: str = "data/financebench/runs.jsonl"
    scores: str = "data/financebench/scores.jsonl"
    agent_llm: str = "deepseek_v4flash@openrouter"
    build_llm: str = "deepseek_v4flash@openrouter"
    judge_llm: str = "deepseek_v4flash@openrouter"
    skip_ocr: bool = False
    build_force: bool = True
    build_llm_enabled: bool = True
    workers: int = 4
    summary_min_tokens: int = 800
    context_safety_ratio: float = 0.9
    embeddings: str | None = None
    fts: bool = True
    chunk_size_tokens: int = 1500
    docs: list[str] = []
    limit: int | None = None
    agent_profile: str = "docgraph"
    folder_id: str | None = None

    def model_post_init(self, __context) -> None:
        """Expand ``~`` and resolve project-relative paths to absolute."""

        def _abs(p: str) -> str:
            path = Path(p).expanduser()
            return str(path if path.is_absolute() else PROJECT_ROOT / path)

        self.pdfs_dir = _abs(self.pdfs_dir)
        self.markdown_dir = _abs(self.markdown_dir)
        self.kg_db = _abs(self.kg_db)
        self.onedrive_markdown_dir = _abs(self.onedrive_markdown_dir)
        self.runs = _abs(self.runs)
        self.scores = _abs(self.scores)


def _load_config(path: Path) -> BenchConfig:
    """Load the nested bench YAML into a flat :class:`BenchConfig`."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    paths = raw.get("paths", {}) or {}
    llms = raw.get("llms", {}) or {}
    build = raw.get("build", {}) or {}
    questions = raw.get("questions", {}) or {}
    agent = raw.get("agent", {}) or {}
    return BenchConfig(
        pdfs_dir=paths.get("pdfs_dir", "data/pdfs"),
        markdown_dir=paths.get("markdown_dir", "data/markdown_multi"),
        kg_db=paths.get("kg_db", "data/kg/financebench_multi.db"),
        onedrive_markdown_dir=paths.get(
            "onedrive_markdown_dir", "~/OneDrive/prj/financebench/markdown"
        ),
        runs=paths.get("runs", "data/financebench/runs.jsonl"),
        scores=paths.get("scores", "data/financebench/scores.jsonl"),
        agent_llm=llms.get("agent", "deepseek_v4flash@openrouter"),
        build_llm=llms.get("build", "deepseek_v4flash@openrouter"),
        judge_llm=llms.get("judge", "deepseek_v4flash@openrouter"),
        skip_ocr=bool(build.get("skip_ocr", False)),
        build_force=bool(build.get("force", True)),
        build_llm_enabled=bool(build.get("llm", True)),
        workers=int(build.get("workers", 4)),
        summary_min_tokens=int(build.get("summary_min_tokens", 800)),
        context_safety_ratio=float(build.get("context_safety_ratio", 0.9)),
        embeddings=build.get("embeddings"),
        fts=bool(build.get("fts", True)),
        chunk_size_tokens=int(build.get("chunk_size_tokens", 1500)),
        docs=list(questions.get("docs", []) or []),
        limit=questions.get("limit"),
        agent_profile=agent.get("profile", "docgraph"),
        folder_id=agent.get("folder_id"),
    )


def _step_fetch(cfg: BenchConfig) -> None:
    """Download each configured doc's PDF."""
    from financebench.bench.fetch_pdf import fetch_pdf

    for doc in cfg.docs:
        fetch_pdf(doc, pdfs_dir=Path(cfg.pdfs_dir))


def _step_build(cfg: BenchConfig) -> None:
    """OCR/markdownize each doc, copy it in, then build the graph once."""
    from financebench.bench.build_graph import (
        MD_FILENAME_SUFFIX,
        build_document_graph,
        copy_markdown_to_project,
        markdownize_target,
    )

    pdfs = Path(cfg.pdfs_dir)
    onedrive = Path(cfg.onedrive_markdown_dir)
    md_dir = Path(cfg.markdown_dir)
    md_dir.mkdir(parents=True, exist_ok=True)
    for doc in cfg.docs:
        if cfg.skip_ocr:
            md_path = onedrive / f"{doc}{MD_FILENAME_SUFFIX}"
            if not md_path.exists():
                raise SystemExit(
                    f"--skip-ocr set but markdown not found: {md_path}; "
                    "run without --skip fetch first."
                )
        else:
            md_path = markdownize_target(
                doc,
                force=cfg.build_force,
                pdfs_dir=pdfs,
                onedrive_markdown_dir=onedrive,
            )
        copy_markdown_to_project(md_path, markdown_dir=md_dir)

    llm_arg = cfg.build_llm if cfg.build_llm_enabled else None
    Path(cfg.kg_db).parent.mkdir(parents=True, exist_ok=True)
    result = build_document_graph(
        cfg.docs[0] if cfg.docs else "",
        force=cfg.build_force,
        llm=llm_arg,
        workers=cfg.workers,
        summary_min_tokens=cfg.summary_min_tokens,
        context_safety_ratio=cfg.context_safety_ratio,
        markdown_dir=md_dir,
        kg_db=Path(cfg.kg_db),
        embeddings_id=cfg.embeddings,
        fts=cfg.fts,
        chunk_size_tokens=cfg.chunk_size_tokens,
    )
    logger.success(
        "Graph built: {} sections, {} summarized, {} doc(s) ({} degraded)",
        result.get("sections_created"),
        result.get("sections_summarized"),
        result.get("documents_processed"),
        result.get("files_degraded"),
    )


def _step_run(cfg: BenchConfig) -> None:
    """Write the multi-doc questions, then run the agent over them."""
    from financebench.bench.load_dataset import load_financebench, write_questions
    from financebench.bench.run_questions import _run_all

    df = load_financebench()
    questions = write_questions(df, cfg.docs)
    if cfg.limit:
        questions = questions[: cfg.limit]

    runs_path = Path(cfg.runs)
    runs_path.parent.mkdir(parents=True, exist_ok=True)
    runs_path.write_text("", encoding="utf-8")
    logger.info(
        "Running {} question(s) over {} (agent={}, db={}, folder={})",
        len(questions),
        cfg.docs,
        cfg.agent_llm,
        cfg.kg_db,
        cfg.folder_id,
    )
    asyncio.run(
        _run_all(
            questions,
            cfg.agent_llm,
            cfg.kg_db,
            folder_id=cfg.folder_id,
            profile_name=cfg.agent_profile,
            runs_path=runs_path,
            embeddings_id=cfg.embeddings,
        )
    )
    print(f"runs={runs_path}")


def _step_grade(cfg: BenchConfig) -> None:
    """Grade the runs and write the scores + summary."""
    from financebench.bench.grade import _grade_all, _summarize

    runs_path = Path(cfg.runs)
    scores_path = Path(cfg.scores)
    runs = [
        json.loads(line)
        for line in runs_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    scores_path.parent.mkdir(parents=True, exist_ok=True)
    scores_path.write_text("", encoding="utf-8")
    logger.info("Grading {} run(s) with judge={}", len(runs), cfg.judge_llm)
    scores = asyncio.run(_grade_all(runs, cfg.judge_llm, scores_path=scores_path))
    summary = _summarize(scores)
    summary_path = scores_path.parent / "scores_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"scores={scores_path}")
    print(f"summary={json.dumps(summary)}")


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run the FinanceBench bench pipeline from a YAML config."
    )
    parser.add_argument(
        "--config",
        default=str(PROJECT_ROOT / "config" / "bench.yaml"),
        help="Path to the bench YAML config.",
    )
    parser.add_argument(
        "--docs",
        default=None,
        help="Comma-separated doc_names overriding config questions.docs.",
    )
    parser.add_argument(
        "--skip",
        action="append",
        default=[],
        choices=ALL_STEPS,
        help="Skip a step (repeatable).",
    )
    parser.add_argument(
        "--step",
        default=None,
        choices=ALL_STEPS,
        help="Run only this one step (overrides --skip).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Run only the first N questions.",
    )
    args = parser.parse_args(argv)

    load_env()
    ensure_dirs()
    cfg = _load_config(Path(args.config))
    if args.docs:
        cfg.docs = [d.strip() for d in args.docs.split(",") if d.strip()]
    if args.limit is not None:
        cfg.limit = args.limit
    if not cfg.docs:
        raise SystemExit(
            "No docs configured (set questions.docs in the config or pass --docs)."
        )

    steps = [args.step] if args.step else [s for s in ALL_STEPS if s not in args.skip]
    logger.info("Steps: {} | docs: {}", steps, cfg.docs)
    for step in steps:
        if step == "fetch":
            _step_fetch(cfg)
        elif step == "build":
            _step_build(cfg)
        elif step == "run":
            _step_run(cfg)
        elif step == "grade":
            _step_grade(cfg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
