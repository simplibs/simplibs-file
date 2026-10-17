import os
from pathlib import Path
import pytest
from simplibs.file.rules._helpers import read_file_head

_CANNOT_REVOKE_ACCESS = os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0)


def _head(path, *, max_bytes=1000, encoding="utf-8"):
    return read_file_head(path, max_bytes=max_bytes, encoding=encoding)


def test_read_file_head_returns_the_decoded_text(tmp_path) -> None:
    target = tmp_path / "a.txt"
    target.write_bytes("Příliš žluťoučký kůň".encode("utf-8"))
    assert _head(target) == "Příliš žluťoučký kůň"


def test_read_file_head_of_an_empty_file_is_an_empty_string_not_none(tmp_path) -> None:
    target = tmp_path / "empty.txt"
    target.write_bytes(b"")
    result = _head(target)
    assert result == ""
    assert result is not None


@pytest.mark.parametrize(
    ("raw", "max_bytes", "expected"),
    [
        (b"abcdef", 3, "abc"),
        (b"abc", 3, "abc"),
        (b"abc", 100, "abc"),
    ],
)
def test_read_file_head_reads_at_most_max_bytes(tmp_path, raw, max_bytes, expected) -> None:
    target = tmp_path / "a.txt"
    target.write_bytes(raw)
    assert _head(target, max_bytes=max_bytes) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (b"a\r\nb", "a\nb"),
        (b"a\rb", "a\nb"),
        (b"a\nb", "a\nb"),
        (b"a\r\nb\rc\nd", "a\nb\nc\nd"),
        (b"\r\n\r\n", "\n\n"),
    ],
)
def test_read_file_head_normalizes_line_endings(tmp_path, raw, expected) -> None:
    target = tmp_path / "a.txt"
    target.write_bytes(raw)
    assert _head(target) == expected


def test_read_file_head_a_character_cut_by_max_bytes_is_not_an_error(tmp_path) -> None:
    target = tmp_path / "a.txt"
    target.write_bytes("ač".encode("utf-8"))   # b"a\xc4\x8d"
    assert _head(target, max_bytes=2) == "a"


def test_read_file_head_a_truncated_character_is_an_error_when_the_head_is_the_whole_file(tmp_path) -> None:
    target = tmp_path / "a.txt"
    target.write_bytes(b"a\xc4")
    assert _head(target, max_bytes=100) is None


def test_read_file_head_undecodable_bytes_give_none(tmp_path) -> None:
    target = tmp_path / "a.txt"
    target.write_bytes(b"\xff\xfe\xfa")
    assert _head(target) is None


@pytest.mark.parametrize(
    ("encoding", "raw", "expected"),
    [
        ("utf-8-sig", b"\xef\xbb\xbfhello", "hello"),
        ("utf-8", b"\xef\xbb\xbfhello", "\ufeffhello"),
        ("cp1250", "č".encode("cp1250"), "č"),
        ("utf-16", "ab".encode("utf-16"), "ab"),
    ],
)
def test_read_file_head_decodes_with_the_given_encoding(tmp_path, encoding, raw, expected) -> None:
    target = tmp_path / "a.txt"
    target.write_bytes(raw)
    assert _head(target, encoding=encoding) == expected


def test_read_file_head_is_none_for_a_missing_path(tmp_path) -> None:
    assert _head(tmp_path / "missing.txt") is None


def test_read_file_head_is_none_for_a_directory(tmp_path) -> None:
    assert _head(tmp_path) is None


def test_read_file_head_is_none_for_a_path_with_a_null_byte() -> None:
    assert _head(Path("a\0b")) is None


@pytest.mark.parametrize("error", [OSError("boom"), PermissionError("denied"), ValueError("embedded null byte")])
def test_read_file_head_turns_os_and_value_errors_into_none(tmp_path, monkeypatch, error) -> None:
    target = tmp_path / "a.txt"
    target.write_bytes(b"x")

    def refusing(self, *args, **kwargs):
        raise error

    monkeypatch.setattr(Path, "open", refusing)
    assert _head(target) is None


def test_read_file_head_does_not_hide_other_exceptions(tmp_path, monkeypatch) -> None:
    def broken(self, *args, **kwargs):
        raise RuntimeError("bug")

    monkeypatch.setattr(Path, "is_file", broken)
    with pytest.raises(RuntimeError):
        _head(tmp_path)


def test_read_file_head_arguments_after_the_path_are_keyword_only(tmp_path) -> None:
    with pytest.raises(TypeError):
        read_file_head(tmp_path / "a.txt", 100, "utf-8")


@pytest.mark.skipif(_CANNOT_REVOKE_ACCESS, reason="Permissions cannot be revoked here (Windows or root).")
def test_read_file_head_is_none_for_an_unreadable_file(tmp_path) -> None:
    target = tmp_path / "a.txt"
    target.write_bytes(b"x")
    target.chmod(0o000)
    try:
        assert _head(target) is None
    finally:
        target.chmod(0o600)
