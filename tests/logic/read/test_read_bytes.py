import importlib
from pathlib import Path
import pytest
from simplibs.exception import AccessError, NotFoundError, StateError
from simplibs.file.logic.read import read_bytes

MODULE = importlib.import_module("simplibs.file.logic.read.read_bytes")


def test_read_bytes_returns_the_exact_content(tmp_path: Path) -> None:
    """Every byte arrives untouched — endings, NULs, high bytes."""
    data = b"a\r\nb\rc\nd\x00\xff\xfe"
    file = tmp_path / "a.bin"
    file.write_bytes(data)

    assert read_bytes(file) == data


def test_read_bytes_empty_file_is_empty_bytes(tmp_path: Path) -> None:
    """An empty file is b"", not an error."""
    file = tmp_path / "empty.bin"
    file.write_bytes(b"")

    assert read_bytes(file) == b""


def test_read_bytes_returns_bytes_type(tmp_path: Path) -> None:
    """The result is plain bytes."""
    file = tmp_path / "a.bin"
    file.write_bytes(b"x")

    assert type(read_bytes(file)) is bytes


def test_read_bytes_accepts_string_path(tmp_path: Path) -> None:
    """A str path works like a Path."""
    file = tmp_path / "a.bin"
    file.write_bytes(b"abc")

    assert read_bytes(str(file)) == b"abc"


def test_read_bytes_large_file(tmp_path: Path) -> None:
    """A multi-megabyte file is read whole."""
    data = bytes(range(256)) * 12_000
    file = tmp_path / "big.bin"
    file.write_bytes(data)

    assert read_bytes(file) == data


def test_read_bytes_follows_symlink(tmp_path: Path) -> None:
    """The CONTENT behind a link is read."""
    real = tmp_path / "real.bin"
    real.write_bytes(b"content")
    link = tmp_path / "link.bin"
    try:
        link.symlink_to(real)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available here")

    assert read_bytes(link) == b"content"


def test_read_bytes_missing_file_raises_not_found(tmp_path: Path) -> None:
    """A missing file is NotFoundError."""
    with pytest.raises(NotFoundError) as info:
        read_bytes(tmp_path / "missing.bin")

    assert info.value.error_name == "FILE_READ_NOT_FOUND"
    assert isinstance(info.value, FileNotFoundError)


def test_read_bytes_directory_raises_state_error(tmp_path: Path) -> None:
    """A directory cannot be read as a file."""
    with pytest.raises(StateError) as info:
        read_bytes(tmp_path)

    assert info.value.error_name == "FILE_READ_NOT_A_FILE"


def test_read_bytes_refused_read_is_access_error(tmp_path: Path, monkeypatch) -> None:
    """A locked file or a permission problem is a card, not a bare PermissionError."""
    file = tmp_path / "locked.bin"
    file.write_bytes(b"abc")
    original_read_bytes = Path.read_bytes

    def refusing_read_bytes(self):
        if self.name == "locked.bin":
            raise PermissionError("denied")
        return original_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", refusing_read_bytes)

    with pytest.raises(AccessError) as info:
        read_bytes(file)

    assert info.value.error_name == "FILE_READ_FAILED"
    assert isinstance(info.value, PermissionError)


def test_read_bytes_file_vanishing_after_the_check_is_access_error(tmp_path: Path, monkeypatch) -> None:
    """The file disappears between the check and the read."""
    gone = tmp_path / "gone.bin"
    monkeypatch.setattr(MODULE, "resolve_source_file", lambda path, operation: gone)

    with pytest.raises(AccessError) as info:
        read_bytes("whatever.bin")

    assert info.value.error_name == "FILE_READ_FAILED"
    assert isinstance(info.value, FileNotFoundError)
