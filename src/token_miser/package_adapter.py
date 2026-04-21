"""Adapter providing loadout-compatible package operations.

All package management interactions go through this module, isolating the
coupling so the rest of token_miser doesn't import them directly.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

_REQUIRED_FIELDS = {"name", "version", "author", "description", "targets"}
_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
_BACKUP_DIR = ".loadout-backups"
_STATE_FILE = ".loadout-state.json"


def read_active_state(target: Path) -> dict[str, Any] | None:
    path = target / _STATE_FILE
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        print(f"Warning: state file is corrupted and will be ignored: {path}", file=sys.stderr)
        return None


def validate_package(bundle_path: Path) -> list[str]:
    errors: list[str] = []
    if bundle_path is None:
        errors.append("No package path provided")
        return errors
    if not bundle_path.exists():
        errors.append(f"Package path does not exist: {bundle_path}")
        return errors
    if not bundle_path.is_dir():
        errors.append(f"Package path is not a directory: {bundle_path}")
        return errors
    manifest_path = bundle_path / "manifest.yaml"
    if not manifest_path.exists():
        errors.append("manifest.yaml not found in package")
        return errors
    try:
        data = yaml.safe_load(manifest_path.read_text())
    except yaml.YAMLError as e:
        errors.append(f"manifest.yaml is not valid YAML: {e}")
        return errors
    if not isinstance(data, dict):
        errors.append("manifest.yaml must be a YAML mapping")
        return errors
    for f in _REQUIRED_FIELDS:
        if f not in data or data[f] is None:
            errors.append(f"missing required field: {f}")
    version = data.get("version")
    if version and (not isinstance(version, str) or not _SEMVER_RE.match(str(version))):
        errors.append(f"invalid semver version: {version!r}")
    targets = data.get("targets") or []
    declared_paths = []
    for i, t in enumerate(targets):
        if not isinstance(t, dict):
            errors.append(f"target {i} is not a mapping")
            continue
        if "path" not in t:
            errors.append(f"target {i} missing 'path'")
        if "dest" not in t:
            errors.append(f"target {i} missing 'dest'")
        if "path" in t:
            declared_paths.append(t["path"])
    for p in declared_paths:
        src = (bundle_path / p).resolve()
        if not src.is_relative_to(bundle_path.resolve()):
            errors.append(f"Target source escapes package directory: {p}")
            continue
        if not src.exists():
            errors.append(f"Target source not found in package: {p}")
    return errors


def apply_package(bundle_path: Path, target: Path) -> None:
    errors = validate_package(bundle_path)
    if errors:
        raise ValueError("Package validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

    data = yaml.safe_load((bundle_path / "manifest.yaml").read_text())
    targets = data.get("targets") or []

    def _resolve_dest(dest_str: str) -> Path | None:
        if dest_str.startswith("~/.claude/"):
            dest_str = dest_str[len("~/.claude/"):]
        elif dest_str in ("~/.claude", "~") or dest_str.startswith("/"):
            return None
        elif dest_str.startswith("~/"):
            dest_str = dest_str[2:]
        if not dest_str:
            return None
        resolved = (target / dest_str).resolve()
        if not resolved.is_relative_to(target.resolve()):
            return None
        return resolved

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
    backup_dir = target / _BACKUP_DIR / timestamp
    target.mkdir(parents=True, exist_ok=True)
    backup_dir.mkdir(parents=True, exist_ok=True)

    for entry in targets:
        if not isinstance(entry, dict) or "dest" not in entry:
            continue
        dest = _resolve_dest(entry["dest"])
        if dest is None or not dest.exists():
            continue
        rel = dest.relative_to(target.resolve())
        backup_dest = backup_dir / rel
        backup_dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.is_dir():
            shutil.copytree(dest, backup_dest)
        else:
            shutil.copy2(dest, backup_dest)

    placed_paths: list[str] = []
    with tempfile.TemporaryDirectory(dir=target.parent) as staging_str:
        staging = Path(staging_str)
        staged: list[tuple[Path, Path]] = []
        for entry in targets:
            if not isinstance(entry, dict) or "path" not in entry or "dest" not in entry:
                continue
            src = bundle_path / entry["path"]
            if not src.resolve().is_relative_to(bundle_path.resolve()):
                continue
            dest = _resolve_dest(entry["dest"])
            if dest is None:
                continue
            staged_dest = staging / entry["path"]
            staged_dest.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                shutil.copytree(src, staged_dest)
            else:
                shutil.copy2(src, staged_dest)
            staged.append((staged_dest, dest))
            placed_paths.append(str(dest))
        for staged_path, final_dest in staged:
            final_dest.parent.mkdir(parents=True, exist_ok=True)
            if final_dest.exists() and final_dest.is_dir():
                shutil.rmtree(final_dest)
            shutil.move(str(staged_path), final_dest)

    state = {
        "active": data.get("name", bundle_path.name),
        "applied_at": datetime.now(timezone.utc).isoformat(),
        "package_path": str(bundle_path.resolve()),
        "manifest_version": data.get("version", ""),
        "backup": timestamp,
        "placed_paths": placed_paths,
    }
    state_path = target / _STATE_FILE
    state_path.write_text(json.dumps(state, indent=2) + "\n")


def restore_package(target: Path) -> None:
    state = read_active_state(target)
    if state is None:
        raise ValueError("No active loadout state found. Nothing to restore.")
    backup = state.get("backup")
    if not backup:
        raise ValueError("State file has no backup timestamp. Cannot restore.")
    backup_dir = target / _BACKUP_DIR / backup
    if not backup_dir.exists():
        raise ValueError(f"Backup not found: {backup_dir}")

    placed_paths = state.get("placed_paths")
    target_resolved = target.resolve()
    if placed_paths is not None:
        for path_str in placed_paths:
            p = Path(path_str).resolve()
            if not p.is_relative_to(target_resolved):
                continue
            if p.exists():
                if p.is_dir():
                    shutil.rmtree(p)
                else:
                    p.unlink()

    for backup_file in backup_dir.rglob("*"):
        if not backup_file.is_file():
            continue
        rel = backup_file.relative_to(backup_dir)
        dest = target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup_file, dest)

    state_path = target / _STATE_FILE
    if state_path.exists():
        state_path.unlink()


def pack_current_config(source: Path, output: Path) -> Path:
    _DEFAULT_TARGETS = [
        ("CLAUDE.md", "CLAUDE.md"),
        ("AGENTS.md", "AGENTS.md"),
        ("settings.json", "settings.json"),
        ("hooks", "hooks"),
        ("bin", "bin"),
    ]
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    targets = []
    for src_name, dest_name in _DEFAULT_TARGETS:
        src = source / src_name
        if not src.exists():
            continue
        dest = output / src_name
        if src.is_dir():
            shutil.copytree(src, dest)
        else:
            shutil.copy2(src, dest)
        targets.append({"path": src_name, "dest": dest_name})
    manifest_data = {
        "name": output.name,
        "version": "0.0.1",
        "author": "packed",
        "description": f"Packed from {source}",
        "targets": targets,
    }
    with (output / "manifest.yaml").open("w") as f:
        yaml.dump(manifest_data, f, default_flow_style=False)
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
