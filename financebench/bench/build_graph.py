"""Build the financebench Document Graph for the target document.

Pipeline:
1. OCR the target PDF with Mistral OCR (``mistral-ocr-latest`` batch API) and
   write ``<doc>_pdf.md`` to the OneDrive mirror (persistent backup). Falls back
   to ``markitdown`` if the Mistral batch job fails, matching markdownize_flow.
2. Copy that Markdown into ``data/markdown/`` so Document node paths are
   project-relative (the OneDrive copy is just the saved backup).
3. Build the ``Folder → Document → MarkdownSection`` graph into the Ladybug
   (Kuzu) database at ``data/kg/financebench_tree.db``.

The underlying OCR processor and graph ingestor are called directly (not via the
Prefect ``@flow`` wrappers) so the bench harness is deterministic and does not
depend on a Prefect server.

Usage:
```bash
uv run python -m financebench.bench.build_graph
uv run python -m financebench.bench.build_graph --doc AMD_2022_10K --force
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
    KG_DB,
    MARKDOWN_DIR,
    ONEDRIVE_MARKDOWN_DIR,
    PDFS_DIR,
    ensure_dirs,
    load_env,
)
from financebench.bench.fetch_pdf import resolve_doc_name

MD_FILENAME_SUFFIX = "_pdf.md"


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


def build_document_graph(doc_name: str, *, force: bool) -> dict:
    """Build (or rebuild) the Document Graph from ``data/markdown/`` into the DB."""
    from genai_graph.kg.backend import KuzuBackend
    from genai_graph.kg.document_graph.ingest import (
        drop_document_graph,
        ingest_document_graph,
    )
    from genai_graph.kg.factories.document_graph_factory import DocumentGraphFactory

    ensure_dirs()
    md_files = list(MARKDOWN_DIR.glob("*.md"))
    if not md_files:
        raise SystemExit(
            f"No markdown found in {MARKDOWN_DIR} — run markdownize first."
        )

    logger.info(
        "Building Document Graph: sources={} db={} force={}", MARKDOWN_DIR, KG_DB, force
    )
    backend = KuzuBackend()
    backend.connect(str(KG_DB))
    try:
        if force:
            logger.info("Dropping existing Document Graph tables at {}", KG_DB)
            drop_document_graph(backend)
        factory = DocumentGraphFactory(sources=[str(MARKDOWN_DIR)], recursive=True)
        result = ingest_document_graph(backend, factory, force=force)
    finally:
        backend.close()

    logger.success(
        "Graph built: {} processed ({} skipped), {} failed, {} sections, {} relationships",
        result.documents_processed,
        result.documents_skipped,
        result.documents_failed,
        result.sections_created,
        result.relationships_created,
    )
    return result.model_dump()


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
    args = parser.parse_args(argv)

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
    result = build_document_graph(doc_name, force=args.force)

    print(f"doc={doc_name}")
    print(f"db={KG_DB}")
    print(f"sections_created={result.get('sections_created')}")
    print(f"documents_processed={result.get('documents_processed')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
