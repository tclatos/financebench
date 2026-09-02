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
import sys
from pathlib import Path

from loguru import logger
from omegaconf import OmegaConf
from pydantic import BaseModel, Field

from genai_tk.config_mgmt.config_mngr import global_config
from financebench.bench._env import PROJECT_ROOT, ensure_dirs, load_env

ALL_STEPS = ("fetch", "build", "run", "grade")


class BenchConfig(BaseModel):
    """Flat bench config loaded from a named YAML profile; paths resolved to absolute."""

    profile_name: str = "mistral_glm"
    description: str = ""
    markdownize_profile: str = "medium"
    pdfs_dir: str = "data/pdfs"
    markdown_dir: str = "data/markdown_multi"
    kg_db: str = "data/kg/financebench_multi.db"
    onedrive_markdown_dir: str = "~/OneDrive/prj/financebench/markdown"
    runs: str = "data/financebench/{profile}/runs.jsonl"
    scores: str = "data/financebench/{profile}/scores.jsonl"
    scores_summary: str = "data/financebench/{profile}/scores_summary.json"
    agent_llm: str = "glm_5.2@openrouter"
    build_llm: str = "deepseek-v4-flash-0731@openrouter"
    judge_llm: str = "DeepSeek-V4-Pro-0813@openrouter"
    skip_ocr: bool = False
    build_force: bool = True
    build_llm_enabled: bool = True
    structure_strategy: str = "auto"
    generate_summaries: bool = True
    workers: int = 4
    summary_min_tokens: int = 800
    context_safety_ratio: float = 0.9
    embeddings: str | None = None
    fts: bool = True
    chunk_size_tokens: int = 1500
    pathspecs: list[str] = Field(default_factory=list)
    docs: list[str] = Field(default_factory=list)
    limit: int | None = None
    agent_profile: str = "default"
    folder_id: str | None = None
    judge_enabled: bool = True
    monitoring: str | list[str] | None = None
    question_concurrency: int = 10
    judge_concurrency: int = 5

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

    def resolve_docs(
        self,
        *,
        docs_override: list[str] | None = None,
        pathspecs_override: list[str] | None = None,
    ) -> list[str]:
        """Resolve document names from explicit overrides, pathspecs against available dataset docs, or config."""
        if docs_override:
            return docs_override

        from financebench.bench.load_dataset import load_financebench, match_docs_by_pathspecs

        active_pathspecs = pathspecs_override or self.pathspecs
        if active_pathspecs:
            try:
                df = load_financebench()
                all_docs = sorted(df["doc_name"].dropna().unique().tolist())
                matched = match_docs_by_pathspecs(all_docs, active_pathspecs)
                if matched:
                    return matched
            except Exception as exc:
                logger.warning("Could not filter dataset by pathspecs ({}): {}", active_pathspecs, exc)

        return self.docs


def _get_raw_bench_conf(config_path: Path | None = None) -> dict:
    """Load bench.yaml with OmegaConf interpolation."""
    cfg_file = config_path or (PROJECT_ROOT / "config" / "bench.yaml")
    if not cfg_file.exists():
        return {}
    try:
        # Use genai-tk global_config if available so ${paths.*} interpolate
        root_conf = global_config().root
        loaded = OmegaConf.load(cfg_file)
        merged = OmegaConf.merge(root_conf, loaded)
        return OmegaConf.to_container(merged, resolve=True) or {}
    except Exception:
        loaded = OmegaConf.load(cfg_file)
        return OmegaConf.to_container(loaded, resolve=True) or {}


def list_bench_profiles(config_path: Path | None = None) -> dict[str, dict]:
    """Return all available bench profiles in the config file."""
    raw = _get_raw_bench_conf(config_path)
    profiles = raw.get("bench_profiles", {})
    return profiles


