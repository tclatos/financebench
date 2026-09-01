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
import pathspec

from financebench.bench._env import FB_DIR, ensure_dirs, load_env

DATASET_ID = "PatronusAI/financebench"
DATASET_CACHE = FB_DIR / "financebench_merged.parquet"
QUESTIONS_PATH = FB_DIR / "questions.jsonl"
TARGET_PATH = FB_DIR / "target_doc.txt"


def match_docs_by_pathspecs(all_docs: list[str], pathspecs: list[str]) -> list[str]:
    """Filter doc_names using gitwildmatch/gitignore style pathspecs.

    Args:
        all_docs: List of candidate document names.
        pathspecs: List of pathspec patterns (supports ``!`` for exclusion).

    Returns:
        Filtered and stable list of matching document names.
    """
    if not pathspecs:
        return all_docs
    spec = pathspec.PathSpec.from_lines("gitwildmatch", pathspecs)
    matched = [d for d in all_docs if spec.match_file(d)]
    return matched


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
        raw_evidence = row.get("evidence")
        if raw_evidence is None or (isinstance(raw_evidence, float) and math.isnan(raw_evidence)):
            evidence = []
        elif hasattr(raw_evidence, "__len__") and len(raw_evidence) == 0:
            evidence = []
        elif hasattr(raw_evidence, "tolist"):
            evidence = raw_evidence.tolist()
        else:
            evidence = raw_evidence or []
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


def questions_for_docs(df: pd.DataFrame, doc_names: list[str]) -> list[dict]:
    """Return the question rows for several *doc_names* as JSON-safe dicts.

    Rows are concatenated and re-sorted by ``financebench_id`` so a multi-doc
    question set reads in a stable order.
    """
    rows: list[dict] = []
    for name in doc_names:
        rows.extend(questions_for_doc(df, name))
    rows.sort(key=lambda r: str(r["financebench_id"]))
    return rows


def write_questions(df: pd.DataFrame, doc_names: str | list[str]) -> list[dict]:
    """Write the per-question JSONL for *doc_names* (one or several) and record the selection.

    Pass a single doc_name or a list; the rows for all named docs are written in
    ``financebench_id`` order so the agent answers a multi-doc corpus.
    """
    names = [doc_names] if isinstance(doc_names, str) else list(doc_names)
    rows = questions_for_docs(df, names)
    with QUESTIONS_PATH.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    TARGET_PATH.write_text(",".join(names), encoding="utf-8")
    logger.info(
        "Wrote {} questions for {} doc(s) to {}", len(rows), len(names), QUESTIONS_PATH
    )
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
