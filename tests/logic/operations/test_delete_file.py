import importlib
import os
import stat
from pathlib import Path
from types import SimpleNamespace
import pytest
from simplibs.exception import AccessError, NotFoundError, StateError
from simplibs.file.logic.operations import delete_file

MODULE = importlib.import_module("simplibs.file.logic.operations.delete_file")


def _file(path: Path, data: bytes = b"content") -> Path:
    path.write_bytes(data)
    return path


def _symlink_or_skip(link: Path, target: Path, *, directory: bool = False) -> None:
    try:
        link.symlink_to(target, target_is_directory=directory)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available here")


# ----------------------------------------------------------------------
# Deleting
# ----------------------------------------------------------------------

def test_delete_file_removes_the_file(tmp_path: Path) -> None:
    """The file is gone."""
    file = _file(tmp_path / "a.txt")

    delete_file(file)

    assert not file.exists()


def test_delete_file_returns_the_normalized_path_of_the_deleted_entry(tmp_path: Path) -> None:
    """The result is the path the entry had."""
    file = _file(tmp_path / "a.txt")

    result = delete_file(file)

    assert isinstance(result, Path)
    assert result == tmp_path.resolve() / "a.txt"


def test_delete_file_accepts_string_path(tmp_path: Path) -> None:
    """A str path works like a Path."""
    file = _file(tmp_path / "a.txt")

    delete_file(str(file))

    assert not file.exists()


def test_delete_file_empty_file(tmp_path: Path) -> None:
    """An empty file is a file."""
    file = _file(tmp_path / "empty.txt", b"")

    delete_file(file)

    assert not file.exists()


def test_delete_file_leaves_other_files_alone(tmp_path: Path) -> None:
    """Only the given entry goes."""
    file = _file(tmp_path / "a.txt")
    other = _file(tmp_path / "b.txt")

    delete_file(file)

    assert other.exists()


# ----------------------------------------------------------------------
# Entry semantics
# ----------------------------------------------------------------------

def test_delete_file_symlink_is_deleted_and_its_target_survives(tmp_path: Path) -> None:
    """The old version deleted the TARGET and left the dangling link behind."""
    real = _file(tmp_path / "real.txt", b"precious")
    link = tmp_path / "link.txt"
    _symlink_or_skip(link, real)

    result = delete_file(link)

    assert not link.is_symlink()
    assert real.read_bytes() == b"precious"
    assert result == tmp_path.resolve() / "link.txt"


def test_delete_file_dangling_symlink_can_be_deleted(tmp_path: Path) -> None:
    """A link to nothing is a perfectly deletable entry."""
    link = tmp_path / "dangling.txt"
    _symlink_or_skip(link, tmp_path / "gone.txt")

    delete_file(link)

    assert not link.is_symlink()


def test_delete_file_symlink_to_a_folder_removes_only_the_link(tmp_path: Path) -> None:
    """The folder behind the link and its content stay."""
    folder = tmp_path / "folder"
    folder.mkdir()
    _file(folder / "inside.txt")
    link = tmp_path / "link_to_folder"
    _symlink_or_skip(link, folder, directory=True)

    delete_file(link)

    assert not link.is_symlink()
    assert (folder / "inside.txt").exists()


# ----------------------------------------------------------------------
# Missing and not a file
# ----------------------------------------------------------------------

def test_delete_file_missing_raises_not_found(tmp_path: Path) -> None:
    """Nothing there is NotFoundError."""
    with pytest.raises(NotFoundError) as info:
        delete_file(tmp_path / "missing.txt")

    assert info.value.error_name == "FILE_DELETE_NOT_FOUND"
    assert isinstance(info.value, FileNotFoundError)


def test_delete_file_missing_ok_accepts_a_missing_path(tmp_path: Path) -> None:
    """missing_ok=True is silent and still returns the path."""
    result = delete_file(tmp_path / "missing.txt", missing_ok=True)

    assert result == tmp_path.resolve() / "missing.txt"


def test_delete_file_directory_is_a_state_error_and_stays(tmp_path: Path) -> None:
    """The old code reached unlink and got a raw PermissionError or IsADirectoryError."""
    folder = tmp_path / "folder"
    folder.mkdir()

    with pytest.raises(StateError) as info:
        delete_file(folder)

    assert info.value.error_name == "FILE_DELETE_NOT_A_FILE"
    assert folder.is_dir()


def test_delete_file_missing_ok_does_not_excuse_a_directory(tmp_path: Path) -> None:
    """missing_ok only covers a MISSING path."""
    with pytest.raises(StateError):
        delete_file(tmp_path, missing_ok=True)


# ----------------------------------------------------------------------
# Race: the file vanishes between the check and unlink
# ----------------------------------------------------------------------

def test_delete_file_vanished_after_the_check_is_not_found(tmp_path: Path, monkeypatch) -> None:
    """An honest "not found" when the caller did not allow a missing file."""
    file = _file(tmp_path / "a.txt")

    def vanished(self, *args, **kwargs):
        raise FileNotFoundError("gone")

    monkeypatch.setattr(Path, "unlink", vanished)

    with pytest.raises(NotFoundError) as info:
        delete_file(file)

    assert info.value.error_name == "FILE_DELETE_NOT_FOUND"


