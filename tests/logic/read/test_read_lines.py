from pathlib import Path
import pytest
from simplibs.exception import ConversionError, NotFoundError, StateError
from simplibs.file.logic.read import read_lines
from simplibs.file.logic.write import write_lines


def _write(path: Path, data: bytes) -> Path:
    path.write_bytes(data)
    return path


@pytest.mark.parametrize(
    "data, expected",
    [
        (b"a\nb\nc\n", ["a", "b", "c"]),
        (b"a\r\nb\r\nc\r\n", ["a", "b", "c"]),
        (b"a\rb\rc\r", ["a", "b", "c"]),
        (b"a\nb\r\nc\rd", ["a", "b", "c", "d"]),
        (b"a\nb\nc", ["a", "b", "c"]),
        (b"a\n\nb\n", ["a", "", "b"]),
        (b"\n", [""]),
        (b"", []),
    ],
    ids=["LF", "CRLF", "CR", "mixed", "no-final-newline", "blank-line", "only-newline", "empty"],
)
def test_read_lines_splits_on_the_three_endings(tmp_path: Path, data, expected) -> None:
    """Only `\\n`, `\\r\\n` and `\\r` end a line; a final line without ending is kept."""
    file = _write(tmp_path / "a.txt", data)

    assert read_lines(file) == expected


def test_read_lines_returns_a_list(tmp_path: Path) -> None:
    """A real list, not an iterator."""
    file = _write(tmp_path / "a.txt", b"a\n")

    assert type(read_lines(file)) is list


def test_read_lines_keep_ends_preserves_every_original_ending(tmp_path: Path) -> None:
    """With keep_ends each line carries exactly its own terminator."""
    file = _write(tmp_path / "a.txt", b"a\nb\r\nc\rd")

    assert read_lines(file, keep_ends=True) == ["a\n", "b\r\n", "c\r", "d"]


def test_read_lines_keep_ends_joins_back_to_the_original_text(tmp_path: Path) -> None:
    """Nothing is lost: joined lines are the file's own characters."""
    original = "a\r\nb\rc\n\nžluť"
    file = _write(tmp_path / "a.txt", original.encode("utf-8"))

    assert "".join(read_lines(file, keep_ends=True)) == original


@pytest.mark.parametrize("separator", ["\x0b", "\x0c", "\x1c", "\x85", "\u2028", "\u2029"])
def test_read_lines_does_not_split_on_unicode_separators(tmp_path: Path, separator) -> None:
    """A source file containing a form feed must not fall apart (unlike `str.splitlines`)."""
    file = _write(tmp_path / "a.txt", f"a{separator}b\nc\n".encode("utf-8"))

    assert read_lines(file) == [f"a{separator}b", "c"]


def test_read_lines_removes_a_bom(tmp_path: Path) -> None:
    """The BOM does not become part of the first line."""
    file = _write(tmp_path / "a.txt", b"\xef\xbb\xbfa\nb\n")

    assert read_lines(file) == ["a", "b"]


def test_read_lines_uses_the_given_encoding(tmp_path: Path) -> None:
    """cp1250 text needs its encoding."""
    file = _write(tmp_path / "a.txt", "žluťoučký\nkůň\n".encode("cp1250"))

    assert read_lines(file, encoding="cp1250") == ["žluťoučký", "kůň"]


def test_read_lines_errors_replace(tmp_path: Path) -> None:
    """errors="replace" reads through invalid bytes."""
    file = _write(tmp_path / "a.txt", b"a\xffb\nc\n")

    assert read_lines(file, errors="replace") == ["a\ufffdb", "c"]


def test_read_lines_undecodable_bytes_raise_a_card(tmp_path: Path) -> None:
    """Invalid bytes are a ConversionError."""
    file = _write(tmp_path / "a.txt", b"ok\n\xff\n")

    with pytest.raises(ConversionError) as info:
        read_lines(file)

    assert info.value.error_name == "FILE_DECODE_FAILED"


def test_read_lines_round_trip_with_write_lines(tmp_path: Path) -> None:
    """`write_lines(p, read_lines(p))` reproduces a LF file."""
    file = _write(tmp_path / "a.txt", b"one\ntwo\n\nthree\n")

    write_lines(file, read_lines(file))

    assert file.read_bytes() == b"one\ntwo\n\nthree\n"


def test_read_lines_accepts_string_path(tmp_path: Path) -> None:
    """A str path works like a Path."""
    file = _write(tmp_path / "a.txt", b"a\n")

    assert read_lines(str(file)) == ["a"]


def test_read_lines_missing_file_raises_not_found(tmp_path: Path) -> None:
    """A missing file is NotFoundError."""
    with pytest.raises(NotFoundError) as info:
        read_lines(tmp_path / "missing.txt")

    assert info.value.error_name == "FILE_READ_NOT_FOUND"


def test_read_lines_directory_raises_state_error(tmp_path: Path) -> None:
    """A directory is not a file."""
    with pytest.raises(StateError) as info:
        read_lines(tmp_path)

    assert info.value.error_name == "FILE_READ_NOT_A_FILE"