def load_bench_profile(
    profile_name: str | None = None,
    config_path: Path | None = None,
) -> BenchConfig:
    """Load a named bench profile into a :class:`BenchConfig`."""
    cfg_file = config_path or (PROJECT_ROOT / "config" / "bench.yaml")
    if not cfg_file.exists():
        raise FileNotFoundError(f"Config file not found: {cfg_file}")

    raw = _get_raw_bench_conf(config_path)
    profiles = raw.get("bench_profiles", {})
    default_name = raw.get("default_profile", "mistral_glm")

    selected_name = profile_name or default_name
    if selected_name in profiles:
        prof_data = profiles[selected_name] or {}
    else:
        available = list(profiles.keys())
        raise KeyError(
            f"Bench profile '{selected_name}' not found in {cfg_file}. Available: {available}"
        )

    # Top-level paths with per-profile override support
    top_paths = raw.get("paths", {}) or {}
    prof_paths = prof_data.get("paths", {}) or {}
    paths = {**top_paths, **prof_paths}

    llms = prof_data.get("llms", {}) or {}
    build = prof_data.get("build", {}) or {}
    files = prof_data.get("files", {}) or prof_data.get("questions", {}) or {}
    agent = prof_data.get("agent", {}) or {}
    judge = prof_data.get("judge", {}) or {}

    pathspecs = files.get("pathspecs", [])
    if isinstance(pathspecs, str):
        pathspecs = [pathspecs]

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
        agent_llm=llms.get("agent", "glm_5.2@openrouter"),
        build_llm=llms.get("build", "deepseek-v4-flash-0731@openrouter"),
        judge_llm=llms.get("judge", "DeepSeek-V4-Pro-0813@openrouter"),
        skip_ocr=bool(build.get("skip_ocr", False)),
        build_force=bool(build.get("force", True)),
        build_llm_enabled=bool(build.get("llm", True)),
        structure_strategy=str(build.get("structure_strategy", "auto")),
        generate_summaries=bool(build.get("summaries", build.get("generate_summaries", build.get("llm", True)))),
        workers=int(build.get("workers", 4)),
        summary_min_tokens=int(build.get("summary_min_tokens", 800)),
        context_safety_ratio=float(build.get("context_safety_ratio", 0.9)),
        embeddings=build.get("embeddings"),
        fts=bool(build.get("fts", True)),
        chunk_size_tokens=int(build.get("chunk_size_tokens", 1500)),
        pathspecs=list(pathspecs),
        docs=list(files.get("docs", []) or []),
        limit=files.get("limit"),
        agent_profile=agent.get("profile", "default"),
        folder_id=agent.get("folder_id"),
        judge_enabled=bool(judge.get("enabled", True)),
        monitoring=prof_data.get("monitoring", None),
        question_concurrency=int(agent.get("concurrency", 10)),
        judge_concurrency=int(judge.get("concurrency", 5)),
    )
    cfg.docs = cfg.resolve_docs()
    return cfg


def configure_bench_monitoring(
    monitoring: str | list[str] | None, project_name: str = "financebench"
) -> None:
    """Configure or disable tracing monitoring (LangSmith/LangChain, LangFuse, local, etc.)."""
    import os
    from genai_tk.utils.tracing import reset_monitoring, setup_monitoring

    if not monitoring or str(monitoring).lower() in ("none", "null", "off", "false"):
        os.environ["LANGSMITH_TRACING"] = "false"
        os.environ.pop("LANGCHAIN_TRACING_V2", None)
        reset_monitoring()
        return

    backends = [monitoring] if isinstance(monitoring, str) else list(monitoring)
    normalized_backends: list[str] = []
    for b in backends:
        b_str = str(b).strip().lower()
        if b_str in ("langchain", "langsmith"):
            normalized_backends.append("langsmith")
        elif b_str in ("langfuse", "local", "otel"):
            normalized_backends.append(b_str)

    os.environ["LANGSMITH_PROJECT"] = project_name
    if "langsmith" in normalized_backends:
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
    else:
        os.environ["LANGSMITH_TRACING"] = "false"
        os.environ.pop("LANGCHAIN_TRACING_V2", None)

    try:
        root = global_config().root
        if "monitoring" in root:
            root.monitoring.backends = normalized_backends
            root.monitoring.project = project_name
    except Exception:
        pass

    reset_monitoring()
    setup_monitoring()


def _step_fetch(cfg: BenchConfig) -> None:
    """Download each configured doc's PDF using Prefect fetch_flow."""
    from financebench.bench.flows import fetch_flow

    fetch_flow(cfg)


def _step_build(cfg: BenchConfig) -> None:
    """OCR/markdownize each doc, copy it in, then build the graph once using Prefect flows."""
    from financebench.bench.flows import build_graph_flow, markdownize_flow

    markdownize_flow(cfg)
    build_graph_flow(cfg)


def _step_run(cfg: BenchConfig) -> None:
    """Write the multi-doc questions, then run the agent over them using Prefect run_questions_flow."""
    from financebench.bench.flows import run_questions_flow

    run_questions_flow(cfg)
    print(f"runs={cfg.runs}")


def _step_grade(cfg: BenchConfig) -> None:
    """Grade the runs and write the scores + summary using Prefect grade_flow."""
    from financebench.bench.flows import grade_flow

    grade_flow(cfg)
    print(f"scores={cfg.scores}")
    print(f"summary={cfg.scores_summary}")


def run_bench(
    cfg: BenchConfig,
    *,
    steps: list[str] | None = None,
    skip: list[str] | None = None,
    step: str | None = None,
) -> None:
    """Execute the benchmark pipeline stages for *cfg* via Prefect orchestration."""
    from financebench.bench.flows import bench_flow

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
    bench_flow(cfg, steps=selected_steps)


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
