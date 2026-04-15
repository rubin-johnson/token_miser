"""Arm parsing — resolves CLI spec to a loadout path."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Arm:
    name: str
    loadout_path: str = ""


def parse_arm(spec: str) -> Arm:
    """Parse an arm spec from CLI arguments.

    'vanilla' -> Arm with no loadout (baseline).
    Any other string -> must be an existing directory (loadout bundle path).
    """
    if spec == "vanilla":
        return Arm(name="vanilla")

    path = Path(spec)
    if not path.exists():
        raise ValueError(f"Arm path does not exist: {spec}")
    if not path.is_dir():
        raise ValueError(f"Arm path is not a directory: {spec}")

    return Arm(name=path.name, loadout_path=str(path.resolve()))