def test_delete_file_vanished_after_the_check_is_fine_with_missing_ok(tmp_path: Path, monkeypatch) -> None:
    """The outcome the caller wanted is reached anyway."""
    file = _file(tmp_path / "a.txt")

    def vanished(self, *args, **kwargs):
        raise FileNotFoundError("gone")

    monkeypatch.setattr(Path, "unlink", vanished)

    assert delete_file(file, missing_ok=True) == tmp_path.resolve() / "a.txt"


# ----------------------------------------------------------------------
# Refusals of the OS and `force`
# ----------------------------------------------------------------------

def _unlink_failing_first(monkeypatch, error) -> list[Path]:
    """The first unlink raises `error`; later ones really delete."""
    original_unlink = Path.unlink
    calls: list[Path] = []

    def flaky_unlink(self, *args, **kwargs):
        calls.append(self)
        if len(calls) == 1:
            raise error
        return original_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", flaky_unlink)
    return calls


def test_delete_file_permission_error_without_force_is_an_access_error(tmp_path: Path, monkeypatch) -> None:
    """Removing a protection is an explicit choice, off by default."""
    file = _file(tmp_path / "a.txt")
    _unlink_failing_first(monkeypatch, PermissionError("read-only"))

    with pytest.raises(AccessError) as info:
        delete_file(file)

    assert info.value.error_name == "FILE_DELETE_FAILED"
    assert isinstance(info.value, PermissionError)
    assert file.exists()


def test_delete_file_force_clears_the_flag_and_tries_once_more(tmp_path: Path, monkeypatch) -> None:
    """On Windows a read-only file cannot be deleted until the flag is cleared."""
    file = _file(tmp_path / "a.txt")
    calls = _unlink_failing_first(monkeypatch, PermissionError("read-only"))

    delete_file(file, force=True)

    assert len(calls) == 2
    assert not file.exists()


def test_delete_file_force_that_still_fails_is_an_access_error(tmp_path: Path, monkeypatch) -> None:
    """A second refusal is reported."""
    file = _file(tmp_path / "a.txt")

    def always_refusing(self, *args, **kwargs):
        raise PermissionError("still locked")

    monkeypatch.setattr(Path, "unlink", always_refusing)

    with pytest.raises(AccessError) as info:
        delete_file(file, force=True)

    assert info.value.error_name == "FILE_DELETE_FAILED"
    assert file.exists()


def test_delete_file_force_does_not_touch_the_flag_of_a_symlink_target(tmp_path: Path, monkeypatch) -> None:
    """The flag of a symlink's TARGET is never touched."""
    real = _file(tmp_path / "real.txt")
    link = tmp_path / "link.txt"
    _symlink_or_skip(link, real)
    chmod_calls: list[Path] = []
    monkeypatch.setattr(
        MODULE, "os", SimpleNamespace(path=os.path, chmod=lambda path, mode: chmod_calls.append(path)),
    )
    _unlink_failing_first(monkeypatch, PermissionError("locked"))

    delete_file(link, force=True)

    assert chmod_calls == []
    assert real.exists()


def test_delete_file_force_makes_the_file_writable_before_the_retry(tmp_path: Path, monkeypatch) -> None:
    """The flag is cleared with S_IWRITE."""
    file = _file(tmp_path / "a.txt")
    modes: list[int] = []
    monkeypatch.setattr(MODULE, "os", SimpleNamespace(path=os.path, chmod=lambda path, mode: modes.append(mode)))
    _unlink_failing_first(monkeypatch, PermissionError("read-only"))

    delete_file(file, force=True)

    assert modes == [stat.S_IWRITE]


@pytest.mark.skipif(os.name != "nt", reason="read-only files cannot be deleted on Windows")
def test_delete_file_read_only_file_on_windows(tmp_path: Path) -> None:
    """The real thing: without force it fails, with force it is deleted."""
    file = _file(tmp_path / "a.txt")
    os.chmod(file, stat.S_IREAD)

    with pytest.raises(AccessError):
        delete_file(file)
    assert file.exists()

    delete_file(file, force=True)
    assert not file.exists()


def test_delete_file_other_os_failure_is_an_access_error(tmp_path: Path, monkeypatch) -> None:
    """Any other refusal is a card, not a bare OSError."""
    file = _file(tmp_path / "a.txt")
    _unlink_failing_first(monkeypatch, OSError("input/output error"))

    with pytest.raises(AccessError) as info:
        delete_file(file)

    assert info.value.error_name == "FILE_DELETE_FAILED"
    assert isinstance(info.value, OSError)


def test_delete_file_refused_existence_check_is_an_access_error(tmp_path: Path, monkeypatch) -> None:
    """When the OS refuses even the check, an AccessError card is raised."""
    file = _file(tmp_path / "a.txt")

    def refusing_lexists(path):
        raise PermissionError("denied")

    monkeypatch.setattr(MODULE, "os", SimpleNamespace(path=SimpleNamespace(lexists=refusing_lexists)))

    with pytest.raises(AccessError) as info:
        delete_file(file)

    assert info.value.error_name == "FILE_DELETE_FAILED"
    assert file.exists()
