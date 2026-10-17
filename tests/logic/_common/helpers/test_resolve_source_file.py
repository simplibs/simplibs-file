from pathlib import Path
import pytest
from simplibs.exception import AccessError, NotFoundError, StateError
from simplibs.file.logic._common.helpers import resolve_source_file


def _symlink_or_skip(link: Path, target: Path) -> None:
    """Create a symlink, or skip the test where the platform does not allow it."""
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available here")


# ----------------------------------------------------------------------
# Success
# ----------------------------------------------------------------------

def test_resolve_source_file_returns_normalized_path_of_existing_file(tmp_path: Path) -> None:
    """An existing regular file is returned as a normalized, absolute Path."""
    file = tmp_path / "a.txt"
    file.write_text("x", encoding="utf-8")

    result = resolve_source_file(file, "read")

    assert isinstance(result, Path)
    assert result == file.resolve()
    assert result.is_absolute()


def test_resolve_source_file_accepts_string_path(tmp_path: Path) -> None:
    """A str path is accepted like a Path."""
    file = tmp_path / "a.txt"
    file.write_text("x", encoding="utf-8")

    assert resolve_source_file(str(file), "read") == file.resolve()


def test_resolve_source_file_makes_relative_path_absolute(tmp_path: Path, monkeypatch) -> None:
    """A relative path is resolved against the current working directory."""
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    result = resolve_source_file("a.txt", "read")

    assert result == (tmp_path / "a.txt").resolve()


def test_resolve_source_file_follows_symlink_to_file(tmp_path: Path) -> None:
    """The CONTENT is wanted, so a symlink to a file resolves to its target."""
    real = tmp_path / "real.txt"
    real.write_text("x", encoding="utf-8")
    link = tmp_path / "link.txt"
    _symlink_or_skip(link, real)

    assert resolve_source_file(link, "read") == real.resolve()


# ----------------------------------------------------------------------
# Failures
# ----------------------------------------------------------------------

@pytest.mark.parametrize("operation", ["read", "copy", "inspect", "hash"])
def test_resolve_source_file_missing_file_raises_not_found(tmp_path: Path, operation) -> None:
    """Nothing at the path -> NotFoundError named after the operation."""
    with pytest.raises(NotFoundError) as info:
        resolve_source_file(tmp_path / "missing.txt", operation)

    assert info.value.error_name == f"FILE_{operation.upper()}_NOT_FOUND"
    assert isinstance(info.value, FileNotFoundError)


@pytest.mark.parametrize("operation", ["read", "hash"])
def test_resolve_source_file_directory_raises_state_error(tmp_path: Path, operation) -> None:
    """A directory is something, but not a regular file -> StateError."""
    folder = tmp_path / "folder"
    folder.mkdir()

    with pytest.raises(StateError) as info:
        resolve_source_file(folder, operation)

    assert info.value.error_name == f"FILE_{operation.upper()}_NOT_A_FILE"
    assert isinstance(info.value, IsADirectoryError)


def test_resolve_source_file_dangling_symlink_is_not_found(tmp_path: Path) -> None:
    """A link whose target is gone has no content to work with."""
    link = tmp_path / "dangling.txt"
    _symlink_or_skip(link, tmp_path / "gone.txt")

    with pytest.raises(NotFoundError):
        resolve_source_file(link, "read")


def test_resolve_source_file_refused_existence_check_is_access_error(tmp_path: Path, monkeypatch) -> None:
    """Path.exists() can raise for some paths; that is reported as AccessError, not a bare traceback."""
    file = tmp_path / "locked.txt"
    file.write_text("x", encoding="utf-8")
    target = file.resolve()
    original_exists = Path.exists

    def refusing_exists(self, *args, **kwargs):
        if self == target:
            raise PermissionError("denied")
        return original_exists(self, *args, **kwargs)

    monkeypatch.setattr(Path, "exists", refusing_exists)

    with pytest.raises(AccessError) as info:
        resolve_source_file(file, "read")

    assert info.value.error_name == "FILE_READ_FAILED"
    assert isinstance(info.value, PermissionError)
