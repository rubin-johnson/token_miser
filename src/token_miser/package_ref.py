"""Package ref parsing — resolves CLI spec to a package path."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class PackageRef:
    name: str
    package_path: str = ""


def parse_package_ref(spec: str) -> PackageRef:
    """Parse a package ref spec from CLI arguments.

    'vanilla' -> PackageRef with no package (baseline).
    Any other string -> must be an existing directory (package path).
    """
    if spec == "vanilla":
        return PackageRef(name="vanilla")

    path = Path(spec)
    if not path.exists():
        raise ValueError(f"Package path does not exist: {spec}")
    if not path.is_dir():
        raise ValueError(f"Package path is not a directory: {spec}")

    return PackageRef(name=path.name, package_path=str(path.resolve()))
