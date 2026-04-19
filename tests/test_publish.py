"""Tests for publish — push tuned packages to git for kanon distribution."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from token_miser.publish import generate_manifest_snippet, publish_package


@pytest.fixture
def sample_package(tmp_path: Path) -> Path:
    pkg = tmp_path / "tuned-package"
    pkg.mkdir()
    (pkg / "CLAUDE.md").write_text("# Tuned config\n")
    manifest = {
        "name": "tuned-2026-04-15",
        "version": "0.1.1",
        "author": "token-miser",
        "description": "Tuned package with 2 recommendations",
        "targets": [{"path": "CLAUDE.md", "dest": "CLAUDE.md"}],
    }
    (pkg / "manifest.yaml").write_text(yaml.dump(manifest))
    return pkg


@pytest.fixture
def target_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "target-repo"
    repo.mkdir()
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@test.com"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "Test"],
        check=True,
        capture_output=True,
    )
    (repo / "README.md").write_text("# Packages\n")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "initial"],
        check=True,
        capture_output=True,
    )
    return repo


class TestPublishPackage:
    def test_publishes_to_local_repo(self, sample_package: Path, target_repo: Path) -> None:
        result = publish_package(sample_package, str(target_repo), name="my-tuned")
        assert result["package_name"] == "my-tuned"
        assert (target_repo / "my-tuned" / "CLAUDE.md").exists()
        assert (target_repo / "my-tuned" / "manifest.yaml").exists()

    def test_uses_manifest_name_when_no_name_given(self, sample_package: Path, target_repo: Path) -> None:
        result = publish_package(sample_package, str(target_repo))
        assert result["package_name"] == "tuned-2026-04-15"

    def test_creates_git_commit(self, sample_package: Path, target_repo: Path) -> None:
        publish_package(sample_package, str(target_repo), name="my-pkg")
        log = subprocess.run(
            ["git", "-C", str(target_repo), "log", "--oneline", "-1"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert "my-pkg" in log.stdout

    def test_tags_with_version(self, sample_package: Path, target_repo: Path) -> None:
        result = publish_package(sample_package, str(target_repo), name="my-pkg", version="1.0.0")
        tags = subprocess.run(
            ["git", "-C", str(target_repo), "tag", "-l"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert "my-pkg/1.0.0" in tags.stdout
        assert result["version"] == "1.0.0"

    def test_uses_manifest_version_when_no_version_given(self, sample_package: Path, target_repo: Path) -> None:
        result = publish_package(sample_package, str(target_repo))
        tags = subprocess.run(
            ["git", "-C", str(target_repo), "tag", "-l"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert "tuned-2026-04-15/0.1.1" in tags.stdout
        assert result["version"] == "0.1.1"

    def test_invalid_package_raises(self, tmp_path: Path, target_repo: Path) -> None:
        bad = tmp_path / "no-manifest"
        bad.mkdir()
        with pytest.raises(ValueError, match="not a valid package"):
            publish_package(bad, str(target_repo))


class TestGenerateManifestSnippet:
    def test_generates_xml(self) -> None:
        snippet = generate_manifest_snippet("my-pkg", "1.0.0", "origin")
        assert '<project name="my-pkg"' in snippet
        assert 'revision="refs/tags/my-pkg/1.0.0"' in snippet
        assert 'remote="origin"' in snippet

    def test_includes_path(self) -> None:
        snippet = generate_manifest_snippet("my-pkg", "1.0.0", "origin")
        assert 'path=".packages/my-pkg"' in snippet
