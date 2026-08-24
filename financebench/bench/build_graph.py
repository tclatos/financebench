"""Build the financebench Document Graph for the target document.

Pipeline:
1. OCR the target PDF with Mistral OCR (``mistral-ocr-latest`` batch API) and
   write ``<doc>_pdf.md`` to the OneDrive mirror (persistent backup). Falls back
   to ``markitdown`` if the Mistral batch job fails, matching markdownize_flow.
2. Copy that Markdown into ``data/markdown/`` so Document node paths are
   project-relative (the OneDrive copy is just the saved backup).
3. Build the ``Folder → Document → MarkdownSection`` graph into the Ladybug
   (Kuzu) database at ``data/kg/financebench_tree.db``.

With ``--llm``, the build uses the LLM-enhanced path: a cheap flash model
extracts each document's outline (TOC + per-section descriptions and summaries
+ a document description/summary) in one call, cached by ``markdown_hash``;
section nodes then carry those descriptions/summaries and the Document node
carries the document-level description/summary. Without ``--llm`` the fast
algorithmic heading parser is used (no summaries).

The underlying OCR processor and graph ingestor are called directly (not via the
Prefect ``@flow`` wrappers) so the bench harness is deterministic and does not
depend on a Prefect server.

Usage:
```bash
uv run python -m financebench.bench.build_graph
uv run python -m financebench.bench.build_graph --doc AMD_2022_10K --force
uv run python -m financebench.bench.build_graph --skip-ocr --force --llm
```
"""

from __future__ import annotations

import argparse
import asyncio
import shutil
import sys
from pathlib import Path

from loguru import logger

from financebench.bench._env import (
    DEFAULT_BUILD_LLM,
    KG_DB,
    MARKDOWN_DIR,
    ONEDRIVE_MARKDOWN_DIR,
    PDFS_DIR,
    ensure_dirs,
    load_env,
)
from financebench.bench.fetch_pdf import resolve_doc_name

MD_FILENAME_SUFFIX = "_pdf.md"


def _resolve_build_llm(llm: str | None) -> str | None:
    """Resolve a ``--llm`` value to a concrete ``name@provider`` id, or None.

    A value containing ``@`` is a literal id; any other non-empty value is a
    config tag resolved via ``kg_build.llms.<tag>`` (falling back to the
    ``kg_build.llms.default`` tag). ``None`` keeps the algorithmic-only path.
    Mirrors ``document_graph_flow._resolve_build_llm`` without importing the
    Prefect-decorated flow module (the bench harness bypasses Prefect).
    """
    if llm is None:
        return None
    if "@" in llm:
        return llm
    from genai_tk.config_mgmt.config_mngr import global_config

    cfg = global_config()
    resolved = cfg.get_str(f"kg_build.llms.{llm}", default=None)
    if resolved:
        return resolved
    return cfg.get_str("kg_build.llms.default", default=None)


def _ocr_pdf(pdf_path: Path) -> str:
    """Return the Markdown text for *pdf_path* via Mistral OCR (markitdown fallback)."""
    from genai_tk.workflow.markdownize.converters import _markitdown_text
    from genai_tk.workflow.markdownize.mistral import MistralOCRBatchProcessor

    try:
        texts = asyncio.run(MistralOCRBatchProcessor().process_batch([pdf_path]))
        text = texts.get(str(pdf_path))
        if text:
            logger.success("Mistral OCR completed for {}", pdf_path.name)
            return text
        logger.warning(
            "Mistral OCR returned no text for {}; using markitdown fallback.",
            pdf_path.name,
        )
    except Exception as exc:  # noqa: BLE101
        logger.warning(
            "Mistral batch OCR failed ({}); falling back to markitdown for {}.",
            exc,
            pdf_path.name,
        )
    return _markitdown_text(pdf_path)


def markdownize_target(doc_name: str, *, force: bool) -> Path:
    """OCR the target PDF to the OneDrive mirror and return the produced .md path."""
    from genai_tk.workflow.markdownize.routing import _write_markdown

    ensure_dirs()
    load_env()
    pdf_path = PDFS_DIR / f"{doc_name}.pdf"
    if not pdf_path.exists():
        raise SystemExit(f"PDF not found: {pdf_path} — run fetch_pdf first.")

    ONEDRIVE_MARKDOWN_DIR.mkdir(parents=True, exist_ok=True)
    md_name = f"{doc_name}{MD_FILENAME_SUFFIX}"
    md_path = ONEDRIVE_MARKDOWN_DIR / md_name

    if md_path.exists() and not force:
        logger.info("Markdown already present (use --force to re-OCR): {}", md_path)
        return md_path

    logger.info("OCR-ing {} via Mistral OCR → {}", pdf_path, md_path)
    text = _ocr_pdf(pdf_path)
    _write_markdown(md_path, pdf_path, text)
    logger.success(
        "OCR markdown written: {} ({} bytes)", md_path, md_path.stat().st_size
    )
    return md_path


def copy_markdown_to_project(md_path: Path) -> Path:
    """Copy the OneDrive markdown into ``data/markdown/`` for graph ingestion."""
    ensure_dirs()
    dest = MARKDOWN_DIR / md_path.name
    shutil.copy2(md_path, dest)
    logger.info("Copied {} → {}", md_path, dest)
    return dest


