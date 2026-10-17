from pathlib import Path
import pytest
from simplibs.exception import AccessError, AlreadyExistsError, StateError
from simplibs.file.logic.write._helpers import prepare_write_target


def test_prepare_write_target_returns_the_normalized_path(tmp_path: Path) -> None:
    """The result is an absolute, resolved Path."""
    result = prepare_write_target(tmp_path / "a.txt", "write")

    assert isinstance(result, Path)
    assert result == (tmp_path / "a.txt").resolve()
    assert result.is_absolute()


def test_prepare_write_target_accepts_string_path(tmp_path: Path) -> None:
    """A str path works like a Path."""
    assert prepare_write_target(str(tmp_path / "a.txt"), "write") == (tmp_path / "a.txt").resolve()


def test_prepare_write_target_creates_missing_folders_but_not_the_file(tmp_path: Path) -> None:
    """The folder is guaranteed; the file itself is the writer's job."""
    result = prepare_write_target(tmp_path / "a" / "b" / "out.txt", "write")

    assert result.parent.is_dir()
    assert not result.exists()


def test_prepare_write_target_existing_file_is_fine_by_default(tmp_path: Path) -> None:
    """overwrite defaults to True."""
    file = tmp_path / "a.txt"
    file.write_text("old", encoding="utf-8")

    assert prepare_write_target(file, "write") == file.resolve()
    assert file.read_text(encoding="utf-8") == "old"


@pytest.mark.parametrize("operation", ["write", "append"])
def test_prepare_write_target_existing_file_without_overwrite_is_refused(tmp_path: Path, operation) -> None:
    """overwrite=False refuses an existing file, naming the operation."""
    file = tmp_path / "a.txt"
    file.write_text("old", encoding="utf-8")

    with pytest.raises(AlreadyExistsError) as info:
        prepare_write_target(file, operation, overwrite=False)

    assert info.value.error_name == f"FILE_{operation.upper()}_DESTINATION_EXISTS"
    assert isinstance(info.value, FileExistsError)
    assert file.read_text(encoding="utf-8") == "old"


def test_prepare_write_target_missing_file_without_overwrite_is_fine(tmp_path: Path) -> None:
    """overwrite=False only matters when something is there."""
    assert prepare_write_target(tmp_path / "new.txt", "write", overwrite=False) == (tmp_path / "new.txt").resolve()


@pytest.mark.parametrize("operation", ["write", "append"])
@pytest.mark.parametrize("overwrite", [True, False])
def test_prepare_write_target_directory_is_a_state_error(tmp_path: Path, operation, overwrite) -> None:
    """A directory can never become a file, with or without overwrite."""
    folder = tmp_path / "folder"
    folder.mkdir()

    with pytest.raises(StateError) as info:
        prepare_write_target(folder, operation, overwrite=overwrite)

    assert info.value.error_name == f"FILE_{operation.upper()}_DESTINATION_IS_DIRECTORY"
    assert isinstance(info.value, IsADirectoryError)


def test_prepare_write_target_follows_a_symlink_to_a_file(tmp_path: Path) -> None:
    """The CONTENT behind the link is written, so the real file is the target."""
    real = tmp_path / "real.txt"
    real.write_text("x", encoding="utf-8")
    link = tmp_path / "link.txt"
    try:
        link.symlink_to(real)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available here")

    assert prepare_write_target(link, "write") == real.resolve()


def test_prepare_write_target_dangling_symlink_targets_the_missing_file(tmp_path: Path) -> None:
    """A link to nothing resolves to its (missing) target, which can then be created."""
    link = tmp_path / "link.txt"
    try:
        link.symlink_to(tmp_path / "later.txt")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available here")

    assert prepare_write_target(link, "write") == (tmp_path / "later.txt").resolve()


def test_prepare_write_target_file_in_the_parent_chain_fails(tmp_path: Path) -> None:
    """A folder cannot be created below a regular file."""
    (tmp_path / "file").write_text("x", encoding="utf-8")

    with pytest.raises((StateError, OSError)):
        prepare_write_target(tmp_path / "file" / "sub" / "out.txt", "write")


def test_prepare_write_target_refused_check_is_an_access_error(tmp_path: Path, monkeypatch) -> None:
    """When the OS refuses even the checks, an AccessError card is raised."""
    target = (tmp_path / "locked.txt").resolve()
    original_is_dir = Path.is_dir

    def refusing_is_dir(self):
        if self == target:
            raise PermissionError("denied")
        return original_is_dir(self)

    monkeypatch.setattr(Path, "is_dir", refusing_is_dir)

    with pytest.raises(AccessError) as info:
        prepare_write_target(target, "write")

    assert info.value.error_name == "FILE_WRITE_FAILED"
    assert isinstance(info.value, PermissionError)
