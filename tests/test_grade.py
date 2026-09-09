"""Unit tests for financebench bench grading and summary parsing."""

import json

from genai_graph.bench.judge import _parse_judge_json
from genai_graph.bench.models import JudgeVerdict
from genai_graph.bench.summary import compute_bench_summary


def test_parse_verdict_correct():
    raw_json = json.dumps(
        {
            "correctness": "correct",
            "numeric_match": True,
            "groundedness": "grounded",
            "error_category": None,
            "rationale": "The answer matches the gold value $3,565M exactly.",
        }
    )
    data = _parse_judge_json(raw_json)
    verdict = JudgeVerdict.model_validate(data)
    assert verdict.correctness == "correct"
    assert verdict.numeric_match is True
    assert verdict.groundedness == "grounded"
    assert verdict.error_category is None


def test_parse_verdict_visual_chart_error():
    raw_json = json.dumps(
        {
            "correctness": "incorrect",
            "numeric_match": False,
            "groundedness": "ungrounded",
            "error_category": "missing_ocr_or_visual_chart",
            "rationale": "Question asks for visual chart data missing from OCR.",
        }
    )
    data = _parse_judge_json(raw_json)
    verdict = JudgeVerdict.model_validate(data)
    assert verdict.correctness == "incorrect"
    assert verdict.error_category == "missing_ocr_or_visual_chart"


def test_parse_verdict_calculation_error():
    raw_json = json.dumps(
        {
            "correctness": "incorrect",
            "numeric_match": False,
            "groundedness": "grounded",
            "error_category": "calculation_or_math_error",
            "rationale": "Operating margin was calculated with the wrong denominator.",
        }
    )
    data = _parse_judge_json(raw_json)
    verdict = JudgeVerdict.model_validate(data)
    assert verdict.correctness == "incorrect"
    assert verdict.error_category == "calculation_or_math_error"


def test_summarize_with_ocr_adjustment():
    scores = [
        {
            "id": "FB_001",
            "correctness": "correct",
            "numeric_match": True,
            "groundedness": "grounded",
            "error_category": None,
            "n_tool_calls": 3,
            "input_tokens": 1000,
            "output_tokens": 200,
        },
        {
            "id": "FB_002",
            "correctness": "incorrect",
            "numeric_match": False,
            "groundedness": "ungrounded",
            "error_category": "missing_ocr_or_visual_chart",
            "n_tool_calls": 1,
            "input_tokens": 500,
            "output_tokens": 50,
        },
    ]

    summary = compute_bench_summary(scores, profile_name="test_profile")
    assert summary.total_questions == 2
    assert summary.correct == 1
    assert summary.ocr_errors == 1
    assert summary.ocr_adjusted_accuracy == 1.0


if __name__ == "__main__":
    test_parse_verdict_correct()
    test_parse_verdict_visual_chart_error()
    test_parse_verdict_calculation_error()
    test_summarize_with_ocr_adjustment()
    print("All financebench grade unit tests passed!")