def build_document_graph(
    doc_name: str,
    *,
    force: bool,
    llm: str | None = None,
    llm_max_tokens: int | None = None,
    summary_min_tokens: int = 800,
    workers: int = 4,
    context_safety_ratio: float = 0.9,
) -> dict:
    """Build (or rebuild) the Document Graph from ``data/markdown/`` into the DB.

    With *llm* resolved to a concrete id, the LLM-enhanced build path runs: a
    flash model extracts each document's outline (TOC + descriptions +
    summaries) in one call, cached by ``markdown_hash``; sections then carry
    those descriptions/summaries and the Document carries the document-level
    description/summary. Without *llm* the fast algorithmic path is used.
    """
    from genai_graph.kg.backend import KuzuBackend
    from genai_graph.kg.document_graph.ingest import (
        drop_document_graph,
        ingest_document_graph,
    )
    from genai_graph.kg.document_graph.outline_extract import OutlineConfig
    from genai_graph.kg.factories.document_graph_factory import DocumentGraphFactory

    ensure_dirs()
    md_files = list(MARKDOWN_DIR.glob("*.md"))
    if not md_files:
        raise SystemExit(
            f"No markdown found in {MARKDOWN_DIR} — run markdownize first."
        )

    resolved_llm = _resolve_build_llm(llm)
    outline_config: OutlineConfig | None = None
    if resolved_llm is not None:
        cache_root = str(KG_DB.with_suffix("")) + "_outlines"
        outline_config = OutlineConfig(
            llm=resolved_llm,
            llm_max_tokens=llm_max_tokens,
            summary_min_tokens=summary_min_tokens,
            cache_root=cache_root,
            context_safety_ratio=context_safety_ratio,
        )

    logger.info(
        "Building Document Graph: sources={} db={} force={} llm={}",
        MARKDOWN_DIR,
        KG_DB,
        force,
        resolved_llm or "algo",
    )
    backend = KuzuBackend()
    backend.connect(str(KG_DB))
    try:
        if force:
            logger.info("Dropping existing Document Graph tables at {}", KG_DB)
            drop_document_graph(backend)
        factory = DocumentGraphFactory(
            sources=[str(MARKDOWN_DIR)],
            recursive=True,
            outline_config=outline_config,
        )
        # The pre-pass warms the content-addressed outline cache in parallel (no DB),
        # so the subsequent ingest reads each outline from disk without an LLM call.
        files_degraded = 0
        outline_warnings: list[str] = []
        if outline_config is not None:
            stats = factory.extract_outlines(workers=workers)
            files_degraded = stats.degraded_count
            outline_warnings = list(stats.warnings)
            logger.info(
                "Outline pre-pass: {} file(s), {} degraded, {} LLM call(s)",
                stats.total_files,
                files_degraded,
                stats.llm_calls,
            )
        result = ingest_document_graph(backend, factory, force=force)
    finally:
        backend.close()

    logger.success(
        "Graph built: {} processed ({} skipped), {} failed, {} sections, "
        "{} summarized, {} relationships, {} degraded",
        result.documents_processed,
        result.documents_skipped,
        result.documents_failed,
        result.sections_created,
        result.sections_summarized,
        result.relationships_created,
        files_degraded,
    )
    out = result.model_dump()
    out["files_degraded"] = files_degraded
    out["outline_llm"] = resolved_llm
    out["warnings"] = [*outline_warnings, *result.warnings]
    return out


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="OCR the target PDF and build the Document Graph."
    )
    parser.add_argument(
        "--doc", default=None, help="doc_name (default: selected target)."
    )
    parser.add_argument(
        "--force", action="store_true", help="Re-OCR and rebuild the graph."
    )
    parser.add_argument(
        "--skip-ocr",
        action="store_true",
        help="Skip markdownize; only copy markdown + build graph.",
    )
    parser.add_argument(
        "--llm",
        nargs="?",
        const=DEFAULT_BUILD_LLM,
        default=None,
        help=(
            "Use the LLM-enhanced build: a flash model extracts each document's "
            "outline (TOC + descriptions + summaries). Pass a literal `name@provider` "
            "id, a `kg_build.llms.<tag>` tag, or omit the value to use "
            f"{DEFAULT_BUILD_LLM}. Without this flag the algorithmic path is used."
        ),
    )
    parser.add_argument(
        "--llm-max-tokens",
        type=int,
        default=None,
        help="Explicit max output tokens for the outline call (reasoning models).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Parallelism for the outline pre-pass (default: 4).",
    )
    parser.add_argument(
        "--summary-min-tokens",
        type=int,
        default=800,
        help="Token heuristic for what counts as a 'substantial' section (default: 800).",
    )
    parser.add_argument(
        "--context-safety-ratio",
        type=float,
        default=0.9,
        help="Degrade to algo parsing above this fraction of the context window (default: 0.9).",
    )
    args = parser.parse_args(argv)

    load_env()
    doc_name = resolve_doc_name(args.doc)

    if not args.skip_ocr:
        md_path = markdownize_target(doc_name, force=args.force)
    else:
        md_path = ONEDRIVE_MARKDOWN_DIR / f"{doc_name}{MD_FILENAME_SUFFIX}"
        if not md_path.exists():
            raise SystemExit(
                f"Markdown not found at {md_path}; run without --skip-ocr first."
            )

    copy_markdown_to_project(md_path)
    result = build_document_graph(
        doc_name,
        force=args.force,
        llm=args.llm,
        llm_max_tokens=args.llm_max_tokens,
        summary_min_tokens=args.summary_min_tokens,
        workers=args.workers,
        context_safety_ratio=args.context_safety_ratio,
    )

    print(f"doc={doc_name}")
    print(f"db={KG_DB}")
    print(f"outline_llm={result.get('outline_llm')}")
    print(f"sections_created={result.get('sections_created')}")
    print(f"sections_summarized={result.get('sections_summarized')}")
    print(f"documents_processed={result.get('documents_processed')}")
    print(f"files_degraded={result.get('files_degraded')}")
    if result.get("warnings"):
        print("warnings:")
        for w in result["warnings"]:
            print(f"  - {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
