import importlib
from pathlib import Path
import pytest
from simplibs.exception import AccessError, NotFoundError, StateError
from simplibs.file.logic.inspect import file_size

MODULE = importlib.import_module("simplibs.file.logic.inspect.file_size")


def test_file_size_of_empty_file_is_zero(tmp_path: Path) -> None:
    """An empty file has size 0 — a number, not an error."""
    file = tmp_path / "empty.bin"
    file.write_bytes(b"")

    assert file_size(file) == 0


@pytest.mark.parametrize("size", [1, 10, 4096, 1_048_576 + 1])
def test_file_size_returns_exact_byte_count(tmp_path: Path, size) -> None:
    """The size is the logical length of the content in bytes."""
    file = tmp_path / "data.bin"
    file.write_bytes(b"x" * size)

    assert file_size(file) == size


def test_file_size_counts_bytes_not_characters(tmp_path: Path) -> None:
    """Multi-byte characters count with their encoded length."""
    file = tmp_path / "text.txt"
    file.write_text("žluťoučký", encoding="utf-8")

    assert file_size(file) == len("žluťoučký".encode("utf-8"))


def test_file_size_accepts_string_path(tmp_path: Path) -> None:
    """A str path works like a Path."""
    file = tmp_path / "data.bin"
    file.write_bytes(b"abc")

    assert file_size(str(file)) == 3


def test_file_size_returns_int(tmp_path: Path) -> None:
    """The result is a plain int."""
    file = tmp_path / "data.bin"
    file.write_bytes(b"abc")

    assert type(file_size(file)) is int


def test_file_size_of_symlink_is_size_of_target(tmp_path: Path) -> None:
    """A symlink is followed, so it reports the target's size."""
    real = tmp_path / "real.bin"
    real.write_bytes(b"x" * 7)
    link = tmp_path / "link.bin"
    try:
        link.symlink_to(real)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available here")

    assert file_size(link) == 7


def test_file_size_missing_file_raises_not_found(tmp_path: Path) -> None:
    """'Size of nothing' has no honest number."""
    with pytest.raises(NotFoundError) as info:
        file_size(tmp_path / "missing.bin")

    assert info.value.error_name == "FILE_INSPECT_NOT_FOUND"


def test_file_size_directory_raises_state_error(tmp_path: Path) -> None:
    """A directory is not a regular file."""
    with pytest.raises(StateError) as info:
        file_size(tmp_path)

    assert info.value.error_name == "FILE_INSPECT_NOT_A_FILE"


def test_file_size_refused_stat_is_access_error(monkeypatch) -> None:
    """When the OS refuses to report the size, an AccessError card is raised."""

    class _Unstatable:
        def stat(self):
            raise PermissionError("denied")

        def __str__(self) -> str:
            return "unstatable.bin"

    monkeypatch.setattr(MODULE, "resolve_source_file", lambda path, operation: _Unstatable())

    with pytest.raises(AccessError) as info:
        file_size("whatever.bin")

    assert info.value.error_name == "FILE_INSPECT_FAILED"
    assert isinstance(info.value, PermissionError)
