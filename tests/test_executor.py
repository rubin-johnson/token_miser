"""Tests for executor module."""
import json

from token_miser.executor import filter_env, parse_claude_json


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
    }).encode()
    result = parse_claude_json(data)
    assert result.result == "Hello world"
    assert result.total_cost_usd == 0.0042
    assert result.usage.input_tokens == 100
    assert result.usage.output_tokens == 50
    assert result.usage.cache_creation_input_tokens == 10
    assert result.usage.cache_read_input_tokens == 5


def test_parse_claude_json_missing_fields():
    data = json.dumps({"result": "ok"}).encode()
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
