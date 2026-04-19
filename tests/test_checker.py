"""Tests for success criteria checker."""
import os

from token_miser.checker import check_all_criteria, check_criterion
from token_miser.environment import EnvironmentContext
from token_miser.task import Criterion


def _make_env(tmp_path) -> EnvironmentContext:
    return EnvironmentContext(home_dir=str(tmp_path / "home"), workspace_dir=str(tmp_path / "workspace"))


def test_file_exists_pass(tmp_path):
    env = _make_env(tmp_path)
    os.makedirs(env.workspace_dir, exist_ok=True)
    (tmp_path / "workspace" / "foo.py").write_text("x")
    result = check_criterion(Criterion(type="file_exists", paths=["foo.py"]), env)
    assert result.passed


def test_file_exists_fail(tmp_path):
    env = _make_env(tmp_path)
    os.makedirs(env.workspace_dir, exist_ok=True)
    result = check_criterion(Criterion(type="file_exists", paths=["missing.py"]), env)
    assert not result.passed
    assert "missing.py" in result.detail


def test_command_exits_zero(tmp_path):
    env = _make_env(tmp_path)
    os.makedirs(env.workspace_dir, exist_ok=True)
    os.makedirs(env.home_dir, exist_ok=True)
    result = check_criterion(Criterion(type="command_exits_zero", command="echo ok"), env)
    assert result.passed


def test_command_fails(tmp_path):
    env = _make_env(tmp_path)
    os.makedirs(env.workspace_dir, exist_ok=True)
    os.makedirs(env.home_dir, exist_ok=True)
    result = check_criterion(Criterion(type="command_exits_zero", command="exit 1"), env)
    assert not result.passed
    assert "Exit code 1" in result.detail


def test_output_contains_pass(tmp_path):
    env = _make_env(tmp_path)
    os.makedirs(env.workspace_dir, exist_ok=True)
    os.makedirs(env.home_dir, exist_ok=True)
    result = check_criterion(
        Criterion(type="output_contains", command="echo hello world", contains=["hello", "world"]), env
    )
    assert result.passed


def test_output_contains_fail(tmp_path):
    env = _make_env(tmp_path)
    os.makedirs(env.workspace_dir, exist_ok=True)
    os.makedirs(env.home_dir, exist_ok=True)
    result = check_criterion(
        Criterion(type="output_contains", command="echo hello", contains=["goodbye"]), env
    )
    assert not result.passed
    assert "goodbye" in result.detail


def test_unknown_type(tmp_path):
    env = _make_env(tmp_path)
    os.makedirs(env.workspace_dir, exist_ok=True)
    result = check_criterion(Criterion(type="bogus"), env)
    assert not result.passed
    assert "Unknown" in result.detail


def test_command_succeeds_alias(tmp_path):
    env = _make_env(tmp_path)
    os.makedirs(env.workspace_dir, exist_ok=True)
    os.makedirs(env.home_dir, exist_ok=True)
    c = Criterion(type="command_succeeds", command="true")
    result = check_criterion(c, env)
    assert result.passed is True


def test_command_succeeds_failure(tmp_path):
    env = _make_env(tmp_path)
    os.makedirs(env.workspace_dir, exist_ok=True)
    os.makedirs(env.home_dir, exist_ok=True)
    c = Criterion(type="command_succeeds", command="false")
    result = check_criterion(c, env)
    assert result.passed is False


def test_output_contains_fails_on_nonzero_exit(tmp_path):
    env = _make_env(tmp_path)
    os.makedirs(env.workspace_dir, exist_ok=True)
    os.makedirs(env.home_dir, exist_ok=True)
    c = Criterion(type="output_contains", command="echo expected; exit 1", contains=["expected"])
    result = check_criterion(c, env)
    assert result.passed is False
    assert "exit" in result.detail.lower() or "1" in result.detail


def test_check_all_criteria(tmp_path):
    env = _make_env(tmp_path)
    os.makedirs(env.workspace_dir, exist_ok=True)
    os.makedirs(env.home_dir, exist_ok=True)
    (tmp_path / "workspace" / "exists.txt").write_text("x")
    criteria = [
        Criterion(type="file_exists", paths=["exists.txt"]),
        Criterion(type="file_exists", paths=["missing.txt"]),
        Criterion(type="command_exits_zero", command="echo ok"),
    ]
    results = check_all_criteria(criteria, env)
    assert len(results) == 3
    assert results[0].passed
    assert not results[1].passed
    assert results[2].passed
