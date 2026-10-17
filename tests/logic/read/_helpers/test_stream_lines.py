import inspect
from pathlib import Path
import pytest
from simplibs.exception import AccessError, ConversionError
from simplibs.file.logic.read._helpers import stream_lines


def _write(path: Path, data: bytes) -> Path:
    path.write_bytes(data)
    return path


def _stream(path: Path, *, encoding="utf-8-sig", errors="strict", keep_ends=False):
    return stream_lines(path, encoding=encoding, errors=errors, keep_ends=keep_ends)


# ----------------------------------------------------------------------
# Lines
# ----------------------------------------------------------------------

def test_stream_lines_is_a_lazy_generator(tmp_path: Path) -> None:
    """Nothing runs (not even opening the file) until it is iterated."""
    stream = _stream(tmp_path / "missing.txt")

    assert inspect.isgenerator(stream)


@pytest.mark.parametrize(
    "data, expected",
    [
        (b"a\nb\nc\n", ["a", "b", "c"]),
        (b"a\r\nb\r\nc\r\n", ["a", "b", "c"]),
        (b"a\rb\rc\r", ["a", "b", "c"]),
        (b"a\nb\r\nc\rd", ["a", "b", "c", "d"]),
        (b"a\nb\nc", ["a", "b", "c"]),
        (b"a\n\nb\n", ["a", "", "b"]),
        (b"", []),
        (b"\n", [""]),
    ],
    ids=["LF", "CRLF", "CR", "mixed", "no-final-newline", "blank-line", "empty", "only-newline"],
)
def test_stream_lines_splits_on_the_three_endings(tmp_path: Path, data, expected) -> None:
    """`\\n`, `\\r\\n` and `\\r` end a line, and the ending is removed by default."""
    file = _write(tmp_path / "a.txt", data)

    assert list(_stream(file)) == expected


def test_stream_lines_keep_ends_returns_the_original_endings(tmp_path: Path) -> None:
    """With keep_ends every line carries exactly its own ending."""
    file = _write(tmp_path / "a.txt", b"a\nb\r\nc\rd")

    assert list(_stream(file, keep_ends=True)) == ["a\n", "b\r\n", "c\r", "d"]


@pytest.mark.parametrize("separator", ["\x0c", "\x85", "\u2028", "\u2029"])
def test_stream_lines_does_not_split_on_unicode_separators(tmp_path: Path, separator) -> None:
    """Form feeds and Unicode separators stay inside their line."""
    file = _write(tmp_path / "a.txt", f"a{separator}b\nc\n".encode("utf-8"))

    assert list(_stream(file)) == [f"a{separator}b", "c"]


def test_stream_lines_utf8_sig_strips_the_bom_of_the_first_line(tmp_path: Path) -> None:
    """The BOM does not become part of the first line."""
    file = _write(tmp_path / "a.txt", b"\xef\xbb\xbfa\nb\n")

    assert list(_stream(file)) == ["a", "b"]


def test_stream_lines_plain_utf8_keeps_the_bom(tmp_path: Path) -> None:
    """With plain utf-8 the BOM is a character of the first line."""
    file = _write(tmp_path / "a.txt", b"\xef\xbb\xbfa\n")

    assert list(_stream(file, encoding="utf-8")) == ["\ufeffa"]


def test_stream_lines_uses_the_given_encoding(tmp_path: Path) -> None:
    """The file is decoded with the requested encoding."""
    file = _write(tmp_path / "a.txt", "žluťoučký\nkůň\n".encode("cp1250"))

    assert list(_stream(file, encoding="cp1250")) == ["žluťoučký", "kůň"]


# ----------------------------------------------------------------------
# The file handle
# ----------------------------------------------------------------------

def _track_open_handles(monkeypatch) -> list:
    """Record every handle Path.open returns, so the tests can see whether it was closed."""
    handles: list = []
    original_open = Path.open

    def tracking_open(self, *args, **kwargs):
        handle = original_open(self, *args, **kwargs)
        handles.append(handle)
        return handle

    monkeypatch.setattr(Path, "open", tracking_open)
    return handles


def test_stream_lines_closes_the_file_when_exhausted(tmp_path: Path, monkeypatch) -> None:
    """Reading to the end releases the file."""
    file = _write(tmp_path / "a.txt", b"a\nb\n")
    handles = _track_open_handles(monkeypatch)

    assert list(_stream(file)) == ["a", "b"]

    assert len(handles) == 1
    assert handles[0].closed


def test_stream_lines_closes_the_file_when_the_generator_is_closed_early(tmp_path: Path, monkeypatch) -> None:
    """Abandoning the iteration must not leak the handle."""
    file = _write(tmp_path / "a.txt", b"a\nb\nc\n")
    handles = _track_open_handles(monkeypatch)
    stream = _stream(file)

    assert next(stream) == "a"
    stream.close()

    assert handles[0].closed


# ----------------------------------------------------------------------
# Failures
# ----------------------------------------------------------------------

def test_stream_lines_invalid_bytes_raise_a_card_without_an_offset(tmp_path: Path) -> None:
    """The offset inside a block is meaningless for the file, so the card omits it."""
    file = _write(tmp_path / "a.txt", b"ok\n\xff\n")

    with pytest.raises(ConversionError) as info:
        list(_stream(file))

    assert info.value.error_name == "FILE_DECODE_FAILED"
    assert isinstance(info.value, UnicodeDecodeError)
    assert "byte offset" not in str(info.value)


def test_stream_lines_invalid_bytes_far_into_the_file_are_reached_lazily(tmp_path: Path) -> None:
    """Lines before the bad block are yielded first; the error appears only when it is reached."""
    file = _write(tmp_path / "a.txt", b"x\n" * 10_000 + b"\xff\n")
    received: list[str] = []

    with pytest.raises(ConversionError):
        for line in _stream(file):
            received.append(line)

    assert len(received) >= 4000
    assert set(received) == {"x"}


def test_stream_lines_invalid_bytes_never_reached_never_fail(tmp_path: Path) -> None:
    """Stopping before the bad block means the error never appears."""
    file = _write(tmp_path / "a.txt", b"x\n" * 10_000 + b"\xff\n")
    stream = _stream(file)

    assert next(stream) == "x"
    stream.close()


def test_stream_lines_errors_replace_reads_through_invalid_bytes(tmp_path: Path) -> None:
    """errors="replace" substitutes instead of failing."""
    file = _write(tmp_path / "a.txt", b"a\xffb\n")

    assert list(_stream(file, errors="replace")) == ["a\ufffdb"]


def test_stream_lines_missing_file_is_an_access_error_at_the_first_next(tmp_path: Path) -> None:
    """stream_lines itself does no existence check; the OS refusal becomes a card."""
    stream = _stream(tmp_path / "missing.txt")

    with pytest.raises(AccessError) as info:
        next(stream)

    assert info.value.error_name == "FILE_READ_FAILED"
    assert isinstance(info.value, FileNotFoundError)


def test_stream_lines_os_failure_in_the_middle_of_the_file_is_an_access_error(tmp_path: Path, monkeypatch) -> None:
    """A disk problem while reading is reported as a card, not a bare OSError."""
    file = _write(tmp_path / "a.txt", b"a\nb\n")

    class _BrokenHandle:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def __iter__(self):
            raise OSError("input/output error")

    monkeypatch.setattr(Path, "open", lambda self, *args, **kwargs: _BrokenHandle())

    with pytest.raises(AccessError) as info:
        list(_stream(file))

    assert info.value.error_name == "FILE_READ_FAILED"
    assert isinstance(info.value, OSError)
