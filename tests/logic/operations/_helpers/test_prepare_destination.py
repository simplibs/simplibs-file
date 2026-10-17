import importlib
import os
from pathlib import Path
from types import SimpleNamespace
import pytest
from simplibs.exception import AccessError, AlreadyExistsError, ParamError, StateError
from simplibs.file.logic.operations._helpers import prepare_destination

MODULE = importlib.import_module("simplibs.file.logic.operations._helpers.prepare_destination")


def _file(path: Path, text: str = "x") -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _symlink_or_skip(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available here")


# ----------------------------------------------------------------------
# Acceptable destinations
# ----------------------------------------------------------------------

@pytest.mark.parametrize("operation", ["copy", "move"])
@pytest.mark.parametrize("overwrite", [True, False])
def test_prepare_destination_missing_destination_is_fine(tmp_path: Path, operation, overwrite) -> None:
    """Nothing there, nothing to refuse."""
    source = _file(tmp_path / "source.txt")

    assert prepare_destination(source, tmp_path / "new.txt", operation, overwrite=overwrite) is None


@pytest.mark.parametrize("operation", ["copy", "move"])
def test_prepare_destination_existing_destination_with_overwrite_is_fine(tmp_path: Path, operation) -> None:
    """overwrite=True allows replacing."""
    source = _file(tmp_path / "source.txt")
    destination = _file(tmp_path / "destination.txt")

    assert prepare_destination(source, destination, operation, overwrite=True) is None


def test_prepare_destination_touches_nothing_on_disk(tmp_path: Path) -> None:
    """It only checks."""
    source = _file(tmp_path / "source.txt", "s")
    destination = _file(tmp_path / "destination.txt", "d")

    prepare_destination(source, destination, "copy", overwrite=True)

    assert source.read_text(encoding="utf-8") == "s"
    assert destination.read_text(encoding="utf-8") == "d"


# ----------------------------------------------------------------------
# Refusals
# ----------------------------------------------------------------------

@pytest.mark.parametrize("operation", ["copy", "move"])
@pytest.mark.parametrize("overwrite", [True, False])
def test_prepare_destination_same_path_is_a_param_error(tmp_path: Path, operation, overwrite) -> None:
    """Copying a file onto itself would truncate it."""
    source = _file(tmp_path / "source.txt")

    with pytest.raises(ParamError) as info:
        prepare_destination(source, source, operation, overwrite=overwrite)

    assert info.value.error_name == f"FILE_{operation.upper()}_SAME_FILE"
    assert isinstance(info.value, ValueError)


@pytest.mark.parametrize("operation", ["copy", "move"])
@pytest.mark.parametrize("overwrite", [True, False])
def test_prepare_destination_directory_is_a_state_error(tmp_path: Path, operation, overwrite) -> None:
    """A directory can never be replaced by a file."""
    source = _file(tmp_path / "source.txt")
    folder = tmp_path / "folder"
    folder.mkdir()

    with pytest.raises(StateError) as info:
        prepare_destination(source, folder, operation, overwrite=overwrite)

    assert info.value.error_name == f"FILE_{operation.upper()}_DESTINATION_IS_DIRECTORY"
    assert isinstance(info.value, IsADirectoryError)


@pytest.mark.parametrize("operation", ["copy", "move"])
def test_prepare_destination_existing_destination_without_overwrite_is_refused(tmp_path: Path, operation) -> None:
    """overwrite=False protects an existing file."""
    source = _file(tmp_path / "source.txt")
    destination = _file(tmp_path / "destination.txt")

    with pytest.raises(AlreadyExistsError) as info:
        prepare_destination(source, destination, operation, overwrite=False)

    assert info.value.error_name == f"FILE_{operation.upper()}_DESTINATION_EXISTS"
    assert isinstance(info.value, FileExistsError)


# ----------------------------------------------------------------------
# Another spelling of the same file
# ----------------------------------------------------------------------

@pytest.mark.parametrize("operation", ["copy", "move"])
@pytest.mark.parametrize("overwrite", [True, False])
def test_prepare_destination_hard_link_is_the_same_file(tmp_path: Path, operation, overwrite) -> None:
    """Two names, one file: a copy onto it would truncate the source."""
    source = _file(tmp_path / "source.txt")
    destination = tmp_path / "hardlink.txt"
    try:
        os.link(source, destination)
    except (OSError, NotImplementedError):
        pytest.skip("hard links are not available here")

    with pytest.raises(ParamError) as info:
        prepare_destination(source, destination, operation, overwrite=overwrite)

    assert info.value.error_name == f"FILE_{operation.upper()}_SAME_FILE"


def test_prepare_destination_symlink_pointing_at_the_source_is_the_same_file(tmp_path: Path) -> None:
    """A link to the source is another spelling of it."""
    source = _file(tmp_path / "source.txt")
    link = tmp_path / "link.txt"
    _symlink_or_skip(link, source)

    with pytest.raises(ParamError):
        prepare_destination(source, link, "copy", overwrite=True)


# ----------------------------------------------------------------------
# Dangling symlinks and symlinks to folders
# ----------------------------------------------------------------------

def test_prepare_destination_dangling_symlink_counts_as_existing(tmp_path: Path) -> None:
    """A plain exists() would call it free and the replace would silently remove the link."""
    source = _file(tmp_path / "source.txt")
    link = tmp_path / "dangling.txt"
    _symlink_or_skip(link, tmp_path / "gone.txt")

    with pytest.raises(AlreadyExistsError):
        prepare_destination(source, link, "copy", overwrite=False)


def test_prepare_destination_dangling_symlink_can_be_replaced_with_overwrite(tmp_path: Path) -> None:
    """overwrite=True accepts replacing the link entry."""
    source = _file(tmp_path / "source.txt")
    link = tmp_path / "dangling.txt"
    _symlink_or_skip(link, tmp_path / "gone.txt")

    assert prepare_destination(source, link, "copy", overwrite=True) is None


def test_prepare_destination_symlink_to_a_folder_is_an_entry_not_a_folder(tmp_path: Path) -> None:
    """The link itself can be replaced; only a real directory is refused."""
    source = _file(tmp_path / "source.txt")
    folder = tmp_path / "folder"
    folder.mkdir()
    link = tmp_path / "link_to_folder"
    _symlink_or_skip(link, folder)

    assert prepare_destination(source, link, "move", overwrite=True) is None


# ----------------------------------------------------------------------
# Case-only rename
# ----------------------------------------------------------------------

def _fake_same_file_os() -> SimpleNamespace:
    """A filesystem where every destination exists and is the same file as the source."""
    return SimpleNamespace(path=SimpleNamespace(lexists=lambda path: True, samefile=lambda a, b: True))


def test_prepare_destination_case_only_move_is_a_legitimate_rename(monkeypatch) -> None:
    """On a case-insensitive filesystem `a.txt` -> `A.txt` is the same file, yet a valid rename."""
    monkeypatch.setattr(MODULE, "os", _fake_same_file_os())

    assert prepare_destination(Path("a.txt"), Path("A.txt"), "move", overwrite=False) is None


def test_prepare_destination_case_only_copy_is_still_the_same_file(monkeypatch) -> None:
    """For a copy it would truncate the source."""
    monkeypatch.setattr(MODULE, "os", _fake_same_file_os())

    with pytest.raises(ParamError) as info:
        prepare_destination(Path("a.txt"), Path("A.txt"), "copy", overwrite=True)

    assert info.value.error_name == "FILE_COPY_SAME_FILE"


def test_prepare_destination_move_to_a_different_name_of_the_same_file_is_refused(monkeypatch) -> None:
    """Only a case change is excused, not any other alias."""
    monkeypatch.setattr(MODULE, "os", _fake_same_file_os())

    with pytest.raises(ParamError) as info:
        prepare_destination(Path("a.txt"), Path("alias.txt"), "move", overwrite=True)

    assert info.value.error_name == "FILE_MOVE_SAME_FILE"


@pytest.mark.skipif(os.name != "nt", reason="case-insensitive filesystem semantics of Windows")
def test_prepare_destination_case_only_move_on_windows_is_allowed(tmp_path: Path) -> None:
    """The real thing: `a.txt` -> `A.txt` on NTFS. (`Path('a.txt') == Path('A.txt')` is True there.)"""
    source = _file(tmp_path / "a.txt")
    destination = tmp_path / "A.txt"

    assert prepare_destination(source, destination, "move", overwrite=False) is None


@pytest.mark.skipif(os.name != "nt", reason="case-insensitive filesystem semantics of Windows")
def test_prepare_destination_case_only_copy_on_windows_is_refused(tmp_path: Path) -> None:
    """On NTFS a copy `a.txt` -> `A.txt` is a copy onto itself."""
    source = _file(tmp_path / "a.txt")

    with pytest.raises(ParamError):
        prepare_destination(source, tmp_path / "A.txt", "copy", overwrite=True)


# ----------------------------------------------------------------------
# Failures of the disk checks
# ----------------------------------------------------------------------

def test_prepare_destination_refused_existence_check_is_an_access_error(tmp_path: Path, monkeypatch) -> None:
    """When the OS refuses even the checks, an AccessError card is raised."""
    source = _file(tmp_path / "source.txt")

    def refusing_lexists(path):
        raise PermissionError("denied")

    monkeypatch.setattr(MODULE, "os", SimpleNamespace(path=SimpleNamespace(lexists=refusing_lexists)))

    with pytest.raises(AccessError) as info:
        prepare_destination(source, tmp_path / "destination.txt", "copy", overwrite=True)

    assert info.value.error_name == "FILE_COPY_FAILED"
    assert isinstance(info.value, PermissionError)


def test_prepare_destination_failing_samefile_is_treated_as_a_different_file(tmp_path: Path, monkeypatch) -> None:
    """A samefile() problem is not a reason to refuse."""
    source = _file(tmp_path / "source.txt")
    destination = _file(tmp_path / "destination.txt")

    def failing_samefile(a, b):
        raise OSError("cannot compare")

    monkeypatch.setattr(
        MODULE, "os", SimpleNamespace(path=SimpleNamespace(lexists=lambda path: True, samefile=failing_samefile)),
    )

    assert prepare_destination(source, destination, "copy", overwrite=True) is None
