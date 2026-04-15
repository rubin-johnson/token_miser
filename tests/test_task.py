"""Tests for task loading and validation."""

import pytest
import yaml

from token_miser.task import load_task


@pytest.fixture()
def valid_task_file(tmp_path):
    data = {
        "id": "test-001",
        "name": "Test Task",
        "repo": "/tmp/fakerepo",
        "starting_commit": "abc123",
        "prompt": "Do the thing",
        "success_criteria": [
            {"type": "file_exists", "paths": ["foo.py"]},
            {"type": "command_exits_zero", "command": "echo ok"},
        ],
        "quality_rubric": [
            {"dimension": "correctness", "prompt": "Is it correct?"},
        ],
    }
    f = tmp_path / "task.yaml"
    f.write_text(yaml.dump(data))
    return f


@pytest.fixture()
def sequential_task_file(tmp_path):
    data = {
        "id": "seq-001",
        "name": "Sequential Task",
        "repo": "/tmp/fakerepo",
        "starting_commit": "abc123",
        "prompts": ["First prompt", "Second prompt"],
        "success_criteria": [],
    }
    f = tmp_path / "seq.yaml"
    f.write_text(yaml.dump(data))
    return f


def test_load_valid(valid_task_file):
    t = load_task(valid_task_file)
    assert t.id == "test-001"
    assert t.type == "single_shot"
    assert t.prompt == "Do the thing"
    assert len(t.success_criteria) == 2
    assert t.success_criteria[0].type == "file_exists"
    assert len(t.quality_rubric) == 1


def test_load_sequential(sequential_task_file):
    t = load_task(sequential_task_file)
    assert t.id == "seq-001"
    assert t.type == "sequential"
    assert len(t.prompts) == 2


def test_type_inference_single_shot(valid_task_file):
    t = load_task(valid_task_file)
    assert t.type == "single_shot"


def test_type_inference_sequential(sequential_task_file):
    t = load_task(sequential_task_file)
    assert t.type == "sequential"


def test_sequential_requires_two_prompts(tmp_path):
    data = {"id": "bad", "prompts": ["only one"]}
    f = tmp_path / "bad.yaml"
    f.write_text(yaml.dump(data))
    with pytest.raises(ValueError, match="at least 2 prompts"):
        load_task(f)


def test_missing_id(tmp_path):
    f = tmp_path / "no-id.yaml"
    f.write_text(yaml.dump({"prompt": "hi"}))
    with pytest.raises(ValueError, match="missing required 'id'"):
        load_task(f)


def test_single_shot_requires_prompt(tmp_path):
    f = tmp_path / "no-prompt.yaml"
    f.write_text(yaml.dump({"id": "x"}))
    with pytest.raises(ValueError, match="requires a 'prompt' field"):
        load_task(f)


def test_nonexistent_file():
    with pytest.raises(FileNotFoundError):
        load_task("/tmp/does-not-exist-12345.yaml")
