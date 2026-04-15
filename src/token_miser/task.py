"""Task YAML loading and validation."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Criterion:
    type: str
    paths: list[str] = field(default_factory=list)
    command: str = ""
    contains: list[str] = field(default_factory=list)


@dataclass
class RubricDimension:
    dimension: str
    prompt: str


@dataclass
class Task:
    id: str
    name: str
    repo: str
    starting_commit: str
    prompt: str = ""
    prompts: list[str] = field(default_factory=list)
    type: str = "single_shot"
    success_criteria: list[Criterion] = field(default_factory=list)
    quality_rubric: list[RubricDimension] = field(default_factory=list)
    repo_id: str = ""
    category: str = ""
    setup_commands: list[str] = field(default_factory=list)


def load_task(filename: str | Path) -> Task:
    """Load and validate a task YAML file."""
    path = Path(filename)
    data = yaml.safe_load(path.read_text())

    task_id = data.get("id", "")
    if not task_id:
        raise ValueError(f"Task file {filename} missing required 'id' field")

    prompts = data.get("prompts", [])
    prompt = data.get("prompt", "")
    task_type = data.get("type", "")

    if not task_type:
        task_type = "sequential" if prompts else "single_shot"

    if task_type == "sequential" and len(prompts) < 2:
        raise ValueError(f"Sequential task {task_id} requires at least 2 prompts")
    if task_type == "single_shot" and not prompt:
        raise ValueError(f"Single-shot task {task_id} requires a 'prompt' field")

    criteria = [
        Criterion(
            type=c.get("type", ""),
            paths=c.get("paths", []),
            command=c.get("command", ""),
            contains=c.get("contains", []),
        )
        for c in data.get("success_criteria", [])
    ]

    rubric = [
        RubricDimension(dimension=r["dimension"], prompt=r["prompt"])
        for r in data.get("quality_rubric", [])
    ]

    # Resolve ${VAR} references in repo path from environment
    repo = data.get("repo", "")
    repo = os.path.expandvars(repo)

    return Task(
        id=task_id,
        name=data.get("name", ""),
        repo=repo,
        starting_commit=data.get("starting_commit", ""),
        prompt=prompt,
        prompts=prompts,
        type=task_type,
        success_criteria=criteria,
        quality_rubric=rubric,
        repo_id=data.get("repo_id", ""),
        category=data.get("category", ""),
        setup_commands=data.get("setup_commands", []),
    )
