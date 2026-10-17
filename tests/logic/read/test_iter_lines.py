from pathlib import Path
import pytest
from simplibs.exception import ConversionError, NotFoundError, StateError
from simplibs.file.logic.read import iter_lines, read_lines


def _write(path: Path, data: bytes) -> Path:
    path.write_bytes(data)
    return path


def test_iter_lines_returns_a_lazy_iterator_not_a_list(tmp_path: Path) -> None:
    """Memory use stays flat — the result is an iterator."""
    file = _write(tmp_path / "a.txt", b"a\nb\n")

    lines = iter_lines(file)

    assert not isinstance(lines, list)
    assert iter(lines) is lines
    assert list(lines) == ["a", "b"]


@pytest.mark.parametrize(
    "data",
    [
        b"a\nb\nc\n",
        b"a\r\nb\r\nc",
        b"a\rb\rc\r",
        b"a\nb\r\nc\rd",
        b"\xef\xbb\xbfbom\nline\n",
        "a\u2028b\x0cc\n".encode("utf-8"),
        b"",
        b"\n\n",
    ],
    ids=["LF", "CRLF-no-final", "CR", "mixed", "BOM", "unicode-separators", "empty", "blank-lines"],
)
@pytest.mark.parametrize("keep_ends", [False, True])
def test_iter_lines_gives_the_same_lines_as_read_lines(tmp_path: Path, data, keep_ends) -> None:
    """The lazy counterpart: same line rules, same results."""
    file = _write(tmp_path / "a.txt", data)

    assert list(iter_lines(file, keep_ends=keep_ends)) == read_lines(file, keep_ends=keep_ends)


def test_iter_lines_keep_ends_preserves_original_endings(tmp_path: Path) -> None:
    """Each line carries its own terminator."""
    file = _write(tmp_path / "a.txt", b"a\nb\r\nc\rd")

    assert list(iter_lines(file, keep_ends=True)) == ["a\n", "b\r\n", "c\r", "d"]


def test_iter_lines_uses_the_given_encoding(tmp_path: Path) -> None:
    """cp1250 text needs its encoding."""
    file = _write(tmp_path / "a.txt", "žluťoučký\n".encode("cp1250"))

    assert list(iter_lines(file, encoding="cp1250")) == ["žluťoučký"]


def test_iter_lines_accepts_string_path(tmp_path: Path) -> None:
    """A str path works like a Path."""
    file = _write(tmp_path / "a.txt", b"a\n")

    assert list(iter_lines(str(file))) == ["a"]


def test_iter_lines_missing_file_is_reported_at_the_call(tmp_path: Path) -> None:
    """Eager check: the error appears when the function is CALLED, not at the first next()."""
    with pytest.raises(NotFoundError) as info:
        iter_lines(tmp_path / "missing.txt")

    assert info.value.error_name == "FILE_READ_NOT_FOUND"


def test_iter_lines_directory_is_reported_at_the_call(tmp_path: Path) -> None:
    """A directory is refused at the call as well."""
    with pytest.raises(StateError) as info:
        iter_lines(tmp_path)

    assert info.value.error_name == "FILE_READ_NOT_A_FILE"


def test_iter_lines_invalid_bytes_are_reported_during_iteration_not_at_the_call(tmp_path: Path) -> None:
    """Only the content can reveal bad bytes, so the call itself succeeds."""
    file = _write(tmp_path / "a.txt", b"ok\n\xff\n")

    lines = iter_lines(file)

    with pytest.raises(ConversionError) as info:
        list(lines)

    assert info.value.error_name == "FILE_DECODE_FAILED"


def test_iter_lines_errors_replace(tmp_path: Path) -> None:
    """errors="replace" reads through invalid bytes."""
    file = _write(tmp_path / "a.txt", b"a\xffb\n")

    assert list(iter_lines(file, errors="replace")) == ["a\ufffdb"]


def test_iter_lines_closing_early_releases_the_file(tmp_path: Path, monkeypatch) -> None:
    """Abandoning the iteration must close the handle."""
    file = _write(tmp_path / "a.txt", b"a\nb\nc\n")
    handles: list = []
    original_open = Path.open

    def tracking_open(self, *args, **kwargs):
        handle = original_open(self, *args, **kwargs)
        handles.append(handle)
        return handle

    monkeypatch.setattr(Path, "open", tracking_open)
    lines = iter_lines(file)

    assert next(lines) == "a"
    lines.close()

    assert handles[0].closed
