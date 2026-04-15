"""Tests for recommendation engine."""
import json

from token_miser.db import Run
from token_miser.recommend import (
    Recommendation,
    analyze_results,
    rule_empty_claude_md,
    rule_high_tokens_no_grep,
    rule_high_variance_feature_tasks,
    rule_high_wall_low_quality,
    rule_low_criteria_pass_rate,
    rule_low_minimal_change,
)


def _run(**kwargs) -> Run:
    defaults = dict(
        task_id="t1", package_name="a", input_tokens=10000, output_tokens=10000,
        criteria_pass=9, criteria_total=10, wall_seconds=60.0,
        quality_scores=json.dumps({"minimal_change": 0.9, "correctness": 0.9}),
    )
    defaults.update(kwargs)
    return Run(**defaults)


# --- rule_high_tokens_no_grep ---

class TestHighTokensNoGrep:
    def test_triggers_when_high_tokens_and_no_grep(self):
        runs = [_run(input_tokens=25000, output_tokens=20000)]
        rec = rule_high_tokens_no_grep(runs, "## My Config\nBe concise.")
        assert rec is not None
        assert rec.category == "token_efficiency"
        assert rec.confidence > 0

    def test_no_trigger_when_tokens_low(self):
        runs = [_run(input_tokens=10000, output_tokens=10000)]
        rec = rule_high_tokens_no_grep(runs, "Be concise.")
        assert rec is None

    def test_no_trigger_when_grep_present(self):
        runs = [_run(input_tokens=25000, output_tokens=20000)]
        rec = rule_high_tokens_no_grep(runs, "Use grep before reading files.")
        assert rec is None

    def test_no_trigger_when_glob_present(self):
        runs = [_run(input_tokens=25000, output_tokens=20000)]
        rec = rule_high_tokens_no_grep(runs, "Use glob for file search.")
        assert rec is None

    def test_no_trigger_empty_runs(self):
        rec = rule_high_tokens_no_grep([], "Be concise.")
        assert rec is None


# --- rule_low_minimal_change ---

class TestLowMinimalChange:
    def test_triggers_when_low_score(self):
        runs = [
            _run(quality_scores=json.dumps({"minimal_change": 0.5})),
            _run(quality_scores=json.dumps({"minimal_change": 0.6})),
        ]
        rec = rule_low_minimal_change(runs, "")
        assert rec is not None
        assert rec.category == "quality"

    def test_no_trigger_when_score_high(self):
        runs = [_run(quality_scores=json.dumps({"minimal_change": 0.9}))]
        rec = rule_low_minimal_change(runs, "")
        assert rec is None

    def test_handles_empty_json(self):
        runs = [_run(quality_scores="")]
        rec = rule_low_minimal_change(runs, "")
        assert rec is None

    def test_handles_malformed_json(self):
        runs = [_run(quality_scores="not json")]
        rec = rule_low_minimal_change(runs, "")
        assert rec is None

    def test_handles_missing_key(self):
        runs = [_run(quality_scores=json.dumps({"correctness": 0.5}))]
        rec = rule_low_minimal_change(runs, "")
        assert rec is None


# --- rule_high_variance_feature_tasks ---

class TestHighVarianceFeatureTasks:
    def test_triggers_on_high_variance(self):
        runs = [
            _run(task_id="feat-add-login", input_tokens=10000, output_tokens=10000),
            _run(task_id="feat-add-signup", input_tokens=80000, output_tokens=80000),
        ]
        rec = rule_high_variance_feature_tasks(runs, "")
        assert rec is not None
        assert rec.category == "structure"

    def test_no_trigger_low_variance(self):
        runs = [
            _run(task_id="feat-a", input_tokens=20000, output_tokens=20000),
            _run(task_id="feat-b", input_tokens=21000, output_tokens=21000),
        ]
        rec = rule_high_variance_feature_tasks(runs, "")
        assert rec is None

    def test_no_trigger_no_feature_tasks(self):
        runs = [
            _run(task_id="fix-bug", input_tokens=10000, output_tokens=10000),
            _run(task_id="refactor", input_tokens=80000, output_tokens=80000),
        ]
        rec = rule_high_variance_feature_tasks(runs, "")
        assert rec is None

    def test_no_trigger_single_feature_task(self):
        runs = [_run(task_id="feat-only", input_tokens=50000, output_tokens=50000)]
        rec = rule_high_variance_feature_tasks(runs, "")
        assert rec is None


