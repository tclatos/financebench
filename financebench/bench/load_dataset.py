"""Load the FinanceBench dataset and select the target document.

Caches the Hugging Face dataset under ``data/financebench/`` and auto-selects
the single ``doc_name`` with the most questions in the 150-row open-source
split, then writes one JSONL row per question for that document.

Usage:
```bash
uv run python -m financebench.bench.load_dataset
uv run python -m financebench.bench.load_dataset --doc 3M_2022_10K
```
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter

import pandas as pd
from datasets import load_dataset
from loguru import logger

from financebench.bench._env import FB_DIR, ensure_dirs, load_env

DATASET_ID = "PatronusAI/financebench"
DATASET_CACHE = FB_DIR / "financebench_merged.parquet"
QUESTIONS_PATH = FB_DIR / "questions.jsonl"
TARGET_PATH = FB_DIR / "target_doc.txt"


def load_financebench() -> pd.DataFrame:
    """Load the merged FinanceBench open-source split as a DataFrame.

    Uses a local parquet cache so repeated runs do not hit Hugging Face.
    """
    ensure_dirs()
    load_env()
    if DATASET_CACHE.exists():
        logger.info("Loading cached dataset from {}", DATASET_CACHE)
        return pd.read_parquet(DATASET_CACHE)

    logger.info("Downloading {} from Hugging Face", DATASET_ID)
    ds = load_dataset(DATASET_ID, split="train")
    df = ds.to_pandas()
    FB_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(DATASET_CACHE, index=False)
    logger.info("Cached {} rows to {}", len(df), DATASET_CACHE)
    return df


def select_target_doc(df: pd.DataFrame) -> str:
    """Return the ``doc_name`` with the most questions in *df*."""
    counts = Counter(df["doc_name"].tolist())
    doc_name, n = counts.most_common(1)[0]
    logger.info("Selected target doc: {} ({} questions)", doc_name, n)
    return doc_name


def _clean(value):
    """Return *value* as JSON-safe: pandas/float NaN -> ``None``."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def questions_for_doc(df: pd.DataFrame, doc_name: str) -> list[dict]:
    """Return the question rows for *doc_name* as JSON-serialisable dicts."""
    sub = df[df["doc_name"] == doc_name].sort_values("financebench_id")
    rows: list[dict] = []
    for _, row in sub.iterrows():
        evidence = row.get("evidence") or []
        rows.append(
            {
                "financebench_id": row["financebench_id"],
                "company": row["company"],
                "doc_name": row["doc_name"],
                "doc_type": row["doc_type"],
                "doc_period": int(row["doc_period"]),
                "gics_sector": _clean(row.get("gics_sector")),
                "question_type": row["question_type"],
                "question_reasoning": _clean(row.get("question_reasoning")),
                "domain_question_num": _clean(row.get("domain_question_num")),
                "question": row["question"],
                "answer": row["answer"],
                "justification": _clean(row.get("justification")),
                "evidence": [
                    {
                        "evidence_text": _clean(ev.get("evidence_text")),
                        "evidence_doc_name": _clean(ev.get("evidence_doc_name")),
                        "evidence_page_num": _clean(ev.get("evidence_page_num")),
                        "evidence_text_full_page": _clean(
                            ev.get("evidence_text_full_page")
                        ),
                    }
                    for ev in evidence
                ],
            }
        )
    return rows


def write_questions(df: pd.DataFrame, doc_name: str) -> list[dict]:
    """Write the per-question JSONL for *doc_name* and record the selection."""
    rows = questions_for_doc(df, doc_name)
    with QUESTIONS_PATH.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    TARGET_PATH.write_text(doc_name, encoding="utf-8")
    logger.info("Wrote {} questions to {}", len(rows), QUESTIONS_PATH)
    return rows


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Load FinanceBench and select a target doc."
    )
    parser.add_argument(
        "--doc", default=None, help="Override the auto-selected doc_name."
    )
    args = parser.parse_args(argv)

    df = load_financebench()
    doc_name = args.doc or select_target_doc(df)
    write_questions(df, doc_name)
    print(f"target_doc={doc_name}")
    print(f"questions={QUESTIONS_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
