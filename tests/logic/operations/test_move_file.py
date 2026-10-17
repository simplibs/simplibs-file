import errno
import importlib
import inspect
import os
from pathlib import Path
import pytest
from simplibs.exception import AccessError, AlreadyExistsError, NotFoundError, ParamError, StateError
from simplibs.file.logic.operations import move_file

MODULE = importlib.import_module("simplibs.file.logic.operations.move_file")
ACROSS = importlib.import_module("simplibs.file.logic.operations._helpers.move_across_devices")


def _file(path: Path, data: bytes = b"content") -> Path:
    path.write_bytes(data)
    return path


def _drafts(folder: Path) -> list[Path]:
    return sorted(folder.glob(".*.draft"))


def _symlink_or_skip(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available here")


def _cross_device_replace(source, destination, **kwargs):
    """What os.replace does between two devices."""
    raise OSError(errno.EXDEV, "Invalid cross-device link")


# ----------------------------------------------------------------------
# Moving and renaming
# ----------------------------------------------------------------------

def test_move_file_renames_in_the_same_folder(tmp_path: Path) -> None:
    """The content appears under the new name; the old name is gone."""
    source = _file(tmp_path / "old.txt", b"data")

    move_file(source, tmp_path / "new.txt")

    assert (tmp_path / "new.txt").read_bytes() == b"data"
    assert not source.exists()


def test_move_file_moves_to_another_folder_creating_it(tmp_path: Path) -> None:
    """The destination's folder is guaranteed."""
    source = _file(tmp_path / "a.txt", b"data")

    move_file(source, tmp_path / "x" / "y" / "a.txt")

    assert (tmp_path / "x" / "y" / "a.txt").read_bytes() == b"data"
    assert not source.exists()


def test_move_file_returns_the_normalized_destination(tmp_path: Path) -> None:
    """The result is the absolute destination path."""
    source = _file(tmp_path / "a.txt")

    result = move_file(source, tmp_path / "b.txt")

    assert isinstance(result, Path)
    assert result == tmp_path.resolve() / "b.txt"


def test_move_file_accepts_string_paths(tmp_path: Path) -> None:
    """str paths work like Paths."""
    source = _file(tmp_path / "a.txt")

    move_file(str(source), str(tmp_path / "b.txt"))

    assert (tmp_path / "b.txt").exists()


def test_move_file_keeps_the_modification_time(tmp_path: Path) -> None:
    """A rename keeps the file's metadata."""
    source = _file(tmp_path / "a.txt")
    os.utime(source, (1_600_000_000, 1_600_000_000))

    move_file(source, tmp_path / "b.txt")

    assert int((tmp_path / "b.txt").stat().st_mtime) == 1_600_000_000


def test_move_file_has_no_sync_parameter() -> None:
    """A same-device rename has no data to flush; the parameter would promise more than it can keep."""
    assert "sync" not in inspect.signature(move_file).parameters


# ----------------------------------------------------------------------
# overwrite
# ----------------------------------------------------------------------

def test_move_file_default_refuses_an_existing_destination(tmp_path: Path) -> None:
    """overwrite defaults to False — both files stay untouched."""
    source = _file(tmp_path / "a.txt", b"source")
    destination = _file(tmp_path / "b.txt", b"destination")

    with pytest.raises(AlreadyExistsError) as info:
        move_file(source, destination)

    assert info.value.error_name == "FILE_MOVE_DESTINATION_EXISTS"
    assert source.read_bytes() == b"source"
    assert destination.read_bytes() == b"destination"


def test_move_file_overwrite_replaces_an_existing_destination(tmp_path: Path) -> None:
    """overwrite=True replaces it in one atomic rename."""
    source = _file(tmp_path / "a.txt", b"source")
    destination = _file(tmp_path / "b.txt", b"destination that is longer")

    move_file(source, destination, overwrite=True)

    assert destination.read_bytes() == b"source"
    assert not source.exists()


# ----------------------------------------------------------------------
# Entry semantics
# ----------------------------------------------------------------------

def test_move_file_moves_a_symlink_as_a_link(tmp_path: Path) -> None:
    """The old version moved the TARGET."""
    real = _file(tmp_path / "real.txt", b"precious")
    link = tmp_path / "link.txt"
    _symlink_or_skip(link, real)

    move_file(link, tmp_path / "moved_link.txt")

    assert (tmp_path / "moved_link.txt").is_symlink()
    assert not link.is_symlink()
    assert real.read_bytes() == b"precious"


def test_move_file_moves_a_dangling_symlink(tmp_path: Path) -> None:
    """A link to nothing is a perfectly movable entry."""
    link = tmp_path / "dangling.txt"
    _symlink_or_skip(link, tmp_path / "gone.txt")

    move_file(link, tmp_path / "moved.txt")

    assert (tmp_path / "moved.txt").is_symlink()
    assert not link.is_symlink()


# ----------------------------------------------------------------------
# Refusals
# ----------------------------------------------------------------------

def test_move_file_missing_source_raises_not_found(tmp_path: Path) -> None:
    """A missing source is NotFoundError."""
    with pytest.raises(NotFoundError) as info:
        move_file(tmp_path / "missing.txt", tmp_path / "b.txt")

    assert info.value.error_name == "FILE_MOVE_NOT_FOUND"
    assert not (tmp_path / "b.txt").exists()


def test_move_file_directory_as_source_is_a_state_error(tmp_path: Path) -> None:
    """A directory is a clear card."""
    folder = tmp_path / "folder"
    folder.mkdir()

    with pytest.raises(StateError) as info:
        move_file(folder, tmp_path / "b.txt")

    assert info.value.error_name == "FILE_MOVE_NOT_A_FILE"
    assert folder.is_dir()


@pytest.mark.parametrize("overwrite", [True, False])
def test_move_file_directory_as_destination_is_a_state_error(tmp_path: Path, overwrite) -> None:
    """A directory can never be replaced by a file."""
    source = _file(tmp_path / "a.txt")
    folder = tmp_path / "folder"
    folder.mkdir()

    with pytest.raises(StateError) as info:
        move_file(source, folder, overwrite=overwrite)

    assert info.value.error_name == "FILE_MOVE_DESTINATION_IS_DIRECTORY"
    assert source.exists()


def test_move_file_onto_itself_is_refused(tmp_path: Path) -> None:
    """Same path: nothing happens to the file."""
    source = _file(tmp_path / "a.txt", b"precious")

    with pytest.raises(ParamError) as info:
        move_file(source, source, overwrite=True)

    assert info.value.error_name == "FILE_MOVE_SAME_FILE"
    assert source.read_bytes() == b"precious"


def test_move_file_onto_a_hard_link_of_itself_is_refused(tmp_path: Path) -> None:
    """Another name of the same file is the same file."""
    source = _file(tmp_path / "a.txt", b"precious")
    alias = tmp_path / "alias.txt"
    try:
        os.link(source, alias)
    except (OSError, NotImplementedError):
        pytest.skip("hard links are not available here")

    with pytest.raises(ParamError):
        move_file(source, alias, overwrite=True)

    assert source.read_bytes() == b"precious"


@pytest.mark.skipif(os.name != "nt", reason="case-insensitive filesystem semantics of Windows")
def test_move_file_case_only_rename_on_windows(tmp_path: Path) -> None:
    """`a.txt` -> `A.txt` is the same file on NTFS, yet a valid rename."""
    source = _file(tmp_path / "a.txt", b"data")

    move_file(source, tmp_path / "A.txt")

    assert [item.name for item in tmp_path.iterdir()] == ["A.txt"]


# ----------------------------------------------------------------------
# Across devices
# ----------------------------------------------------------------------

def test_move_file_falls_back_to_copy_and_delete_across_devices(tmp_path: Path, monkeypatch) -> None:
    """`os.replace` cannot cross filesystems — that is a signal, not a failure."""
    source = _file(tmp_path / "a.txt", b"data")
    monkeypatch.setattr(MODULE, "replace_with_retry", _cross_device_replace)

    result = move_file(source, tmp_path / "other" / "a.txt")

    assert result == tmp_path.resolve() / "other" / "a.txt"
    assert (tmp_path / "other" / "a.txt").read_bytes() == b"data"
    assert not source.exists()
    assert _drafts(tmp_path / "other") == []


def test_move_file_cross_device_fallback_keeps_the_modification_time(tmp_path: Path, monkeypatch) -> None:
    """The atomic copy carries the metadata."""
    source = _file(tmp_path / "a.txt")
    os.utime(source, (1_600_000_000, 1_600_000_000))
    monkeypatch.setattr(MODULE, "replace_with_retry", _cross_device_replace)

    move_file(source, tmp_path / "b.txt")

    assert int((tmp_path / "b.txt").stat().st_mtime) == 1_600_000_000


def test_move_file_cross_device_fallback_overwrites_when_allowed(tmp_path: Path, monkeypatch) -> None:
    """overwrite=True applies to the fallback too."""
    source = _file(tmp_path / "a.txt", b"new")
    destination = _file(tmp_path / "b.txt", b"old content that is longer")
    monkeypatch.setattr(MODULE, "replace_with_retry", _cross_device_replace)

    move_file(source, destination, overwrite=True)

    assert destination.read_bytes() == b"new"
    assert not source.exists()


def test_move_file_cross_device_failed_copy_keeps_the_source(tmp_path: Path, monkeypatch) -> None:
    """A failure at any point leaves at least one complete file."""
    source = _file(tmp_path / "a.txt", b"precious")
    monkeypatch.setattr(MODULE, "replace_with_retry", _cross_device_replace)

    def failing_copy(src, dst, *, sync=False):
        raise OSError("disk full")

    monkeypatch.setattr(ACROSS, "copy_atomically", failing_copy)

    with pytest.raises(AccessError) as info:
        move_file(source, tmp_path / "b.txt")

    assert info.value.error_name == "FILE_MOVE_FAILED"
    assert source.read_bytes() == b"precious"
    assert not (tmp_path / "b.txt").exists()


def test_move_file_cross_device_symlink_is_refused_with_a_card(tmp_path: Path, monkeypatch) -> None:
    """A link is not silently turned into a regular file on another device."""
    real = _file(tmp_path / "real.txt", b"precious")
    link = tmp_path / "link.txt"
    _symlink_or_skip(link, real)
    monkeypatch.setattr(MODULE, "replace_with_retry", _cross_device_replace)

    with pytest.raises(AccessError) as info:
        move_file(link, tmp_path / "moved.txt")

    assert info.value.error_name == "FILE_MOVE_FAILED"
    assert link.is_symlink()
    assert not (tmp_path / "moved.txt").exists()


def test_move_file_other_os_failure_is_a_card_and_does_not_start_the_fallback(tmp_path: Path, monkeypatch) -> None:
    """Anything but "different device" is a real failure."""
    source = _file(tmp_path / "a.txt", b"precious")
    fallback_calls: list[tuple] = []

    def refusing_replace(src, dst, **kwargs):
        raise PermissionError("denied")

    monkeypatch.setattr(MODULE, "replace_with_retry", refusing_replace)
    monkeypatch.setattr(MODULE, "move_across_devices", lambda *args, **kwargs: fallback_calls.append(args))

    with pytest.raises(AccessError) as info:
        move_file(source, tmp_path / "b.txt")

    assert info.value.error_name == "FILE_MOVE_FAILED"
    assert isinstance(info.value, PermissionError)
    assert fallback_calls == []
    assert source.read_bytes() == b"precious"


def test_move_file_unremovable_source_after_a_cross_device_copy_is_a_card(tmp_path: Path, monkeypatch) -> None:
    """Worst case: both files exist, none is lost."""
    source = _file(tmp_path / "a.txt", b"precious")
    monkeypatch.setattr(MODULE, "replace_with_retry", _cross_device_replace)
    original_unlink = Path.unlink

    def refusing_unlink(self, *args, **kwargs):
        if self.name == "a.txt":
            raise PermissionError("locked")
        return original_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", refusing_unlink)

    with pytest.raises(AccessError) as info:
        move_file(source, tmp_path / "b.txt")

    assert info.value.error_name == "FILE_MOVE_FAILED"
    assert source.read_bytes() == b"precious"
    assert (tmp_path / "b.txt").read_bytes() == b"precious"
