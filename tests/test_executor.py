"""Tests for executor module."""
import json
from pathlib import Path

from token_miser.executor import filter_env, load_claude_env, parse_claude_json


def test_parse_claude_json():
    data = json.dumps({
        "result": "Hello world",
        "total_cost_usd": 0.0042,
        "usage": {
            "input_tokens": 100,
            "output_tokens": 50,
            "cache_creation_input_tokens": 10,
            "cache_read_input_tokens": 5,
        },
    })
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
