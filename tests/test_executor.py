"""Tests for executor module."""

import json
from pathlib import Path

import pytest

from token_miser.backends.base import Usage
from token_miser.backends.claude import ClaudeBackend
from token_miser.backends.codex import CodexBackend, estimate_codex_cost
from token_miser.executor import filter_env, load_claude_env, parse_claude_json


def test_parse_claude_json():
    data = json.dumps(
        {
            "result": "Hello world",
            "total_cost_usd": 0.0042,
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
                "cache_creation_input_tokens": 10,
                "cache_read_input_tokens": 5,
            },
        }
    )
    result = parse_claude_json(data)
    assert result.result == "Hello world"
    assert result.total_cost_usd == 0.0042
    assert result.usage.input_tokens == 100
    assert result.usage.output_tokens == 50
    assert result.usage.cache_creation_input_tokens == 10
    assert result.usage.cache_read_input_tokens == 5


def test_parse_claude_json_missing_fields():
    data = json.dumps({"result": "ok"})
    result = parse_claude_json(data)
    assert result.result == "ok"
    assert result.total_cost_usd == 0.0
    assert result.usage.input_tokens == 0


def test_filter_env_overrides_home():
    env = filter_env("/tmp/fake-home")
    assert env["HOME"] == "/tmp/fake-home"


def test_filter_env_strips_claudecode(monkeypatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    env = filter_env("/tmp/h")
    assert "CLAUDECODE" not in env


def test_filter_env_merges_extra():
    env = filter_env("/tmp/h", extra={"CLAUDE_CODE_USE_BEDROCK": "1", "AWS_REGION": "us-east-1"})
    assert env["CLAUDE_CODE_USE_BEDROCK"] == "1"
    assert env["AWS_REGION"] == "us-east-1"
    assert env["HOME"] == "/tmp/h"


def test_filter_env_extra_overrides_parent(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "eu-west-1")
    env = filter_env("/tmp/h", extra={"AWS_REGION": "us-east-1"})
    assert env["AWS_REGION"] == "us-east-1"


def test_load_claude_env_from_file(tmp_path: Path):
    env_file = tmp_path / "claude.env"
    env_file.write_text(
        "# Bedrock config\n"
        "CLAUDE_CODE_USE_BEDROCK=1\n"
        "AWS_REGION=us-east-1\n"
        "AWS_PROFILE=work-profile\n"
        "\n"
        "# blank lines and comments are skipped\n"
    )
    result = load_claude_env(env_file)
    assert result == {
        "CLAUDE_CODE_USE_BEDROCK": "1",
        "AWS_REGION": "us-east-1",
        "AWS_PROFILE": "work-profile",
    }


def test_load_claude_env_missing_file(tmp_path: Path):
    result = load_claude_env(tmp_path / "nonexistent")
    assert result == {}


def test_load_claude_env_empty_file(tmp_path: Path):
    env_file = tmp_path / "claude.env"
    env_file.write_text("# just a comment\n\n")
    result = load_claude_env(env_file)
    assert result == {}


class TestClaudeEstimateCost:
    def setup_method(self):
        self.backend = ClaudeBackend()

    def test_sonnet_alias(self):
        usage = Usage(input_tokens=1_000_000, output_tokens=0)
        cost = self.backend.estimate_cost(usage, "sonnet")
        assert cost == pytest.approx(3.00, rel=1e-4)

    def test_haiku_alias(self):
        usage = Usage(input_tokens=1_000_000, output_tokens=0)
        cost = self.backend.estimate_cost(usage, "haiku")
        assert cost == pytest.approx(0.80, rel=1e-4)

    def test_opus_alias(self):
        usage = Usage(input_tokens=0, output_tokens=1_000_000)
        cost = self.backend.estimate_cost(usage, "opus")
        assert cost == pytest.approx(75.00, rel=1e-4)

    def test_cached_tokens_cheaper(self):
        full = Usage(input_tokens=1_000_000, output_tokens=0)
        cached = Usage(input_tokens=1_000_000, output_tokens=0, cache_read_input_tokens=1_000_000)
        assert self.backend.estimate_cost(cached, "sonnet") < self.backend.estimate_cost(full, "sonnet")

    def test_cache_creation_tokens_cost_more_than_input(self):
        base = Usage(input_tokens=1_000_000, output_tokens=0)
        with_creation = Usage(
            input_tokens=1_000_000, output_tokens=0, cache_creation_input_tokens=500_000
        )
        base_cost = self.backend.estimate_cost(base, "sonnet")
        creation_cost = self.backend.estimate_cost(with_creation, "sonnet")
        assert creation_cost > base_cost

    def test_cache_creation_sonnet_exact(self):
        usage = Usage(input_tokens=0, output_tokens=0, cache_creation_input_tokens=1_000_000)
        cost = self.backend.estimate_cost(usage, "sonnet")
        # 1.25x input rate: 3.00 * 1.25 = 3.75
        assert cost == pytest.approx(3.75, rel=1e-4)

    def test_unknown_model_returns_zero(self):
        usage = Usage(input_tokens=1_000_000, output_tokens=1_000_000)
        assert self.backend.estimate_cost(usage, "unknown-model-xyz") == 0.0

    def test_default_model_fallback(self):
        usage = Usage(input_tokens=1_000_000, output_tokens=0)
        # Default model is "sonnet"; should not return 0.0
        assert self.backend.estimate_cost(usage) > 0.0


class TestCodexUsageAccumulation:
    """Codex emits multiple turn.completed events; usage must be summed, not overwritten."""

    def _make_codex_output(self, turns: list[dict]) -> str:
        lines = []
        for t in turns:
            lines.append(json.dumps({"type": "turn.completed", "usage": t}))
        return "\n".join(lines)

    def test_multi_turn_usage_accumulated(self, monkeypatch):
        backend = CodexBackend()
        output = self._make_codex_output([
            {"input_tokens": 100, "output_tokens": 50, "cached_input_tokens": 10, "reasoning_tokens": 0},
            {"input_tokens": 200, "output_tokens": 80, "cached_input_tokens": 30, "reasoning_tokens": 5},
        ])

        import subprocess

        fake_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=output, stderr=""
        )
        monkeypatch.setattr("token_miser.backends.codex.subprocess.run", lambda *a, **kw: fake_result)

        result = backend.run("test prompt", "/tmp/home", "/tmp/workspace")
        assert result.usage.input_tokens == 300
        assert result.usage.output_tokens == 130
        assert result.usage.cache_read_input_tokens == 40
        assert result.usage.reasoning_tokens == 5

    def test_single_turn_works(self, monkeypatch):
        backend = CodexBackend()
        output = json.dumps({"type": "turn.completed", "usage": {
            "input_tokens": 500, "output_tokens": 200,
        }})

        import subprocess

        fake_result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=output, stderr=""
        )
        monkeypatch.setattr("token_miser.backends.codex.subprocess.run", lambda *a, **kw: fake_result)

        result = backend.run("test prompt", "/tmp/home", "/tmp/workspace")
        assert result.usage.input_tokens == 500
        assert result.usage.output_tokens == 200


