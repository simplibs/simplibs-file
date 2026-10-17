import os
from pathlib import Path
import pytest
from simplibs.file.rules._helpers import read_file_size


def test_read_file_size_returns_the_size_in_bytes(tmp_path) -> None:
    target = tmp_path / "a.bin"
    target.write_bytes(b"12345")
    assert read_file_size(target) == 5


def test_read_file_size_of_an_empty_file_is_zero_not_none(tmp_path) -> None:
    target = tmp_path / "empty.bin"
    target.write_bytes(b"")
    result = read_file_size(target)
    assert result == 0
    assert result is not None


def test_read_file_size_counts_bytes_not_characters(tmp_path) -> None:
    target = tmp_path / "text.txt"
    target.write_bytes("č".encode("utf-8"))
    assert read_file_size(target) == 2


def test_read_file_size_is_none_for_a_missing_path(tmp_path) -> None:
    assert read_file_size(tmp_path / "missing.bin") is None


def test_read_file_size_is_none_for_a_directory(tmp_path) -> None:
    assert read_file_size(tmp_path) is None


def test_read_file_size_is_none_for_a_path_with_a_null_byte() -> None:
    assert read_file_size(Path("a\0b")) is None


def test_read_file_size_follows_a_symlink_to_a_file(tmp_path, symlink_or_skip) -> None:
    target = tmp_path / "target.bin"
    target.write_bytes(b"123")
    link = tmp_path / "link.bin"
    symlink_or_skip(link, target)
    assert read_file_size(link) == 3


def test_read_file_size_is_none_for_a_dangling_symlink(tmp_path, symlink_or_skip) -> None:
    link = tmp_path / "dangling.bin"
    symlink_or_skip(link, tmp_path / "nowhere.bin")
    assert read_file_size(link) is None


@pytest.mark.parametrize("error", [OSError("boom"), PermissionError("denied"), ValueError("embedded null byte")])
def test_read_file_size_turns_os_and_value_errors_into_none(tmp_path, monkeypatch, error) -> None:
    target = tmp_path / "a.bin"
    target.write_bytes(b"x")

    def refusing(self, *args, **kwargs):
        raise error

    monkeypatch.setattr(Path, "stat", refusing)
    assert read_file_size(target) is None


def test_read_file_size_does_not_hide_other_exceptions(tmp_path, monkeypatch) -> None:
    def broken(self, *args, **kwargs):
        raise RuntimeError("bug")

    monkeypatch.setattr(Path, "is_file", broken)
    with pytest.raises(RuntimeError):
        read_file_size(tmp_path)


@pytest.mark.revocable_permissions
def test_read_file_size_is_none_behind_a_folder_that_cannot_be_entered(tmp_path) -> None:
    folder = tmp_path / "locked"
    folder.mkdir()
    target = folder / "a.bin"
    target.write_bytes(b"x")
    folder.chmod(0o000)
    try:
        assert read_file_size(target) is None
    finally:
        folder.chmod(0o700)
