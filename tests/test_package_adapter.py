"""Tests for package_adapter — adapter wrapping loadout and kanon APIs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from token_miser.package_adapter import (
    apply_package,
    create_package,
    discover_kanon_packages,
    pack_current_config,
    read_active_state,
    restore_package,
    validate_package,
)


@pytest.fixture
def target_dir(tmp_path: Path) -> Path:
    target = tmp_path / ".claude"
    target.mkdir()
    return target


@pytest.fixture
def sample_bundle(tmp_path: Path) -> Path:
    bundle = tmp_path / "my-bundle"
    bundle.mkdir()
    (bundle / "CLAUDE.md").write_text("# Test config\n")
    manifest = {
        "name": "my-bundle",
        "version": "0.1.0",
        "author": "test",
        "description": "test bundle",
        "targets": [{"path": "CLAUDE.md", "dest": "CLAUDE.md"}],
    }
    (bundle / "manifest.yaml").write_text(yaml.dump(manifest))
    return bundle


class TestReadActiveState:
    def test_returns_none_when_no_state(self, target_dir: Path) -> None:
        assert read_active_state(target_dir) is None

    def test_returns_state_when_present(self, target_dir: Path) -> None:
        state = {"active": "my-bundle", "manifest_version": "0.1.0"}
        (target_dir / ".loadout-state.json").write_text(json.dumps(state))
        result = read_active_state(target_dir)
        assert result is not None
        assert result["active"] == "my-bundle"


class TestValidatePackage:
    def test_valid_bundle_returns_empty(self, sample_bundle: Path) -> None:
        assert validate_package(sample_bundle) == []

    def test_missing_manifest_returns_errors(self, tmp_path: Path) -> None:
        bundle = tmp_path / "bad-bundle"
        bundle.mkdir()
        errors = validate_package(bundle)
        assert len(errors) > 0

    def test_nonexistent_path_returns_errors(self, tmp_path: Path) -> None:
        errors = validate_package(tmp_path / "nope")
        assert len(errors) > 0


class TestApplyPackage:
    def test_applies_bundle_to_target(self, sample_bundle: Path, target_dir: Path) -> None:
        apply_package(sample_bundle, target_dir)
        assert (target_dir / "CLAUDE.md").read_text() == "# Test config\n"

    def test_creates_backup(self, sample_bundle: Path, target_dir: Path) -> None:
        (target_dir / "CLAUDE.md").write_text("# Old config\n")
        apply_package(sample_bundle, target_dir)
        backups = list((target_dir / ".loadout-backups").iterdir())
        assert len(backups) == 1


class TestRestorePackage:
    def test_restore_after_apply(self, sample_bundle: Path, target_dir: Path) -> None:
        (target_dir / "CLAUDE.md").write_text("# Original\n")
        apply_package(sample_bundle, target_dir)
        assert (target_dir / "CLAUDE.md").read_text() == "# Test config\n"
        restore_package(target_dir)
        assert (target_dir / "CLAUDE.md").read_text() == "# Original\n"


class TestPackCurrentConfig:
    def test_captures_claude_md(self, tmp_path: Path) -> None:
        source = tmp_path / "source"
        source.mkdir()
        (source / "CLAUDE.md").write_text("# My config\n")
        output = tmp_path / "captured"
        result = pack_current_config(source, output)
        assert result == output
        assert (output / "CLAUDE.md").read_text() == "# My config\n"
        assert (output / "manifest.yaml").exists()

    def test_captures_empty_source(self, tmp_path: Path) -> None:
        source = tmp_path / "empty-source"
        source.mkdir()
        output = tmp_path / "captured"
        result = pack_current_config(source, output)
        assert result == output
        assert (output / "manifest.yaml").exists()


class TestCreatePackage:
    def test_creates_valid_bundle(self, tmp_path: Path) -> None:
        output = tmp_path / "new-bundle"
        files = {"CLAUDE.md": "# Generated config\n"}
        result = create_package(
            name="gen-bundle",
            version="1.0.0",
            author="token-miser",
            description="Generated bundle",
            files=files,
            output_dir=output,
        )
        assert result == output
        assert (output / "CLAUDE.md").read_text() == "# Generated config\n"
        manifest = yaml.safe_load((output / "manifest.yaml").read_text())
        assert manifest["name"] == "gen-bundle"
        assert manifest["version"] == "1.0.0"
        assert validate_package(output) == []

    def test_creates_targets_for_each_file(self, tmp_path: Path) -> None:
        output = tmp_path / "multi"
        files = {"CLAUDE.md": "# config\n", "settings.json": '{"theme":"dark"}'}
        create_package("multi", "0.1.0", "test", "desc", files, output)
        manifest = yaml.safe_load((output / "manifest.yaml").read_text())
        paths = [t["path"] for t in manifest["targets"]]
        assert "CLAUDE.md" in paths
        assert "settings.json" in paths


class TestDiscoverKanonPackages:
    def test_returns_empty_when_no_kanonenv(self, tmp_path: Path) -> None:
        result = discover_kanon_packages(tmp_path / ".kanon")
        assert result == []

    def test_returns_bundle_dirs_from_packages(self, tmp_path: Path) -> None:
        # Create a .packages dir with loadout bundles
        packages = tmp_path / ".packages"
        packages.mkdir()
        bundle = packages / "my-loadout"
        bundle.mkdir()
        (bundle / "manifest.yaml").write_text(
            yaml.dump(
                {
                    "name": "my-loadout",
                    "version": "0.1.0",
                    "author": "test",
                    "description": "a loadout",
                    "targets": [{"path": "CLAUDE.md", "dest": "CLAUDE.md"}],
                }
            )
        )
        (bundle / "CLAUDE.md").write_text("# config\n")

        # Create a .kanon file pointing to this location
        kanonenv = tmp_path / ".kanon"
        kanonenv.write_text(
            "KANON_SOURCE_loadouts_URL=https://example.com/repo.git\n"
            "KANON_SOURCE_loadouts_REVISION=main\n"
            "KANON_SOURCE_loadouts_PATH=manifest.xml\n"
        )

        result = discover_kanon_packages(kanonenv)
        assert len(result) == 1
        assert result[0].name == "my-loadout"