class TestCodexEstimateCost:
    def setup_method(self):
        self.backend = CodexBackend()

    def test_known_model(self):
        usage = Usage(input_tokens=1_000_000, output_tokens=0)
        cost = self.backend.estimate_cost(usage, "gpt-5.4")
        assert cost == pytest.approx(2.50, rel=1e-4)

    def test_cached_tokens_cheaper(self):
        full = Usage(input_tokens=1_000_000, output_tokens=0)
        cached = Usage(input_tokens=1_000_000, output_tokens=0, cache_read_input_tokens=1_000_000)
        assert self.backend.estimate_cost(cached, "gpt-5.4") < self.backend.estimate_cost(full, "gpt-5.4")

    def test_unknown_model_returns_zero(self):
        usage = Usage(input_tokens=1_000_000, output_tokens=1_000_000)
        assert self.backend.estimate_cost(usage, "gpt-unknown") == 0.0

    def test_standalone_function_matches_method(self):
        usage = Usage(input_tokens=500_000, output_tokens=200_000)
        assert estimate_codex_cost("gpt-5.4", usage) == self.backend.estimate_cost(usage, "gpt-5.4")

    def test_default_model_fallback(self):
        usage = Usage(input_tokens=1_000_000, output_tokens=0)
        # Default model is "gpt-5.4"; should not return 0.0
        assert self.backend.estimate_cost(usage) > 0.0
