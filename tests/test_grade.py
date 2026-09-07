"""Unit tests for financebench bench grading and observability metrics."""

import json
from pathlib import Path

from financebench.bench.grade import (
    _parse_verdict,
    _summarize,
    generate_markdown_report,
)


def test_parse_verdict_correct():
    raw_json = json.dumps({
        "correctness": "correct",
        "numeric_match": True,
        "groundedness": "grounded",
        "error_category": None,
        "rationale": "The answer matches the gold value $3,565M exactly.",
    })
    verdict = _parse_verdict(raw_json)
    assert verdict.correctness == "correct"
    assert verdict.numeric_match is True
    assert verdict.groundedness == "grounded"
    assert verdict.error_category is None


def test_parse_verdict_visual_chart_error():
    raw_json = json.dumps({
        "correctness": "incorrect",
        "numeric_match": False,
        "groundedness": "ungrounded",
        "error_category": "missing_ocr_or_visual_chart",
        "rationale": "Question asks for visual chart data missing from OCR.",
    })
    verdict = _parse_verdict(raw_json)
    assert verdict.correctness == "incorrect"
    assert verdict.error_category == "missing_ocr_or_visual_chart"


def test_parse_verdict_calculation_error():
    raw_json = json.dumps({
        "correctness": "incorrect",
        "numeric_match": False,
        "groundedness": "grounded",
        "error_category": "calculation_or_math_error",
        "rationale": "Operating margin was calculated with the wrong denominator.",
    })
    verdict = _parse_verdict(raw_json)
    assert verdict.correctness == "incorrect"
    assert verdict.error_category == "calculation_or_math_error"


def test_summarize_with_ocr_adjustment():
    scores = [
        {
            "financebench_id": "FB_001",
            "correctness": "correct",
            "numeric_match": True,
            "groundedness": "grounded",
            "error_category": None,
            "n_tool_calls": 3,
            "input_tokens": 1000,
            "output_tokens": 200,
        },
        {
            "financebench_id": "FB_002",
            "correctness": "incorrect",
            "numeric_match": False,
            "groundedness": "ungrounded",
            "error_category": "missing_ocr_or_visual_chart",
            "n_tool_calls": 1,
            "input_tokens": 500,
            "output_tokens": 50,
        },
    ]

    summary = _summarize(scores)
    assert summary["n"] == 2
    assert summary["correct"] == 1
    assert summary["ocr_errors"] == 1
    assert summary["ocr_adjusted_n"] == 1
    assert summary["ocr_adjusted_accuracy_correct"] == 1.0
    assert summary["error_breakdown"]["missing_ocr_or_visual_chart"] == 1


def test_generate_markdown_report(tmp_path: Path):
    scores = [
        {
            "financebench_id": "FB_001",
            "doc_name": "apple_10k",
            "question": "What was total revenue?",
            "gold_answer": "$383B",
            "agent_answer": "$383B",
            "correctness": "correct",
            "numeric_match": True,
            "groundedness": "grounded",
            "error_category": None,
            "rationale": "Exact match",
            "n_tool_calls": 2,
            "input_tokens": 1000,
            "output_tokens": 100,
        },
        {
            "financebench_id": "FB_002",
            "doc_name": "apple_10k",
            "question": "What is the chart trend?",
            "gold_answer": "Upward",
            "agent_answer": "Cannot see image",
            "correctness": "incorrect",
            "numeric_match": False,
            "groundedness": "ungrounded",
            "error_category": "missing_ocr_or_visual_chart",
            "rationale": "Chart missing in OCR",
            "n_tool_calls": 1,
            "input_tokens": 500,
            "output_tokens": 50,
        },
    ]
    summary = _summarize(scores)
    out_file = tmp_path / "test_report.md"
    generate_markdown_report(scores, summary, report_path=out_file)

    content = out_file.read_text(encoding="utf-8")
    assert "OCR-Adjusted Exact Correct" in content
    assert "## Error Category Breakdown" in content
    assert "`missing_ocr_or_visual_chart`" in content


if __name__ == "__main__":
    import tempfile

    test_parse_verdict_correct()
    test_parse_verdict_visual_chart_error()
    test_parse_verdict_calculation_error()
    test_summarize_with_ocr_adjustment()
    with tempfile.TemporaryDirectory() as td:
        test_generate_markdown_report(Path(td))
    print("All financebench grade unit tests passed!")

