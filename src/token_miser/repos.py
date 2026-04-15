"""Repo cache management — cloning, fixture unpacking, version pinning."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class RepoSpec:
    id: str
    type: str = "remote"
    url: str = ""
    commit: str = ""
    bundle: str = ""
    shallow: bool = False
    setup_commands: list[str] = field(default_factory=list)


def load_repos_config(repos_yaml: Path) -> dict[str, RepoSpec]:
    """Load repo specifications from repos.yaml."""
    data = yaml.safe_load(repos_yaml.read_text())
    specs: dict[str, RepoSpec] = {}
    for entry in data.get("repos", []):
        spec = RepoSpec(
            id=entry["id"],
            type=entry.get("type", "remote"),
            url=entry.get("url", ""),
            commit=entry.get("commit", ""),
            bundle=entry.get("bundle", ""),
            shallow=entry.get("shallow", False),
            setup_commands=entry.get("setup_commands", []),
        )
        specs[spec.id] = spec
    return specs


def ensure_repo(spec: RepoSpec, cache_dir: Path, benchmarks_dir: Path | None = None) -> Path:
    """Ensure a repo is cloned and at the correct commit. Returns the local path."""
    dest = cache_dir / spec.id

    if dest.exists() and (dest / ".git").exists():
        return dest

    if spec.type == "fixture":
        bundle_path = Path(spec.bundle)
        if not bundle_path.is_absolute() and benchmarks_dir:
            bundle_path = benchmarks_dir / spec.bundle
        subprocess.run(
            ["git", "clone", str(bundle_path), str(dest)],
            check=True, capture_output=True,
        )
        if spec.commit and spec.commit != "HEAD":
            subprocess.run(
                ["git", "-C", str(dest), "checkout", spec.commit],
                check=True, capture_output=True,
            )
    else:
        clone_cmd = ["git", "clone"]
        if spec.shallow:
            clone_cmd.extend(["--depth", "1"])
        clone_cmd.extend([spec.url, str(dest)])
        subprocess.run(clone_cmd, check=True, capture_output=True)

        if spec.commit and spec.commit != "HEAD":
            if spec.shallow:
                subprocess.run(
                    ["git", "-C", str(dest), "fetch", "--depth", "1", "origin", spec.commit],
                    check=True, capture_output=True,
                )
            subprocess.run(
                ["git", "-C", str(dest), "checkout", spec.commit],
                check=True, capture_output=True,
            )

    return dest
