"""Tests for evaluator module (no real API calls)."""

from token_miser.evaluator import _build_judge_prompt, _parse_scores
from token_miser.task import RubricDimension


def test_build_judge_prompt():
    dims = [RubricDimension(dimension="correctness", prompt="Is it correct?")]
    prompt = _build_judge_prompt("Do X", "Did X", dims)
    assert "Do X" in prompt
    assert "Did X" in prompt
    assert "correctness" in prompt


def test_parse_scores_valid():
    text = '[{"dimension": "quality", "score": 0.85, "reason": "Good work."}]'
    dims = [RubricDimension(dimension="quality", prompt="")]
    scores = _parse_scores(text, dims)
    assert len(scores) == 1
    assert scores[0].dimension == "quality"
    assert scores[0].score == 0.85
    assert scores[0].reason == "Good work."


def test_parse_scores_with_code_fence():
    text = '```json\n[{"dimension": "q", "score": 0.5, "reason": "OK"}]\n```'
    scores = _parse_scores(text, [])
    assert len(scores) == 1
    assert scores[0].score == 0.5


def test_parse_scores_out_of_range():
    import pytest

    text = '[{"dimension": "q", "score": 1.5, "reason": "too high"}]'
    with pytest.raises(ValueError, match="out of range"):
        _parse_scores(text, [])


def test_parse_scores_empty_reason():
    import pytest

    text = '[{"dimension": "q", "score": 0.5, "reason": ""}]'
    with pytest.raises(ValueError, match="Empty reason"):
        _parse_scores(text, [])
