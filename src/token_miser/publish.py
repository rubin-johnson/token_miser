"""Publish a tuned package to a git repo for kanon distribution."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import yaml
from loadout.validate import validate_package


def publish_package(
    package_path: Path,
    repo_url: str,
    name: str | None = None,
    version: str | None = None,
    branch: str = "main",
) -> dict[str, str]:
    """Publish a package to a git repo for kanon distribution.

    Returns dict with package_name, version, and tag.
    """
    errors = validate_package(package_path)
    if errors:
        raise ValueError(f"{package_path} is not a valid package:\n" + "\n".join(f"  - {e}" for e in errors))

    manifest = yaml.safe_load((package_path / "manifest.yaml").read_text())
    pkg_name = name or manifest.get("name", package_path.name)
    pkg_version = version or manifest.get("version", "0.0.1")
    tag = f"{pkg_name}/{pkg_version}"

    # Clone or use local repo
    repo_path = Path(repo_url)
    is_local = repo_path.is_dir() and (repo_path / ".git").exists()

    if is_local:
        target_dir = repo_path
    else:
        raise ValueError("Remote repo publishing not yet implemented. Use a local repo path.")

    # Copy package into repo
    dest = target_dir / pkg_name
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(package_path, dest)

    # Update manifest name/version in the published copy
    pub_manifest = yaml.safe_load((dest / "manifest.yaml").read_text())
    pub_manifest["name"] = pkg_name
    pub_manifest["version"] = pkg_version
    with (dest / "manifest.yaml").open("w") as f:
        yaml.dump(pub_manifest, f, default_flow_style=False, sort_keys=False)

    # Git add, commit, tag
    subprocess.run(["git", "-C", str(target_dir), "add", pkg_name], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(target_dir), "commit", "-m", f"publish: {pkg_name} v{pkg_version}"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(target_dir), "tag", tag],
        check=True,
        capture_output=True,
    )

    return {"package_name": pkg_name, "version": pkg_version, "tag": tag}


def generate_manifest_snippet(name: str, version: str, remote: str = "origin") -> str:
    """Generate a kanon XML manifest snippet for a published package."""
    return f'<project name="{name}" path=".packages/{name}" remote="{remote}" revision="refs/tags/{name}/{version}" />'
