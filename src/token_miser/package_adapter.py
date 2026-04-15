"""Adapter wrapping loadout and kanon Python APIs.

All loadout/kanon interactions go through this module, isolating the
coupling so the rest of token_miser doesn't import them directly.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from loadout.apply import apply_package as _loadout_apply
from loadout.pack import pack as _loadout_pack
from loadout.restore import restore_package as _loadout_restore
from loadout.state import read_state
from loadout.validate import validate_package as _loadout_validate


def read_active_state(target: Path) -> dict[str, Any] | None:
    """Read the currently active loadout package state."""
    return read_state(target)


def validate_package(bundle_path: Path) -> list[str]:
    """Validate a loadout package, returning a list of errors (empty = valid)."""
    return _loadout_validate(bundle_path)


def apply_package(bundle_path: Path, target: Path) -> None:
    """Apply a loadout package to the target directory."""
    _loadout_apply(bundle_path, target, yes=True)


def restore_package(target: Path) -> None:
    """Restore the target directory from its most recent backup."""
    _loadout_restore(target, yes=True)


def pack_current_config(source: Path, output: Path) -> Path:
    """Capture the current config at source as a loadout package."""
    _loadout_pack(source, output, yes=True)
    return output


def create_package(
    name: str,
    version: str,
    author: str,
    description: str,
    files: dict[str, str],
    output_dir: Path,
) -> Path:
    """Programmatically create a loadout package from file contents."""
    output_dir.mkdir(parents=True, exist_ok=True)

    targets = []
    for filename, content in files.items():
        (output_dir / filename).write_text(content)
        targets.append({"path": filename, "dest": filename})

    manifest = {
        "name": name,
        "version": version,
        "author": author,
        "description": description,
        "targets": targets,
    }
    with (output_dir / "manifest.yaml").open("w") as f:
        yaml.dump(manifest, f, default_flow_style=False)

    return output_dir


def discover_kanon_packages(kanonenv_path: Path) -> list[Path]:
    """Discover loadout packages available via kanon's .packages/ directory.

    Looks for a .packages/ sibling directory next to the .kanon file and
    returns paths to any subdirectories that contain a manifest.yaml.
    """
    if not kanonenv_path.exists():
        return []

    packages_dir = kanonenv_path.parent / ".packages"
    if not packages_dir.is_dir():
        return []

    packages = []
    for item in sorted(packages_dir.iterdir()):
        if item.is_dir() and (item / "manifest.yaml").exists():
            packages.append(item)
    return packages
