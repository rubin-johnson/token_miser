"""Tests for tune builder."""

import yaml

from token_miser.recommend import Recommendation
from token_miser.tune_builder import build_tuned_package


def _base_bundle(tmp_path):
    """Create a minimal base bundle directory."""
    base = tmp_path / "base-bundle"
    base.mkdir()
    (base / "CLAUDE.md").write_text("# My Config\nBe concise.\n")
    (base / "manifest.yaml").write_text(
        "name: base-bundle\n"
        "version: 0.1.0\n"
        "author: test\n"
        "description: Base config\n"
        "targets:\n"
        "  - path: CLAUDE.md\n"
        "    dest: CLAUDE.md\n"
    )
    return base


def _sample_recs():
    return [
        Recommendation(
            category="token_efficiency",
            title="Add grep-first rule",
            description="Reduces token usage by avoiding full file reads.",
            claude_md_block="- Use grep/glob before reading full files",
            confidence=0.9,
            evidence="avg tokens > 40000",
        ),
        Recommendation(
            category="quality",
            title="Re-read requirement",
            description="Improves pass rate.",
            claude_md_block="- Re-read the requirement before marking done",
            confidence=0.8,
            evidence="pass rate < 85%",
        ),
    ]


class TestBuildTunedPackage:
    def test_builds_valid_bundle(self, tmp_path):
        base = _base_bundle(tmp_path)
        out = tmp_path / "tuned"
        result = build_tuned_package(base, _sample_recs(), out, name="my-tuned")
        assert result == out
        assert (out / "AGENTS.md").exists()
        assert (out / "CLAUDE.md").exists()
        assert (out / "manifest.yaml").exists()

    def test_appends_recommendations_to_agents_md(self, tmp_path):
        base = _base_bundle(tmp_path)
        out = tmp_path / "tuned"
        build_tuned_package(base, _sample_recs(), out)
        content = (out / "AGENTS.md").read_text()
        assert "## Token Miser Recommendations" in content
        assert "grep/glob before reading full files" in content
        assert "Re-read the requirement" in content
        assert "# My Config" in content  # original preserved
        assert (out / "CLAUDE.md").read_text() == "@AGENTS.md\n"

    def test_creates_agents_md_if_claude_md_missing(self, tmp_path):
        base = _base_bundle(tmp_path)
        (base / "CLAUDE.md").unlink()
        out = tmp_path / "tuned"
        build_tuned_package(base, _sample_recs(), out)
        content = (out / "AGENTS.md").read_text()
        assert "## Token Miser Recommendations" in content

    def test_updates_manifest_name(self, tmp_path):
        base = _base_bundle(tmp_path)
        out = tmp_path / "tuned"
        build_tuned_package(base, _sample_recs(), out, name="custom-name")
        manifest = yaml.safe_load((out / "manifest.yaml").read_text())
        assert manifest["name"] == "custom-name"

    def test_updates_manifest_version(self, tmp_path):
        base = _base_bundle(tmp_path)
        out = tmp_path / "tuned"
        build_tuned_package(base, _sample_recs(), out)
        manifest = yaml.safe_load((out / "manifest.yaml").read_text())
        assert manifest["version"] == "0.1.1"

    def test_updates_manifest_description(self, tmp_path):
        base = _base_bundle(tmp_path)
        out = tmp_path / "tuned"
        build_tuned_package(base, _sample_recs(), out)
        manifest = yaml.safe_load((out / "manifest.yaml").read_text())
        assert "2 recommendations" in manifest["description"]

    def test_default_name_when_not_provided(self, tmp_path):
        base = _base_bundle(tmp_path)
        out = tmp_path / "tuned"
        build_tuned_package(base, _sample_recs(), out)
        manifest = yaml.safe_load((out / "manifest.yaml").read_text())
        assert manifest["name"].startswith("tuned-")

    def test_empty_recommendations_copies_unchanged(self, tmp_path):
        base = _base_bundle(tmp_path)
        out = tmp_path / "tuned"
        build_tuned_package(base, [], out)
        content = (out / "CLAUDE.md").read_text()
        assert content == "# My Config\nBe concise.\n"
        assert not (out / "AGENTS.md").exists()
        manifest = yaml.safe_load((out / "manifest.yaml").read_text())
        assert manifest["name"] == "base-bundle"
        assert manifest["version"] == "0.1.0"

    def test_overwrites_existing_output_dir(self, tmp_path):
        base = _base_bundle(tmp_path)
        out = tmp_path / "tuned"
        out.mkdir()
        (out / "stale.txt").write_text("old stuff")
        build_tuned_package(base, _sample_recs(), out, name="fresh")
        assert not (out / "stale.txt").exists()
        assert (out / "CLAUDE.md").exists()
