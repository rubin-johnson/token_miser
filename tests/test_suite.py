"""Tests for suite — benchmark suite loading and management."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from token_miser.suite import BenchmarkTask, list_suites, load_suite


@pytest.fixture
def suites_dir(tmp_path: Path) -> Path:
    d = tmp_path / "suites"
    d.mkdir()
    return d


@pytest.fixture
def tasks_dir(tmp_path: Path) -> Path:
    d = tmp_path / "tasks"
    d.mkdir()
    return d


@pytest.fixture
def quick_suite(suites_dir: Path, tasks_dir: Path) -> Path:
    # Create a minimal task YAML
    task_data = {
        "id": "bm-feat-001",
        "name": "Add CLI subcommand",
        "repo_id": "tiny-cli",
        "starting_commit": "abc123",
        "prompt": "Add a stats subcommand.",
        "success_criteria": [{"type": "file_exists", "paths": ["src/stats.py"]}],
    }
    (tasks_dir / "bm-feat-001.yaml").write_text(yaml.dump(task_data))

    task_data2 = {
        "id": "bm-fix-001",
        "name": "Fix off-by-one",
        "repo_id": "tiny-api",
        "starting_commit": "def456",
        "prompt": "Fix the pagination bug.",
        "success_criteria": [{"type": "command_exits_zero", "command": "pytest"}],
    }
    (tasks_dir / "bm-fix-001.yaml").write_text(yaml.dump(task_data2))

    suite_data = {
        "name": "quick",
        "version": "0.1.0",
        "description": "Fast benchmark suite",
        "tasks": [
            {"file": "bm-feat-001.yaml", "category": "feature", "difficulty": "easy"},
            {"file": "bm-fix-001.yaml", "category": "bugfix", "difficulty": "easy"},
        ],
    }
    path = suites_dir / "quick.yaml"
    path.write_text(yaml.dump(suite_data))
    return path


class TestLoadSuite:
    def test_loads_suite_with_tasks(self, quick_suite: Path, tasks_dir: Path) -> None:
        suite = load_suite(quick_suite, tasks_dir)
        assert suite.name == "quick"
        assert suite.version == "0.1.0"
        assert len(suite.tasks) == 2

    def test_task_has_category_and_difficulty(self, quick_suite: Path, tasks_dir: Path) -> None:
        suite = load_suite(quick_suite, tasks_dir)
        assert suite.tasks[0].category == "feature"
        assert suite.tasks[0].difficulty == "easy"

    def test_task_has_repo_id(self, quick_suite: Path, tasks_dir: Path) -> None:
        suite = load_suite(quick_suite, tasks_dir)
        assert suite.tasks[0].repo_id == "tiny-cli"
        assert suite.tasks[1].repo_id == "tiny-api"

    def test_missing_task_file_raises(self, suites_dir: Path, tasks_dir: Path) -> None:
        suite_data = {
            "name": "bad",
            "version": "0.1.0",
            "description": "Bad suite",
            "tasks": [{"file": "nonexistent.yaml", "category": "feature", "difficulty": "easy"}],
        }
        path = suites_dir / "bad.yaml"
        path.write_text(yaml.dump(suite_data))
        with pytest.raises(FileNotFoundError):
            load_suite(path, tasks_dir)


class TestListSuites:
    def test_lists_available_suites(self, suites_dir: Path) -> None:
        for name in ["quick", "standard"]:
            (suites_dir / f"{name}.yaml").write_text(
                yaml.dump({"name": name, "version": "0.1.0", "description": f"{name} suite", "tasks": []})
            )
        names = list_suites(suites_dir)
        assert "quick" in names
        assert "standard" in names

    def test_empty_dir_returns_empty(self, tmp_path: Path) -> None:
        d = tmp_path / "empty"
        d.mkdir()
        assert list_suites(d) == []


class TestBenchmarkTask:
    def test_has_all_fields(self, quick_suite: Path, tasks_dir: Path) -> None:
        suite = load_suite(quick_suite, tasks_dir)
        t = suite.tasks[0]
        assert isinstance(t, BenchmarkTask)
        assert t.id == "bm-feat-001"
        assert t.name == "Add CLI subcommand"
        assert t.category == "feature"
        assert t.difficulty == "easy"
        assert t.repo_id == "tiny-cli"
