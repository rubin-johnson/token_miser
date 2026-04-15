"""Benchmark suite loading and management."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class BenchmarkTask:
    id: str
    name: str
    repo_id: str
    starting_commit: str
    prompt: str = ""
    prompts: list[str] = field(default_factory=list)
    type: str = "single_shot"
    category: str = ""
    difficulty: str = ""
    setup_commands: list[str] = field(default_factory=list)
    success_criteria: list[dict] = field(default_factory=list)
    quality_rubric: list[dict] = field(default_factory=list)


@dataclass
class Suite:
    name: str
    version: str
    description: str
    tasks: list[BenchmarkTask]


def load_suite(suite_path: Path, tasks_dir: Path) -> Suite:
    """Load a suite manifest and its referenced task YAMLs."""
    data = yaml.safe_load(suite_path.read_text())

    tasks: list[BenchmarkTask] = []
    for entry in data.get("tasks", []):
        task_file = tasks_dir / entry["file"]
        if not task_file.exists():
            raise FileNotFoundError(f"Task file not found: {task_file}")

        task_data = yaml.safe_load(task_file.read_text())

        prompts = task_data.get("prompts", [])
        prompt = task_data.get("prompt", "")
        task_type = task_data.get("type", "")
        if not task_type:
            task_type = "sequential" if prompts else "single_shot"

        tasks.append(BenchmarkTask(
            id=task_data["id"],
            name=task_data.get("name", ""),
            repo_id=task_data.get("repo_id", ""),
            starting_commit=task_data.get("starting_commit", ""),
            prompt=prompt,
            prompts=prompts,
            type=task_type,
            category=entry.get("category", ""),
            difficulty=entry.get("difficulty", ""),
            setup_commands=task_data.get("setup_commands", []),
            success_criteria=task_data.get("success_criteria", []),
            quality_rubric=task_data.get("quality_rubric", []),
        ))

    return Suite(
        name=data["name"],
        version=data.get("version", "0.0.0"),
        description=data.get("description", ""),
        tasks=tasks,
    )


def list_suites(suites_dir: Path) -> list[str]:
    """Return names of available suite YAML files."""
    if not suites_dir.is_dir():
        return []
    return sorted(p.stem for p in suites_dir.glob("*.yaml"))
