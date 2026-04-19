"""Tests for repos — clone cache management and fixture unpacking."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from token_miser.repos import RepoSpec, ensure_repo, load_repos_config


@pytest.fixture
def repos_yaml(tmp_path: Path) -> Path:
    data = {
        "repos": [
            {
                "id": "tiny-cli",
                "type": "fixture",
                "bundle": "fixtures/tiny-cli/repo.bundle",
                "commit": "HEAD",
            },
            {
                "id": "flask",
                "url": "https://github.com/pallets/flask.git",
                "commit": "3262451",
                "shallow": True,
            },
        ]
    }
    path = tmp_path / "repos.yaml"
    path.write_text(yaml.dump(data))
    return path


class TestLoadReposConfig:
    def test_loads_specs(self, repos_yaml: Path) -> None:
        specs = load_repos_config(repos_yaml)
        assert len(specs) == 2
        assert specs["tiny-cli"].id == "tiny-cli"
        assert specs["tiny-cli"].type == "fixture"
        assert specs["flask"].url == "https://github.com/pallets/flask.git"

    def test_empty_file(self, tmp_path: Path) -> None:
        path = tmp_path / "repos.yaml"
        path.write_text(yaml.dump({"repos": []}))
        assert load_repos_config(path) == {}


class TestRepoSpec:
    def test_fixture_spec(self, repos_yaml: Path) -> None:
        specs = load_repos_config(repos_yaml)
        s = specs["tiny-cli"]
        assert s.type == "fixture"
        assert s.bundle == "fixtures/tiny-cli/repo.bundle"

    def test_remote_spec(self, repos_yaml: Path) -> None:
        specs = load_repos_config(repos_yaml)
        s = specs["flask"]
        assert s.type == "remote"
        assert s.shallow is True


class TestEnsureRepo:
    def test_clones_fixture_from_bundle(self, tmp_path: Path) -> None:
        # Create a real git repo and export it as a bundle
        repo_dir = tmp_path / "source-repo"
        repo_dir.mkdir()
        subprocess.run(["git", "init", str(repo_dir)], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(repo_dir), "config", "user.email", "test@test.com"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(repo_dir), "config", "user.name", "Test"],
            check=True,
            capture_output=True,
        )
        (repo_dir / "main.py").write_text("print('hello')\n")
        subprocess.run(["git", "-C", str(repo_dir), "add", "."], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(repo_dir), "commit", "-m", "initial"],
            check=True,
            capture_output=True,
        )

        # Export as bundle
        bundle_path = tmp_path / "repo.bundle"
        subprocess.run(
            ["git", "-C", str(repo_dir), "bundle", "create", str(bundle_path), "--all"],
            check=True,
            capture_output=True,
        )

        spec = RepoSpec(id="test-fixture", type="fixture", bundle=str(bundle_path), commit="HEAD")
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        result = ensure_repo(spec, cache_dir, benchmarks_dir=tmp_path)
        assert result.is_dir()
        assert (result / "main.py").exists()

    def test_idempotent_clone(self, tmp_path: Path) -> None:
        # Create repo + bundle
        repo_dir = tmp_path / "source-repo"
        repo_dir.mkdir()
        subprocess.run(["git", "init", str(repo_dir)], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(repo_dir), "config", "user.email", "test@test.com"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(repo_dir), "config", "user.name", "Test"],
            check=True,
            capture_output=True,
        )
        (repo_dir / "main.py").write_text("print('hello')\n")
        subprocess.run(["git", "-C", str(repo_dir), "add", "."], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(repo_dir), "commit", "-m", "initial"],
            check=True,
            capture_output=True,
        )
        bundle_path = tmp_path / "repo.bundle"
        subprocess.run(
            ["git", "-C", str(repo_dir), "bundle", "create", str(bundle_path), "--all"],
            check=True,
            capture_output=True,
        )

        spec = RepoSpec(id="test-fixture", type="fixture", bundle=str(bundle_path), commit="HEAD")
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        result1 = ensure_repo(spec, cache_dir, benchmarks_dir=tmp_path)
        result2 = ensure_repo(spec, cache_dir, benchmarks_dir=tmp_path)
        assert result1 == result2
