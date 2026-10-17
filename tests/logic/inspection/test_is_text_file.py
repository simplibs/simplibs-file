from pathlib import Path
import pytest
from simplibs.file.logic.inspection import is_text_file


def _write(path: Path, data: bytes) -> Path:
    path.write_bytes(data)
    return path


# ----------------------------------------------------------------------
# Text
# ----------------------------------------------------------------------

def test_is_text_file_utf8_text_is_text(tmp_path: Path) -> None:
    """Plain UTF-8 text is text."""
    file = _write(tmp_path / "a.txt", "Hello, žluťoučký kůň\n".encode("utf-8"))

    assert is_text_file(file) is True


def test_is_text_file_empty_file_is_text_by_convention(tmp_path: Path) -> None:
    """An empty file is text, as `file` and Git treat it."""
    file = _write(tmp_path / "empty.txt", b"")

    assert is_text_file(file) is True


def test_is_text_file_accepts_string_path(tmp_path: Path) -> None:
    """A str path works like a Path."""
    file = _write(tmp_path / "a.txt", b"hello")

    assert is_text_file(str(file)) is True


def test_is_text_file_follows_symlink(tmp_path: Path) -> None:
    """A symlink to a text file is text."""
    real = _write(tmp_path / "real.txt", b"hello")
    link = tmp_path / "link.txt"
    try:
        link.symlink_to(real)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available here")

    assert is_text_file(link) is True


# ----------------------------------------------------------------------
# Binary
# ----------------------------------------------------------------------

def test_is_text_file_nul_character_means_binary(tmp_path: Path) -> None:
    """A NUL character inside the sample is the classic mark of binary content."""
    file = _write(tmp_path / "a.bin", b"ab\x00cd")

    assert is_text_file(file) is False


def test_is_text_file_png_header_is_binary(tmp_path: Path) -> None:
    """A PNG signature is not valid UTF-8."""
    file = _write(tmp_path / "a.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")

    assert is_text_file(file) is False


def test_is_text_file_nul_after_the_sample_is_not_seen(tmp_path: Path) -> None:
    """Documented heuristic: only the first sample_size bytes are judged."""
    file = _write(tmp_path / "a.bin", b"a" * 10 + b"\x00")

    assert is_text_file(file, sample_size=5) is True


def test_is_text_file_nul_inside_the_sample_is_seen(tmp_path: Path) -> None:
    """The same file is binary when the sample reaches the NUL."""
    file = _write(tmp_path / "a.bin", b"a" * 10 + b"\x00")

    assert is_text_file(file, sample_size=11) is False


# ----------------------------------------------------------------------
# Encodings
# ----------------------------------------------------------------------

def test_is_text_file_utf16_is_text_with_matching_encoding(tmp_path: Path) -> None:
    """A NUL BYTE is normal in UTF-16; only a decoded NUL CHARACTER means binary."""
    file = _write(tmp_path / "a.txt", "hello".encode("utf-16"))

    assert is_text_file(file, encoding="utf-16") is True


def test_is_text_file_utf16_is_binary_with_default_encoding(tmp_path: Path) -> None:
    """The same file does not decode as UTF-8."""
    file = _write(tmp_path / "a.txt", "hello".encode("utf-16"))

    assert is_text_file(file) is False


def test_is_text_file_cp1250_text_needs_its_encoding(tmp_path: Path) -> None:
    """cp1250 text is invalid UTF-8, but valid text in its own encoding."""
    file = _write(tmp_path / "a.txt", "žluťoučký kůň".encode("cp1250"))

    assert is_text_file(file) is False
    assert is_text_file(file, encoding="cp1250") is True


# ----------------------------------------------------------------------
# The cut character
# ----------------------------------------------------------------------

def test_is_text_file_multibyte_character_cut_by_sample_end_is_not_an_error(tmp_path: Path) -> None:
    """The sample ends inside a 2-byte character; the rest of the file is valid, so it is text."""
    file = _write(tmp_path / "a.txt", "ž".encode("utf-8") * 100)  # 200 bytes

    assert is_text_file(file, sample_size=5) is True


def test_is_text_file_truncated_character_at_end_of_a_short_file_is_binary(tmp_path: Path) -> None:
    """When the sample is the whole file, a half character really is invalid data."""
    file = _write(tmp_path / "a.txt", b"abc" + "ž".encode("utf-8")[:1])

    assert is_text_file(file) is False


# ----------------------------------------------------------------------
# Never raises for disk problems
# ----------------------------------------------------------------------

def test_is_text_file_missing_path_is_false(tmp_path: Path) -> None:
    """A path that does not exist is a plain 'no'."""
    assert is_text_file(tmp_path / "missing.txt") is False


def test_is_text_file_directory_is_false(tmp_path: Path) -> None:
    """A directory is not a text file."""
    assert is_text_file(tmp_path) is False


def test_is_text_file_unreadable_file_is_false(tmp_path: Path, monkeypatch) -> None:
    """A refusal of the OS is a plain 'no', never an exception."""
    file = _write(tmp_path / "locked.txt", b"hello")
    original_open = Path.open

    def refusing_open(self, *args, **kwargs):
        if self.name == "locked.txt":
            raise PermissionError("denied")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", refusing_open)

    assert is_text_file(file) is False


# ----------------------------------------------------------------------
# The rule bypass
# ----------------------------------------------------------------------

def test_is_text_file_validate_call_bypass_switch_is_accepted(tmp_path: Path) -> None:
    """Rules pass _validate_call=False because they validated the input themselves."""
    file = _write(tmp_path / "a.txt", b"hello")

    assert is_text_file(file, _validate_call=False) is True
    assert is_text_file(file, _validate_call=True) is True
