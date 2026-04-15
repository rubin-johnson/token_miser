"""Tests for arm parsing."""
import pytest

from token_miser.arm import parse_arm


def test_vanilla():
    arm = parse_arm("vanilla")
    assert arm.name == "vanilla"
    assert arm.loadout_path == ""


def test_existing_directory(tmp_path):
    arm = parse_arm(str(tmp_path))
    assert arm.name == tmp_path.name
    assert arm.loadout_path == str(tmp_path)


def test_nonexistent_path():
    with pytest.raises(ValueError, match="does not exist"):
        parse_arm("/tmp/definitely-does-not-exist-9999")


def test_file_path_rejected(tmp_path):
    f = tmp_path / "file.txt"
    f.write_text("x")
    with pytest.raises(ValueError, match="not a directory"):
        parse_arm(str(f))
