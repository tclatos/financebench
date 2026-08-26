"""Download a FinanceBench source PDF into ``data/pdfs/``.

The FinanceBench repo stores one PDF per document under ``/pdfs/<doc_name>.pdf``.
This fetches the target document's PDF (skipping if already present) so the
markdownize step can OCR it.

Usage:
```bash
uv run python -m financebench.bench.fetch_pdf
uv run python -m financebench.bench.fetch_pdf --doc AMD_2022_10K
```
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx
from loguru import logger

from financebench.bench._env import PDFS_DIR, ensure_dirs, load_env
from financebench.bench.load_dataset import TARGET_PATH

PDF_BASE_URL = "https://raw.githubusercontent.com/patronus-ai/financebench/main/pdfs"


def resolve_doc_name(doc_name: str | None) -> str:
    """Return *doc_name* or read the previously selected target from disk."""
    if doc_name:
        return doc_name
    if TARGET_PATH.exists():
        return TARGET_PATH.read_text(encoding="utf-8").strip()
    raise SystemExit(
        "No --doc given and no target_doc.txt found; run load_dataset first."
    )


def fetch_pdf(doc_name: str, *, pdfs_dir: Path | None = None) -> str:
    """Download ``<doc_name>.pdf`` into the pdfs dir and return its path.

    *pdfs_dir* defaults to ``PDFS_DIR`` so the standalone CLI keeps working;
    the orchestrator passes a config-driven dir. Skips an existing file.
    """
    ensure_dirs()
    load_env()
    base = pdfs_dir or PDFS_DIR
    base.mkdir(parents=True, exist_ok=True)
    pdf_path = base / f"{doc_name}.pdf"
    if pdf_path.exists() and pdf_path.stat().st_size > 0:
        logger.info(
            "PDF already present: {} ({} bytes)", pdf_path, pdf_path.stat().st_size
        )
        return str(pdf_path)

    url = f"{PDF_BASE_URL}/{doc_name}.pdf"
    logger.info("Downloading {}", url)
    with httpx.Client(follow_redirects=True, timeout=120) as client:
        resp = client.get(url)
        resp.raise_for_status()
        pdf_path.write_bytes(resp.content)
    logger.success("Saved {} ({} bytes)", pdf_path, pdf_path.stat().st_size)
    return str(pdf_path)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Download a FinanceBench PDF.")
    parser.add_argument(
        "--doc", default=None, help="doc_name to download (default: selected target)."
    )
    args = parser.parse_args(argv)

    doc_name = resolve_doc_name(args.doc)
    path = fetch_pdf(doc_name)
    print(f"pdf={path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
