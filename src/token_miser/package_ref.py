"""Package ref parsing — resolves CLI spec to a package path."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PackageRef:
    name: str
    package_path: str = ""


def resolve_packages_dir(packages_dir: str | None = None) -> Path:
    if packages_dir:
        return Path(packages_dir).expanduser().resolve()
    env = os.environ.get("TOKEN_MISER_PACKAGES_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return Path("packages").resolve()


def list_packages(packages_dir: str | None = None) -> list[str]:
    d = resolve_packages_dir(packages_dir)
    if not d.is_dir():
        return []
    return sorted(p.name for p in d.iterdir() if p.is_dir())


def parse_package_ref(spec: str, packages_dir: str | None = None) -> PackageRef:
    """Parse a package ref spec from CLI arguments.

    'vanilla' -> PackageRef with no package (baseline).
    Spec with / or \\ -> literal path (existing behavior).
    Otherwise -> name-based lookup in packages_dir.
    """
    if spec == "vanilla":
        return PackageRef(name="vanilla")

    if "/" in spec or "\\" in spec:
        path = Path(spec)
        if not path.exists():
            raise ValueError(f"Package path does not exist: {spec}")
        if not path.is_dir():
            raise ValueError(f"Package path is not a directory: {spec}")
        return PackageRef(name=path.name, package_path=str(path.resolve()))

    resolved = resolve_packages_dir(packages_dir)
    pkg_path = resolved / spec
    if not pkg_path.is_dir():
        available = list_packages(packages_dir)
        avail_str = ", ".join(available) if available else "(none)"
        raise ValueError(f"Package '{spec}' not found in {resolved}/ (available: {avail_str})")
    return PackageRef(name=spec, package_path=str(pkg_path.resolve()))
