"""Tests for package ref parsing."""
import pytest

from token_miser.package_ref import (
    list_packages,
    parse_package_ref,
    resolve_packages_dir,
)


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


# --- resolve_packages_dir ---

def test_resolve_explicit_flag(tmp_path):
    assert resolve_packages_dir(str(tmp_path)) == tmp_path.resolve()


def test_resolve_env_var(tmp_path, monkeypatch):
    monkeypatch.setenv("TOKEN_MISER_PACKAGES_DIR", str(tmp_path))
    assert resolve_packages_dir() == tmp_path.resolve()


def test_resolve_flag_beats_env(tmp_path, monkeypatch):
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.setenv("TOKEN_MISER_PACKAGES_DIR", str(tmp_path))
    assert resolve_packages_dir(str(other)) == other.resolve()


def test_resolve_default_fallback(monkeypatch):
    monkeypatch.delenv("TOKEN_MISER_PACKAGES_DIR", raising=False)
    assert resolve_packages_dir().name == "packages"


# --- list_packages ---

def test_list_packages(tmp_path):
    (tmp_path / "alpha").mkdir()
    (tmp_path / "bravo").mkdir()
    (tmp_path / "somefile.txt").write_text("x")
    assert list_packages(str(tmp_path)) == ["alpha", "bravo"]


def test_list_packages_empty(tmp_path):
    assert list_packages(str(tmp_path)) == []


def test_list_packages_nonexistent():
    assert list_packages("/tmp/no-such-dir-999") == []


# --- name-based lookup ---

def test_name_lookup(tmp_path):
    (tmp_path / "token-miser").mkdir()
    ref = parse_package_ref("token-miser", packages_dir=str(tmp_path))
    assert ref.name == "token-miser"
    assert ref.package_path == str((tmp_path / "token-miser").resolve())


def test_name_lookup_not_found(tmp_path):
    (tmp_path / "alpha").mkdir()
    with pytest.raises(ValueError, match=r"Package 'nope' not found.*available: alpha"):
        parse_package_ref("nope", packages_dir=str(tmp_path))


def test_name_lookup_empty_dir(tmp_path):
    with pytest.raises(ValueError, match=r"available: \(none\)"):
        parse_package_ref("nope", packages_dir=str(tmp_path))


def test_slash_path_bypasses_name_lookup(tmp_path):
    ref = parse_package_ref(str(tmp_path))
    assert ref.package_path == str(tmp_path.resolve())


def test_name_lookup_via_env(tmp_path, monkeypatch):
    (tmp_path / "slim-rubin").mkdir()
    monkeypatch.setenv("TOKEN_MISER_PACKAGES_DIR", str(tmp_path))
    ref = parse_package_ref("slim-rubin")
    assert ref.name == "slim-rubin"
    assert ref.package_path == str((tmp_path / "slim-rubin").resolve())
