"""Tests for package ref parsing."""
import pytest

from token_miser.package_ref import parse_package_ref


def test_vanilla():
    ref = parse_package_ref("vanilla")
    assert ref.name == "vanilla"
    assert ref.package_path == ""


def test_existing_directory(tmp_path):
    ref = parse_package_ref(str(tmp_path))
    assert ref.name == tmp_path.name
    assert ref.package_path == str(tmp_path)


def test_nonexistent_path():
    with pytest.raises(ValueError, match="does not exist"):
        parse_package_ref("/tmp/definitely-does-not-exist-9999")


def test_file_path_rejected(tmp_path):
    f = tmp_path / "file.txt"
    f.write_text("x")
    with pytest.raises(ValueError, match="not a directory"):
        parse_package_ref(str(f))
