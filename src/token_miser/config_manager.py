"""Adapter wrapping loadout and kanon Python APIs.

All loadout/kanon interactions go through this module, isolating the
coupling so the rest of token_miser doesn't import them directly.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from loadout.apply import apply_bundle
from loadout.capture import capture_bundle
from loadout.restore import restore_bundle
from loadout.state import read_state
from loadout.validate import validate_bundle


def read_active_profile(target: Path) -> dict[str, Any] | None:
    """Read the currently active loadout profile state."""
    return read_state(target)


def validate_profile(bundle_path: Path) -> list[str]:
    """Validate a loadout bundle, returning a list of errors (empty = valid)."""
    return validate_bundle(bundle_path)


def apply_profile(bundle_path: Path, target: Path) -> None:
    """Apply a loadout bundle to the target directory."""
    apply_bundle(bundle_path, target, yes=True)


def restore_profile(target: Path) -> None:
    """Restore the target directory from its most recent backup."""
    restore_bundle(target, yes=True)


def capture_current_config(source: Path, output: Path) -> Path:
    """Capture the current config at source as a loadout bundle."""
    capture_bundle(source, output, yes=True)
    return output


def create_profile_bundle(
    name: str,
    version: str,
    author: str,
    description: str,
    files: dict[str, str],
    output_dir: Path,
) -> Path:
    """Programmatically create a loadout bundle from file contents."""
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


def discover_kanon_profiles(kanonenv_path: Path) -> list[Path]:
    """Discover loadout bundles available via kanon's .packages/ directory.

    Looks for a .packages/ sibling directory next to the .kanon file and
    returns paths to any subdirectories that contain a manifest.yaml.
    """
    if not kanonenv_path.exists():
        return []

    packages_dir = kanonenv_path.parent / ".packages"
    if not packages_dir.is_dir():
        return []

    profiles = []
    for item in sorted(packages_dir.iterdir()):
        if item.is_dir() and (item / "manifest.yaml").exists():
            profiles.append(item)
    return profiles
