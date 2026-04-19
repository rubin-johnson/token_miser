"""Tune builder: creates tuned loadout packages from recommendations."""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

import yaml

from token_miser.recommend import Recommendation


def _bump_patch(version: str) -> str:
    parts = version.split(".")
    if len(parts) == 3:
        parts[2] = str(int(parts[2]) + 1)
        return ".".join(parts)
    return version


def build_tuned_package(
    base_bundle_path: Path,
    recommendations: list[Recommendation],
    output_dir: Path,
    name: str = "",
) -> Path:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    shutil.copytree(base_bundle_path, output_dir)

    if not recommendations:
        return output_dir

    agents_md_path = output_dir / "AGENTS.md"
    claude_md_path = output_dir / "CLAUDE.md"
    if agents_md_path.exists():
        existing = agents_md_path.read_text()
    elif claude_md_path.exists():
        existing = claude_md_path.read_text()
    else:
        existing = ""

    blocks = [r.claude_md_block for r in recommendations]
    section = "\n## Token Miser Recommendations\n\n" + "\n\n".join(blocks) + "\n"
    agents_md_path.write_text(existing + section)
    claude_md_path.write_text("@AGENTS.md\n")

    manifest_path = output_dir / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text())
    targets = manifest.get("targets") or []
    paths = {t.get("path") for t in targets if isinstance(t, dict)}
    if "AGENTS.md" not in paths:
        targets.append({"path": "AGENTS.md", "dest": "AGENTS.md"})
    if "CLAUDE.md" not in paths:
        targets.append({"path": "CLAUDE.md", "dest": "CLAUDE.md"})
    manifest["targets"] = targets
    manifest["name"] = name if name else f"tuned-{date.today().isoformat()}"
    manifest["version"] = _bump_patch(manifest.get("version", "0.0.0"))
    manifest["description"] = f"Tuned package with {len(recommendations)} recommendations"
    with open(manifest_path, "w") as f:
        yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)

    return output_dir
