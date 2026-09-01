"""Config-driven bench orchestrator: fetch -> markdownize -> build -> run -> grade.

Reads a YAML config (default ``config/bench.yaml``) and runs the full FinanceBench
pipeline for the configured docs into the configured paths, so evaluating a new
set of filings is one command. Individual steps stay available via the other
``financebench.bench.*`` modules (fetch_pdf, load_dataset, build_graph,
run_questions, grade).

Usage:
```bash
uv run cli bench run
uv run cli bench run --profile deepseek_flash
uv run cli bench run --docs-file data/financebench/target_doc.txt
uv run cli bench run --docs A,B --skip fetch
uv run cli bench run --step run --limit 1
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
    """Flat bench config loaded from a named YAML profile; paths resolved to absolute."""

    profile_name: str = "deepseek_flash"
    description: str = ""
    markdownize_profile: str = "medium"
    pdfs_dir: str = "data/pdfs"
    markdown_dir: str = "data/markdown_multi"
    kg_db: str = "data/kg/financebench_multi.db"
    onedrive_markdown_dir: str = "~/OneDrive/prj/financebench/markdown"
    runs: str = "data/financebench/{profile}/runs.jsonl"
    scores: str = "data/financebench/{profile}/scores.jsonl"
    scores_summary: str = "data/financebench/{profile}/scores_summary.json"
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
    docs_file: str | None = None
    docs: list[str] = []
    limit: int | None = None
    agent_profile: str = "default"
    folder_id: str | None = None
    judge_enabled: bool = True

    def model_post_init(self, __context) -> None:
        """Expand ``~``, interpolate ``{profile}``, and resolve project-relative paths to absolute."""

        def _interpolate(p: str) -> str:
            return p.format(profile=self.profile_name)

        self.runs = _interpolate(self.runs)
        self.scores = _interpolate(self.scores)
        self.scores_summary = _interpolate(self.scores_summary)

        def _abs(p: str) -> str:
            path = Path(p).expanduser()
            return str(path if path.is_absolute() else PROJECT_ROOT / path)

        self.pdfs_dir = _abs(self.pdfs_dir)
        self.markdown_dir = _abs(self.markdown_dir)
        self.kg_db = _abs(self.kg_db)
        self.onedrive_markdown_dir = _abs(self.onedrive_markdown_dir)
        self.runs = _abs(self.runs)
        self.scores = _abs(self.scores)
        self.scores_summary = _abs(self.scores_summary)
        if self.docs_file:
            self.docs_file = _abs(self.docs_file)

    def resolve_docs(
        self,
        *,
        docs_override: list[str] | None = None,
        docs_file_override: str | Path | None = None,
    ) -> list[str]:
        """Resolve document names from explicit overrides, a docs file, or config list."""
        if docs_override:
            return docs_override
        file_to_read = docs_file_override or self.docs_file
        if file_to_read:
            p = Path(file_to_read).expanduser()
            if not p.is_absolute():
                p = PROJECT_ROOT / p
            if p.exists():
                text = p.read_text(encoding="utf-8").strip()
                items: list[str] = []
                for line in text.splitlines():
                    for item in line.split(","):
                        val = item.strip()
                        if val and val not in items:
                            items.append(val)
                if items:
                    return items
        return self.docs


def list_bench_profiles(config_path: Path | None = None) -> dict[str, dict]:
    """Return all available bench profiles in the config file."""
    cfg_file = config_path or (PROJECT_ROOT / "config" / "bench.yaml")
    if not cfg_file.exists():
        return {}
    raw = yaml.safe_load(cfg_file.read_text(encoding="utf-8")) or {}
    profiles = raw.get("bench_profiles", {})
    if not profiles and "paths" in raw:
        return {"default": raw}
    return profiles


def load_bench_profile(
    profile_name: str | None = None,
    config_path: Path | None = None,
) -> BenchConfig:
    """Load a named bench profile into a :class:`BenchConfig`."""
    cfg_file = config_path or (PROJECT_ROOT / "config" / "bench.yaml")
    if not cfg_file.exists():
        raise FileNotFoundError(f"Config file not found: {cfg_file}")
    raw = yaml.safe_load(cfg_file.read_text(encoding="utf-8")) or {}
    profiles = raw.get("bench_profiles", {})
    default_name = raw.get("default_profile", "deepseek_flash")

    selected_name = profile_name or default_name
    if not profiles and "paths" in raw:
        prof_data = raw
        selected_name = profile_name or "default"
    elif selected_name in profiles:
        prof_data = profiles[selected_name] or {}
    else:
        available = list(profiles.keys())
        raise KeyError(
            f"Bench profile '{selected_name}' not found in {cfg_file}. Available: {available}"
        )

    paths = prof_data.get("paths", {}) or {}
    llms = prof_data.get("llms", {}) or {}
    build = prof_data.get("build", {}) or {}
    questions = prof_data.get("questions", {}) or {}
    agent = prof_data.get("agent", {}) or {}
    judge = prof_data.get("judge", {}) or {}

    cfg = BenchConfig(
        profile_name=selected_name,
        description=prof_data.get("description", ""),
        markdownize_profile=prof_data.get("markdownize_profile", "medium"),
        pdfs_dir=paths.get("pdfs_dir", "data/pdfs"),
        markdown_dir=paths.get("markdown_dir", "data/markdown_multi"),
        kg_db=paths.get("kg_db", "data/kg/financebench_multi.db"),
        onedrive_markdown_dir=paths.get(
            "onedrive_markdown_dir", "~/OneDrive/prj/financebench/markdown"
        ),
        runs=paths.get("runs", "data/financebench/{profile}/runs.jsonl"),
        scores=paths.get("scores", "data/financebench/{profile}/scores.jsonl"),
        scores_summary=paths.get(
            "scores_summary", "data/financebench/{profile}/scores_summary.json"
        ),
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
        docs_file=questions.get("docs_file"),
        docs=list(questions.get("docs", []) or []),
        limit=questions.get("limit"),
        agent_profile=agent.get("profile", "default"),
        folder_id=agent.get("folder_id"),
        judge_enabled=bool(judge.get("enabled", True)),
    )
    cfg.docs = cfg.resolve_docs()
    return cfg


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
                markdownize_profile=cfg.markdownize_profile,
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
    if not runs_path.exists():
        logger.warning("Runs file does not exist: {}. Skipping grade.", runs_path)
        return
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
    summary_path = Path(cfg.scores_summary)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"scores={scores_path}")
    print(f"summary={json.dumps(summary)}")


def run_bench(
    cfg: BenchConfig,
    *,
    steps: list[str] | None = None,
    skip: list[str] | None = None,
    step: str | None = None,
) -> None:
    """Execute the benchmark pipeline stages for *cfg*."""
    load_env()
    ensure_dirs()

    if not cfg.docs:
        raise SystemExit(
            "No docs configured (set questions.docs or questions.docs_file in config, or pass --docs/--docs-file)."
        )

    if step:
        selected_steps = [step]
    elif steps:
        selected_steps = steps
    else:
        skip_set = set(skip or [])
        if not cfg.judge_enabled:
            skip_set.add("grade")
        selected_steps = [s for s in ALL_STEPS if s not in skip_set]

    logger.info(
        "Bench profile '{}' | Steps: {} | docs: {}",
        cfg.profile_name,
        selected_steps,
        cfg.docs,
    )
    for s in selected_steps:
        if s == "fetch":
            _step_fetch(cfg)
        elif s == "build":
            _step_build(cfg)
        elif s == "run":
            _step_run(cfg)
        elif s == "grade":
            _step_grade(cfg)


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
        "-p",
        "--profile",
        default=None,
        help="Named bench profile to run (defaults to default_profile in config).",
    )
    parser.add_argument(
        "-f",
        "--docs-file",
        default=None,
        help="Path to file containing document names.",
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
    parser.add_argument(
        "--judge",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Enable or disable LLM-as-judge evaluation step.",
    )
    args = parser.parse_args(argv)

    cfg = load_bench_profile(profile_name=args.profile, config_path=Path(args.config))
    if args.docs:
        cfg.docs = [d.strip() for d in args.docs.split(",") if d.strip()]
    elif args.docs_file:
        cfg.docs = cfg.resolve_docs(docs_file_override=args.docs_file)
    if args.limit is not None:
        cfg.limit = args.limit
    if args.judge is not None:
        cfg.judge_enabled = args.judge

    run_bench(cfg, skip=args.skip, step=args.step)
    return 0


if __name__ == "__main__":
    sys.exit(main())
