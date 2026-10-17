from pathlib import Path
import pytest
from simplibs.exception import ConversionError, NotFoundError, StateError
from simplibs.file.logic.read import read_text


def _write(path: Path, data: bytes) -> Path:
    path.write_bytes(data)
    return path


def test_read_text_reads_utf8(tmp_path: Path) -> None:
    """Plain UTF-8 text."""
    file = _write(tmp_path / "a.txt", "žluťoučký kůň\n".encode("utf-8"))

    assert read_text(file) == "žluťoučký kůň\n"


def test_read_text_removes_a_bom_by_default(tmp_path: Path) -> None:
    """A BOM from a Windows tool does not end up in the text."""
    file = _write(tmp_path / "a.txt", b"\xef\xbb\xbfhello")

    assert read_text(file) == "hello"


def test_read_text_accepts_a_file_without_bom(tmp_path: Path) -> None:
    """`utf-8-sig` is tolerant in both directions."""
    file = _write(tmp_path / "a.txt", b"hello")

    assert read_text(file) == "hello"


def test_read_text_empty_file_is_empty_string(tmp_path: Path) -> None:
    """Nothing in, nothing out."""
    file = _write(tmp_path / "a.txt", b"")

    assert read_text(file) == ""


@pytest.mark.parametrize(
    "data, expected",
    [
        (b"a\r\nb\r\n", "a\nb\n"),
        (b"a\rb\r", "a\nb\n"),
        (b"a\nb\n", "a\nb\n"),
        (b"a\r\nb\rc\nd", "a\nb\nc\nd"),
        (b"a\r\n\r\nb", "a\n\nb"),
        (b"a\r\r\nb", "a\n\nb"),
    ],
    ids=["CRLF", "CR", "LF", "mixed", "blank-CRLF", "CR-then-CRLF"],
)
def test_read_text_normalizes_line_endings_to_lf(tmp_path: Path, data, expected) -> None:
    """The same result as `Path.read_text`; `\\r\\n` is one line end, not two."""
    file = _write(tmp_path / "a.txt", data)

    assert read_text(file) == expected


def test_read_text_matches_pathlib_read_text(tmp_path: Path) -> None:
    """Code moving from pathlib keeps behaving."""
    file = _write(tmp_path / "a.txt", "a\r\nb\rc\nžluť\n".encode("utf-8"))

    assert read_text(file) == file.read_text(encoding="utf-8")


def test_read_text_unicode_separators_stay_untouched(tmp_path: Path) -> None:
    """Only `\\r\\n` and `\\r` are translated."""
    file = _write(tmp_path / "a.txt", "a\u2028b\x0cc\n".encode("utf-8"))

    assert read_text(file) == "a\u2028b\x0cc\n"


def test_read_text_uses_the_given_encoding(tmp_path: Path) -> None:
    """cp1250 text needs its encoding."""
    file = _write(tmp_path / "a.txt", "žluťoučký kůň".encode("cp1250"))

    assert read_text(file, encoding="cp1250") == "žluťoučký kůň"


def test_read_text_utf16_with_bom(tmp_path: Path) -> None:
    """A BOM-carrying encoding works when named."""
    file = _write(tmp_path / "a.txt", "hello".encode("utf-16"))

    assert read_text(file, encoding="utf-16") == "hello"


def test_read_text_errors_replace(tmp_path: Path) -> None:
    """errors="replace" reads through invalid bytes."""
    file = _write(tmp_path / "a.txt", b"a\xffb")

    assert read_text(file, errors="replace") == "a\ufffdb"


def test_read_text_undecodable_bytes_raise_a_card(tmp_path: Path) -> None:
    """Invalid bytes are a ConversionError, not a bare UnicodeDecodeError."""
    file = _write(tmp_path / "a.txt", "žluť".encode("cp1250"))

    with pytest.raises(ConversionError) as info:
        read_text(file)

    assert info.value.error_name == "FILE_DECODE_FAILED"
    assert isinstance(info.value, UnicodeDecodeError)


def test_read_text_accepts_string_path(tmp_path: Path) -> None:
    """A str path works like a Path."""
    file = _write(tmp_path / "a.txt", b"x")

    assert read_text(str(file)) == "x"


def test_read_text_missing_file_raises_not_found(tmp_path: Path) -> None:
    """A missing file is NotFoundError."""
    with pytest.raises(NotFoundError) as info:
        read_text(tmp_path / "missing.txt")

    assert info.value.error_name == "FILE_READ_NOT_FOUND"


def test_read_text_directory_raises_state_error(tmp_path: Path) -> None:
    """A directory is not a file."""
    with pytest.raises(StateError) as info:
        read_text(tmp_path)

    assert info.value.error_name == "FILE_READ_NOT_A_FILE"