# --- rule_low_criteria_pass_rate ---

class TestLowCriteriaPassRate:
    def test_triggers_when_low_pass_rate(self):
        runs = [
            _run(criteria_pass=3, criteria_total=10),
            _run(criteria_pass=4, criteria_total=10),
        ]
        rec = rule_low_criteria_pass_rate(runs, "")
        assert rec is not None
        assert rec.category == "quality"

    def test_no_trigger_when_high_pass_rate(self):
        runs = [_run(criteria_pass=9, criteria_total=10)]
        rec = rule_low_criteria_pass_rate(runs, "")
        assert rec is None

    def test_no_trigger_zero_total(self):
        runs = [_run(criteria_pass=0, criteria_total=0)]
        rec = rule_low_criteria_pass_rate(runs, "")
        assert rec is None


# --- rule_empty_claude_md ---

class TestEmptyClaudeMd:
    def test_triggers_on_short_config(self):
        rec = rule_empty_claude_md([], "# Config\nBe concise.\n")
        assert rec is not None
        assert rec.category == "structure"

    def test_no_trigger_on_long_config(self):
        lines = "\n".join(f"rule {i}" for i in range(20))
        rec = rule_empty_claude_md([], lines)
        assert rec is None

    def test_triggers_on_empty_string(self):
        rec = rule_empty_claude_md([], "")
        assert rec is not None


# --- rule_high_wall_low_quality ---

class TestHighWallLowQuality:
    def test_triggers_on_slow_low_quality(self):
        runs = [
            _run(
                wall_seconds=200,
                quality_scores=json.dumps({"correctness": 0.5, "minimal_change": 0.6}),
            ),
        ]
        rec = rule_high_wall_low_quality(runs, "")
        assert rec is not None
        assert rec.category == "token_efficiency"

    def test_no_trigger_when_fast(self):
        runs = [
            _run(
                wall_seconds=30,
                quality_scores=json.dumps({"correctness": 0.5}),
            ),
        ]
        rec = rule_high_wall_low_quality(runs, "")
        assert rec is None

    def test_no_trigger_when_high_quality(self):
        runs = [
            _run(
                wall_seconds=200,
                quality_scores=json.dumps({"correctness": 0.9, "minimal_change": 0.95}),
            ),
        ]
        rec = rule_high_wall_low_quality(runs, "")
        assert rec is None

    def test_handles_empty_quality_scores(self):
        runs = [_run(wall_seconds=200, quality_scores="")]
        rec = rule_high_wall_low_quality(runs, "")
        assert rec is None

    def test_handles_malformed_quality_scores(self):
        runs = [_run(wall_seconds=200, quality_scores="bad")]
        rec = rule_high_wall_low_quality(runs, "")
        assert rec is None


# --- analyze_results ---

class TestAnalyzeResults:
    def test_returns_sorted_by_confidence_descending(self):
        runs = [
            _run(
                task_id="feat-x",
                input_tokens=25000, output_tokens=20000,
                criteria_pass=3, criteria_total=10,
                wall_seconds=200,
                quality_scores=json.dumps({"minimal_change": 0.4, "correctness": 0.5}),
            ),
        ]
        recs = analyze_results(runs, "tiny")
        assert len(recs) > 0
        for i in range(len(recs) - 1):
            assert recs[i].confidence >= recs[i + 1].confidence

    def test_returns_empty_when_no_issues(self):
        runs = [
            _run(
                input_tokens=5000, output_tokens=5000,
                criteria_pass=10, criteria_total=10,
                wall_seconds=30,
                quality_scores=json.dumps({"minimal_change": 0.95, "correctness": 0.95}),
            ),
        ]
        long_md = "\n".join(f"rule {i}: Use grep before reading" for i in range(20))
        recs = analyze_results(runs, long_md)
        assert recs == []

    def test_all_recommendations_are_recommendation_type(self):
        runs = [_run(criteria_pass=1, criteria_total=10)]
        recs = analyze_results(runs, "tiny")
        for r in recs:
            assert isinstance(r, Recommendation)

    def test_empty_runs_with_empty_md(self):
        recs = analyze_results([], "")
        # Should still trigger empty CLAUDE.md rule
        assert any(r.category == "structure" for r in recs)
